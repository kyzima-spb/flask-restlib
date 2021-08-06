from __future__ import annotations
from abc import ABCMeta, abstractmethod
from copy import copy
import typing as t

from flask import current_app
from webargs import fields
from webargs import validate as validators
from webargs.flaskparser import parser

from .http import url_update_query_string
from .types import (
    THttpHeader,
    THttpHeaders,
    TQueryAdapter,
)


__all__ = (
    'AbstractPagination',
    'LimitOffsetPagination',
)

TPagination = t.TypeVar('TPagination', bound='AbstractPagination')


class AbstractPagination(t.Generic[TPagination], metaclass=ABCMeta):
    # https://habr.com/ru/company/ruvds/blog/513766/
    # https://medium.com/swlh/how-to-implement-cursor-pagination-like-a-pro-513140b65f32

    __slots__ = ('_default_limit', '_limit_param_name',)

    def __init__(
        self,
        *,
        default_limit: int = None,
        limit_param_name: str = None
    ) -> None:
        """
        Arguments:
            default_limit (int):
                The default number of collection items per page.
            limit_param_name (str):
                The name of the URL parameter that specifies the number of collection items per page.
        """
        self._default_limit = default_limit
        self._limit_param_name = limit_param_name

    def __call__(self, queryset: TQueryAdapter, base_url: str) -> tuple[TQueryAdapter, THttpHeaders]:
        """
        Applies pagination to the queryset; returns a new queryset and HTTP response headers.

        Arguments:
            queryset (TQueryAdapter): queryset to which to apply navigation.
            base_url (str): URL for Link response headers.
        """
        headers = self.make_headers(copy(queryset), base_url)
        queryset = self.paginate(queryset)
        return queryset, headers

    def get_default_limit(self) -> int:
        """Returns default number of collection items per page."""
        return self._default_limit or current_app.config['RESTLIB_PAGINATION_LIMIT']

    def get_limit(self) -> int:
        """Returns the number of collection items per page."""
        schema = {
            'limit': fields.Int(
                missing=self.get_default_limit(),
                validate=validators.Range(min=1),
                data_key=self.get_limit_param_name()
            )
        }
        return parser.parse(schema, location='query')['limit']

    def get_limit_param_name(self) -> str:
        """Returns name of the URL parameter that specifies the number of collection items per page."""
        return self._limit_param_name or current_app.config['RESTLIB_URL_PARAM_LIMIT']

    @abstractmethod
    def get_total(self, queryset: TQueryAdapter) -> int:
        """Returns the total number of items in the collection."""

    @abstractmethod
    def make_headers(self, queryset: TQueryAdapter, base_url: str) -> THttpHeaders:
        """Returns HTTP headers with pagination."""

    @abstractmethod
    def paginate(self, queryset: TQueryAdapter) -> TQueryAdapter:
        """Applies pagination to the queryset and returns a new queryset."""


class LimitOffsetPagination(AbstractPagination):
    __slots__ = ('_offset_param_name',)

    def __init__(
        self,
        *,
        default_limit: int = None,
        limit_param_name: str = None,
        offset_param_name: str = None
    ) -> None:
        """
        Arguments:
            limit_param_name (str):
                The name of the URL parameter that specifies the number of collection items per page.
            offset_param_name (str):
                The name of the URL parameter that specifies the offset from the first item in the collection.
        """
        super().__init__(
            default_limit=default_limit,
            limit_param_name=limit_param_name
        )
        self._offset_param_name = offset_param_name

    def get_offset(self) -> int:
        """Returns offset from the first item in the collection."""
        schema = {
            'offset': fields.Int(
                missing=0,
                validate=validators.Range(min=0),
                data_key=self.get_offset_param_name()
            )
        }
        return parser.parse(schema, location='query')['offset']

    def get_offset_param_name(self) -> str:
        """
        Returns name of the URL parameter
        that specifies the offset from the first item in the collection.
        """
        return self._offset_param_name or current_app.config['RESTLIB_URL_PARAM_OFFSET']

    def get_total(self, queryset: TQueryAdapter) -> int:
        return queryset.count()

    def make_headers(self, queryset: TQueryAdapter, base_url: str) -> THttpHeaders:
        total = self.get_total(queryset)
        limit = self.get_limit()
        offset = self.get_offset()

        first_page_offset = offset % limit
        current_page = (offset - first_page_offset) // limit
        total_pages = (total - first_page_offset) // limit

        if first_page_offset > 0:
            current_page += 1
            total_pages += 1

        def link_header(rel: str, offset: int = 0) -> THttpHeader:
            url = url_update_query_string(base_url, {
                self.get_limit_param_name(): limit,
                self.get_offset_param_name(): offset,
            })
            return 'Link', f'{url}; rel="{rel}"'

        headers = [
            ('X-Total-Count', str(total)),
            link_header('first'),
            link_header('last', (total_pages - 1) * limit + first_page_offset),
        ]

        if current_page > 0:
            headers.append(link_header('prev', offset - limit if offset > limit else 0))

        if current_page < total_pages:
            headers.append(link_header('next', offset + limit))

        return headers

    def paginate(self, queryset: TQueryAdapter) -> TQueryAdapter:
        queryset.limit(self.get_limit())
        queryset.offset(self.get_offset())
        return queryset
