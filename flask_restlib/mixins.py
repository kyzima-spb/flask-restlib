from flask import request, abort, jsonify, current_app
from webargs import fields
from webargs import validate as validators
from webargs.flaskparser import parser

from flask_restlib.core import UrlQueryFilter
from flask_restlib.utils import strip_sorting_flag


__all__ = (
    'RequestMixin',
    'CreateMixin', 'CreateViewMixin',
    'DestroyMixin', 'DestroyViewMixin',
    'ListMixin', 'ListViewMixin',
    'RetrieveMixin', 'RetrieveViewMixin',
    'UpdateMixin', 'UpdateViewMixin',
)


class RequestMixin:
    """The mixin allows you to automatically fetch data from the request object."""

    def load_from_request(self, **kwargs):
        """Returns a validated JSON document retrieved from the request object."""
        if request.json is None:
            abort(400, 'Invalid input')
        return self.load(request.json, **kwargs)


class CreateMixin:
    """A mixin to add a new resource to the collection."""

    def create(self):
        schema = self.create_schema()
        data = schema.load_from_request()

        with self.create_resource_manager() as rm:
            resource = rm.create(self.get_model_class(), data)

        return schema.dump(resource), 201


class DestroyMixin:
    """A mixin for removing a resource from a collection."""

    def destroy(self, identifier):
        resource = self.get_or_404(identifier)

        with self.create_resource_manager() as rm:
            rm.delete(resource)

        return '', 204


class ListMixin:
    """
    Mixin for getting all resources from the collection.

    Attributes:
        filter_instance (UrlQueryFilter):
            ...
        limit_param_name (str):
            The name of the URL parameter that specifies the number of collection items per page.
        offset_param_name (str):
            The name of the URL parameter that specifies the offset from the first item in the collection.
        search_instance (UrlQueryFilter):
            ...
        sort_param_name (str):
            The name of the URL parameter that is used for sorting.
        sorting_fields (tuple):
            The names of the attributes of the model to be sorted.
    """

    filter_instance = None
    limit_param_name = None
    offset_param_name = None
    search_instance = None
    sort_param_name = None
    sorting_fields = ()

    def _get_pagination(self):
        limit_param_name = self.limit_param_name or current_app.config['RESTLIB_URL_PARAM_LIMIT']
        offset_param_name = self.offset_param_name or current_app.config['RESTLIB_URL_PARAM_OFFSET']
        pagination_schema = {
            limit_param_name: fields.Int(
                missing=current_app.config['RESTLIB_PAGINATION_LIMIT'],
                validate=validators.Range(min=1)
            ),
            offset_param_name: fields.Int(
                missing=0,
                validate=validators.Range(min=0)
            ),
        }
        return parser.parse(pagination_schema, location='query')

    def _get_sort(self):
        def validate(v):
            validator = validators.OneOf(self.sorting_fields)
            validator(strip_sorting_flag(v))

        sort_param_name = self.sort_param_name or current_app.config['RESTLIB_URL_PARAM_SORT']
        sort_schema = {
            sort_param_name: fields.DelimitedList(
                fields.String(validate=validate)
            )
        }

        return parser.parse(sort_schema, location='query').get('sort')

    def list(self):
        q = self.create_queryset()

        if self.filter_instance is not None:
            q.filter(self.filter_instance)

        if self.search_instance is not None:
            q.filter(self.search_instance)

        if current_app.config['RESTLIB_PAGINATION_ENABLED']:
            pagination = self._get_pagination()
            q.limit(pagination['limit'])
            q.offset(pagination['offset'])

        if current_app.config['RESTLIB_SORTING_ENABLED']:
            sort = self._get_sort()
            if sort:
                q.order_by(*sort)

        return jsonify(
            self.create_schema(many=True).dump(q)
        )


class RetrieveMixin:
    """Mixin to get one resource from a collection"""

    def retrieve(self, identifier):
        return self.create_schema().dump(
            self.get_or_404(identifier)
        )


class UpdateMixin:
    """A mixin for editing a resource in a collection."""

    def update(self, identifier):
        resource = self.get_or_404(identifier)

        schema = self.create_schema()
        schema.context['resource'] = resource
        data = schema.load_from_request()

        with self.create_resource_manager() as rm:
            rm.update(resource, data)

        return schema.dump(resource)


class CreateViewMixin(CreateMixin):
    def post(self):
        return self.create()


class DestroyViewMixin(DestroyMixin):
    pk_names = ('id',)

    def delete(self, id):
        return self.destroy(id)


class ListViewMixin(ListMixin):
    def get(self):
        return self.list()


class RetrieveViewMixin(RetrieveMixin):
    pk_names = ('id',)

    def get(self, id):
        return self.retrieve(id)


class UpdateViewMixin(UpdateMixin):
    pk_names = ('id',)

    def put(self, id):
        return self.update(id)
