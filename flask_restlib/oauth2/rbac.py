from __future__ import annotations
from itertools import chain
import typing as t

from .mixins import (
    ScopeMixin,
    UserMixin as _UserMixin
)
from ..utils import iter_to_scope, scope_to_set


__all__ = (
    'RoleMixin',
    'UserMixin',
)


class RoleMixin(ScopeMixin):
    """A mixin for describing a role that uses scopes."""

    def _get_child_scope(self) -> set[str]:
        """Returns the scope set of child roles."""
        return set(chain.from_iterable(
            scope_to_set(r.get_scope()) for r in self.get_children()
        ))

    def _get_role_scope(self) -> set[str]:
        """Returns the scope set of the current role."""
        raise NotImplementedError

    def get_children(self) -> t.Sequence[RoleMixin]:
        """Returns child roles."""
        try:
            return getattr(self, 'children')
        except AttributeError:
            raise NotImplementedError(
                'No `children` attribute - '
                f'override the `{self.__class__.__name__}.get_children()` method.'
            )

    def get_scope(self) -> str:
        """Returns the scopes of the role."""
        return iter_to_scope(
            self._get_role_scope() | self._get_child_scope()
        )


class UserMixin(ScopeMixin, _UserMixin):
    """A mixin for describing a user that uses roles."""

    def get_roles(self) -> t.Sequence[RoleMixin]:
        """Returns the roles assigned to the user."""
        try:
            return getattr(self, 'roles')
        except AttributeError:
            raise NotImplementedError(
                'No `roles` attribute - '
                f'override the `{self.__class__.__name__}.get_roles()` method.'
            )

    def get_scope(self) -> str:
        """Returns the scopes assigned to the user."""
        return iter_to_scope(chain.from_iterable(
            scope_to_set(r.get_scope()) for r in self.get_roles()
        ))
