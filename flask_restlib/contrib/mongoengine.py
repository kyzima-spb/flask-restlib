from copy import deepcopy

from marshmallow import Schema as _Schema, SchemaOpts as _SchemaOpts
from mongoengine.errors import OperationError

from flask_restlib.core import (
    AbstractQueryAdapter, AbstractResourceManager, AbstractFactory, AbstractFilter
)
from flask_restlib.mixins import RequestMixin


class SchemaOpts(_SchemaOpts):
    def __init__(self, meta, ordered=False):
        meta.dump_only = {
            'id', 'created_at', 'updated_at', *getattr(meta, 'dump_only', ())
        }

        super().__init__(meta, ordered=ordered)


class Schema(RequestMixin, _Schema):
    OPTIONS_CLASS = SchemaOpts


class MongoQueryAdapter(AbstractQueryAdapter):
    def _do_select(self, *entities):
        return entities[0].objects

    def _prepare_identifier(self, model_class, identifier):
        """
        Converts the original resource identifier to a Mongo-friendly format.

        Arguments:
            model_class: A reference to the model class.
            identifier (dict): original identifier.

        Returns:
            The transformed identifier.
        """
        identifier = deepcopy(identifier)
        id_field = model_class._meta['id_field']

        if id_field in identifier:
            pk = identifier.pop(id_field)
        else:
            field = getattr(model_class, id_field)
            pk = {}
            for n in field.document_type._fields:
                pk[n] = identifier.pop(n)

        if identifier:
            raise RuntimeError('Invalid identifier.')

        return pk

    def all(self) -> list:
        return self.make_query().all()

    def count(self) -> int:
        return self.make_query().count(with_limit_and_skip=True)

    def exists(self) -> bool:
        return bool(self.make_query().first())

    def filter(self, filter_: AbstractFilter) -> AbstractQueryAdapter:
        pass

    def get(self, identifier):
        q = self.make_query()
        model_class = q._document
        return self.make_query().with_id(
            self._prepare_identifier(model_class, identifier)
        )

    def make_query(self):
        if self._base_query is None:
            q = self._query
        else:
            q = self._base_query

        if self._offset is None:
            start = 0
        else:
            start = self._offset if self._offset > 0 else 0

        if self._limit is not None:
            count = start + self._limit
        else:
            count = None

        q = q.__getitem__(slice(start, count))

        for columns in self._order_by:
            q = q.order_by(*columns)

        return q


class MongoResourceManager(AbstractResourceManager):
    def commit(self):
        pass

    def create(self, model_class, data):
        try:
            if isinstance(data, dict):
                result = model_class(**data).save(force_insert=True)
            else:
                result = model_class.objects.insert([
                    model_class(**attrs) for attrs in data
                ])
            return result
        except OperationError as err:
            raise RuntimeError(err) from err

    def delete(self, resource):
        try:
            resource.delete()
        except OperationError as err:
            raise RuntimeError(err) from err

    def update(self, resource, attributes):
        if not resource.modify(**attributes):
            raise RuntimeError('Failed to update resource.')
        return resource


class MongoEngineFactory(AbstractFactory):
    def create_query_adapter(self, base_query=None) -> MongoQueryAdapter:
        return MongoQueryAdapter(base_query)

    def create_resource_manager(self) -> MongoResourceManager:
        return MongoResourceManager()

    def create_schema(self, model_class):
        pass

    def get_schema_class(self):
        return Schema

    def get_schema_options_class(self):
        return SchemaOpts
