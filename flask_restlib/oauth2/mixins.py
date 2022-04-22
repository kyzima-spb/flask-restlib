from __future__ import annotations
from datetime import datetime
import time
import typing as t

from authlib.oauth2.rfc6749 import (
    AuthorizationCodeMixin as _AuthorizationCodeMixin,
    ClientMixin as _ClientMixin,
    TokenMixin as _TokenMixin,
)
from flask import current_app
from flask_login import UserMixin as _UserMixin

from ..decorators import getattr_or_implement
from ..utils import iter_to_scope, scope_to_set


__all__ = (
    'AuthorizationCodeMixin',
    'ClientMixin',
    'TokenMixin',
    'ScopeMixin',
    'UserMixin',
)


class ScopeMixin:
    """Mixin for entities that use scopes."""

    def get_allowed_scope(self, scope: str) -> str:
        """Returns the allowed scopes from the given scope."""
        if not scope:
            return ''
        return iter_to_scope(
            scope_to_set(self.get_scope()) & scope_to_set(scope)
        )

    @getattr_or_implement
    def get_scope(self) -> str:
        """
        Returns string containing a space-separated list of scope values.

        .. _`Section 3.3`: https://tools.ietf.org/html/rfc7591#section-3.3
        """
        scopes = self.get_scopes()

        if not all(map(lambda i: isinstance(i, str), scopes)):
            import warnings

            warnings.warn(
                'The items of the scopes list are of non-string type. '
                f'Override the `{self.__class__.__name__}.get_scope()` method if necessary.',
                RuntimeWarning
            )

        return iter_to_scope(str(i) for i in scopes)

    @getattr_or_implement
    def get_scopes(self) -> set[t.Any]:
        """Returns list of scope values."""
        return set(getattr(self, 'scopes'))


class AuthorizationCodeMixin(_AuthorizationCodeMixin):
    @getattr_or_implement
    def get_auth_time(self) -> int:
        return getattr(self, 'auth_time')

    @getattr_or_implement
    def get_client(self) -> ClientMixin:
        """Returns the client to which the authorization code was issued."""
        return getattr(self, 'client')

    def is_expired(self) -> bool:
        return self.get_auth_time() + 300 < time.time()

    @getattr_or_implement
    def get_nonce(self) -> str:
        return getattr(self, 'nonce')

    @getattr_or_implement
    def get_redirect_uri(self) -> str:
        return getattr(self, 'redirect_uri')

    @getattr_or_implement
    def get_scope(self) -> str:
        return getattr(self, 'scope')

    @getattr_or_implement
    def get_user(self) -> UserMixin:
        """Returns authorization code owner."""
        return getattr(self, 'user')


class ClientMixin(ScopeMixin, _ClientMixin):
    CLIENT_ID_LENGTH = 48
    CLIENT_SECRET_LENGTH = 120

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
    def client_description(self) -> str:
        return self.client_metadata.get('client_description')

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

    def check_redirect_uri(self, redirect_uri: str) -> bool:
        return redirect_uri in self.redirect_uris

    def has_client_secret(self) -> bool:
        return bool(self.client_secret)

    def check_client_secret(self, client_secret: str) -> bool:
        return self.client_secret == client_secret

    def check_endpoint_auth_method(self, method: str, endpoint: str) -> bool:
        if endpoint == 'token':
            return self.token_endpoint_auth_method == method
        return True

    def check_response_type(self, response_type: str) -> bool:
        return response_type in self.response_types

    def check_grant_type(self, grant_type: str) -> bool:
        return grant_type in self.grant_types

    @getattr_or_implement
    def get_user(self) -> UserMixin:
        """Returns client owner."""
        return getattr(self, 'user')


class TokenMixin(_TokenMixin):
    def check_client(self, client: ClientMixin) -> bool:
        return self.get_client().get_client_id() == client.get_client_id()

    @getattr_or_implement
    def get_access_token(self) -> str:
        """Returns access token string."""
        return getattr(self, 'access_token')

    @getattr_or_implement
    def get_access_token_revoked_at(self) -> int:
        return getattr(self, 'access_token_revoked_at')

    @getattr_or_implement
    def get_client(self) -> ClientMixin:
        """Returns the client to which the token was issued."""
        return getattr(self, 'client')

    def get_expires_at(self) -> int:
        """Returns timestamp indicating when this token will expire."""
        return self.get_issued_at() + self.get_expires_in()

    @getattr_or_implement
    def get_expires_in(self) -> int:
        return getattr(self, 'expires_in')

    @getattr_or_implement
    def get_issued_at(self) -> int:
        return getattr(self, 'issued_at')

    @getattr_or_implement
    def get_refresh_token(self) -> str:
        """Returns refresh token string."""
        return getattr(self, 'refresh_token')

    @getattr_or_implement
    def get_refresh_token_revoked_at(self) -> int:
        return getattr(self, 'refresh_token_revoked_at')

    @getattr_or_implement
    def get_scope(self) -> str:
        return getattr(self, 'scope')

    @getattr_or_implement
    def get_token_type(self) -> str:
        """
        Returns access token type.

        .. https://datatracker.ietf.org/doc/html/rfc6749#section-7.1
        """
        return getattr(self, 'token_type')

    @getattr_or_implement
    def get_user(self) -> UserMixin:
        """Returns token owner."""
        return getattr(self, 'user')

    def is_expired(self) -> bool:
        if not self.get_expires_in():
            return True
        return self.get_expires_at() < time.time()

    def is_refresh_token_valid(self) -> bool:
        """Returns true if the token is not expired, false otherwise."""
        return not (self.is_revoked() or self.is_expired())

    def is_revoked(self) -> bool:
        """Returns true if the token has been revoked, false otherwise."""
        return bool(self.get_access_token_revoked_at() or self.get_refresh_token_revoked_at())


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
