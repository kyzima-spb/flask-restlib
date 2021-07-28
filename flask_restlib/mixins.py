from __future__ import annotations
from datetime import datetime
import time
import typing as t

from authlib.oauth2.rfc6749 import (
    AuthorizationCodeMixin as _AuthorizationCodeMixin,
    ClientMixin as _ClientMixin,
    TokenMixin as _TokenMixin
)
from authlib.oauth2.rfc6749.util import scope_to_list, list_to_scope
from flask import request, abort, current_app
from flask.typing import ResponseReturnValue, HeadersValue
from webargs import fields
from webargs import validate as validators
from webargs.flaskparser import parser
from werkzeug.datastructures import Headers

from flask_login import UserMixin as _UserMixin
from flask_restlib.pagination import TPagination
from flask_restlib.utils import strip_sorting_flag, current_restlib
from flask_restlib.types import (
    TIdentifier,
    TQueryAdapter,
    THttpHeaders
)


__all__ = (
    'CreateMixin', 'CreateViewMixin',
    'DestroyMixin', 'DestroyViewMixin',
    'ListMixin', 'ListViewMixin',
    'RetrieveMixin', 'RetrieveViewMixin',
    'UpdateMixin', 'UpdateViewMixin',
    'AuthorizationCodeMixin', 'ClientMixin', 'TokenMixin', 'UserMixin',
)


class CreateMixin:
    """A mixin to add a new resource to the collection."""

    def get_creation_headers(self, data) -> HeadersValue:
        """Returns HTTP headers on successful resource creation."""
        headers = Headers()
        resource_url = data.get('_links', {}).get('self')

        if resource_url:
            headers.add('Location', resource_url)

        return headers

    def create(self) -> ResponseReturnValue:
        schema = self.create_schema() # type: ignore
        data = parser.parse(schema, location='json_or_form')

        with self.create_resource_manager() as rm: # type: ignore
            resource = rm.create(self.get_model_class(), data) # type: ignore

        data = schema.dump(resource)
        return data, 201, self.get_creation_headers(data)


class DestroyMixin:
    """A mixin for removing a resource from a collection."""

    def destroy(self, identifier: TIdentifier) -> ResponseReturnValue:
        resource = self.get_for_update(identifier) # type: ignore

        with self.create_resource_manager() as rm: # type: ignore
            rm.delete(resource)

        return '', 204


class ListMixin:
    """
    Mixin for getting all resources from the collection.

    Attributes:
        filter_instance:
            ...
        search_instance:
            ...
        sort_param_name (str):
            The name of the URL parameter that is used for sorting.
        sorting_fields (tuple):
            The names of the attributes of the model to be sorted.
        pagination_instance:
            An instance of the paginator.
    """

    filter_instance = None
    search_instance = None
    pagination_instance: t.ClassVar = None
    sort_param_name = None
    sorting_fields = ()

    def _get_sort(self):
        def validate(v):
            validator = validators.OneOf(self.sorting_fields)
            validator(strip_sorting_flag(v))

        sort_param_name = self.sort_param_name or current_app.config['RESTLIB_URL_PARAM_SORT']
        sort_schema = {
            sort_param_name: fields.DelimitedList(
                fields.String(validate=validate)
            )
        }

        return parser.parse(sort_schema, location='query').get('sort')

    def get_pagination(self) -> TPagination:
        """Returns an instance of the paginator."""
        if self.pagination_instance is None:
            return current_restlib.pagination_instance
        return self.pagination_instance

    def list(self) -> ResponseReturnValue:
        q: TQueryAdapter = self.create_queryset() # type: ignore
        headers: THttpHeaders = []

        if self.filter_instance is not None:
            q.filter(self.filter_instance)

        if self.search_instance is not None:
            q.filter(self.search_instance)

        if current_app.config['RESTLIB_SORTING_ENABLED']:
            sort = self._get_sort()
            if sort:
                q.order_by(*sort)

        if current_app.config['RESTLIB_PAGINATION_ENABLED']:
            pagination = self.get_pagination()
            q, pagination_headers = pagination(q, request.url)
            headers.extend(pagination_headers)

        return self.create_schema(many=True).dump(q) # type: ignore


class RetrieveMixin:
    """Mixin to get one resource from a collection"""

    def retrieve(self, identifier: TIdentifier) -> ResponseReturnValue:
        return self.create_schema().dump(  # type: ignore
            self.get_or_404(identifier)  # type: ignore
        )


class UpdateMixin:
    """A mixin for editing a resource in a collection."""

    def update(self, identifier: TIdentifier) -> ResponseReturnValue:
        resource = self.get_for_update(identifier) # type: ignore

        schema = self.create_schema() # type: ignore
        schema.context['resource'] = resource
        data = parser.parse(schema, location='json_or_form')

        with self.create_resource_manager() as rm: # type: ignore
            resource = rm.update(resource, data)

        return schema.dump(resource)


class CreateViewMixin(CreateMixin):
    def post(self) -> ResponseReturnValue:
        return self.create()


class DestroyViewMixin(DestroyMixin):
    lookup_names = ('id',)

    def delete(self, id: TIdentifier) -> ResponseReturnValue:
        return self.destroy(id)


class ListViewMixin(ListMixin):
    def get(self) -> ResponseReturnValue:
        return self.list()


class RetrieveViewMixin(RetrieveMixin):
    lookup_names = ('id',)

    def get(self, id: TIdentifier) -> ResponseReturnValue:
        return self.retrieve(id)


class UpdateViewMixin(UpdateMixin):
    lookup_names = ('id',)

    def put(self, id: TIdentifier) -> ResponseReturnValue:
        return self.update(id)


# OAuth2 Mixins


AuthorizationCodeType = t.TypeVar('AuthorizationCodeType', bound=_AuthorizationCodeMixin)
ClientType = t.TypeVar('ClientType', bound=_ClientMixin)
TokenType = t.TypeVar('TokenType', bound='TokenMixin')
UserType = t.TypeVar('UserType', bound='UserMixin')


class AuthorizationCodeMixin(_AuthorizationCodeMixin):
    def is_expired(self) -> bool:
        return self.auth_time + 300 < time.time()

    def get_redirect_uri(self) -> str:
        return self.redirect_uri

    def get_scope(self) -> str:
        return self.scope

    def get_auth_time(self) -> int:
        return self.auth_time

    def get_nonce(self) -> str:
        return self.nonce


class ClientMixin(_ClientMixin):
    @property
    def client_info(self) -> dict[str, t.Any]:
        """
        Implementation for Client Info in OAuth 2.0 Dynamic Client Registration Protocol via `Section 3.2.1`_.

        .. _`Section 3.2.1`: https://tools.ietf.org/html/rfc7591#section-3.2.1
        """
        return dict(
            client_id=self.client_id,
            client_secret=self.client_secret,
            client_id_issued_at=self.client_id_issued_at,
            client_secret_expires_at=self.client_secret_expires_at,
        )

    @property
    def redirect_uris(self) -> list[str]:
        """
        Array of redirection URI strings for use in redirect-based flows
        such as the authorization code and implicit flows.

        As required by `Section 2`_ of OAuth 2.0 [RFC6749],
        clients using flows with redirection MUST register their redirection URI values.

        Authorization servers that support dynamic registration
        for redirect-based flows MUST implement support for this metadata value.

        .. _`Section 2`: https://tools.ietf.org/html/rfc7591#section-2
        """
        return self.client_metadata.get('redirect_uris', [])

    @property
    def token_endpoint_auth_method(self) -> str:
        """
        String indicator of the requested authentication method for the token endpoint.

        Values defined by this specification are:

        * "none": The client is a public client as defined in OAuth 2.0,
          `Section 2.1`_, and does not have a client secret.

        *  "client_secret_post": The client uses the HTTP POST parameters as defined in OAuth 2.0, `Section 2.3.1`_.

        *  "client_secret_basic": The client uses HTTP Basic as defined in OAuth 2.0, `Section 2.3.1`_.

        Additional values can be defined via the IANA "OAuth Token Endpoint Authentication Methods"
        registry established in `Section 4.2`_.
        Absolute URIs can also be used as values for this parameter without being registered.
        If unspecified or omitted, the default is "client_secret_basic",
        denoting the HTTP Basic authentication scheme as specified in `Section 2.3.1`_ of OAuth 2.0.

        .. _`Section 2.1`: https://tools.ietf.org/html/rfc7591#section-2.1
        .. _`Section 2.3.1`: https://tools.ietf.org/html/rfc7591#section-2.3.1
        .. _`Section 4.2`: https://tools.ietf.org/html/rfc7591#section-4.2
        """
        return self.client_metadata.get(
            'token_endpoint_auth_method',
            'client_secret_basic'
        )

    @property
    def grant_types(self) -> list[str]:
        """
        Array of OAuth 2.0 grant type strings that the client can use at the token endpoint.
        """
        return self.client_metadata.get('grant_types', [])

    @property
    def response_types(self) -> list[str]:
        """
        Array of the OAuth 2.0 response type strings that the client can use at the authorization endpoint.
        """
        return self.client_metadata.get('response_types', [])

    @property
    def client_name(self) -> t.Optional[str]:
        """
        Human-readable string name of the client to be presented to the end-user during authorization.

        If omitted, the authorization server MAY display the raw "client_id" value to the end-user instead.
        It is RECOMMENDED that clients always send this field.

        The value of this field MAY be internationalized, as described in `Section 2.2`_.

        .. _`Section 2.2`: https://tools.ietf.org/html/rfc7591#section-2.2
        """
        return self.client_metadata.get('client_name')

    @property
    def client_uri(self) -> t.Optional[str]:
        """
        URL string of a web page providing information about the client.

        If present, the server SHOULD display this URL to the end-user in a clickable fashion.
        It is RECOMMENDED that clients always send this field.
        The value of this field MUST point to a valid web page.
        The value of this field MAY be internationalized, as described in `Section 2.2`_.

        .. _`Section 2.2`: https://tools.ietf.org/html/rfc7591#section-2.2
        """
        return self.client_metadata.get('client_uri')

    @property
    def logo_uri(self) -> t.Optional[str]:
        """
        URL string that references a logo for the client.

        If present, the server SHOULD display this image to the end-user during approval.
        The value of this field MUST point to a valid image file.
        The value of this field MAY be internationalized, as described in `Section 2.2`_.

        .. _`Section 2.2`: https://tools.ietf.org/html/rfc7591#section-2.2
        """
        return self.client_metadata.get('logo_uri')

    @property
    def scope(self) -> str:
        """
        String containing a space-separated list of scope values
        (as described in `Section 3.3`_ of OAuth 2.0 [RFC6749])
        that the client can use when requesting access tokens.

        The semantics of values in this list are service specific.
        If omitted, an authorization server MAY register a client with a default set of scopes.

        .. _`Section 3.3`: https://tools.ietf.org/html/rfc7591#section-3.3
        """
        return self.client_metadata.get('scope', '')

    @property
    def contacts(self) -> list[str]:
        """
        Array of strings representing ways to contact people responsible for this client, typically email addresses.

        The authorization server MAY make these contact addresses
        available to end-users for support requests for the client.
        See `Section 6`_ for information on Privacy Considerations.

        .. _`Section 6`: https://tools.ietf.org/html/rfc7591#section-6
        """
        return self.client_metadata.get('contacts', [])

    @property
    def tos_uri(self) -> t.Optional[str]:
        """
        URL string that points to a human-readable terms of service document
        for the client that describes a contractual relationship
        between the end-user and the client
        that the end-user accepts when authorizing the client.

        The authorization server SHOULD display this URL to the end-user if it is provided.
        The value of this field MUST point to a valid web page.
        The value of this field MAY be internationalized, as described in `Section 2.2`_.

        .. _`Section 2.2`: https://tools.ietf.org/html/rfc7591#section-2.2
        """
        return self.client_metadata.get('tos_uri')

    @property
    def policy_uri(self) -> t.Optional[str]:
        """
        URL string that points to a human-readable privacy policy document that describes
        how the deployment organization collects, uses, retains, and discloses personal data.

        The authorization server SHOULD display this URL to the end-user if it is provided.
        The value of this field MUST point to a valid web page.
        The value of this field MAY be internationalized, as described in `Section 2.2`_.

        .. _`Section 2.2`: https://tools.ietf.org/html/rfc7591#section-2.2
        """
        return self.client_metadata.get('policy_uri')

    @property
    def jwks_uri(self) -> t.Optional[str]:
        """
        URL string referencing the client's JSON Web Key (JWK) Set [RFC7517] document,
        which contains the client's public keys.

        The value of this field MUST point to a valid JWK Set document.
        These keys can be used by higher-level protocols that use signing or encryption.
        For instance, these keys might be used by some applications
        for validating signed requests made to the token endpoint
        when using JWTs for client authentication [RFC7523].
        Use of this parameter is preferred over the "jwks" parameter, as it allows for easier key rotation.
        The "jwks_uri" and "jwks" parameters MUST NOT both be present in the same request or response.
        """
        return self.client_metadata.get('jwks_uri')

    @property
    def jwks(self) -> list:
        """
        Client's JSON Web Key Set [RFC7517] document value,
        which contains the client's public keys.

        The value of this field MUST be a JSON object containing a valid JWK Set.
        These keys can be used by higher-level protocols that use signing or encryption.
        This parameter is intended to be used by clients that cannot use the "jwks_uri" parameter,
        such as native clients that cannot host public URLs.
        The "jwks_uri" and "jwks" parameters MUST NOT both be present in the same request or response.
        """
        return self.client_metadata.get('jwks', [])

    @property
    def software_id(self) -> t.Optional[str]:
        return self.client_metadata.get('software_id')

    @property
    def software_version(self) -> t.Optional[str]:
        return self.client_metadata.get('software_version')

    @property
    def client_id(self) -> str:
        return str(self.id)

    def get_client_id(self) -> str:
        return self.client_id

    def get_default_redirect_uri(self) -> t.Optional[str]:
        if not self.redirect_uris:
            return None
        return self.redirect_uris[0]

    def get_allowed_scope(self, scope: str) -> str:
        if not scope:
            return ''
        allowed = set(self.scope.split())
        scopes = set(scope_to_list(scope))
        return list_to_scope(allowed & scopes)

    def check_redirect_uri(self, redirect_uri: str) -> bool:
        return redirect_uri in self.redirect_uris

    def has_client_secret(self) -> bool:
        return bool(self.client_secret)

    def check_client_secret(self, client_secret: str) -> bool:
        return self.client_secret == client_secret

    def check_token_endpoint_auth_method(self, method: str) -> bool:
        return self.token_endpoint_auth_method == method

    def check_response_type(self, response_type: str) -> bool:
        return response_type in self.response_types

    def check_grant_type(self, grant_type: str) -> bool:
        return grant_type in self.grant_types


class TokenMixin(_TokenMixin):
    def get_client_id(self) -> str:
        return self.client.get_client_id()

    def get_scope(self) -> str:
        return self.scope

    def get_expires_in(self) -> int:
        return self.expires_in

    def get_expires_at(self) -> int:
        return self.issued_at + self.expires_in

    def is_refresh_token_valid(self) -> bool:
        """Returns true if the token is not expired, false otherwise."""
        if self.revoked:
            return False
        expires_at = datetime.fromtimestamp(self.get_expires_at())
        return expires_at > datetime.utcnow()


class UserMixin(_UserMixin):
    """A mixin for describing a user."""

    def change_password(self, value: str) -> None:
        """Changes the current password to passed."""
        raise NotImplementedError

    def check_password(self, password: str) -> bool:
        """Returns true if the password is valid, false otherwise."""
        raise NotImplementedError

    @classmethod
    def find_by_username(cls, username: str) -> t.Any:
        """Returns the user with passed username, or None."""
        raise NotImplementedError

    def get_user_id(self) -> t.Any:
        """Returns user id, requires Authlib."""
        return self.get_id()
