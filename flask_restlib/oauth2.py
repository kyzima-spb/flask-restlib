from __future__ import annotations
import typing
from typing import ClassVar, Optional
from uuid import uuid4

from authlib.oauth2 import OAuth2Error
from authlib.integrations.flask_oauth2 import AuthorizationServer as _AuthorizationServer
from authlib.oauth2.rfc6749 import grants
from authlib.oauth2.rfc6749.wrappers import OAuth2Request
from authlib.oauth2.rfc7009 import RevocationEndpoint
from flask import (
    Flask, Blueprint, abort, Response,
    current_app, request
)
from flask_login import LoginManager, current_user, login_required
from flask_restlib import F
from flask_restlib.core import (
    QueryAdapterType,
    ResourceManagerType,
    AbstractFactoryType
)
from flask_restlib.mixins import (
    AuthorizationCodeType,
    ClientType,
    TokenType,
    UserType
)
from flask_useful.views import MethodView
from werkzeug.local import LocalProxy


current_oauth2: OAuth2 = LocalProxy(
    lambda: current_app.extensions['restlib_oauth2']
)


class AuthorizationCodeGrant(grants.AuthorizationCodeGrant):
    def save_authorization_code(
        self,
        code: str,
        request: OAuth2Request
    ) -> AuthorizationCodeType:
        with current_oauth2.rm as rm:
            return rm.create(current_oauth2.OAuth2Code, {
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
    ) -> typing.Optional[AuthorizationCodeType]:
        authorization_code = (
            current_oauth2
                .factory
                .create_query_adapter(current_oauth2.OAuth2Code)
                .filter_by(code=code, client=client)
                .one_or_none()
        )

        if authorization_code and not authorization_code.is_expired():
            return authorization_code

        if authorization_code:
            self.delete_authorization_code(authorization_code)

    def delete_authorization_code(
        self,
        authorization_code: AuthorizationCodeType
    ) -> typing.NoReturn:
        with current_oauth2.rm as rm:
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
    ) -> typing.Optional[UserType]:
        user = current_oauth2.OAuth2User.find_by_username(username)
        if user and user.check_password(password):
            return user


class RefreshTokenGrant(grants.RefreshTokenGrant):
    INCLUDE_NEW_REFRESH_TOKEN: ClassVar[bool] = True

    def authenticate_refresh_token(
        self,
        refresh_token: str
    ) -> Optional[TokenType]:
        item = (
            current_oauth2
                .factory
                .create_query_adapter(current_oauth2.OAuth2Token)
                .filter_by(refresh_token=refresh_token)
                .one_or_none()
        )

        if item and item.is_refresh_token_valid():
            return item

    def authenticate_user(self, credential: TokenType) -> UserType:
        return credential.user

    def revoke_old_credential(self, credential: TokenType) -> typing.NoReturn:
        with current_oauth2.rm as rm:
            rm.update(credential, {'revoked': True})


class RevokeToken(RevocationEndpoint):
    def query_token(
        self,
        token: str,
        token_type_hint: str,
        client: ClientType
    ) -> Optional[TokenType]:
        current_app.logger.debug(f'Revocation token: {token}, type hint: {token_type_hint}')

        q = (
            current_oauth2
                .factory
                .create_query_adapter(current_oauth2.OAuth2Token)
                .filter_by(client=client)
        )

        if token_type_hint:
            return q.filter_by(**{token_type_hint: token}).first()

        # without token_type_hint
        current_app.logger.debug(f'Supported token types: {self.SUPPORTED_TOKEN_TYPES}')

        token_model = current_oauth2.OAuth2Token
        qs = (F(token_model.access_token) == token) | (F(token_model.refresh_token) == token)
        return q.filter(qs).first()

    def revoke_token(self, token: TokenType) -> typing.NoReturn:
        with current_oauth2.rm as rm:
            rm.update(token, {'revoked': True})


class AccessTokenView(MethodView):
    def post(self):
        return current_oauth2.create_token_response()


class AuthorizeView(MethodView):
    decorators = [login_required]
    template_name = 'restlib/authorize.html'

    def get(self):
        try:
            grant = current_oauth2.validate_consent_request(end_user=current_user)
        except OAuth2Error as err:
            current_app.logger.error(err.get_body())
            abort(Response(
                err.get_error_description(), err.status_code, err.get_headers()
            ))
        else:
            return self.render_template(grant=grant)

    def post(self):
        grant_user = None
        accept = 'accept' in request.form
        decline = 'decline' in request.form

        if accept and not decline:
            grant_user = current_user

        return current_oauth2.create_authorization_response(
            grant_user=grant_user
        )


class RevokeTokenView(MethodView):
    def post(self):
        return current_oauth2.create_endpoint_response(
            RevokeToken.ENDPOINT_NAME
        )


class AuthorizationServer(_AuthorizationServer):
    def __init__(
        self,
        app: typing.Optional[Flask] = None,
        *,
        factory: AbstractFactoryType,
        user_model: typing.Type,
        client_model: typing.Optional[typing.Type] = None,
        token_model: typing.Optional[typing.Type] = None,
        authorization_code_model: typing.Optional[typing.Type] = None,
        query_client: typing.Optional[typing.Callable] = None,
        save_token: typing.Optional[typing.Callable] = None
    ):
        """
        Arguments:
            app (Flask): Flask application instance that being used.
            factory (AbstractFactoryType): Factory instance that being used.
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

        if client_model is None:
            client_model = factory.create_client_model(user_model)

        if token_model is None:
            token_model = factory.create_token_model(user_model, client_model)

        if authorization_code_model is None:
            authorization_code_model = factory.create_authorization_code_model(
                user_model, client_model
            )

        self.factory = factory

        self.OAuth2User = user_model
        self.OAuth2Client = client_model
        self.OAuth2Token = token_model
        self.OAuth2Code = authorization_code_model

        self.login_manager = LoginManager()
        self.login_manager.user_loader(self._load_user)

        self.authorize_endpoint = AuthorizeView.as_view('authorize')
        self.access_token_endpoint = AccessTokenView.as_view('access_token')
        self.revoke_token_endpoint = RevokeTokenView.as_view('revoke_token')

        self.bp = Blueprint('oauth', __name__, template_folder='templates')
        self.bp.add_url_rule('/authorize', view_func=self.authorize_endpoint)
        self.bp.add_url_rule('/token', view_func=self.access_token_endpoint)
        self.bp.add_url_rule('/revoke', view_func=self.revoke_token_endpoint)

        if app is not None:
            self.init_app(app)

    def init_app(
        self,
        app: Flask,
        *,
        query_client: typing.Optional[typing.Callable] = None,
        save_token: typing.Optional[typing.Callable] = None
    ) -> typing.NoReturn:
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

        app.register_blueprint(self.bp, url_prefix=app.config['RESTLIB_OAUTH2_URL_PREFIX'])

    @property
    def rm(self) -> ResourceManagerType:
        """Returns a resource manager instance."""
        return self.factory.create_resource_manager()

    def _load_user(self, user_id):
        """Returns user by user_id."""
        return self.rm.get(self.OAuth2User, user_id)

    def _query_client(self, client_id: str):
        """Returns client by client_id."""
        return self.rm.get(self.OAuth2Client, client_id)

    def _save_token(
        self,
        token_data: dict,
        request: OAuth2Request
    ) -> typing.NoReturn:
        """Saves tokens to persistent storage."""
        with self.rm:
            self.rm.create(self.OAuth2Token, {
                'id': uuid4(),
                'client': request.client,
                'user': request.user or request.client.user,
                'scope': token_data.pop('scope', ''),
                **token_data,
            })
