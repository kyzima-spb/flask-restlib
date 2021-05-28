from flask import Flask
from flask_restlib import RestLib
from flask_restlib.contrib.sqla import SQLAFactory
from flask_restlib.oauth2 import OAuth2
from flask_sqlalchemy import SQLAlchemy
import pytest


@pytest.fixture
def create_app(request):
    def factory(test_config=None):
        app = Flask(request.module.__name__)
        app.testing = True
        app.config['SECRET_KEY'] = 'Testing application'
        app.config.from_mapping(test_config)
        return app
    return factory


@pytest.fixture
def app(create_app, monkeypatch):
    monkeypatch.setenv('AUTHLIB_INSECURE_TRANSPORT', 'true')
    return create_app({
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
    })


@pytest.fixture
def client(app):
    with app.test_client() as client:
        yield client


@pytest.fixture
def db(app):
    return SQLAlchemy(app)


@pytest.fixture
def Genre(db):
    class Genre(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        name = db.Column(db.String(30), nullable=False)

        def __repr__(self):
            return f'{self.__class__.__name__}(name={self.name!r})'

    Genre.__table__.create(db.engine)
    yield Genre
    Genre.__table__.drop(db.engine)


@pytest.fixture
def User(db):
    class User(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        username = db.Column(db.String(40), nullable=False, unique=True)

        def __repr__(self):
            return f'{self.__class__.__name__}(name={self.username!r})'

        def get_user_id(self):
            return self.id

        def check_password(self, password):
            return password != 'wrong'

        @classmethod
        def find_by_username(cls, username):
            return cls.query.filter_by(username=username).first()

    User.__table__.create(db.engine)
    yield User
    User.__table__.drop(db.engine)


@pytest.fixture
def rest(app):
    return RestLib(app, factory=SQLAFactory())


@pytest.fixture
def oauth2(app, rest, User):
    return OAuth2(app, factory=rest.factory, user_model=User)


@pytest.fixture
def OAuth2Client(db, oauth2):
    oauth2.OAuth2Client.__table__.create(db.engine)
    yield oauth2.OAuth2Client
    oauth2.OAuth2Client.__table__.drop(db.engine)


@pytest.fixture
def OAuth2Token(db, oauth2):
    oauth2.OAuth2Token.__table__.create(db.engine)
    yield oauth2.OAuth2Token
    oauth2.OAuth2Token.__table__.drop(db.engine)


@pytest.fixture
def OAuth2Code(db, oauth2):
    oauth2.OAuth2Code.__table__.create(db.engine)
    yield oauth2.OAuth2Code
    oauth2.OAuth2Code.__table__.drop(db.engine)


@pytest.fixture
def factory():
    return SQLAFactory()


@pytest.fixture
def query_adapter(app, factory):
    def f(base_query):
        with app.app_context():
            yield factory.create_query_adapter(base_query)
    return f


@pytest.fixture
def resource_manager(app, factory):
    with app.app_context():
        yield factory.create_resource_manager()
