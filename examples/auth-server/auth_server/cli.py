import sys

import click
from flask.cli import AppGroup, with_appcontext
from flask_restlib import resource_manager

from .models import db, Scope, Role, User


cli = AppGroup('db')


@cli.command()
@with_appcontext
def drop():
    """Drop all tables in database."""
    if click.confirm('Are you sure you want to delete the database?'):
        db.get_connection().drop_database('auth')
        click.secho('OK', fg='bright_green')


@cli.command()
@with_appcontext
def init():
    """Initialize database with test data."""
    if db.get_db().list_collection_names():
        click.secho('The database is not empty.', err=True, fg='bright_red')
        sys.exit(1)

    with resource_manager() as rm:
        profile_scope = rm.create(Scope, {'name': 'profile', 'description': 'Get profile data'})
        api_scope = rm.create(Scope, {'name': 'api', 'description': 'Call all api methods'})

        user_role = rm.create(Role, {
            'name': 'user',
            'description': 'Regular user',
            'scope': [profile_scope],
        })

        admin_role = rm.create(Role, {
            'name': 'admin',
            'description': 'System administrator',
            'scope': [api_scope],
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

        click.secho('OK', fg='bright_green')
