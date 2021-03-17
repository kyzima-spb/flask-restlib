from __future__ import annotations
from abc import ABCMeta, abstractmethod

from flask import abort


class AbstractQueryBuilder(metaclass=ABCMeta):
    __slots__ = (
        '_base_query', '_query',
        '_limit', '_offset',
        '_order_by',
    )

    def __init__(self, base_query=None):
        if isinstance(base_query, self.__class__):
            base_query = base_query.make_query()

        self._base_query = base_query
        self._query = None
        self._limit = None
        self._offset = None
        self._order_by = set()

    def __iter__(self):
        yield from self.all()

    @abstractmethod
    def _do_select(self, *entities):
        """Creates and returns a native query object using the passed list of models."""

    @abstractmethod
    def all(self) -> list:
        """Returns the results represented by this query as a list."""

    @abstractmethod
    def count(self) -> int:
        """Returns the number of rows that should be returned from the query."""

    @abstractmethod
    def exists(self) -> bool:
        """Returns true if a resource with the specified search criteria exists in persistent storage."""

    @abstractmethod
    def get(self, identifier):
        """Returns a resource based on the given identifier, or None if not found."""

    def get_or_404(self, identifier, description=None):
        """Returns a resource based on the given identifier, throws an HTTP 404 error."""
        resource = self.get(identifier)

        if resource is None:
            abort(404, description=description)

        return resource

    def limit(self, value: int) -> AbstractQueryBuilder:
        """Applies a limit on the number of rows selected by the query."""
        self._limit = value
        return self

    @abstractmethod
    def make_query(self):
        """Creates and returns a native query object."""

    def offset(self, value: int) -> AbstractQueryBuilder:
        """Applies the offset from which the query will select rows."""
        self._offset = value
        return self

    def order_by(self, value) -> AbstractQueryBuilder:
        """Applies sorting by attribute."""
        self._order_by.add(value)
        return self

    def select(self, entity, *entities) -> AbstractQueryBuilder:
        """Using the passed list of models, creates a native query object."""
        if self._base_query is not None:
            raise RuntimeError(
                'If the constructor uses a basic query,'
                f' the `{self.__class__.__name__}.select()` method is not allowed.'
            )

        if self._query is not None:
            raise RuntimeError(
                f'The `{self.__class__.__name__}.select()` method can only be used once. '
            )

        self._query = self._do_select(entity, *entities)

        return self


class AbstractResourceManager(metaclass=ABCMeta):
    """Manager for working with REST resources."""

    def __enter__(self):
        return self

    def __exit__(self, err_type, err, traceback):
        if err is None:
            self.commit()

    @abstractmethod
    def commit(self):
        """Saves the changes to persistent storage."""

    @abstractmethod
    def create(self, model_class, data):
        """
        Creates and returns a new instance of the resource filled with data.

        Arguments:
            model_class: A reference to the model class that describes the REST resource.
            data (dict|list): Resource attributes.
        """

    @abstractmethod
    def delete(self, resource):
        """
        Removes the resource from the persistent storage.

        Arguments:
            resource (object): The resource instance.
        """

    def update(self, resource, attributes):
        """
        Updates the resource with the values of the passed attributes.

        Arguments:
            resource (object): The resource instance.
            attributes (dict): Resource attributes with new values.
        """
        for attr, value in attributes.items():
            setattr(resource, attr, value)


class AbstractFactory(metaclass=ABCMeta):
    """
    Abstract factory.

    Is used for:
    1. create a persistent storage query adapter
    2. creating a resource manager
    3. creating an automatically generated schema
    """

    @abstractmethod
    def create_query_builder(self, base_query=None):
        """
        Creates and returns a queryset for retrieving resources from persistent storage.
        """

    @abstractmethod
    def create_resource_manager(self):
        """Creates and returns a resource manager instance."""

    @abstractmethod
    def create_schema(self, model_class):
        """
        Creates and returns an automatic schema class.

        Arguments:
            model_class: A reference to the model class that describes the REST resource.
        """
