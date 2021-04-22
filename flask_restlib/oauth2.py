from __future__ import annotations
import typing
from typing import ClassVar, Optional
from uuid import uuid4

from authlib.oauth2 import OAuth2Error
from authlib.integrations.flask_oauth2 import AuthorizationServer
from authlib.oauth2.rfc6749 import grants
from authlib.oauth2.rfc6749.wrappers import OAuth2Request
from authlib.oauth2.rfc7009 import RevocationEndpoint
from flask import (
    Flask, Blueprint, abort, Response,
    current_app, request
)
from flask_login import current_user, login_required
from flask_restlib.core import AbstractFactoryType
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
        with current_oauth2.factory.create_resource_manager() as rm:
            return rm.create(current_oauth2.OAuth2Code, {
                'id': uuid4(),
                'code': code,
                'client': request.client,
                'redirect_uri': request.redirect_uri,
                'scope': request.scope,
                'user': request.user,
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

    def delete_authorization_code(
        self,
        authorization_code: AuthorizationCodeType
    ) -> typing.NoReturn:
        with current_oauth2.factory.create_resource_manager() as rm:
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
        with current_oauth2.factory.create_resource_manager() as rm:
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

        item = q.filter_by(access_token=token).first()
        if item:
            return item
        return q.filter_by(refresh_token=token).first()

    def revoke_token(self, token: TokenType) -> typing.NoReturn:
        with current_oauth2.factory.create_resource_manager() as rm:
            rm.update(token, {'revoked': True})


class AccessTokenView(MethodView):
    def post(self):
        return current_oauth2.server.create_token_response()


class AuthorizeView(MethodView):
    decorators = [login_required]
    template_name = 'authorize.html'

    def get(self):
        try:
            grant = current_oauth2.server.validate_consent_request(end_user=current_user)
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

        return current_oauth2.server.create_authorization_response(
            grant_user=grant_user
        )


class RevokeTokenView(MethodView):
    def post(self):
        return current_oauth2.server.create_endpoint_response(
            RevokeToken.ENDPOINT_NAME
        )


class OAuth2:
    def __init__(
        self,
        app: typing.Optional[Flask] = None,
        *,
        factory: AbstractFactoryType,
        user_model: typing.Type,
        client_model: typing.Optional[typing.Type] = None,
        token_model: typing.Optional[typing.Type] = None,
        authorization_code_model: typing.Optional[typing.Type] = None
    ):
        self.factory = factory

        if client_model is None:
            client_model = factory.create_client_model(user_model)

        if token_model is None:
            token_model = factory.create_token_model(user_model, client_model)

        if authorization_code_model is None:
            authorization_code_model = factory.create_authorization_code_model(
                user_model, client_model
            )

        self.OAuth2User = user_model
        self.OAuth2Client = client_model
        self.OAuth2Token = token_model
        self.OAuth2Code = authorization_code_model

        self.bp = Blueprint('oauth', __name__)
        self.server = AuthorizationServer()

        self.authorize_endpoint = AuthorizeView.as_view('authorize')
        self.access_token_endpoint = AccessTokenView.as_view('access_token')
        self.revoke_token_endpoint = RevokeTokenView.as_view('revoke_token')

        self.bp.add_url_rule('/authorize', view_func=self.authorize_endpoint)
        self.bp.add_url_rule('/token', view_func=self.access_token_endpoint)
        self.bp.add_url_rule('/revoke', view_func=self.revoke_token_endpoint)

        if app is not None:
            self.init_app(app)

    def init_app(self, app: Flask) -> typing.NoReturn:
        app.config.setdefault('RESTLIB_OAUTH2_URL_PREFIX', '/oauth')
        app.config.setdefault('RESTLIB_OAUTH2_AUTHORIZATION_CODE_GRANT', True)
        app.config.setdefault('RESTLIB_OAUTH2_IMPLICIT_GRANT', True)
        app.config.setdefault('RESTLIB_OAUTH2_RESOURCE_OWNER_GRANT', True)
        app.config.setdefault('RESTLIB_OAUTH2_CLIENT_CREDENTIALS_GRANT', True)
        app.config.setdefault('RESTLIB_OAUTH2_REFRESH_TOKEN_GRANT', True)

        app.extensions['restlib_oauth2'] = self

        self.server.init_app(app, query_client=self.query_client, save_token=self.save_token)

        if app.config['RESTLIB_OAUTH2_AUTHORIZATION_CODE_GRANT']:
            self.server.register_grant(AuthorizationCodeGrant)

        if app.config['RESTLIB_OAUTH2_IMPLICIT_GRANT']:
            self.server.register_grant(grants.ImplicitGrant)

        if app.config['RESTLIB_OAUTH2_RESOURCE_OWNER_GRANT']:
            self.server.register_grant(PasswordGrant)

        if app.config['RESTLIB_OAUTH2_CLIENT_CREDENTIALS_GRANT']:
            self.server.register_grant(grants.ClientCredentialsGrant)

        if app.config['RESTLIB_OAUTH2_REFRESH_TOKEN_GRANT']:
            self.server.register_grant(RefreshTokenGrant)

        self.server.register_endpoint(RevokeToken)

        app.register_blueprint(self.bp, url_prefix=app.config['RESTLIB_OAUTH2_URL_PREFIX'])

    def query_client(self, client_id: str):
        rm = self.factory.create_resource_manager()
        return rm.get(self.OAuth2Client, client_id)

    def save_token(
        self,
        token_data: dict,
        request: OAuth2Request
    ) -> typing.NoReturn:
        with self.factory.create_resource_manager() as rm:
            token_data.setdefault('scope', '')
            user = request.user or request.client.user
            rm.create(self.OAuth2Token, {
                'id': uuid4(),
                'client': request.client,
                'user': user,
                **token_data
            })
