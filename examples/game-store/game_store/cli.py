import click
from flask.cli import AppGroup, with_appcontext
from flask_restlib import resource_manager, authorization_server

from .models import db


cli = AppGroup('store')


@cli.command()
@with_appcontext
def init_db():
    db.create_all()


@cli.command()
@click.argument('email')
@click.option(
    '--password',
    help='Password',
    prompt=True,
    confirmation_prompt=True,
    hide_input=True
)
@click.option('--name', prompt=True)
def superuser(email, password, name):
    with resource_manager() as rm:
        rm.create(authorization_server.OAuth2User, {
            'email': email,
            'password': password,
            'is_active': True,
            'is_admin': True,
            'display_name': name,
        })
        click.secho('Super user successfully created.', color='green')
