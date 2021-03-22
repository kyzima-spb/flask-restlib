from __future__ import annotations
from abc import ABCMeta, abstractmethod
import typing

from flask import abort
from marshmallow import Schema
from webargs.flaskparser import parser


__all__ = (
    'AbstractQueryAdapter',
    'AbstractResourceManager',
    'AbstractFactory',
    'AbstractFilter',
)


class AbstractFilter(metaclass=ABCMeta):
    """
    An instance of the current class is used as a filter
    for the results of a persistent storage query.
    """

    @abstractmethod
    def apply_to(self, q):
        """
        Applies the current filter to the given queryset and returns the native queryset.

        Arguments:
            q: native queryset.
        """


class UrlQueryFilter(AbstractFilter):
    """
    The filter uses a URL query string and schema to collect and validate input data.

    Filtering your results use a unique query parameter for each of your fields.

    For example, to filter users based on their username:
    GET /users?username=admin

    If you would like to add full text search to your API,
    use a q query parameter, for example:
    GET /users?q=Admin
    """

    def __init__(self, filter_schema: typing.Union[type, Schema]):
        """
        Arguments:
            filter_schema (type|Schema):
                A reference to a schema class, or an instance for collecting and validating input data.
        """
        if isinstance(filter_schema, type):
            filter_schema = filter_schema(partial=True)
        else:
            if not filter_schema.partial:
                filter_schema.partial = True

        self._filter_schema = filter_schema

    @abstractmethod
    def _do_apply(self, q, input_data: dict):
        """
        Applies the current filter to the given queryset and returns the native queryset.

        Arguments:
            q: native queryset.
            input_data (dict): the input used for filtering.
        """

    def apply_to(self, q):
        input_data = self.get_input_data()
        return self._do_apply(q, input_data)

    def get_input_data(self) -> dict:
        """Returns the input used for filtering."""
        return parser.parse(self._filter_schema, location='query')


class AbstractQueryAdapter(metaclass=ABCMeta):
    __slots__ = (
        '_base_query', '_model_class',
        '_limit', '_offset',
        '_order_by',
    )

    def __init__(self, base_query=None):
        if isinstance(base_query, self.__class__):
            base_query = base_query.make_query()

        self._base_query = base_query
        self._model_class = None
        self._limit = None
        self._offset = None
        self._order_by = []

    def __iter__(self):
        yield from self.all()

    @abstractmethod
    def _do_select(self):
        """Creates and returns a native query object using the passed list of models."""

    def _get_query(self):
        """Returns the native queryset."""
        if self._base_query is None:
            return self._do_select()
        return self._base_query

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
    def filter(self, filter_: AbstractFilter) -> AbstractQueryAdapter:
        """Applies this filter to the current queryset."""

    @abstractmethod
    def get(self, identifier):
        """Returns a resource based on the given identifier, or None if not found."""

    def get_or_404(self, identifier, description=None):
        """Returns a resource based on the given identifier, throws an HTTP 404 error."""
        resource = self.get(identifier)

        if resource is None:
            abort(404, description=description)

        return resource

    def limit(self, value: int) -> AbstractQueryAdapter:
        """Applies a limit on the number of rows selected by the query."""
        self._limit = value
        return self

    @abstractmethod
    def make_query(self):
        """Creates and returns a native query object."""

    def offset(self, value: int) -> AbstractQueryAdapter:
        """Applies the offset from which the query will select rows."""
        self._offset = value
        return self

    def order_by(self, column, *columns) -> AbstractQueryAdapter:
        """Applies sorting by attribute."""
        self._order_by.append((column, *columns))
        return self

    def select(self, model_class) -> AbstractQueryAdapter:
        """Using the passed list of models, creates a native query object."""
        if self._base_query is not None:
            raise RuntimeError(
                'If the constructor uses a basic query,'
                f' the `{self.__class__.__name__}.select()` method is not allowed.'
            )

        if self._model_class is not None:
            raise RuntimeError(
                f'The `{self.__class__.__name__}.select()` method can only be used once. '
            )

        self._model_class = model_class

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
    def create_query_adapter(self, base_query=None) -> AbstractQueryAdapter:
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

    @abstractmethod
    def get_schema_class(self):
        """
        Returns a reference to the base class of the schema
        used in serialization and validation.
        """

    @abstractmethod
    def get_schema_options_class(self):
        """Returns a reference to the base schema options class."""
