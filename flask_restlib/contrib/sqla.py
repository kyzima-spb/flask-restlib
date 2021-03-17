from __future__ import annotations
import typing

import sqlalchemy as sa
from flask import current_app
from flask_restlib import current_restlib
from flask_restlib.core import (
    AbstractQueryBuilder, AbstractResourceManager, AbstractFactory
)
from flask_restlib.mixins import RequestMixin


class QueryBuilder(AbstractQueryBuilder):
    __slots__ = ('session',)

    def __init__(self, base_query=None, *, session):
        super().__init__(base_query)
        self.session = session

    def _do_select(self, *entities):
        return self.session.query(*entities)

    def all(self) -> list:
        return self.make_query().all()

    def count(self) -> int:
        return self.make_query().count()

    def exists(self) -> bool:
        q = self.make_query().exists()
        return self.session.query(q).scalar()

    def get(self, identifier):
        return self.make_query().get(identifier)

    def make_query(self):
        q = self._base_query or self._query

        for column in self._order_by:
            q = q.order_by(sa.text(column))

        if self._limit is not None:
            q = q.limit(self._limit)

        if self._offset is not None:
            q = q.offset(self._offset)

        return q


class ResourceManager(AbstractResourceManager):
    def __init__(self, session):
        self.session = session

    def commit(self):
        self.session.commit()

    def create(self, model_class, data):
        if isinstance(data, dict):
            resource = model_class(**data)
            self.session.add(resource)
            return resource
        self.session.bulk_insert_mappings(model_class, data)

    def delete(self, resource):
        self.session.delete(resource)


class SQLAFactory(AbstractFactory):
    def __init__(self, session=None):
        self.session = session or self.get_session()

    def get_session(self):
        ext = current_app.extensions.get('sqlalchemy')

        if ext is None:
            raise RuntimeError(
                'An extension named sqlalchemy was not found '
                'in the list of registered extensions for the current application.'
            )

        return ext.db.session

    def create_query_builder(self, base_query=None):
        return QueryBuilder(base_query, session=self.session)

    def create_resource_manager(self):
        return ResourceManager(self.session)

    def create_schema(self, model_class):
        class Meta:
            model = model_class

        name = '%sSchema' % model_class.__name__
        bases = (RequestMixin, current_restlib.ma.SQLAlchemyAutoSchema)

        return type(name, bases, {'Meta': Meta})

    # def get_resource_manager_class(self):
    #     """
    #     Returns a reference to the class of the resource manager.
    #     """
    #     return ResourceManager
        # if self.resource_manager_class is None:
        #     self.__class__.resource_manager_class = current_restlib.ResourceManager
        #
        # return self.resource_manager_class
