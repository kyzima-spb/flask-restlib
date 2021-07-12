from __future__ import annotations
import secrets
import typing
import typing as t
from typing import ClassVar, Optional
from uuid import uuid4

from authlib.oauth2 import OAuth2Error
from authlib.integrations.flask_oauth2 import (
    AuthorizationServer as _AuthorizationServer
)
from authlib.oauth2.rfc6749 import grants
from authlib.oauth2.rfc6749.wrappers import OAuth2Request
from authlib.oauth2.rfc6750 import BearerTokenValidator as _BearerTokenValidator
from authlib.oauth2.rfc7009 import RevocationEndpoint
from flask import (
    Flask, Blueprint, abort,
    current_app, request,
    url_for, redirect
)
from flask_login import (
    LoginManager, current_user, login_required, login_user, logout_user
)
from flask_restlib.forms import LoginForm
from flask_restlib.mixins import (
    AuthorizationCodeType,
    ClientType,
    TokenType,
    UserType
)
from flask_restlib.utils import (
    F,
    current_restlib,
    query_adapter,
    resource_manager
)
from flask_useful.views import MethodView, FormView
from flask_useful.utils import flash
from flask_wtf.csrf import validate_csrf
from werkzeug.local import LocalProxy
from wtforms.validators import ValidationError


authorization_server = LocalProxy(
    lambda: current_restlib.authorization_server
)


def generate_client_id(length: int) -> str:
    while 1:
        client_id = secrets.token_hex(length // 2)

        if authorization_server.query_client(client_id) is None:
            return client_id


def generate_client_secret(length: int) -> str:
    return secrets.token_hex(length // 2)


class AuthorizationCodeGrant(grants.AuthorizationCodeGrant):
    def save_authorization_code(
        self,
        code: str,
        request: OAuth2Request
    ) -> AuthorizationCodeType:
        with resource_manager() as rm:
            return rm.create(authorization_server.OAuth2Code, {
                'id': uuid4(),
                'code': code,
                'client': request.client,
                'redirect_uri': request.redirect_uri,
                'scope': request.scope,
                'user': request.user._get_current_object(),
            })

    def query_authorization_code(
        self,
        code: str,
        client: ClientType
    ) -> t.Optional[AuthorizationCodeType]:
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
        authorization_code: AuthorizationCodeType
    ) -> None:
        with resource_manager() as rm:
            rm.delete(authorization_code)

    def authenticate_user(
        self,
        authorization_code: AuthorizationCodeType
    ) -> UserType:
        return authorization_code.user


class PasswordGrant(grants.ResourceOwnerPasswordCredentialsGrant):
    def authenticate_user(
        self,
        username: str,
        password: str
    ) -> t.Optional[UserType]:
        user = authorization_server.OAuth2User.find_by_username(username)
        if user and user.check_password(password):
            return user
        return None


class RefreshTokenGrant(grants.RefreshTokenGrant):
    INCLUDE_NEW_REFRESH_TOKEN: t.ClassVar[bool] = True

    def authenticate_refresh_token(
        self,
        refresh_token: str
    ) -> t.Optional[TokenType]:
        item = (
            query_adapter(authorization_server.OAuth2Token)
                .filter_by(refresh_token=refresh_token)
                .one_or_none()
        )

        if item and item.is_refresh_token_valid():
            return item

        return None

    def authenticate_user(self, credential: TokenType) -> UserType:
        return credential.user

    def revoke_old_credential(self, credential: TokenType) -> None:
        with resource_manager() as rm:
            rm.update(credential, {'revoked': True})


class RevokeToken(RevocationEndpoint):
    def query_token(
        self,
        token: str,
        token_type_hint: str,
        client: ClientType
    ) -> Optional[TokenType]:
        current_app.logger.debug(f'Revocation token: {token}, type hint: {token_type_hint}')

        q = query_adapter(authorization_server.OAuth2Token).filter_by(client=client)

        if token_type_hint:
            return q.filter_by(**{token_type_hint: token}).first()

        # without token_type_hint
        current_app.logger.debug(f'Supported token types: {self.SUPPORTED_TOKEN_TYPES}')

        token_model = authorization_server.OAuth2Token
        qs = (F(token_model.access_token) == token) | (F(token_model.refresh_token) == token)
        return q.filter(qs).first()

    def revoke_token(self, token: TokenType) -> None:
        with resource_manager() as rm:
            rm.update(token, {'revoked': True})


class BearerTokenValidator(_BearerTokenValidator):
    def authenticate_token(self, token_string):
        return (
            query_adapter(authorization_server.OAuth2Token)
                .filter_by(access_token=token_string)
                .first()
        )

    def request_invalid(self, request):
        return False

    def token_revoked(self, token):
        return token.revoked


# Views


class IndexView(MethodView):
    """Home page."""
    decorators = [login_required]
    template_name = 'restlib/index.html'

    def get(self):
        return self.render_template()


class LoginView(FormView):
    """Account authentication."""
    form_class = LoginForm
    template_name = 'restlib/login.html'

    def get(self):
        if current_user.is_authenticated:
            return redirect(url_for('oauth.index'))
        return super().get()

    def form_valid(self, form, obj=None):
        user = authorization_server.OAuth2User.find_by_username(form.username.data)

        if user and user.check_password(form.password.data):
            remember = current_app.config['RESTLIB_REMEMBER_ME'] and form.remember_me.data
            login_user(user, remember=remember)

            redirect_url = request.args.get('next')

            if redirect_url is None or not redirect_url.startswith('/'):
                redirect_url = url_for('oauth.index')

            return redirect(redirect_url)

        flash.error('Invalid account')

        return self.form_invalid(form, obj)


class LogoutView(MethodView):
    """Logout of your account."""
    decorators = [login_required]

    def get(self):
        logout_user()
        return redirect(url_for('oauth.login'))


class AuthorizeView(MethodView):
    """Application authorization."""
    decorators = [login_required]
    template_name = 'restlib/authorize.html'

    def get(self):
        try:
            grant = authorization_server.validate_consent_request(end_user=current_user)
        except OAuth2Error as err:
            error_message = ', '.join(f'{k}: {v}' for k, v in err.get_body())
            current_app.logger.error(error_message)
            abort(err.status_code, err.error)
        else:
            return self.render_template(grant=grant)

    def post(self):
        try:
            validate_csrf(request.form.get('csrf_token', ''))
        except ValidationError as err:
            flash.error(str(err))
            return redirect(request.url)

        grant_user = None
        accept = 'accept' in request.form
        decline = 'decline' in request.form

        if accept and not decline:
            grant_user = current_user

        return authorization_server.create_authorization_response(
            grant_user=grant_user
        )


class AccessTokenView(MethodView):
    """Access token request."""
    def post(self):
        return authorization_server.create_token_response()


class RevokeTokenView(MethodView):
    """Revokes a previously issued token."""
    def post(self):
        return authorization_server.create_endpoint_response(
            RevokeToken.ENDPOINT_NAME
        )


class AuthorizationServer(_AuthorizationServer):
    def __init__(
        self,
        app: typing.Optional[Flask] = None,
        *,
        user_model: UserType,
        client_model: ClientType,
        token_model: TokenType,
        authorization_code_model: AuthorizationCodeType,
        query_client: typing.Optional[typing.Callable] = None,
        save_token: typing.Optional[typing.Callable] = None
    ):
        """
        Arguments:
            app (Flask): Flask application instance that being used.
            user_model: Reference to the User model class.
            client_model: OAuth client model class.
            token_model: OAuth token model class.
            authorization_code_model: OAuth code model class.
            query_client: A function to get client by client_id.
            save_token: A function to save tokens.
        """
        if save_token is None:
            save_token = self._save_token

        if query_client is None:
            query_client = self._query_client

        super().__init__(save_token=save_token, query_client=query_client)

        self.OAuth2User = user_model
        self.OAuth2Client = client_model
        self.OAuth2Token = token_model
        self.OAuth2Code = authorization_code_model

        self.login_manager = LoginManager()
        self.login_manager.user_loader(self._load_user)
        self.login_manager.login_view = 'oauth.login'

        self.index_endpoint = IndexView.as_view('index')
        self.login_endpoint = LoginView.as_view('login')
        self.logout_endpoint = LogoutView.as_view('logout')
        self.authorize_endpoint = AuthorizeView.as_view('authorize')
        self.access_token_endpoint = AccessTokenView.as_view('access_token')
        self.revoke_token_endpoint = RevokeTokenView.as_view('revoke_token')

        self.bp = Blueprint('oauth', __name__, template_folder='templates')

        if app is not None:
            self.init_app(app)

    def init_app(
        self,
        app: Flask,
        *,
        query_client: typing.Optional[typing.Callable] = None,
        save_token: typing.Optional[typing.Callable] = None
    ) -> None:
        super().init_app(app, query_client=query_client, save_token=save_token)

        app.config.setdefault('RESTLIB_OAUTH2_URL_PREFIX', '/oauth')
        app.config.setdefault('RESTLIB_OAUTH2_AUTHORIZATION_CODE_GRANT', True)
        app.config.setdefault('RESTLIB_OAUTH2_IMPLICIT_GRANT', True)
        app.config.setdefault('RESTLIB_OAUTH2_RESOURCE_OWNER_GRANT', True)
        app.config.setdefault('RESTLIB_OAUTH2_CLIENT_CREDENTIALS_GRANT', True)
        app.config.setdefault('RESTLIB_OAUTH2_REFRESH_TOKEN_GRANT', True)

        app.extensions['restlib_oauth2'] = self

        if app.config['RESTLIB_OAUTH2_AUTHORIZATION_CODE_GRANT']:
            self.register_grant(AuthorizationCodeGrant)

        if app.config['RESTLIB_OAUTH2_IMPLICIT_GRANT']:
            self.register_grant(grants.ImplicitGrant)

        if app.config['RESTLIB_OAUTH2_RESOURCE_OWNER_GRANT']:
            self.register_grant(PasswordGrant)

        if app.config['RESTLIB_OAUTH2_CLIENT_CREDENTIALS_GRANT']:
            self.register_grant(grants.ClientCredentialsGrant)

        if app.config['RESTLIB_OAUTH2_REFRESH_TOKEN_GRANT']:
            self.register_grant(RefreshTokenGrant)

        self.register_endpoint(RevokeToken)

        self.login_manager.init_app(app)

        self.bp.add_url_rule('/', view_func=self.index_endpoint)
        self.bp.add_url_rule('/login', view_func=self.login_endpoint)
        self.bp.add_url_rule('/logout', view_func=self.logout_endpoint)
        self.bp.add_url_rule('/authorize', view_func=self.authorize_endpoint)
        self.bp.add_url_rule('/token', view_func=self.access_token_endpoint)
        self.bp.add_url_rule('/revoke', view_func=self.revoke_token_endpoint)
        app.register_blueprint(self.bp, url_prefix=app.config['RESTLIB_OAUTH2_URL_PREFIX'])

    def _load_user(self, user_id):
        """Returns user by user_id."""
        return resource_manager().get(self.OAuth2User, user_id)

    def _query_client(self, client_id: str) -> t.Optional[ClientType]:
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
                'user': request.user or request.client.user,
                'scope': token_data.pop('scope', ''),
                **token_data,
            })
