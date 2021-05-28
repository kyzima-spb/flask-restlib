import pytest


@pytest.fixture
def user(db, User):
    user = User(username='foo')
    db.session.add(user)
    db.session.commit()
    return user


@pytest.fixture
def make_oauth_client(user, db, OAuth2Client):
    def f(grant_types):
        client = OAuth2Client(
            id='password-client',
            client_secret='password-secret',
            client_metadata={
                'scope': 'profile games',
                'grant_types': grant_types,
                'redirect_uris': ['http://localhost/authorized'],
            },
            user=user
        )
        db.session.add(client)
        db.session.commit()
        return client
    return f


@pytest.fixture
def oauth_client(make_oauth_client):
    return make_oauth_client(['password', 'refresh_token'])


@pytest.fixture
def request_token(client, basic_header):
    def f(data=None, auth=None):
        headers = {}

        if auth is not None:
            headers.update(basic_header(*auth))

        return client.post('/oauth/token', data=data, headers=headers).get_json()
    return f


@pytest.mark.usefixtures(
    'oauth_client', 'OAuth2Token', 'OAuth2Code'
)
class TestPassword:
    @pytest.mark.parametrize('invalid_auth', (
        None,
        ('invalid-client', 'password-secret'),
        ('password-client', 'invalid-secret'),
    ), ids=repr)
    def test_invalid_client(self, invalid_auth, request_token):
        resp = request_token(data={
            'grant_type': 'password',
            'username': 'foo',
            'password': 'ok',
        }, auth=invalid_auth)
        assert resp['error'] == 'invalid_client'

    @pytest.mark.skip(reason='Пока не реализовано')
    def test_invalid_scope(self, request_token, oauth2):
        oauth2.server.scopes_supported = ['profile']
        resp = request_token(data={
            'grant_type': 'password',
            'username': 'foo',
            'password': 'ok',
            'scope': 'invalid'
        }, auth=('password-client', 'password-secret'))
        assert resp['error'] == 'invalid_scope'

    @pytest.mark.parametrize('data', (
        {},
        {'grant_type': 'invalid_grant'},
    ), ids=repr)
    def test_unsupported_grant_type(self, data, request_token):
        resp = request_token(data=data, auth=('password-client', 'password-secret'))
        assert resp['error'] == 'unsupported_grant_type'

    @pytest.mark.parametrize('data', (
        {},
        {'username': 'foo'},
        {'password': 'wrong'},
        {'username': 'foo', 'password': 'wrong'},
    ), ids=repr)
    def test_invalid_request(self, data, request_token):
        resp = request_token(data={
            'grant_type': 'password',
            **data
        }, auth=('password-client', 'password-secret'))
        assert resp['error'] == 'invalid_request'

    def test_authorize_token(self, request_token):
        resp = request_token(data={
            'grant_type': 'password',
            'username': 'foo',
            'password': 'ok',
        }, auth=('password-client', 'password-secret'))
        assert 'access_token' in resp


def test_unauthorized_client(make_oauth_client, request_token):
    make_oauth_client(['invalid_grant_type'])
    resp = request_token(data={
        'grant_type': 'password',
        'username': 'foo',
        'password': 'ok',
    }, auth=('password-client', 'password-secret'))
    assert resp['error'] == 'unauthorized_client'
