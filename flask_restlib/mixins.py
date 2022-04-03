from __future__ import annotations
import typing as t

from flask import request, current_app
from flask.typing import ResponseReturnValue, HeadersValue
from webargs.flaskparser import parser
from werkzeug.datastructures import Headers

from .globals import current_restlib
from .filters import TFilter
from .pagination import TPagination
from .sorting import TSortHandler
from .types import (
    TIdentifier,
    TLookupNames,
    TQueryAdapter,
    THttpHeaders
)


__all__ = (
    'CreateMixin', 'CreateViewMixin',
    'DestroyMixin', 'DestroyViewMixin',
    'ListMixin', 'ListViewMixin',
    'RetrieveMixin', 'RetrieveViewMixin',
    'UpdateMixin', 'UpdateViewMixin',
)


class CreateMixin:
    """A mixin to add a new resource to the collection."""

    def get_creation_headers(self, data) -> HeadersValue:
        """Returns HTTP headers on successful resource creation."""
        headers = Headers()
        resource_url = data.get('_links', {}).get('self')

        if resource_url:
            headers.add('Location', resource_url)

        return headers

    def create(self) -> ResponseReturnValue:
        schema = self.create_schema() # type: ignore
        data = parser.parse(schema, location='json_or_form')

        with self.create_resource_manager() as rm: # type: ignore
            resource = rm.create(self.get_model_class(), data) # type: ignore

        data = schema.dump(resource)
        return data, 201, self.get_creation_headers(data)


class DestroyMixin:
    """A mixin for removing a resource from a collection."""

    def destroy(self, identifier: TIdentifier) -> ResponseReturnValue:
        resource = self.get_for_update(identifier) # type: ignore

        with self.create_resource_manager() as rm: # type: ignore
            rm.delete(resource)

        return '', 204


class ListBaseMixin(t.Generic[TFilter, TSortHandler, TPagination]):
    """
    Mixin for getting all resources from the collection.

    Attributes:
        filters (list):
        pagination_handler (TPagination): An instance of the paginator.
        sort_handler (TSortHandler): an instance of the sort handler.
    """
    filters: t.List[TFilter] = []
    pagination_handler: t.Optional[TPagination] = None
    sort_handler: t.Optional[TSortHandler] = None

    def get_pagination(self) -> TPagination:
        """Returns an instance of the paginator."""
        if self.pagination_handler is None:
            return current_restlib.pagination_handler
        return self.pagination_handler

    def get_sort(self) -> t.Optional[TSortHandler]:
        """Returns an instance of the sort handler."""
        return self.sort_handler

    def filter_queryset(self, q: TQueryAdapter) -> TQueryAdapter:
        """Applies filters to a queryset and returns a new queryset."""
        for f in self.filters:
            q = f.filter(q)
        return q

    def paginate_queryset(self, q: TQueryAdapter) -> tuple[TQueryAdapter, THttpHeaders]:
        """Applies pagination to a queryset and returns a new queryset and HTTP headers."""
        if current_app.config['RESTLIB_PAGINATION_ENABLED']:
            pagination = self.get_pagination()
            return pagination(q, request.url)
        return q, []

    def sort_queryset(self, q: TQueryAdapter) -> TQueryAdapter:
        """Applies a sort to a queryset and returns a new queryset."""
        if current_app.config['RESTLIB_SORTING_ENABLED']:
            sort_handler = self.get_sort()
            if sort_handler is not None:
                q = sort_handler.execute(q)
        return q


class ListMixin(
    ListBaseMixin[TFilter, TSortHandler, TPagination]
):
    def list(self) -> ResponseReturnValue:
        q: TQueryAdapter = self.create_queryset() # type: ignore
        headers: THttpHeaders = []

        q = self.filter_queryset(q)
        q = self.sort_queryset(q)
        q, pagination_headers = self.paginate_queryset(q)
        headers.extend(pagination_headers)

        return self.create_schema(many=True).dump(q), headers # type: ignore


class ChildListMixin(
    ListBaseMixin[TFilter, TSortHandler, TPagination]
):
    model_child_property: t.Optional[str] = None

    def create_child_queryset(self, resource: t.Any) -> TQueryAdapter:
        """
        Creates and returns a queryset for retrieving child resources from persistent storage.
        """
        if self.model_child_property is not None:
            factory = self.get_factory()  # type: ignore
            return factory.create_query_adapter(
                getattr(resource, self.model_child_property)
            )
        raise NotImplementedError

    def list(self, identifier: TIdentifier) -> ResponseReturnValue:
        resource = self.get_or_404(identifier)  # type: ignore

        q: TQueryAdapter = self.create_child_queryset(resource)  # type: ignore
        headers: THttpHeaders = []

        q = self.filter_queryset(q)
        q = self.sort_queryset(q)
        q, pagination_headers = self.paginate_queryset(q)
        headers.extend(pagination_headers)

        return self.create_schema(many=True).dump(q), headers  # type: ignore


class RetrieveMixin:
    """Mixin to get one resource from a collection"""

    def retrieve(self, identifier: TIdentifier) -> ResponseReturnValue:
        return self.create_schema().dump(  # type: ignore
            self.get_or_404(identifier)  # type: ignore
        )


class UpdateMixin:
    """A mixin for editing a resource in a collection."""

    def update(self, identifier: TIdentifier) -> ResponseReturnValue:
        resource = self.get_for_update(identifier) # type: ignore

        schema = self.create_schema() # type: ignore
        schema.context['resource'] = resource
        data = parser.parse(schema, location='json_or_form')

        with self.create_resource_manager() as rm: # type: ignore
            resource = rm.update(resource, data)

        return schema.dump(resource)


class CreateViewMixin(CreateMixin):
    def post(self) -> ResponseReturnValue:
        return self.create()


class DestroyViewMixin(DestroyMixin):
    lookup_names: t.ClassVar[TLookupNames] = ('id',)

    def delete(self, id: TIdentifier) -> ResponseReturnValue:
        return self.destroy(id)


class ListViewMixin(
    ListMixin[TFilter, TSortHandler, TPagination]
):
    def get(self) -> ResponseReturnValue:
        return self.list()


class ChildListViewMixin(
    ChildListMixin[TFilter, TSortHandler, TPagination]
):
    lookup_names: t.ClassVar[TLookupNames] = ('id',)

    def get(self, id: TIdentifier) -> ResponseReturnValue:
        return self.list(id)


class RetrieveViewMixin(RetrieveMixin):
    lookup_names: t.ClassVar[TLookupNames] = ('id',)

    def get(self, id: TIdentifier) -> ResponseReturnValue:
        return self.retrieve(id)


class UpdateViewMixin(UpdateMixin):
    lookup_names: t.ClassVar[TLookupNames] = ('id',)

    def put(self, id: TIdentifier) -> ResponseReturnValue:
        return self.update(id)
