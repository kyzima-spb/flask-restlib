from __future__ import annotations
from functools import lru_cache, partial
import typing as t

from authlib.integrations.sqla_oauth2 import (
    OAuth2TokenMixin as _OAuth2TokenMixin,
    OAuth2AuthorizationCodeMixin as _OAuth2AuthorizationCodeMixin
)
from flask import current_app
from flask_marshmallow.sqla import (
    SQLAlchemyAutoSchema as _SQLAlchemyAutoSchema,
    SQLAlchemyAutoSchemaOpts as _SQLAlchemyAutoSchemaOpts,
    SQLAlchemySchema as _SQLAlchemySchema,
    SQLAlchemySchemaOpts as _SQLAlchemySchemaOpts,
)
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Query, relationship
from sqlalchemy_utils.functions import (
    get_declarative_base,
    get_primary_keys
)
from sqlalchemy_utils.types import UUIDType
from werkzeug.local import LocalProxy

from ..core import (
    AbstractQueryAdapter,
    AbstractResourceManager,
    AbstractFactory,
    QueryExpression,
)
from ..mixins import (
    AuthorizationCodeMixin,
    ClientMixin,
    TokenMixin
)
from ..oauth2 import generate_client_id
from ..schemas import RestlibMixin
from ..types import (
    TIdentifier,
    TQueryAdapter,
    TResourceManager,
    TSchema,
)
from ..utils import strip_sorting_flag


__all__ = (
    'OAuth2ClientMixin', 'OAuth2TokenMixin', 'OAuth2AuthorizationCodeMixin',
    'QueryAdapter', 'ResourceManager', 'SQLAFactory',
)


def create_fk_column(model_class) -> sa.ForeignKey:
    pk = get_primary_keys(model_class)

    if len(pk) > 1:
        raise RuntimeError('Composite primary key')

    pk_name, pk_column = pk.popitem()
    return sa.ForeignKey(pk_column, onupdate='CASCADE', ondelete='CASCADE')


@lru_cache
def create_client_reference_mixin(client_model):
    class _ClientRelationshipMixin:
        @declared_attr
        def client_id(cls):
            return sa.Column(create_fk_column(client_model), nullable=False)

        @declared_attr
        def client(cls):
            return relationship(client_model)
    return _ClientRelationshipMixin


@lru_cache
def create_user_reference_mixin(user_model):
    class _UserReferenceMixin:
        @declared_attr
        def user_id(cls):
            return sa.Column(create_fk_column(user_model), nullable=False)

        @declared_attr
        def user(cls):
            return relationship(user_model)
    return _UserReferenceMixin


# todo: OAuth 2.0

class OAuth2ClientMixin(ClientMixin):
    __tablename__ = 'oauth2_client'

    id = sa.Column(
        sa.String(48),
        primary_key=True,
        default=partial(generate_client_id, 48)
    )
    client_secret = sa.Column(
        sa.String(120),
        nullable=False,
        default=''
    )
    client_id_issued_at = sa.Column(
        sa.Integer,
        nullable=False,
        default=0
    )
    client_secret_expires_at = sa.Column(
        sa.Integer,
        nullable=False,
        default=0
    )
    client_metadata = sa.Column(sa.JSON, nullable=False)


class OAuth2TokenMixin(_OAuth2TokenMixin, TokenMixin):
    __tablename__ = 'oauth2_token'
    id = sa.Column(UUIDType(binary=False), primary_key=True)


class OAuth2AuthorizationCodeMixin(_OAuth2AuthorizationCodeMixin, AuthorizationCodeMixin):
    __tablename__ = 'oauth2_code'
    id = sa.Column(UUIDType(binary=False), primary_key=True)


# todo: Marshmallow


class SQLAlchemySchemaOpts(RestlibMixin.Opts, _SQLAlchemySchemaOpts):
    pass


class SQLAlchemyAutoSchemaOpts(RestlibMixin.Opts, _SQLAlchemyAutoSchemaOpts):
    pass


class SQLAlchemySchema(_SQLAlchemySchema):
    OPTIONS_CLASS = SQLAlchemySchemaOpts


class SQLAlchemyAutoSchema(_SQLAlchemyAutoSchema):
    OPTIONS_CLASS = SQLAlchemyAutoSchemaOpts


class SQLAModelField:
    def __init__(self, column):
        self.column = column

    def __eq__(self, other):
        return SQLAQueryExpression(self.column == other)

    def __ne__(self, other):
        return SQLAQueryExpression(self.column.name != other)

    def __lt__(self, other):
        return SQLAQueryExpression(self.column.name < other)

    def __le__(self, other):
        return SQLAQueryExpression(self.column.name <= other)

    def __gt__(self, other):
        return SQLAQueryExpression(self.column.name > other)

    def __ge__(self, other):
        return SQLAQueryExpression(self.column.name >= other)


class SQLAQueryExpression(QueryExpression):
    def __and__(self, other):
        return self.__class__(sa.and_(self.expr, other.expr))

    def __call__(self, q):
        return q.filter(self.expr)

    def __or__(self, other):
        return self.__class__(sa.or_(self.expr, other.expr))


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

    def filter_by(self: TQueryAdapter, **kwargs: t.Any) -> TQueryAdapter:
        # print(get_query_entities(self._base_query))
        self._base_query = self._base_query.filter_by(**kwargs)
        return self

    def make_query(self) -> t.Any:
        q = self._base_query

        for columns in self._order_by:
            q = q.order_by(*columns)

        if self._limit is not None:
            q = q.limit(self._limit)

        if self._offset is not None:
            q = q.offset(self._offset)

        return q

    def order_by(
            self: TQueryAdapter,
            column: str,
            *columns: tuple[str]
    ) -> TQueryAdapter:
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
    def __init__(self, session) -> None:
        self.session = session

    def commit(self) -> None:
        self.session.commit()

    def create(
        self,
        model_class: t.Any,
        data: t.Union[dict, list[dict]]
    ) -> t.Any:
        if isinstance(data, dict):
            resource = model_class(**data)
            self.session.add(resource)
            return resource
        self.session.bulk_insert_mappings(model_class, data)

    def delete(self, resource: t.Any) -> None:
        self.session.delete(resource)

    def get(
        self,
        model_class: t.Type[t.Any],
        identifier: TIdentifier
    ) -> t.Optional[t.Any]:
        return self.session.query(model_class).get(identifier)

    def rollback(self) -> None:
        self.session.rollback()

    def update(
        self,
        resource: t.Any,
        attributes: dict
    ) -> t.Any:
        self.populate_obj(resource, attributes)
        return resource


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

    def create_model_field_adapter(self, column):
        return SQLAModelField(column)

    def create_query_adapter(self, base_query: t.Any) -> TQueryAdapter:
        return QueryAdapter(base_query, session=self.session)

    def create_resource_manager(self) -> TResourceManager:
        return ResourceManager(self.session)

    def create_schema(self, model_class) -> t.Type[TSchema]:
        class Meta:
            model = model_class

        name = '%sSchema' % model_class.__name__
        bases = (self.get_auto_schema_class(),)

        return type(name, bases, {'Meta': Meta})

    def get_auto_schema_class(self) -> t.Type[TSchema]:
        return SQLAlchemyAutoSchema

    def get_auto_schema_options_class(self):
        return SQLAlchemyAutoSchemaOpts

    def get_schema_class(self) -> t.Type[TSchema]:
        return SQLAlchemySchema

    def get_schema_options_class(self):
        return SQLAlchemySchemaOpts

    def create_client_model(self, user_model):
        return type(
            'OAuth2Client',
            (
                create_user_reference_mixin(user_model),
                OAuth2ClientMixin,
                get_declarative_base(user_model),
            ),
            {}
        )

    def create_token_model(self, user_model, client_model):
        return type(
            'OAuth2Token',
            (
                create_user_reference_mixin(user_model),
                create_client_reference_mixin(client_model),
                OAuth2TokenMixin,
                get_declarative_base(user_model),
            ),
            {}
        )

    def create_authorization_code_model(self, user_model, client_model):
        return type(
            'OAuth2Code',
            (
                create_user_reference_mixin(user_model),
                create_client_reference_mixin(client_model),
                OAuth2AuthorizationCodeMixin,
                get_declarative_base(user_model),
            ),
            {}
        )
