import sys

import click
from flask.cli import AppGroup, with_appcontext
from flask_restlib import resource_manager, authorization_server
# from flask_restlib.cli import save_client

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
        oauth_scope = rm.create(Scope, {'name': 'oauth', 'description': 'Manage OAuth2'})
        api_scope = rm.create(Scope, {'name': 'api', 'description': 'Call all api methods'})

        user_role = rm.create(Role, {
            'name': 'user',
            'description': 'Regular user',
            'scopes': [profile_scope],
            # 'scopes': ['profile'],
        })

        admin_role = rm.create(Role, {
            'name': 'admin',
            'description': 'System administrator',
            'scopes': [api_scope],
            # 'scopes': ['api'],
            'children': [user_role],
        })

        admin_user = rm.create(User, {
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

        client = rm.create(authorization_server.OAuth2Client, {
            'user': admin_user,
            'id': 'test',
            'client_secret': 'test',
            'client_metadata': {
                'client_name': 'Client for administration',
                'grant_types': [
                    'authorization_code',
                    'refresh_token',
                ],
                'response_types': [
                    'code',
                ],
                'token_endpoint_auth_method': 'client_secret_basic',
                'redirect_uris': [
                    'http://127.0.0.1:5000/blank',
                ],
            },
            'scopes': [api_scope, profile_scope],
            # 'scopes': ['api', 'profile'],
        })

        click.secho('OK', fg='bright_green')


from PyInquirer import prompt


@cli.command()
@with_appcontext
def test():
    pass


    # admin_role = Role.objects(name='admin').first()
    # print(admin_role._get_child_scopes())
    # print(admin_role.get_scopes())
    # print(admin_role.get_scope())
    # print(admin_role.get_allowed_scope('oauth'))

    # admin_user = User.objects(email='admin@example.com').first()
    # print(admin_user.get_scopes())
    # print(admin_user.get_scope())

    # client = authorization_server.OAuth2Client.objects(id='test').first()
    # print(client.get_scope())

    # api_scope1 = Scope.objects(name='api').first()
    # api_scope2 = Scope.objects(name='api').first()
    # print(api_scope1 is api_scope2)
    # print(hash(api_scope1), hash(api_scope2))
    # print(api_scope1 == api_scope2)
