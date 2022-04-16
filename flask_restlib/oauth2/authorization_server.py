from __future__ import annotations
from functools import lru_cache
import secrets
import typing as t
from uuid import uuid4

from authlib.integrations.flask_oauth2 import (
    AuthorizationServer as _AuthorizationServer
)
from authlib.oauth2.rfc6749 import grants
from authlib.oauth2.rfc6749.wrappers import OAuth2Request
from authlib.oauth2.rfc6750 import BearerTokenValidator as _BearerTokenValidator
from authlib.oauth2.rfc7636 import CodeChallenge
from flask import (
    Blueprint,
    current_app,
    Flask,
    Request,
)
from flask_login import current_user, LoginManager

from ..exceptions import LogicalError
from ..globals import (
    authorization_server,
    current_restlib,
    query_adapter,
    resource_manager
)
from ..utils import camel_to_list
from .mixins import (
    AuthorizationCodeMixin,
    ClientMixin,
    TokenMixin,
    ScopeMixin,
    UserMixin,
)
from . import views


__all__ = (
    'generate_client_id',
    'generate_client_secret',
    'get_authentication_methods',
    'get_response_types',
    'save_client',
    'validate_client_id',
    'AuthorizationServer',
    'BearerTokenValidator',
)


def generate_client_id(length: int) -> str:
    """Creates and returns a unique client ID of the specified length."""
    while 1:
        client_id = secrets.token_hex(length // 2)

        if validate_client_id(client_id):
            return client_id


def generate_client_secret(length: int) -> str:
    """Generates and returns a client secret key of the specified length."""
    return secrets.token_hex(length // 2)


def get_authentication_methods(grants: list[grants.BaseGrant]) -> set[str]:
    """Returns a list of authentication methods for the given grants."""
    return {
        i for g in grants for i in g.TOKEN_ENDPOINT_AUTH_METHODS if i != 'none'
    }


def get_response_types(grants: list[grants.BaseGrant]) -> list[str]:
    """Returns a list of response types for the given grants."""
    return list({t for g in grants for t in getattr(g, 'RESPONSE_TYPES', ())})


def save_client(
    is_public: bool,
    scopes: list,
    client_metadata: dict,
    client_id: t.Optional[str] = None,
    client_secret: t.Optional[str] = None,
    user: t.Optional[UserMixin] = None
) -> ClientMixin:
    """Saves OAuth client to persistent storage."""
    user = user or current_user

    if not user:
        raise LogicalError('Failed to get the current user.')

    if not client_id:
        n = authorization_server.OAuth2Client.CLIENT_ID_LENGTH
        client_id = generate_client_id(n)

    if not is_public and not client_secret:
        n = authorization_server.OAuth2Client.CLIENT_SECRET_LENGTH
        client_secret = generate_client_secret(n)

    if is_public:
        if client_secret:
            raise LogicalError('For public clients it is not possible to set the client_secret.')

        if client_metadata.get('token_endpoint_auth_method'):
            raise LogicalError('Public clients do not require authentication.')

        client_metadata['token_endpoint_auth_method'] = 'none'

    with resource_manager() as rm:
        client = rm.create(authorization_server.OAuth2Client, {
            'id': client_id,
            'client_secret': client_secret,
            'client_metadata': client_metadata,
            'scopes': scopes,
            'user': user,
        })

    return client


def validate_client_id(client_id: str) -> bool:
    """
    Returns true if the specified client ID is unique, false otherwise.

    Arguments:
        client_id (str): client ID.
    """
    if not client_id:
        return False
    return authorization_server.query_client(client_id) is None


class AuthorizationCodeGrant(grants.AuthorizationCodeGrant):
    TOKEN_ENDPOINT_AUTH_METHODS = ['client_secret_basic', 'client_secret_post', 'none']

    def save_authorization_code(
        self,
        code: str,
        request: OAuth2Request
    ) -> AuthorizationCodeMixin:
        code_challenge = request.data.get('code_challenge')
        code_challenge_method = request.data.get('code_challenge_method')

        if code_challenge_method is None and code_challenge is not None:
            # https://datatracker.ietf.org/doc/html/rfc7636#section-4.3
            code_challenge_method = 'plain'

        with resource_manager() as rm:
            return rm.create(authorization_server.OAuth2Code, {
                'id': uuid4(),
                'code': code,
                'client': request.client,
                'redirect_uri': request.redirect_uri,
                'scope': request.scope,
                'user': request.user._get_current_object(),
                'code_challenge': code_challenge,
                'code_challenge_method': code_challenge_method,
            })

    def query_authorization_code(
        self,
        code: str,
        client: ClientMixin
    ) -> t.Optional[AuthorizationCodeMixin]:
        authorization_code = (
            query_adapter(authorization_server.OAuth2Code)
                .filter_by(code=code, client=client)
                .one_or_none()
        )

        if authorization_code and not authorization_code.is_expired():
            return authorization_code

        if authorization_code:
            self.delete_authorization_code(authorization_code)

        return None

    def delete_authorization_code(
        self,
        authorization_code: AuthorizationCodeMixin
    ) -> None:
        with resource_manager() as rm:
            rm.delete(authorization_code)

    def authenticate_user(
        self,
        authorization_code: AuthorizationCodeMixin
    ) -> UserMixin:
        return authorization_code.get_user()


class PasswordGrant(grants.ResourceOwnerPasswordCredentialsGrant):
    def authenticate_user(
        self,
        username: str,
        password: str
    ) -> t.Optional[UserMixin]:
        user = authorization_server.OAuth2User.find_by_username(username)
        if user and user.check_password(password):
            return user
        return None


class RefreshTokenGrant(grants.RefreshTokenGrant):
    INCLUDE_NEW_REFRESH_TOKEN: t.ClassVar[bool] = True

    def authenticate_refresh_token(
        self,
        refresh_token: str
    ) -> t.Optional[TokenMixin]:
        item = (
            query_adapter(authorization_server.OAuth2Token)
                .filter_by(refresh_token=refresh_token)
                .one_or_none()
        )

        if item and item.is_refresh_token_valid():
            return item

        return None

    def authenticate_user(self, credential: TokenMixin) -> UserMixin:
        return credential.get_user()

    def revoke_old_credential(self, credential: TokenMixin) -> None:
        with resource_manager() as rm:
            rm.update(credential, {
                'access_token_revoked_at': True,
                'refresh_token_revoked_at': True,
            })


class AuthorizationServer(_AuthorizationServer):
    def __init__(
        self,
        app: t.Optional[Flask] = None,
        *,
        user_model: t.Type[UserMixin],
        client_model: t.Type[ClientMixin],
        token_model: t.Type[TokenMixin],
        authorization_code_model: t.Type[AuthorizationCodeMixin],
        query_client: t.Optional[t.Callable] = None,
        query_supported_scopes: t.Optional[t.Callable] = None,
        save_token: t.Optional[t.Callable] = None
    ):
        """
        Arguments:
            app (Flask): Flask application instance that being used.
            user_model: Reference to the User model class.
            client_model: OAuth client model class.
            token_model: OAuth token model class.
            authorization_code_model: OAuth code model class.
            query_client: A function to get client by client_id.
            query_supported_scopes: A function to get supported scopes.
            save_token: A function to save tokens.
        """
        if save_token is None:
            save_token = self._save_token

        if query_client is None:
            query_client = self._query_client

        super().__init__(save_token=save_token, query_client=query_client)

        self._registered_grants: list[t.Type[grants.BaseGrant]] = []
        self._query_supported_scopes = query_supported_scopes

        self.OAuth2User = user_model
        self.OAuth2Client = client_model
        self.OAuth2Token = token_model
        self.OAuth2Code = authorization_code_model

        self.login_manager = LoginManager()
        self.login_manager.user_loader(self._load_user)
        self.login_manager.request_loader(self._load_user_from_request)
        self.login_manager.login_view = 'oauth.login'

        self.index_endpoint = views.IndexView.as_view('index')
        self.login_endpoint = views.LoginView.as_view('login')
        self.logout_endpoint = views.LogoutView.as_view('logout')
        self.authorize_endpoint = views.AuthorizeView.as_view('authorize')
        self.access_token_endpoint = views.AccessTokenView.as_view('access_token')
        self.revoke_token_endpoint = views.RevokeTokenView.as_view('revoke_token')

        self.bp = Blueprint('oauth', __name__, template_folder='../templates')

        if app is not None:
            self.init_app(app)

    def init_app(
        self,
        app: Flask,
        *,
        query_client: t.Optional[t.Callable] = None,
        save_token: t.Optional[t.Callable] = None
    ) -> None:
        app.config.setdefault('RESTLIB_OAUTH2_URL_PREFIX', '/oauth')
        app.config.setdefault('RESTLIB_OAUTH2_AUTHORIZATION_CODE_GRANT', True)
        app.config.setdefault('RESTLIB_OAUTH2_IMPLICIT_GRANT', True)
        app.config.setdefault('RESTLIB_OAUTH2_RESOURCE_OWNER_GRANT', True)
        app.config.setdefault('RESTLIB_OAUTH2_CLIENT_CREDENTIALS_GRANT', True)
        app.config.setdefault('RESTLIB_OAUTH2_REFRESH_TOKEN_GRANT', True)

        if app.config['RESTLIB_OAUTH2_REFRESH_TOKEN_GRANT']:
            app.config.setdefault('OAUTH2_REFRESH_TOKEN_GENERATOR', True)

        super().init_app(app, query_client=query_client, save_token=save_token)

        app.extensions['restlib_oauth2'] = self

        if app.config['RESTLIB_OAUTH2_AUTHORIZATION_CODE_GRANT']:
            self.register_grant(AuthorizationCodeGrant, [CodeChallenge(required=True)])

        if app.config['RESTLIB_OAUTH2_IMPLICIT_GRANT']:
            self.register_grant(grants.ImplicitGrant)

        if app.config['RESTLIB_OAUTH2_RESOURCE_OWNER_GRANT']:
            self.register_grant(PasswordGrant)

        if app.config['RESTLIB_OAUTH2_CLIENT_CREDENTIALS_GRANT']:
            self.register_grant(grants.ClientCredentialsGrant)

        if app.config['RESTLIB_OAUTH2_REFRESH_TOKEN_GRANT']:
            self.register_grant(RefreshTokenGrant)

        self.register_endpoint(views.RevokeTokenEndpoint)

        self.login_manager.init_app(app)

        self.bp.add_url_rule('/', view_func=self.index_endpoint)
        self.bp.add_url_rule('/login', view_func=self.login_endpoint)
        self.bp.add_url_rule('/logout', view_func=self.logout_endpoint)
        self.bp.add_url_rule('/authorize', view_func=self.authorize_endpoint)
        self.bp.add_url_rule('/token', view_func=self.access_token_endpoint)
        self.bp.add_url_rule('/revoke', view_func=self.revoke_token_endpoint)
        app.register_blueprint(self.bp, url_prefix=app.config['RESTLIB_OAUTH2_URL_PREFIX'])

    def _load_user(self, user_id: t.Any) -> t.Optional[UserMixin]:
        """Returns user by user_id."""
        return resource_manager().get(self.OAuth2User, user_id)

    def _load_user_from_request(self, request: Request) -> t.Optional[UserMixin]:
        """Returns user by access token."""
        try:
            token = current_restlib.resource_protector.acquire_token()
            return token.get_user()
        except:
            return None

    def _query_client(self, client_id: str) -> t.Optional[ClientMixin]:
        """Returns client by client_id."""
        return resource_manager().get(self.OAuth2Client, client_id)

    def _save_token(
        self,
        token_data: dict,
        request: OAuth2Request
    ) -> None:
        """Saves tokens to persistent storage."""
        with resource_manager() as rm:
            rm.create(self.OAuth2Token, {
                'id': uuid4(),
                'client': request.client,
                'user': request.user or request.client.get_user(),
                **token_data,
            })

    def generate_token(
        self,
        grant_type: str,
        client: ClientMixin,
        user: t.Optional[UserMixin] = None,
        scope: t.Optional[str] = None,
        expires_in: t.Optional[int] = None,
        include_refresh_token: bool = True
    ) -> dict[str, t.Any]:
        if scope is not None and user is not None:
            current_app.logger.debug(
                f'Generate token for user: {user} with scope: {scope!r}'
            )

            if isinstance(user, ScopeMixin):
                scope = user.get_allowed_scope(scope)

        return super().generate_token(
            grant_type=grant_type,
            client=client,
            user=user,
            scope=scope,
            expires_in=expires_in,
            include_refresh_token=include_refresh_token
        )

    @lru_cache
    def get_registered_grants(
        self,
        *,
        only_public: bool = False,
        only_confidential: bool = False
    ) -> dict[str, t.Type[grants.BaseGrant]]:
        """Returns registered grants."""
        grants = {}

        for grant in self._registered_grants:
            flag = not (only_public ^ only_confidential)
            auth_methods = set(grant.TOKEN_ENDPOINT_AUTH_METHODS)

            if not flag and only_public:
                flag = bool(auth_methods & {'none'})

            if not flag and only_confidential:
                flag = bool(auth_methods ^ {'none'})

            if flag:
                grants[' '.join(camel_to_list(grant.__name__))] = grant

        return grants

    def get_supported_scopes(self) -> set[t.Any]:
        """Returns set of supported scopes by this authorization server."""
        if self._query_supported_scopes is not None:
            return self._query_supported_scopes()
        return set(self.scopes_supported)

    def register_grant(
        self,
        grant_cls: t.Type[grants.BaseGrant],
        extensions: t.Optional[list] = None
    ) -> None:
        """Register a grant class into the endpoint registry."""
        super().register_grant(grant_cls, extensions)
        self._registered_grants.append(grant_cls)


class BearerTokenValidator(_BearerTokenValidator):
    def authenticate_token(self, token_string: str) -> t.Optional[TokenMixin]:
        return (
            query_adapter(authorization_server.OAuth2Token)
                .filter_by(access_token=token_string)
                .first()
        )
