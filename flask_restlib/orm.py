from __future__ import annotations
from abc import ABCMeta, abstractmethod
import copy
from types import TracebackType
import typing as t

from . import exceptions
from .types import (
    TException,
    TIdentifier,
    TQueryExpression,
    TQueryFilter,
    TResourceManager,
    TQueryAdapter,
)


__all__ = (
    'AbstractQueryAdapter',
    'AbstractQueryExpression',
    'AbstractResourceManager',
)


class AbstractQueryExpression(metaclass=ABCMeta):
    """
    An adapter represent that is:

    * model column that overloads all valid operators;
    * an expression with which one of the valid operators can be used.

    For example::

        >>> from flask_restlib import Q, authorization_server
        >>> model = authorization_server.OAuth2Token
        >>> token = 'abcde12345'
        >>> (Q(model.access_token) == token) | (Q(model.refresh_token) == token)
        <flask_restlib.contrib.sqla.SQLAQueryExpression object at 0x101029dd0>

    An instance of the current class is used as a filter
    for the results of a persistent storage query.
    """

    __slots__ = ('_native_expression',)

    def __init__(self, expr: t.Any) -> None:
        self._native_expression = self.to_native(expr)

    def __repr__(self) -> str:
        return str(self._native_expression)

    @abstractmethod
    def __call__(self, q):
        """
        Applies the current filter to the given queryset and returns the native queryset.

        Arguments:
            q: native queryset.
        """

    @abstractmethod
    def __and__(self, other: t.Any) -> TQueryExpression:
        """Implement the ``&`` operator."""

    @abstractmethod
    def __or__(self, other: t.Any) -> TQueryExpression:
        """Implement the ``|`` operator."""

    @abstractmethod
    def __eq__(self, other: t.Any) -> TQueryExpression:
        """Implement the ``==`` operator."""

    @abstractmethod
    def __ne__(self, other: t.Any) -> TQueryExpression:
        """Implement the ``!=`` operator."""

    @abstractmethod
    def __lt__(self, other: t.Any) -> TQueryExpression:
        """Implement the ``<`` operator."""

    @abstractmethod
    def __le__(self, other: t.Any) -> TQueryExpression:
        """Implement the ``<=`` operator."""

    @abstractmethod
    def __gt__(self, other: t.Any) -> TQueryExpression:
        """Implement the ``>`` operator."""

    @abstractmethod
    def __ge__(self, other: t.Any) -> TQueryExpression:
        """Implement the ``>=`` operator."""

    def to_native(self, expr: t.Any) -> t.Any:
        if isinstance(expr, self.__class__):
            return expr._native_expression
        return expr


class AbstractQueryAdapter(metaclass=ABCMeta):
    __slots__ = (
        '_base_query',
        '_limit',
        '_offset',
        '_order_by',
    )

    def __init__(self, base_query: t.Any) -> None:
        """
        Arguments:
            base_query: native queryset or a reference to the model class.
        """
        if isinstance(base_query, self.__class__):
            base_query = base_query.make_query()

        self._base_query = base_query
        self._limit: t.Optional[int] = None
        self._offset: t.Optional[int] = None
        self._order_by: list[t.Iterable] = [] # fixme: уточнить тип

    def __iter__(self):
        yield from self.all()

    @abstractmethod
    def all(self) -> list:
        """Returns the results represented by this query as a list."""

    @abstractmethod
    def count(self) -> int:
        """Returns the number of rows that should be returned from the query."""

    @abstractmethod
    def exists(self) -> bool:
        """
        Returns true if a resource with the specified search criteria exists in persistent storage.
        """

    def filter(self: TQueryAdapter, filter_callback: TQueryFilter) -> TQueryAdapter:
        """Applies this filter to the current queryset."""
        self._base_query = filter_callback(self.make_query())
        return self

    @abstractmethod
    def filter_by(self: TQueryAdapter, **kwargs: t.Any) -> TQueryAdapter:
        """Applies these criteria to the current queryset."""

    def first(self) -> t.Optional[t.Any]:
        """
        Return the first result of this query or None if the result doesn’t contain any row.
        """
        result = copy.copy(self).limit(1).all()
        return result[0] if len(result) > 0 else None

    def limit(self: TQueryAdapter, value: int) -> TQueryAdapter:
        """Applies a limit on the number of rows selected by the query."""
        self._limit = value
        return self

    @abstractmethod
    def make_query(self) -> t.Any:
        """Creates and returns a native query object."""

    def one(self) -> t.Any:
        """Return exactly one result or raise an exception."""
        try:
            result = self.one_or_none()
        except exceptions.MultipleResourcesFound as err:
            raise exceptions.MultipleResourcesFound(
                f"Multiple rows were found for `{self.__class__.__name__}.one()`."
            ) from err
        else:
            if result is None:
                raise exceptions.NoResourcesFound(
                    f'No row was found for `{self.__class__.__name__}.one()`.'
                )
            return result

    def one_or_none(self) -> t.Optional[t.Any]:
        """
        Return at most one result or raise an exception.
        Returns None if the query selects no rows.
        """
        result = copy.copy(self).limit(2).all()
        found = len(result)

        if found == 0:
            return None

        if found > 1:
            raise exceptions.MultipleResourcesFound(
                f"Multiple rows were found for `{self.__class__.__name__}.one_or_none()`."
            )

        return result[0]

    def offset(self: TQueryAdapter, value: int) -> TQueryAdapter:
        """Applies the offset from which the query will select rows."""
        self._offset = value
        return self

    def order_by(
        self: TQueryAdapter,
        column: str,
        *columns: tuple[str]
    ) -> TQueryAdapter:
        """Applies sorting by attribute."""
        self._order_by.append((column, *columns))
        return self


class AbstractResourceManager(metaclass=ABCMeta):
    """Manager for working with REST resources."""

    def __enter__(self: TResourceManager) -> TResourceManager:
        return self

    def __exit__(
        self,
        err_type: t.Type[TException],
        err: TException,
        traceback: TracebackType
    ) -> None:
        if err is None:
            self.commit()
        else:
            self.rollback()

    @abstractmethod
    def commit(self) -> None:
        """Saves the changes to persistent storage."""

    @abstractmethod
    def create(
        self,
        model_class: t.Any,
        data: t.Union[dict, list[dict]]
    ) -> t.Any:
        """
        Creates and returns a new instance of the resource filled with data.

        Arguments:
            model_class: A reference to the model class that describes the REST resource.
            data (dict|list): Resource attributes.
        """

    @abstractmethod
    def delete(self, resource: t.Any) -> None:
        """
        Removes the resource from the persistent storage.

        Arguments:
            resource (object): The resource instance.
        """

    @abstractmethod
    def get(
        self,
        model_class: t.Type[t.Any],
        identifier: TIdentifier
    ) -> t.Optional[t.Any]:
        """
        Returns a resource based on the given identifier, or None if not found.

        Arguments:
            model_class (type): A reference to the model class that describes the REST resource.
            identifier: A scalar, tuple, or dictionary representing the primary key.
        """

    def populate_obj(
        self,
        resource: t.Any,
        attributes: dict
    ) -> None:
        """
        Populates the attributes of the given resource with data from the given attributes argument.

        Arguments:
            resource (object): The resource instance.
            attributes (dict): Resource attributes with new values.
        """
        for attr, value in attributes.items():
            setattr(resource, attr, value)

    @abstractmethod
    def rollback(self) -> None:
        """Rollback the current transaction in progress."""

    @abstractmethod
    def update(
        self,
        resource: t.Any,
        attributes: dict
    ) -> t.Any:
        """
        Updates the resource with the values of the passed attributes.

        Arguments:
            resource (object): The resource instance.
            attributes (dict): Resource attributes with new values.
        """