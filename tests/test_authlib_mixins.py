import inspect
import re

from authlib.integrations.sqla_oauth2 import (
    OAuth2ClientMixin,
    OAuth2TokenMixin,
    OAuth2AuthorizationCodeMixin
)
from flask_restlib.mixins import (
    ClientMixin,
    TokenMixin,
    AuthorizationCodeMixin
)
import pytest


EMPTY = inspect.Signature.empty


@pytest.fixture
def source():
    def get(object_):
        sig = inspect.signature(object_)
        sig = sig.replace(
            parameters=[
                p.replace(annotation=EMPTY) for n, p in sig.parameters.items()
            ],
            return_annotation=EMPTY
        )

        code = inspect.getsource(object_)
        code = code.replace(f'"""{object_.__doc__}"""' or '', '')
        result = []

        for line in code.splitlines():
            line = line.strip()

            if line.startswith('def'):
                line = re.sub(r'\(.*:', str(sig), line)

            if line:
                result.append(line)

        return result
    return get


class TestOAuth2ClientMixin:
    original = OAuth2ClientMixin
    ported = ClientMixin

    def test_client_info(self, source):
        result = source(self.ported.client_info.fget)
        expected = source(self.original.client_info.fget)
        assert result == expected

    def test_client_metadata(self, source):
        result = source(self.ported.client_metadata.fget)
        expected = source(self.original.client_metadata.fget)
        assert result == expected

    def test_set_client_metadata(self, source):
        result = source(self.ported.set_client_metadata)
        expected = source(self.original.set_client_metadata)
        assert result == expected

    def test_redirect_uris(self, source):
        result = source(self.ported.redirect_uris.fget)
        expected = source(self.original.redirect_uris.fget)
        assert result == expected

    def test_token_endpoint_auth_method(self, source):
        result = source(self.ported.token_endpoint_auth_method.fget)
        expected = source(self.original.token_endpoint_auth_method.fget)
        assert result == expected

    def test_grant_types(self, source):
        result = source(self.ported.grant_types.fget)
        expected = source(self.original.grant_types.fget)
        assert result == expected

    def test_response_types(self, source):
        result = source(self.ported.response_types.fget)
        expected = source(self.original.response_types.fget)
        assert result == expected

    def test_client_name(self, source):
        result = source(self.ported.client_name.fget)
        expected = source(self.original.client_name.fget)
        assert result == expected

    def test_client_uri(self, source):
        result = source(self.ported.client_uri.fget)
        expected = source(self.original.client_uri.fget)
        assert result == expected

    def test_logo_uri(self, source):
        result = source(self.ported.logo_uri.fget)
        expected = source(self.original.logo_uri.fget)
        assert result == expected

    def test_scope(self, source):
        result = source(self.ported.scope.fget)
        expected = source(self.original.scope.fget)
        assert result == expected

    def test_contacts(self, source):
        result = source(self.ported.contacts.fget)
        expected = source(self.original.contacts.fget)
        assert result == expected

    def test_tos_uri(self, source):
        result = source(self.ported.tos_uri.fget)
        expected = source(self.original.tos_uri.fget)
        assert result == expected

    def test_policy_uri(self, source):
        result = source(self.ported.policy_uri.fget)
        expected = source(self.original.policy_uri.fget)
        assert result == expected

    def test_jwks_uri(self, source):
        result = source(self.ported.jwks_uri.fget)
        expected = source(self.original.jwks_uri.fget)
        assert result == expected

    def test_jwks(self, source):
        result = source(self.ported.jwks.fget)
        expected = source(self.original.jwks.fget)
        assert result == expected

    def test_software_id(self, source):
        result = source(self.ported.software_id.fget)
        expected = source(self.original.software_id.fget)
        assert result == expected

    def test_software_version(self, source):
        result = source(self.ported.software_version.fget)
        expected = source(self.original.software_version.fget)
        assert result == expected

    def test_get_client_id(self, source):
        result = source(self.ported.get_client_id)
        expected = source(self.original.get_client_id)
        assert result == expected

    def test_get_default_redirect_uri(self, source):
        result = source(self.ported.get_default_redirect_uri)
        expected = source(self.original.get_default_redirect_uri)
        assert result == expected

    def test_get_allowed_scope(self, source):
        expected = set(source(self.original.check_redirect_uri))
        result = set(source(self.ported.check_redirect_uri))
        result.update({
            'scopes = scope_to_list(scope)',
            'return list_to_scope([s for s in scopes if s in allowed])'
        })
        assert not expected - result

    def test_check_redirect_uri(self, source):
        result = source(self.ported.check_redirect_uri)
        expected = source(self.original.check_redirect_uri)
        assert result == expected

    def test_has_client_secret(self, source):
        result = source(self.ported.has_client_secret)
        expected = source(self.original.has_client_secret)
        assert result == expected

    def test_check_client_secret(self, source):
        result = source(self.ported.check_client_secret)
        expected = source(self.original.check_client_secret)
        assert result == expected

    def test_check_token_endpoint_auth_method(self, source):
        result = source(self.ported.check_token_endpoint_auth_method)
        expected = source(self.original.check_token_endpoint_auth_method)
        assert result == expected

    def test_check_response_type(self, source):
        result = source(self.ported.check_response_type)
        expected = source(self.original.check_response_type)
        assert result == expected

    def test_check_grant_type(self, source):
        result = source(self.ported.check_grant_type)
        expected = source(self.original.check_grant_type)
        assert result == expected


class TestOAuth2TokenMixin:
    original = OAuth2TokenMixin
    ported = TokenMixin

    def test_get_client_id(self, source):
        result = source(self.ported.get_client_id)
        expected = source(self.original.get_client_id)
        assert result == expected

    def test_get_scope(self, source):
        result = source(self.ported.get_scope)
        expected = source(self.original.get_scope)
        assert result == expected

    def test_get_expires_in(self, source):
        result = source(self.ported.get_expires_in)
        expected = source(self.original.get_expires_in)
        assert result == expected

    def test_get_expires_at(self, source):
        result = source(self.ported.get_expires_at)
        expected = source(self.original.get_expires_at)
        assert result == expected


class TestOAuth2AuthorizationCodeMixin:
    original = OAuth2AuthorizationCodeMixin
    ported = AuthorizationCodeMixin

    def test_is_expired(self, source):
        result = source(self.ported.is_expired)
        expected = source(self.original.is_expired)
        assert result == expected

    def test_get_redirect_uri(self, source):
        result = source(self.ported.get_redirect_uri)
        expected = source(self.original.get_redirect_uri)
        assert result == expected

    def test_get_scope(self, source):
        result = source(self.ported.get_scope)
        expected = source(self.original.get_scope)
        assert result == expected

    def test_get_auth_time(self, source):
        result = source(self.ported.get_auth_time)
        expected = source(self.original.get_auth_time)
        assert result == expected

    def test_get_nonce(self, source):
        result = source(self.ported.get_nonce)
        expected = source(self.original.get_nonce)
        assert result == expected
