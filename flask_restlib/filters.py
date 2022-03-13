from __future__ import annotations
from abc import ABCMeta, abstractmethod
import typing as t

from marshmallow import Schema
from webargs.core import ArgMap as TArgMap
from webargs.flaskparser import parser

from .types import TQueryAdapter


__all__ = (
    'AbstractFilter',
    'TFilter',
)


TFilter = t.TypeVar('TFilter', bound='AbstractFilter')


class AbstractFilter(metaclass=ABCMeta):
    """
    The filter uses a URL query string and schema to collect and validate input data.

    Filtering your results use a unique query parameter for each of your fields.

    For example, to filter users based on their username:
    GET /users?username=admin

    If you would like to add full text search to your API,
    use a q query parameter, for example:
    GET /users?q=Admin
    """

    @abstractmethod
    def __call__(self, q: TQueryAdapter, input_data: dict) -> TQueryAdapter:
        """
        Applies the current filter to the given queryset and returns new queryset.

        Arguments:
            q: current queryset.
            input_data (dict): the input used for filtering.
        """

    def create_schema(self) -> TArgMap:
        """Creates and returns a schema instance that is used to validate the input data."""
        schema = self.schema

        if isinstance(schema, dict):
            schema = Schema.from_dict(schema)

        if isinstance(schema, Schema):
            schema.partial = True

        return schema

    def filter(self, q: TQueryAdapter) -> TQueryAdapter:
        """
        Applies the current filter to the given queryset and returns new queryset.

        Arguments:
            q: current queryset.
        """
        return self(q, self.get_input_data())

    def get_input_data(self) -> dict:
        """Returns the input used for filtering."""
        return parser.parse(self.create_schema(), location='query')

    @property
    @abstractmethod
    def schema(self) -> TArgMap:
        """Defines and returns dictionary or a Schema instance for validating input data."""
