from __future__ import annotations
import typing

import sqlalchemy as sa
from sqlalchemy.orm import Query
from flask import current_app
from flask_marshmallow.sqla import SQLAlchemyAutoSchema, SQLAlchemyAutoSchemaOpts
from werkzeug.local import LocalProxy

from flask_restlib.core import (
    AbstractQueryAdapter, AbstractResourceManager, AbstractFactory, AbstractFilter
)
from flask_restlib.utils import strip_sorting_flag


class AutoSchemaOpts(SQLAlchemyAutoSchemaOpts):
    def __init__(self, meta, ordered=False):
        # if not hasattr(meta, 'sqla_session'):
        #     meta.sqla_session = models.db.session

        meta.dump_only = {
            'id', 'created_at', 'updated_at', *getattr(meta, 'dump_only', ())
        }

        super().__init__(meta, ordered=ordered)


class AutoSchema(SQLAlchemyAutoSchema):
    OPTIONS_CLASS = AutoSchemaOpts


class QueryAdapter(AbstractQueryAdapter):
    __slots__ = ('session',)

    def __init__(self, base_query, *, session):
        if not isinstance(base_query, Query):
            base_query = session.query(base_query)

        super().__init__(base_query)
        self.session = session

    def all(self) -> list:
        return self.make_query().all()

    def count(self) -> int:
        return self.make_query().count()

    def exists(self) -> bool:
        q = self.make_query().exists()
        return self.session.query(q).scalar()

    def make_query(self):
        q = self._base_query

        for columns in self._order_by:
            q = q.order_by(*columns)

        if self._limit is not None:
            q = q.limit(self._limit)

        if self._offset is not None:
            q = q.offset(self._offset)

        return q

    def order_by(self, column, *columns) -> AbstractQueryAdapter:
        args = []

        for name in (column, *columns):
            if isinstance(name, str):
                order = sa.desc if name.startswith('-') else sa.asc
                name = order(sa.text(
                    strip_sorting_flag(name)
                ))
            args.append(name)

        return super().order_by(*args)


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

    def get(
        self,
        model_class: type,
        identifier: typing.Union[typing.Any, tuple, dict]
    ) -> typing.Union[typing.Any, None]:
        return self.session.query(model_class).get(identifier)


class SQLAFactory(AbstractFactory):
    def __init__(self, session=None):
        self.session = session or LocalProxy(lambda: self.get_session())

    def get_session(self):
        ext = current_app.extensions.get('sqlalchemy')

        if ext is None:
            raise RuntimeError(
                'An extension named sqlalchemy was not found '
                'in the list of registered extensions for the current application.'
            )

        return ext.db.session

    def create_query_adapter(self, base_query=None) -> QueryAdapter:
        return QueryAdapter(base_query, session=self.session)

    def create_resource_manager(self):
        return ResourceManager(self.session)

    def create_schema(self, model_class):
        class Meta:
            model = model_class

        name = '%sSchema' % model_class.__name__
        bases = (self.get_schema_class(),)

        return type(name, bases, {'Meta': Meta})

    def get_schema_class(self):
        return AutoSchema

    def get_schema_options_class(self):
        return AutoSchemaOpts
