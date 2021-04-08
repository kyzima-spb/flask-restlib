from datetime import datetime
import typing

from authlib.integrations.sqla_oauth2 import (
    OAuth2ClientMixin, OAuth2TokenMixin, OAuth2AuthorizationCodeMixin,
    create_query_client_func,
    create_save_token_func
)
from authlib.oauth2 import OAuth2Error
from authlib.oauth2.rfc6749 import grants
from authlib.oauth2.rfc7009 import RevocationEndpoint
from authlib.integrations.flask_oauth2 import (
    AuthorizationServer, ResourceProtector
)
from flask import Flask, Blueprint, request, render_template, current_app, abort, Response
from flask_useful.views import MethodView
from flask_login import current_user, login_required
import sqlalchemy as sa
from sqlalchemy.orm import relationship

from game_store.models import db, User


bp = Blueprint('oauth', __name__, url_prefix='/oauth')
oauth = AuthorizationServer()
require_oauth = ResourceProtector()


class OAuth2Client(db.Model, OAuth2ClientMixin):
    id = sa.Column(sa.Integer, primary_key=True)
    user_id = sa.Column(
        sa.Integer, sa.ForeignKey('user.id', ondelete='CASCADE')
    )
    user = relationship('User')


class OAuth2Token(db.Model, OAuth2TokenMixin):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE')
    )
    user = db.relationship('User')

    def is_refresh_token_valid(self):
        if self.revoked:
            return False
        expires_at = datetime.fromtimestamp(self.get_expires_at())
        return expires_at > datetime.utcnow()


class OAuth2Code(db.Model, OAuth2AuthorizationCodeMixin):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey('user.id', ondelete='CASCADE')
    )
    user = db.relationship('User')


class AuthorizationCodeGrant(grants.AuthorizationCodeGrant):
    def save_authorization_code(self, code, request):
        client = request.client
        auth_code = OAuth2Code(
            code=code,
            client_id=client.client_id,
            redirect_uri=request.redirect_uri,
            scope=request.scope,
            user_id=request.user.id,
        )
        db.session.add(auth_code)
        db.session.commit()
        return auth_code

    def query_authorization_code(self, code, client):
        authorization_code = OAuth2Code.query.filter_by(
            code=code, client_id=client.client_id
        ).first()
        if authorization_code and not authorization_code.is_expired():
            return authorization_code

    def delete_authorization_code(self, authorization_code):
        db.session.delete(authorization_code)
        db.session.commit()

    def authenticate_user(self, authorization_code):
        return User.query.get(authorization_code.user_id)


class PasswordGrant(grants.ResourceOwnerPasswordCredentialsGrant):
    def authenticate_user(self, username, password):
        user = User.query.filter_by(email=username).first()
        if user and user.check_password(password):
            return user


class RefreshTokenGrant(grants.RefreshTokenGrant):
    INCLUDE_NEW_REFRESH_TOKEN = True

    def authenticate_refresh_token(self, refresh_token):
        item = OAuth2Token.query.filter_by(refresh_token=refresh_token).first()
        # define is_refresh_token_valid by yourself
        # usually, you should check if refresh token is expired and revoked
        if item and item.is_refresh_token_valid():
            return item

    def authenticate_user(self, credential):
        return User.query.get(credential.user_id)

    def revoke_old_credential(self, credential):
        credential.revoked = True
        db.session.add(credential)
        db.session.commit()


class RevokeToken(RevocationEndpoint):
    def query_token(self, token, token_type_hint, client):
        q = OAuth2Token.query.filter_by(client_id=client.client_id)
        if token_type_hint == 'access_token':
            return q.filter_by(access_token=token).first()
        elif token_type_hint == 'refresh_token':
            return q.filter_by(refresh_token=token).first()
        # without token_type_hint
        item = q.filter_by(access_token=token).first()
        if item:
            return item
        return q.filter_by(refresh_token=token).first()

    def revoke_token(self, token):
        token.revoked = True
        db.session.add(token)
        db.session.commit()


def query_client(client_id):
    return OAuth2Client.query.filter_by(client_id=client_id).first()


def save_token(token_data, request):
    if request.user:
        user_id = request.user.get_user_id()
    else:
        # client_credentials grant_type
        user_id = request.client.user_id
        # or, depending on how you treat client_credentials
        user_id = None
    token = OAuth2Token(
        client_id=request.client.client_id,
        user_id=user_id,
        **token_data
    )
    db.session.add(token)
    db.session.commit()


class AccessTokenView(MethodView):
    def post(self):
        return oauth.create_token_response()


class RevokeTokenView(MethodView):
    def post(self):
        return oauth.create_endpoint_response(RevokeToken.ENDPOINT_NAME)


class AuthorizeView(MethodView):
    decorators = [login_required]
    template_name = 'authorize.html'

    def get(self):
        try:
            grant = oauth.validate_consent_request(end_user=current_user)
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

        return oauth.create_authorization_response(grant_user=grant_user)


authorize_endpoint = AuthorizeView.as_view('authorize')
access_token_endpoint = AccessTokenView.as_view('access_token')
revoke_token_endpoint = RevokeTokenView.as_view('revoke_token')

bp.add_url_rule('/authorize', view_func=authorize_endpoint)
bp.add_url_rule('/token', view_func=access_token_endpoint)
bp.add_url_rule('/revoke', view_func=revoke_token_endpoint)


def init_app(app: Flask) -> typing.NoReturn:
    query_client = create_query_client_func(db.session, OAuth2Client)
    save_token = create_save_token_func(db.session, OAuth2Token)

    oauth.init_app(app, query_client=query_client, save_token=save_token)

    oauth.register_grant(AuthorizationCodeGrant)
    oauth.register_grant(grants.ImplicitGrant)
    oauth.register_grant(PasswordGrant)
    oauth.register_grant(grants.ClientCredentialsGrant)
    oauth.register_grant(RefreshTokenGrant)

    oauth.register_endpoint(RevokeToken)

    app.register_blueprint(bp)
