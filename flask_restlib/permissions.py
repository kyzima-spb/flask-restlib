from __future__ import annotations
import typing

from authlib.oauth2 import OAuth2Error
from authlib.oauth2.rfc6749 import MissingAuthorizationError
from authlib.integrations.flask_oauth2.resource_protector import ResourceProtector
from flask_login import current_user
from flask_restlib import current_restlib
from flask_restlib.exceptions import AuthenticationError, AuthorizationError


class Permission:
    """A base class from which all permission classes should inherit."""

    def check_permission(self, view) -> typing.NoReturn:
        """
        Checks if permission was granted,
        otherwise raises `AuthorizationError` or `AuthenticationError`.
        """

    def check_resource_permission(self, view, resource) -> typing.NoReturn:
        """
        Checks if permission for the object was granted,
        otherwise raises `AuthorizationError`.
        """


class IsAuthenticated(Permission):
    """Allows access only to authenticated users."""

    def check_permission(self, view) -> typing.NoReturn:
        if not current_user.is_authenticated:
            raise AuthenticationError


class TokenHasScope(Permission):
    """
    The TokenHasScope permission class allows access
    when the current access token has been authorized for all the scopes.
    """
    def __init__(
        self,
        scope: typing.Optional[typing.Union[str, list]] = None,
        operator: str = 'AND',
        optional: bool = False
    ):
        """
        Arguments:
            scope (str|list): string or list of scope values.
            operator (str): value of "AND" or "OR".
            optional (bool): allow if no token is given.
        """
        self.scope = scope
        self.operator = operator
        self.optional = optional

    def get_resource_protector(self) -> ResourceProtector:
        return current_restlib.resource_protector

    def check_permission(self, view) -> typing.NoReturn:
        try:
            self.get_resource_protector().acquire_token(
                self.scope, self.operator
            )
        except MissingAuthorizationError as err:
            if not self.optional:
                raise AuthenticationError(err.get_error_description()) from err
        except OAuth2Error as err:
            raise AuthorizationError(err.get_error_description()) from err