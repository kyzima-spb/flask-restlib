from __future__ import annotations
import typing as t

from flask import current_app
import marshmallow as ma
from marshmallow import fields, validates
from marshmallow.types import StrSequenceOrSet

from . import validators
from .globals import authorization_server
from .oauth2.authorization_server import (
    get_authentication_methods,
    get_response_types
)


__all__ = (
    'RestlibMixin',
    'RestlibSchemaOpts',
    'RestlibSchema',
    'ClientSchema',
)


class RestlibMixin:
    class Opts:
        def __init__(self, meta: object, *args: t.Any, **kwargs: t.Any) -> None:
            # self.links = getattr(meta, 'links', {})
            self._dump_only: StrSequenceOrSet = ()
            self._load_only: StrSequenceOrSet = ()
            super().__init__(meta, *args, **kwargs)  # type: ignore

        @property
        def dump_only(self) -> set[str]:
            config = current_app.config
            dump_only = {
                config['RESTLIB_ID_FIELD'],
                config['RESTLIB_CREATED_FIELD'],
                config['RESTLIB_UPDATED_FIELD'],
            }
            dump_only.update(config['RESTLIB_DUMP_ONLY'])
            dump_only.update(self._dump_only)
            return dump_only

        @dump_only.setter
        def dump_only(self, value: StrSequenceOrSet) -> None:
            self._dump_only = value

        @property
        def load_only(self) -> set[str]:
            load_only = set()
            load_only.update(current_app.config['RESTLIB_LOAD_ONLY'])
            load_only.update(self._load_only)
            return load_only

        @load_only.setter
        def load_only(self, value: StrSequenceOrSet) -> None:
            self._load_only = value


class RestlibSchemaOpts(RestlibMixin.Opts, ma.SchemaOpts):
    pass


class RestlibSchema(ma.Schema):
    OPTIONS_CLASS = RestlibSchemaOpts


class ClientMetadataSchema(ma.Schema):
    client_name = fields.String(
        required=True,
        validate=validators.Length(min=1)
    )
    client_description = fields.String()
    grant_types = fields.List(
        fields.String,
        required=True,
        validate=validators.Length(min=1)
    )
    token_endpoint_auth_method = fields.String()
    redirect_uris = fields.List(
        fields.String(
            validate=validators.URL()
        )
    )
    scope = fields.String()
    client_uri = fields.Url()
    logo_uri = fields.Url()
    contacts = fields.List(
        fields.String(
            validate=validators.Length(min=1)
        )
    )
    tos_uri = fields.Url()
    policy_uri = fields.Url()
    # jwks_uri = fields.Url()
    # jwks = fields.List(fields.String)
    # software_id = fields.String()
    # software_version = fields.String()


class ClientSchema(ma.Schema):
    class Meta:
        load_only = {'is_public', 'client_secret'}

    is_public = fields.Boolean(required=True)
    client_id = fields.String(
        validate=validators.Length(max=48)
    )
    client_secret = fields.String(
        validate=validators.Length(max=120)
    )
    client_metadata = fields.Nested(
        ClientMetadataSchema,
        required=True,
    )

    @validates('client_id')
    def validate_client_id(self, client_id):
        entity = self.context.get('resource')
        v = validators.UniqueEntity(authorization_server.OAuth2Client, 'id', entity)
        v(client_id)

    @ma.post_load
    def post_validate(self, in_data, **kwargs):
        is_public = in_data['is_public']
        metadata = in_data['client_metadata']

        if is_public:
            if 'client_secret' in in_data:
                raise validators.ValidationError({
                    'client_secret': [
                        'For public clients it is not possible to set the client_secret.',
                    ],
                })

            if 'token_endpoint_auth_method' in metadata:
                raise validators.ValidationError({'client_metadata': {
                    'token_endpoint_auth_method': [
                        'Public clients do not require authentication.'
                    ],
                }})

        allowed_grants = authorization_server.get_registered_grants(
            only_public=is_public,
            only_confidential=not is_public
        ).values()
        allowed_grant_types = {g.GRANT_TYPE for g in allowed_grants}
        grants = [g for g in allowed_grants if g.GRANT_TYPE in metadata['grant_types']]

        if set(metadata['grant_types']) - allowed_grant_types:
            raise validators.ValidationError({'client_metadata': {
                'grant_types': [
                    f'Must be one of: {", ".join(allowed_grant_types)}.',
                ],
            }})

        if not is_public:
            allowed_auth_methods = get_authentication_methods(grants)
            if metadata.get('token_endpoint_auth_method') not in allowed_auth_methods:
                raise validators.ValidationError({'client_metadata': {
                    'token_endpoint_auth_method': [
                        f'Must be one of: {", ".join(allowed_auth_methods)}.',
                    ],
                }})

        metadata['response_types'] = get_response_types(grants)

        if metadata['response_types'] and not metadata.get('redirect_uris'):
            raise validators.ValidationError({'client_metadata': {
                'redirect_uris': ['Required field.'],
            }})

        if not metadata['response_types'] and 'redirect_uris' in metadata:
            raise validators.ValidationError({'client_metadata': {
                'redirect_uris': ['Unknown field.'],
            }})

        return in_data
