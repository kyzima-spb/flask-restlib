from __future__ import annotations
from itertools import chain
import typing as t

from flask import current_app
import marshmallow as ma
from marshmallow import fields
from marshmallow.types import StrSequenceOrSet

from flask_restlib import validators
from flask_restlib.oauth2 import (
    authorization_server,
    generate_client_id,
    generate_client_secret,
    validate_client_id
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
    description = fields.String(
        missing=''
    )
    grant_types = fields.List(
        fields.String(
            validate=validators.Length(min=1)
        ),
        required=True,
        validate=validators.Length(min=1)
    )
    token_endpoint_auth_method = fields.String(
        required=True,
        validate=validators.Length(min=1)
    )
    redirect_uris = fields.List(
        fields.String(
            validate=validators.URL()
        ),
        missing=[]
    )
    scope = fields.String(
        missing=''
    )
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
    is_public = fields.Boolean(required=True)
    id = fields.String(
        missing='',
        validate=validators.Length(max=48)
    )
    client_secret = fields.String(
        missing='',
        validate=validators.Length(max=120)
    )
    client_metadata = fields.Nested(
        ClientMetadataSchema,
        required=True,
    )

    @ma.post_load
    def post_validate(self, in_data, **kwargs):
        is_public = in_data.pop('is_public')

        if is_public and in_data['client_secret']:
            raise validators.ValidationError({
                'client_secret': [
                    'For public clients it is not possible to set the client_secret.',
                ],
            })

        if in_data['id']:
            if not validate_client_id(in_data['id']):
                raise validators.ValidationError({
                    'id': ['Client ID already exists.']
                })
        else: # fixme: need factory
            length = self.fields['id'].validate.max
            in_data['id'] = generate_client_id(length)

        if not is_public and not in_data['client_secret']: # fixme: need factory
            length = self.fields['client_secret'].validate.max
            in_data['client_secret'] = generate_client_secret(length)

        metadata = in_data['client_metadata']
        grants = authorization_server.get_registered_grants(
            only_public=is_public,
            only_confidential=not is_public
        ).values()

        allowed_grant_types = {g.GRANT_TYPE for g in grants}
        unknown_grant_types = set(metadata['grant_types']) - allowed_grant_types
        if unknown_grant_types:
            raise validators.ValidationError({'client_metadata': {
                'grant_types': [
                    f'Must be one of: {", ".join(allowed_grant_types)}.',
                ],
            }})

        grants = [
            g for g in grants if g.GRANT_TYPE in metadata['grant_types']
        ]

        if is_public:
            if metadata['token_endpoint_auth_method'] != 'none':
                raise validators.ValidationError({'client_metadata': {
                    'token_endpoint_auth_method': [
                        'Only none is allowed for public clients.'
                    ],
                }})
        else:
            allowed_auth_methods = set(
                i for grant in grants for i in grant.TOKEN_ENDPOINT_AUTH_METHODS if i != 'none'
            )
            if metadata['token_endpoint_auth_method'] not in allowed_auth_methods:
                raise validators.ValidationError({'client_metadata': {
                    'token_endpoint_auth_method': [
                        f'Must be one of: {", ".join(allowed_auth_methods)}.',
                    ],
                }})

        metadata['response_types'] = list(set(chain.from_iterable(
            getattr(g, 'RESPONSE_TYPES', ()) for g in grants
        )))

        if metadata['response_types'] and not metadata['redirect_uris']:
            raise validators.ValidationError({'client_metadata': {
                'redirect_uris': ['Is required field.'],
            }})

        if not metadata['response_types'] and metadata['redirect_uris']:
            raise validators.ValidationError({'client_metadata': {
                'redirect_uris': ['The field must be empty.'],
            }})

        return in_data
