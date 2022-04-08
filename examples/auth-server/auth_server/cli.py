import click
from flask.cli import AppGroup, with_appcontext
from flask_restlib import resource_manager

from .models import db, Scope, Role, User


cli = AppGroup('db')


@cli.command()
@with_appcontext
def create():
    """Create all tables in database."""
    db.create_all()


@cli.command()
@with_appcontext
def drop():
    """Drop all tables in database."""
    db.drop_all()


@cli.command()
@with_appcontext
def init():
    """Initialize database with test data."""
    with resource_manager() as rm:
        user_role = rm.create(Role, {
            'name': 'user',
            'description': 'Regular user',
            'scope': [
                Scope(name='profile', description='Get profile data'),
            ],
        })

        admin_role = rm.create(Role, {
            'name': 'admin',
            'description': 'System administrator',
            'scope': [
                Scope(name='api', description='Call all api methods'),
            ],
            'children': [user_role],
        })

        rm.create(User, {
            'email': 'admin@example.com',
            'password': 'admin',
            'is_active': True,
            'roles': [admin_role],
        })

        rm.create(User, {
            'email': 'user@example.com',
            'password': 'user',
            'is_active': True,
            'roles': [user_role],
        })
