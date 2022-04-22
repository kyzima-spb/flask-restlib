from __future__ import annotations
import typing as t
from urllib.parse import urlparse

from authlib.oauth2 import OAuth2Error
from authlib.oauth2.rfc6749.token_endpoint import TokenEndpoint
from authlib.oauth2.rfc6749.wrappers import OAuth2Request
from authlib.oauth2.rfc7009 import RevocationEndpoint
from authlib.oauth2.rfc7662 import IntrospectionEndpoint as AbstractIntrospectionEndpoint
from flask import (
    abort,
    current_app,
    request,
    redirect,
    url_for,
)
from flask.typing import ResponseReturnValue
from flask_login import (
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_useful.views import MethodView, FormView
from flask_useful.utils import flash
from flask_wtf import FlaskForm
from flask_wtf.csrf import validate_csrf
from wtforms.validators import ValidationError

from .mixins import ClientMixin, TokenMixin
from ..forms import LoginForm
from ..globals import (
    authorization_server,
    Q,
    query_adapter,
    resource_manager
)


__all__ = (
    'AccessTokenView',
    'AuthorizeView',
    'IndexView',
    'LoginView',
    'LogoutView',
    'IntrospectionEndpoint',
    'IntrospectionTokenView',
    'RevokeTokenEndpoint',
    'RevokeTokenView',
)


def query_token(token_string: str, token_type_hint: str) -> t.Optional[TokenMixin]:
    """Returns the token from persistent storage by the given token string."""
    current_app.logger.debug(f'Query token: {token_string}, type hint: {token_type_hint}')

    model = authorization_server.OAuth2Token
    q = query_adapter(model)

    if token_type_hint:
        return q.filter_by(**{token_type_hint: token_string}).first()

    current_app.logger.debug(f'Supported token types: {TokenEndpoint.SUPPORTED_TOKEN_TYPES}')

    qs = (Q(model.access_token) == token_string) | (Q(model.refresh_token) == token_string)

    return q.filter(qs).first()


class AccessTokenView(MethodView):
    """Access token request."""
    def post(self) -> ResponseReturnValue:
        return authorization_server.create_token_response()


class AuthorizeView(MethodView):
    """Application authorization."""
    decorators = [login_required]
    template_name = 'restlib/authorize.html'

    def get(self) -> ResponseReturnValue:
        try:
            grant = authorization_server.get_consent_grant(end_user=current_user)
        except OAuth2Error as err:
            error_message = ', '.join(f'{k}: {v}' for k, v in err.get_body())
            current_app.logger.error(error_message)
            abort(err.status_code, err.error)
        else:
            return self.render_template(grant=grant)

    def post(self) -> ResponseReturnValue:
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


class IndexView(MethodView):
    """Home page."""
    decorators = [login_required]
    template_name = 'restlib/index.html'

    def get(self) -> ResponseReturnValue:
        return self.render_template()


class LoginView(FormView):
    """Account authentication."""
    form_class = LoginForm
    template_name = 'restlib/login.html'

    def get(self) -> ResponseReturnValue:
        if current_user.is_authenticated:
            return redirect(url_for('oauth.index'))
        return super().get()

    def form_valid(
        self,
        form: FlaskForm,
        obj: t.Optional[t.Any] = None
    ) -> ResponseReturnValue:
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

    def get(self) -> ResponseReturnValue:
        redirect_url = url_for('oauth.login')
        client_id = request.args.get('client_id')
        logout_uri = request.args.get(
            current_app.config['RESTLIB_URL_PARAM_LOGOUT']
        )

        if client_id and logout_uri:
            client = authorization_server.query_client(client_id)

            if client is not None:
                redirect_domains = {urlparse(url).netloc for url in client.redirect_uris}
                logout_domain = urlparse(logout_uri).netloc

                if logout_domain in redirect_domains:
                    redirect_url = logout_uri

        logout_user()

        return redirect(redirect_url)


class IntrospectionEndpoint(AbstractIntrospectionEndpoint):
    def query_token(self, token_string: str, token_type_hint: str) -> t.Optional[TokenMixin]:
        return query_token(token_string, token_type_hint)

    def introspect_token(self, token: TokenMixin) -> dict[str, t.Any]:
        return {
            'active': True,
            'scope': token.get_scope(),
            'client_id': token.get_client().get_client_id(),
            # 'username': get_token_username(token),
            'token_type': token.get_token_type(),
            'exp': token.get_expires_at(),
            'iat': token.get_issued_at(),
            # 'sub': get_token_user_sub(token),
            # 'iss': 'https://server.example.com/',
        }

    def check_permission(
        self,
        token: TokenMixin,
        client: ClientMixin,
        request: OAuth2Request
    ) -> bool:
        return token.check_client(client)


class IntrospectionTokenView(MethodView):
    """Introspection a previously issued token."""
    def post(self) -> ResponseReturnValue:
        return authorization_server.create_endpoint_response(
            IntrospectionEndpoint.ENDPOINT_NAME
        )


class RevokeTokenEndpoint(RevocationEndpoint):
    def query_token(self, token_string: str, token_type_hint: str) -> t.Optional[TokenMixin]:
        return query_token(token_string, token_type_hint)

    def revoke_token(self, token: TokenMixin, request: OAuth2Request) -> None:
        hint = request.form.get('token_type_hint')
        with resource_manager() as rm:
            if hint == 'access_token':
                rm.update(token, {'access_token_revoked_at': True})
            else:
                rm.update(token, {
                    'access_token_revoked_at': True,
                    'refresh_token_revoked_at': True,
                })


class RevokeTokenView(MethodView):
    """Revokes a previously issued token."""
    def post(self) -> ResponseReturnValue:
        return authorization_server.create_endpoint_response(
            RevokeTokenEndpoint.ENDPOINT_NAME
        )
