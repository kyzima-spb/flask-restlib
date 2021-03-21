from flask_restlib.core import (
    AbstractQueryAdapter, AbstractResourceManager, AbstractFactory, AbstractFilter
)
from mongoengine.errors import OperationError


class MongoQueryAdapter(AbstractQueryAdapter):
    def _do_select(self, *entities):
        return entities[0].objects

    def all(self) -> list:
        return self.make_query().all()

    def count(self) -> int:
        return self.make_query().count(with_limit_and_skip=True)

    def exists(self) -> bool:
        return bool(self.make_query().first())

    def filter(self, filter_: AbstractFilter) -> AbstractQueryAdapter:
        pass

    def get(self, identifier):
        return self.make_query().with_id(identifier)

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
