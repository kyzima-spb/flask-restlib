from __future__ import annotations
from abc import ABCMeta, abstractmethod
import copy
from types import TracebackType
import typing as t

from . import exceptions
from .types import (
    TIdentifier,
    TQueryFilter,
)


__all__ = (
    'AbstractQueryAdapter',
    'AbstractQueryExpression',
    'AbstractResourceManager',
)


TQueryExpression = t.TypeVar('TQueryExpression', bound='AbstractQueryExpression')
TQueryAdapter = t.TypeVar('TQueryAdapter', bound='AbstractQueryAdapter')
TNativeQuery = t.TypeVar('TNativeQuery')
TResourceManager = t.TypeVar('TResourceManager', bound='AbstractResourceManager')
TModel = t.TypeVar('TModel')


class AbstractQueryExpression(
    t.Generic[TNativeQuery],
    metaclass=ABCMeta
):
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
    def __call__(self, q: TNativeQuery) -> TNativeQuery:
        """
        Applies the current filter to the given queryset and returns the native queryset.

        Arguments:
            q: native queryset.
        """

    @abstractmethod
    def __and__(self: TQueryExpression, other: t.Any) -> TQueryExpression:
        """Implement the ``&`` operator."""

    @abstractmethod
    def __or__(self: TQueryExpression, other: t.Any) -> TQueryExpression:
        """Implement the ``|`` operator."""

    @abstractmethod
    def __eq__(self: TQueryExpression, other: t.Any) -> TQueryExpression:  # type: ignore
        """Implement the ``==`` operator."""

    @abstractmethod
    def __ne__(self: TQueryExpression, other: t.Any) -> TQueryExpression:  # type: ignore
        """Implement the ``!=`` operator."""

    @abstractmethod
    def __lt__(self: TQueryExpression, other: t.Any) -> TQueryExpression:
        """Implement the ``<`` operator."""

    @abstractmethod
    def __le__(self: TQueryExpression, other: t.Any) -> TQueryExpression:
        """Implement the ``<=`` operator."""

    @abstractmethod
    def __gt__(self: TQueryExpression, other: t.Any) -> TQueryExpression:
        """Implement the ``>`` operator."""

    @abstractmethod
    def __ge__(self: TQueryExpression, other: t.Any) -> TQueryExpression:
        """Implement the ``>=`` operator."""

    def to_native(self, expr: t.Any) -> TNativeQuery:
        """Retrieves a native expression from the adapter and returns it."""
        if isinstance(expr, self.__class__):
            return expr._native_expression
        return expr


class AbstractQueryAdapter(
    t.Generic[TNativeQuery],
    metaclass=ABCMeta
):
    __slots__ = (
        '_base_query',
        '_limit',
        '_offset',
        '_order_by',
    )

    def __init__(
        self: TQueryAdapter,
        base_query: t.Union[TNativeQuery, TQueryAdapter]
    ) -> None:
        """
        Arguments:
            base_query: native queryset or a reference to the model class.
        """
        self._base_query: TNativeQuery

        if isinstance(base_query, self.__class__):
            self._base_query = base_query.make_query()
        else:
            self._base_query = self.prepare_query(base_query)

        self._limit: t.Optional[int] = None
        self._offset: t.Optional[int] = None
        self._order_by: list[tuple] = []

    def __iter__(self) -> t.Iterator[t.Any]:
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
    def make_query(self) -> TNativeQuery:
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
        column: t.Union[str, tuple[str, bool]],
        *columns: t.Union[str, tuple[str, bool]]
    ) -> TQueryAdapter:
        """Applies sorting by attribute."""
        self._order_by.append((column, *columns))
        return self

    @abstractmethod
    def prepare_query(self, base_query: TNativeQuery) -> TNativeQuery:
        """Processes the constructor's input argument and returns a native query."""


class AbstractResourceManager(
    t.Generic[TModel],
    metaclass=ABCMeta
):
    """Manager for working with REST resources."""

    def __enter__(self: TResourceManager) -> TResourceManager:
        return self

    def __exit__(
        self,
        err_type: t.Optional[t.Type[BaseException]],
        err: t.Optional[BaseException],
        traceback: t.Optional[TracebackType]
    ) -> t.Optional[bool]:
        if err is None:
            self.commit()
        else:
            self.rollback()
        return None

    @abstractmethod
    def commit(self) -> None:
        """Saves the changes to persistent storage."""

    @abstractmethod
    def create(
        self,
        model_class: t.Type[TModel],
        data: t.Union[dict, list[dict]]
    ) -> t.Union[TModel, list[TModel]]:
        """
        Creates and returns a new instance of the resource filled with data.

        Arguments:
            model_class: A reference to the model class that describes the REST resource.
            data (dict|list): Resource attributes.
        """

    @abstractmethod
    def delete(self, resource: TModel) -> None:
        """
        Removes the resource from the persistent storage.

        Arguments:
            resource (object): The resource instance.
        """

    @abstractmethod
    def get(
        self,
        model_class: t.Type[TModel],
        identifier: TIdentifier
    ) -> t.Optional[TModel]:
        """
        Returns a resource based on the given identifier, or None if not found.

        Arguments:
            model_class (type): A reference to the model class that describes the REST resource.
            identifier: A scalar, tuple, or dictionary representing the primary key.
        """

    def populate_obj(
        self,
        resource: TModel,
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
        resource: TModel,
        attributes: dict
    ) -> TModel:
        """
        Updates the resource with the values of the passed attributes.

        Arguments:
            resource (object): The resource instance.
            attributes (dict): Resource attributes with new values.
        """
