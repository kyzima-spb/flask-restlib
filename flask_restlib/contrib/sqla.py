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
from sqlalchemy.ext.mutable import MutableList
from sqlalchemy.orm import (
    Query,
    relationship,
    Session,
)
from sqlalchemy_utils.functions import (
    get_declarative_base,
    get_primary_keys
)
from sqlalchemy_utils.types import UUIDType
from werkzeug.local import LocalProxy

from ..core import AbstractFactory
from ..oauth2.authorization_server import generate_client_id
from ..oauth2.mixins import (
    AuthorizationCodeMixin,
    ClientMixin,
    TokenMixin,
    UserMixin,
)
from ..oauth2.rbac import RoleMixin
from ..orm import (
    AbstractQueryAdapter,
    AbstractQueryExpression,
    AbstractResourceManager,
)
from ..schemas import RestlibMixin
from ..types import (
    TIdentifier,
)


__all__ = (
    'create_authorization_code_model',
    'create_client_model',
    'create_role_model',
    'create_token_model',
    'SQLAQueryAdapter',
    'SQLAResourceManager',
    'SQLAFactory',
)


TModel = t.TypeVar('TModel')


def create_fk_column(model_class: t.Type[t.Any]) -> sa.ForeignKey:
    """Creates and returns a column for the foreign key related to the given model."""
    pk = get_primary_keys(model_class)

    if len(pk) > 1:
        raise RuntimeError('Composite primary key')

    pk_name, pk_column = pk.popitem()
    return sa.ForeignKey(pk_column, onupdate='CASCADE', ondelete='CASCADE')


@lru_cache
def create_client_reference_mixin(client_model: t.Type[ClientMixin]) -> t.Type[t.Any]:
    """Creates and returns a mixin with a reference to the OAuth2 client model."""
    class _ClientRelationshipMixin:
        @declared_attr
        def client_id(cls) -> sa.Column:
            return sa.Column(create_fk_column(client_model), nullable=False)

        @declared_attr
        def client(cls) -> sa.orm.RelationshipProperty:
            return relationship(client_model)
    return _ClientRelationshipMixin


@lru_cache
def create_user_reference_mixin(user_model: t.Type[UserMixin]) -> t.Type:
    """Creates and returns a mixin with a reference to the user model."""
    class _UserReferenceMixin:
        @declared_attr
        def user_id(cls) -> sa.Column:
            return sa.Column(create_fk_column(user_model), nullable=False)

        @declared_attr
        def user(cls) -> sa.orm.RelationshipProperty:
            return relationship(user_model)
    return _UserReferenceMixin


# todo: OAuth 2.0

def create_role_model(
    base_model_class: t.Type,
    table_name: str = 'oauth2_role',
    is_abstract: bool = False
) -> t.Type[RoleMixin]:
    """
    Creates and returns a base abstract class to describe a role.

    The name of the new class is OAuth2Role, use it in a relationship or class reference.

    Arguments:
        base_model_class: a base class for declarative class definitions.
        table_name (str): table name in the database.
        is_abstract (bool): make the model abstract, by default False.
    """
    ref_table_name = f'{table_name}_children'

    role_children = sa.Table(
        ref_table_name, base_model_class.metadata,
        sa.Column('parent_role_id', sa.ForeignKey(f'{table_name}.id'), primary_key=True),
        sa.Column('child_role_id', sa.ForeignKey(f'{table_name}.id'), primary_key=True),
    )

    class OAuth2Role(RoleMixin, base_model_class):
        __abstract__ = is_abstract
        __tablename__ = table_name

        id = sa.Column(sa.Integer, primary_key=True)
        name = sa.Column(sa.String(50), unique=True, nullable=False)
        description = sa.Column(sa.String(500), default='', nullable=False)
        scope = sa.Column(sa.Text, default='')

        @declared_attr
        def children(cls) -> sa.orm.RelationshipProperty:
            return relationship(
                cls,
                secondary=role_children,
                primaryjoin=f'{cls.__name__}.id == {ref_table_name}.c.parent_role_id',
                secondaryjoin=f'{cls.__name__}.id == {ref_table_name}.c.child_role_id',
                backref='parents'
            )

    return OAuth2Role


def create_client_model(
    user_model: t.Type[UserMixin],
    table_name: str = 'oauth2_client',
    is_abstract: bool = False
) -> t.Type[ClientMixin]:
    """
    Creates and returns a base abstract class to describe a OAuth2 client.

    The name of the new class is OAuth2Client, use it in a relationship or class reference.

    Arguments:
        user_model: reference to the user model class.
        table_name (str): table name in the database.
        is_abstract (bool): make the model abstract, by default False.
    """

    class OAuth2Client(
        create_user_reference_mixin(user_model),  # type: ignore
        ClientMixin,
        get_declarative_base(user_model)  # type: ignore
    ):
        __abstract__ = is_abstract
        __tablename__ = table_name

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
        scopes = sa.Column(
            MutableList.as_mutable(sa.JSON),
            nullable=False,
            default=list
        )

    return OAuth2Client


def create_token_model(
    user_model: t.Type[UserMixin],
    client_model: t.Type[ClientMixin],
    table_name: str = 'oauth2_token',
    is_abstract: bool = False
) -> t.Type[TokenMixin]:
    """
    Creates and returns a base abstract class to describe a OAuth2 token.

    The name of the new class is OAuth2Token, use it in a relationship or class reference.

    Arguments:
        user_model: reference to the user model class.
        client_model: reference to the client model class.
        table_name (str): table name in the database.
        is_abstract (bool): make the model abstract, by default False.
    """

    class OAuth2Token(
        create_user_reference_mixin(user_model),  # type: ignore
        create_client_reference_mixin(client_model),  # type: ignore
        _OAuth2TokenMixin,
        TokenMixin,
        get_declarative_base(user_model),  # type: ignore
    ):
        __abstract__ = is_abstract
        __tablename__ = table_name

        id = sa.Column(UUIDType(binary=False), primary_key=True)

    return OAuth2Token


def create_authorization_code_model(
    user_model: t.Type[UserMixin],
    client_model: t.Type[ClientMixin],
    table_name: str = 'oauth2_code',
    is_abstract: bool = False
) -> t.Type[AuthorizationCodeMixin]:
    """
    Creates and returns a base abstract class to describe a OAuth2 authorization code.

    The name of the new class is OAuth2Code, use it in a relationship or class reference.

    Arguments:
        user_model: reference to the user model class.
        client_model: reference to the client model class.
        table_name (str): table name in the database.
        is_abstract (bool): make the model abstract, by default False.
    """

    class OAuth2Code(
        create_user_reference_mixin(user_model),  # type: ignore
        create_client_reference_mixin(client_model),  # type: ignore
        _OAuth2AuthorizationCodeMixin,
        AuthorizationCodeMixin,
        get_declarative_base(user_model),  # type: ignore
    ):
        __abstract__ = is_abstract
        __tablename__ = table_name

        id = sa.Column(UUIDType(binary=False), primary_key=True)

    return OAuth2Code


# todo: Marshmallow


class SQLAlchemySchemaOpts(RestlibMixin.Opts, _SQLAlchemySchemaOpts):
    pass


class SQLAlchemyAutoSchemaOpts(RestlibMixin.Opts, _SQLAlchemyAutoSchemaOpts):
    pass


class SQLAlchemySchema(_SQLAlchemySchema):
    OPTIONS_CLASS = SQLAlchemySchemaOpts


class SQLAlchemyAutoSchema(_SQLAlchemyAutoSchema):
    OPTIONS_CLASS = SQLAlchemyAutoSchemaOpts


# todo: ORM Adapter


class SQLAQueryExpression(AbstractQueryExpression[Query]):
    def __call__(self, q: Query) -> Query:
        return q.filter(self._native_expression)

    def __and__(self, other: t.Any) -> SQLAQueryExpression:
        return self.__class__(self._native_expression & self.to_native(other))

    def __or__(self, other: t.Any) -> SQLAQueryExpression:
        return self.__class__(self._native_expression | self.to_native(other))

    def __eq__(self, other: t.Any) -> SQLAQueryExpression:  # type: ignore
        return self.__class__(self._native_expression == self.to_native(other))

    def __ne__(self, other: t.Any) -> SQLAQueryExpression:  # type: ignore
        return self.__class__(self._native_expression != self.to_native(other))

    def __lt__(self, other: t.Any) -> SQLAQueryExpression:
        return self.__class__(self._native_expression < self.to_native(other))

    def __le__(self, other: t.Any) -> SQLAQueryExpression:
        return self.__class__(self._native_expression <= self.to_native(other))

    def __gt__(self, other: t.Any) -> SQLAQueryExpression:
        return self.__class__(self._native_expression > self.to_native(other))

    def __ge__(self, other: t.Any) -> SQLAQueryExpression:
        return self.__class__(self._native_expression >= self.to_native(other))

# _TNativeQuery = t.Union[t.Type[_TModel], Query]

class SQLAQueryAdapter(AbstractQueryAdapter[Query]):
    __slots__ = ('session',)

    def __init__(
        self,
        base_query: t.Union[Query, SQLAQueryAdapter],
        *,
        session: Session
    ) -> None:
        self.session = session
        super().__init__(base_query)
        # from sqlalchemy.ext.declarative import declarative_base
        # Base = declarative_base()
        # SQLAQueryAdapter(Base, session=None)
        # reveal_type(self._base_query)

    def all(self) -> list:
        return self.make_query().all()

    def count(self) -> int:
        return self.make_query().count()

    def exists(self) -> bool:
        q = self.make_query().exists()
        return self.session.query(q).scalar()

    def filter_by(self, **kwargs: t.Any) -> SQLAQueryAdapter:
        self._base_query = self._base_query.filter_by(**kwargs)
        return self

    def make_query(self) -> Query:
        q = self._base_query

        for columns in self._order_by:
            q = q.order_by(*columns)

        if self._limit is not None:
            q = q.limit(self._limit)

        if self._offset is not None:
            q = q.offset(self._offset)

        return q

    def order_by(
        self,
        column: t.Union[str, tuple[str, bool]],
        *columns: t.Union[str, tuple[str, bool]]
    ) -> SQLAQueryAdapter:
        args = []

        for param in (column, *columns):
            if isinstance(param, str):
                name = param
                order = sa.asc
            else:
                name, desc = param
                order = sa.desc if desc else sa.asc

            args.append(
                order(sa.text(name))
            )

        self._order_by.append(tuple(args))

        return self

    def prepare_query(self, base_query: Query) -> Query:
        if isinstance(base_query, Query):
            return base_query
        return self.session.query(base_query)


class SQLAResourceManager(AbstractResourceManager[TModel]):
    def __init__(self, session: Session) -> None:
        self.session = session

    def commit(self) -> None:
        self.session.commit()

    def create(
        self,
        model_class: t.Type[TModel],
        data: t.Union[dict, list[dict]]
    ) -> t.Union[TModel, list[TModel]]:
        if isinstance(data, dict):
            resource = model_class(**data)
            self.session.add(resource)
            return resource
        self.session.bulk_insert_mappings(model_class, data)

    def delete(self, resource: TModel) -> None:
        self.session.delete(resource)

    def get(
        self,
        model_class: t.Type[TModel],
        identifier: TIdentifier
    ) -> t.Optional[TModel]:
        return self.session.query(model_class).get(identifier)

    def rollback(self) -> None:
        self.session.rollback()

    def update(
        self,
        resource: TModel,
        attributes: dict
    ) -> TModel:
        self.populate_obj(resource, attributes)
        return resource


class SQLAFactory(
    AbstractFactory[
        SQLAQueryExpression,
        SQLAQueryAdapter,
        SQLAResourceManager,
        SQLAlchemySchema,
        SQLAlchemySchemaOpts,
        TModel
    ],
    t.Generic[TModel]
):
    def __init__(self, session: t.Optional[Session] = None) -> None:
        self.session = session or LocalProxy(lambda: self.get_session())

    def get_session(self) -> Session:
        ext = current_app.extensions.get('sqlalchemy')

        if ext is None:
            raise RuntimeError(
                'An extension named sqlalchemy was not found '
                'in the list of registered extensions for the current application.'
            )

        return ext.db.session

    def create_query_adapter(self, base_query: t.Any) -> SQLAQueryAdapter:
        return SQLAQueryAdapter(base_query, session=self.session)

    def create_query_expression(self, expr: t.Any) -> SQLAQueryExpression:
        return SQLAQueryExpression(expr)

    def create_resource_manager(self) -> SQLAResourceManager[TModel]:
        return SQLAResourceManager(self.session)

    def create_schema(self, model_class: t.Type[TModel]) -> t.Type[SQLAlchemyAutoSchema]:
        class Meta:
            model = model_class

        name = '%sSchema' % model_class.__name__
        bases = (self.get_auto_schema_class(),)

        return type(name, bases, {'Meta': Meta})

    def get_auto_schema_class(self) -> t.Type[SQLAlchemyAutoSchema]:
        return SQLAlchemyAutoSchema

    def get_auto_schema_options_class(self) -> t.Type[SQLAlchemyAutoSchemaOpts]:
        return SQLAlchemyAutoSchemaOpts

    def get_schema_class(self) -> t.Type[SQLAlchemySchema]:
        return SQLAlchemySchema

    def get_schema_options_class(self) -> t.Type[SQLAlchemySchemaOpts]:
        return SQLAlchemySchemaOpts

    def create_client_model(self, user_model: t.Type[UserMixin]) -> t.Type[ClientMixin]:
        return create_client_model(user_model)

    def create_token_model(
        self,
        user_model: t.Type[UserMixin],
        client_model: t.Type[ClientMixin]
    ) -> t.Type[TokenMixin]:
        return create_token_model(user_model, client_model)

    def create_authorization_code_model(
        self,
        user_model: t.Type[UserMixin],
        client_model: t.Type[ClientMixin]
    ) -> t.Type[AuthorizationCodeMixin]:
        return create_authorization_code_model(user_model, client_model)
