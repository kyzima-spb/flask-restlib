from __future__ import annotations
from abc import ABCMeta, abstractmethod
from functools import wraps
import typing as t

from authlib.oauth2 import OAuth2Error
from authlib.oauth2.rfc6749 import MissingAuthorizationError
from authlib.integrations.flask_oauth2.resource_protector import ResourceProtector
from flask import request
from flask_login import current_user

from .globals import current_restlib
from .exceptions import AuthenticationError, AuthorizationError
from .types import TView


_F = t.TypeVar('_F', bound=t.Callable[['Permission', 'Permission'], 'Permission'])


def check_type(method: _F) -> _F:
    @wraps(method)
    def wrapper(self: Permission, other: Permission) -> Permission:
        if isinstance(other, Permission):
            return method(self, other)
        return NotImplemented
    return t.cast(_F, wrapper)


class Permission(metaclass=ABCMeta):
    """
    A base class from which all permission classes should inherit.
    """

    @check_type
    def __and__(self, other: Permission) -> Permission:
        return AND(self, other)

    @check_type
    def __or__(self, other: Permission) -> Permission:
        return OR(self, other)

    @check_type
    def __rand__(self, other: Permission) -> Permission:
        return AND(other, self)

    @check_type
    def __ror__(self, other: Permission) -> Permission:
        return OR(other, self)

    @abstractmethod
    def check_permission(self, view: TView, resource: t.Optional[t.Any] = None) -> None:
        """
        Checks if permission was granted, otherwise raises any exception.

        If passed resource then checks if permission for the object was granted.
        """


class AND(Permission):
    """Access is allowed if both operands succeed."""

    def __init__(self, op1: Permission, op2: Permission) -> None:
        self.op1 = op1
        self.op2 = op2

    def check_permission(self, view: TView, resource: t.Optional[t.Any] = None) -> None:
        self.op1.check_permission(view, resource)
        self.op2.check_permission(view, resource)


class OR(Permission):
    """Access is allowed if one of the operands succeeds."""

    def __init__(self, op1: Permission, op2: Permission) -> None:
        self.op1 = op1
        self.op2 = op2

    def check_permission(self, view: TView, resource: t.Optional[t.Any] = None) -> None:
        try:
            self.op1.check_permission(view, resource)
        except:
            self.op2.check_permission(view, resource)


class IsAuthenticated(Permission):
    """Allows access only to authenticated users."""

    def check_permission(self, view: TView, resource: t.Optional[t.Any] = None) -> None:
        if not current_user.is_authenticated:
            raise AuthenticationError


class PublicMethods(Permission):
    """Allows public access only for the listed methods."""

    def __init__(self, methods: t.Sequence[str]) -> None:
        self.methods = set(methods)

    def check_permission(self, view: TView, resource: t.Optional[t.Any] = None) -> None:
        if request.method not in self.methods:
            raise AuthenticationError


class TokenHasScope(Permission):
    """
    The TokenHasScope permission class allows access
    when the current access token has been authorized for all the scopes.
    """
    def __init__(
        self,
        scope: t.Optional[t.Union[str, list]] = None,
        optional: bool = False
    ) -> None:
        """
        Arguments:
            scope (str|list): string or list of scope values.
            optional (bool): allow if no token is given.
        """
        self.scope = scope
        self.optional = optional

    def get_resource_protector(self) -> ResourceProtector:
        return current_restlib.resource_protector

    def check_permission(self, view: TView, resource: t.Optional[t.Any] = None) -> None:
        try:
            self.get_resource_protector().acquire_token(self.scope)
        except MissingAuthorizationError as err:
            if not self.optional:
                raise AuthenticationError(err.get_error_description()) from err
        except OAuth2Error as err:
            msg = err.get_error_description() or str(err)
            raise AuthorizationError(msg) from err
