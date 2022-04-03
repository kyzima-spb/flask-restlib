from __future__ import annotations
import typing as t

from authlib.oauth2.rfc6749.grants import BaseGrant
import click
from flask.cli import AppGroup, with_appcontext
from PyInquirer import prompt

from . import validators
from .globals import authorization_server
from .oauth2.authorization_server import (
    save_client,
    get_authentication_methods,
    get_response_types,
    validate_client_id
)
from .types import TFunc


CLIENT_AUTHENTICATION = {
    'client_secret_basic': 'HTTP Basic authentication',
    'client_secret_post': 'Including in the request-body',
    'none': 'No authentication required',
}


api_cli = AppGroup('api', help='Flask-Restlib CLI')


def fill_response_types(answer: dict) -> None:
    """Adds authorization server response types to the current answers."""
    answer['response_types'] = get_response_types(answer['grants'])


def fill_grant_types(answer: dict) -> None:
    """Adds string grant types to the current answers."""
    answer['grant_types'] = [grant.GRANT_TYPE for grant in answer['grants']]


def get_auth_method_choices(grants: list[BaseGrant]) -> list[dict]:
    """
    Returns a list of client authentication methods
    in a format that an input element can understand.
    """
    return [
        {'name': CLIENT_AUTHENTICATION[i], 'value': i}
        for i in get_authentication_methods(grants)
    ]


def get_grant_choices(is_public: bool) -> list[dict]:
    """Returns a list of grants in a format that an input element can understand."""
    grants = authorization_server.get_registered_grants(
        only_public=is_public,
        only_confidential=not is_public
    )
    return [
        {'name': name, 'value': grant} for name, grant in grants.items()
    ]


def make_action_step(func: TFunc) -> dict:
    """
    Creates a step that is always skipped,
    but first applies the passed function to the list of current answers.
    Dirty hack.
    """
    def wrapper(answer: dict) -> bool:
        func(answer)
        return False
    return {
        'type': 'input',
        'name': '',
        'message': '',
        'when': wrapper,
    }


def validate_url(value: str, multiline: bool = False, required: bool = False) -> t.Union[bool, str]:
    if not value:
        return 'Input required' if required else True

    uris = value.splitlines() if multiline else [value]
    validator = validators.URL()

    for i in uris:
        try:
            validator(i)
        except validators.ValidationError:
            return f'Not a valid URL: {i}'

    return True


def validate_user(ctx, param, value):
    with ctx.obj.load_app().app_context():
        user = authorization_server.OAuth2User.find_by_username(value)
        if user is None:
            raise click.BadParameter('User not exist.')
        return user


@api_cli.command()  # type: ignore
@click.argument('user', metavar='USERNAME', callback=validate_user)
def create_client(user: t.Any) -> None:
    """Create OAuth2 client."""
    data = prompt(
        [
            {
                'type': 'list',
                'name': 'is_public',
                'message': 'Choice client type',
                'choices': ['Public', 'Confidential'],
                'filter': lambda client_type: client_type == 'Public',
            },
            {
                'type': 'input',
                'name': 'client_id',
                'message': 'Enter client ID',
                'validate': lambda answer: (
                    not answer or validate_client_id(answer) or 'Client ID already exists.'
                ),
            },
            {
                'type': 'input',
                'name': 'client_secret',
                'message': 'Enter client secret',
                'when': lambda answer: not answer['is_public'],
            },
        ]
    )
    metadata: dict = prompt(
        [
            {
                'type': 'input',
                'name': 'client_name',
                'message': 'Enter client name',
                'validate': bool,
            },
            {
                'type': 'input',
                'name': 'client_description',
                'message': 'Enter client description',
            },
            {
                'type': 'checkbox',
                'name': 'grants',
                'message': 'Choice grant types',
                'choices': lambda answer: get_grant_choices(data['is_public']),
                'validate': lambda answer: bool(answer) or 'You must choose at least one grant.',
            },
            make_action_step(fill_grant_types),
            make_action_step(fill_response_types),
            {
                'type': 'list',
                'name': 'token_endpoint_auth_method',
                'message': 'Choice client authorization method',
                'when': lambda answer: not data['is_public'],
                'choices': lambda answer: get_auth_method_choices(answer['grants']),
            },
            {
                'type': 'input',
                'name': 'redirect_uris',
                'message': (
                    'Enter redirect URI (Each URL is on a separate line)\n'
                    '  Press Meta+Enter in order to accept the input or Escape followed by Enter\n'
                    '  > '
                ),
                'when': lambda answer: answer['response_types'],
                'filter': lambda value: value.splitlines(),
                'validate': lambda uris: validate_url(uris, multiline=True, required=True),
                'multiline': True,
            },
            {
                'type': 'input',
                'name': 'scope',
                'message': 'Enter a space-separated list of scope values',
            },
            {
                'type': 'confirm',
                'name': 'additional',
                'message': 'Enter additional client information?',
                'default': False,
            },
            make_action_step(lambda answer: answer.pop('grants')),
        ]
    )

    if metadata.pop('additional'):
        additional_metadata = prompt([
            {
                'type': 'input',
                'name': 'client_uri',
                'message': 'Enter URL with client information',
                'validate': validate_url,
            },
            {
                'type': 'input',
                'name': 'logo_uri',
                'message': 'Enter logo URL',
                'validate': validate_url,
            },
            {
                'type': 'input',
                'name': 'contacts',
                'message': (
                    'Ways to contact people responsible for this client\n'
                    '  Typically email addresses (Each contact is on a separate line)\n'
                    '  Press Meta+Enter in order to accept the input or Escape followed by Enter\n'
                    '  > '
                ),
                'filter': lambda value: value.splitlines() if value else [],
                'multiline': True,
            },
            {
                'type': 'input',
                'name': 'tos_uri',
                'message': (
                    'Enter URL to a human-readable terms of service document\n'
                    '  (https://tools.ietf.org/html/rfc7591#section-2.2)\n'
                ),
                'validate': validate_url,
            },
            {
                'type': 'input',
                'name': 'policy_uri',
                'message': (
                    'Enter URL to a human-readable privacy policy document\n'
                    '  (https://tools.ietf.org/html/rfc7591#section-2.2)\n'
                ),
                'validate': validate_url,
            },
        ])
        metadata.update({k: v for k, v in additional_metadata.items() if v})

    client = save_client(user=user, client_metadata=metadata, **data)

    click.secho(
        '\nYou have successfully created a new OAuth 2.0 client.',
        fg='bright_green',
        bold=True
    )
    click.secho(f'''
        Client ID:     {client.id}
        Client secret: {client.client_secret}
    ''')
