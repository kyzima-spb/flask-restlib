from __future__ import annotations
from itertools import chain
import typing as t

from .mixins import (
    ScopeMixin,
    UserMixin as _UserMixin
)
from ..decorators import getattr_or_implement
from ..utils import iter_to_scope, scope_to_set


__all__ = (
    'RoleMixin',
    'UserMixin',
)


class RoleMixin(ScopeMixin):
    """A mixin for describing a role that uses scopes."""

    def __str__(self) -> str:
        return self.get_name()

    def _get_child_scopes(self) -> set[t.Any]:
        """Returns the scope set of child roles."""
        return set(chain.from_iterable(
            r.get_scopes() for r in self.get_children()
        ))

    def _get_role_scopes(self) -> set[t.Any]:
        """Returns the scope set of the current role."""
        raise NotImplementedError(
            f'The `{self.__class__.__name__}.scopes` attribute does not exist, '
            f'override the `{self.__class__.__name__}._get_role_scope()` method.'
        )

    @getattr_or_implement
    def get_children(self) -> t.Sequence[RoleMixin]:
        """Returns child roles."""
        return getattr(self, 'children')

    @getattr_or_implement
    def get_description(self) -> str:
        """Returns the full description of the role."""
        return getattr(self, 'description')

    @getattr_or_implement
    def get_name(self) -> str:
        """Returns the programmatic name of the role, which is unique."""
        return getattr(self, 'name')

    def get_scopes(self) -> set[t.Any]:
        """Returns the scopes of the role."""
        try:
            role_scopes = super().get_scopes()
        except NotImplementedError:
            role_scopes = self._get_role_scopes()
        return role_scopes | self._get_child_scopes()


class UserMixin(ScopeMixin, _UserMixin):
    """A mixin for describing a user that uses roles."""

    @getattr_or_implement
    def get_roles(self) -> t.Sequence[RoleMixin]:
        """Returns the roles assigned to the user."""
        return getattr(self, 'roles')

    def get_scopes(self) -> set[t.Any]:
        """Returns the scopes assigned to the user."""
        return set(chain.from_iterable(
            r.get_scopes() for r in self.get_roles()
        ))
