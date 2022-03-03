from __future__ import annotations
import typing as t

from flask import request, current_app
from marshmallow.fields import String
from webargs.fields import DelimitedList
from webargs import validate as validators
from webargs.core import ArgMap as TArgMap
from webargs.flaskparser import parser

from .utils import strip_sorting_flag
from .types import TQueryAdapter


__all__ = ('SortHandler', 'TSortHandler',)


TSortHandler = t.TypeVar('TSortHandler', bound='SortHandler')


class SortHandler:
    __slots__ = ('_sorting_fields', '_sort_param_name')

    def __init__(self, sorting_fields: t.Sequence[str], sort_param_name: str = '') -> None:
        """
        Arguments:
            sorting_fields: The names of the attributes of the model to be sorted.
            sort_param_name (str): the name of the URL parameter that is used for sorting.
        """
        self._sorting_fields: set[str] = set(sorting_fields)
        self._sort_param_name = sort_param_name

    def __call__(self, q: TQueryAdapter, input_data: t.Dict[str, bool]) -> TQueryAdapter:
        """
        Applies a sort to the given queryset and returns new queryset.

        Arguments:
            q: current queryset.
            input_data (dict): sorting rules.
        """
        return q.order_by(*input_data.items())

    def execute(self, q: TQueryAdapter) -> TQueryAdapter:
        """
        Applies a sort to the given queryset and returns new queryset.

        Arguments:
            q: current queryset.

        """
        if request.args.get(self.sort_param_name):
            input_data = {
                strip_sorting_flag(param): param.startswith('-')
                for param in parser.parse(self.schema, location='query')['sort']
            }
            q = self(q, input_data)
        return q

    @property
    def schema(self) -> TArgMap:
        class Validator(validators.OneOf):
            def __call__(self, value: t.Any) -> t.Any:
                return super().__call__(strip_sorting_flag(value))

        return {
            'sort': DelimitedList(
                String(
                    validate=Validator(self._sorting_fields),
                    data_key=self.sort_param_name,
                ),
                missing=(),
            )
        }

    @property
    def sort_param_name(self) -> str:
        """Returns the name of the URL parameter that is used for sorting."""
        if not self._sort_param_name:
            self._sort_param_name = current_app.config['RESTLIB_URL_PARAM_SORT']
        return self._sort_param_name
