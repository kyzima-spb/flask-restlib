from flask import Flask
from flask_restlib import RestLib
from flask_restlib.contrib.sqla import SQLAFactory
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
def rest(app):
    return RestLib(app, factory=SQLAFactory())


@pytest.fixture
def factory():
    return SQLAFactory()
