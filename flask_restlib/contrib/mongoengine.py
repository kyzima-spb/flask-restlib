from __future__ import annotations
from copy import deepcopy
from functools import partial
import time
import typing as t

try:
    from flask_mongoengine import Document
except ImportError:
    from mongoengine import Document
from marshmallow import Schema as _Schema, SchemaOpts as _SchemaOpts
import mongoengine as me
from mongoengine.errors import OperationError
from mongoengine.queryset.base import BaseQuerySet

from flask_restlib.core import (
    AbstractQueryAdapter,
    AbstractResourceManager,
    AbstractFactory,
    QueryExpression
)
from flask_restlib.mixins import (
    AuthorizationCodeMixin,
    ClientMixin,
    TokenMixin
)
from flask_restlib.oauth2 import generate_client_id


__all__ = (
    'AbstractOAuth2Client', 'AbstractOAuth2Token', 'AbstractOAuth2AuthorizationCode',
    'MongoQueryAdapter', 'MongoResourceManager', 'MongoEngineFactory',
)


class AbstractOAuth2Client(ClientMixin, Document):
    id = me.StringField(
        primary_key=True,
        max_length=48,
        default=partial(generate_client_id, 48)
    )
    client_secret = me.StringField(
        max_length=120,
        default=''
    )
    client_id_issued_at = me.IntField(default=0)
    client_secret_expires_at = me.IntField(default=0)
    client_metadata = me.DictField(required=True)

    meta = {
        'abstract': True,
        'collection': 'oauth2_client',
    }


class AbstractOAuth2Token(TokenMixin, Document):
    id = me.UUIDField(primary_key=True)
    token_type = me.StringField(
        max_length=40,
        default='Bearer'
    )
    access_token = me.StringField(
        required=True,
        max_length=255,
        unique=True
    )
    refresh_token = me.StringField(
        max_length=255,
        unique=True,
        sparse=True
    )
    scope = me.StringField(default='')
    revoked = me.BooleanField(default=False)
    issued_at = me.IntField(
        default=lambda: int(time.time())
    )
    expires_in = me.IntField(default=0)

    meta = {
        'abstract': True,
        'collection': 'oauth2_token',
        'indexes': [
            'access_token',
            'refresh_token',
        ],
    }


class AbstractOAuth2AuthorizationCode(AuthorizationCodeMixin, Document):
    id = me.UUIDField(primary_key=True)
    code = me.StringField(
        required=True,
        max_length=120,
        unique=True
    )
    redirect_uri = me.StringField(default='')
    response_type = me.StringField(default='')
    scope = me.StringField(default='')
    nonce = me.StringField(default='')
    auth_time = me.IntField(
        default=lambda: int(time.time())
    )

    code_challenge = me.StringField(default='')
    code_challenge_method = me.StringField(
        max_length=48,
        default=''
    )

    meta = {
        'abstract': True,
        'collection': 'oauth2_code',
    }


class SchemaOpts(_SchemaOpts):
    def __init__(self, meta, ordered=False):
        meta.dump_only = {
            'id', 'created_at', 'updated_at', *getattr(meta, 'dump_only', ())
        }

        super().__init__(meta, ordered=ordered)


class Schema(_Schema):
    OPTIONS_CLASS = SchemaOpts


class MongoModelField:
    def __init__(self, column):
        self.column = column

    def __eq__(self, other):
        return self.make_expression(self.column.name, other)

    def __ne__(self, other):
        return self.make_expression(f'{self.column.name}__ne', other)

    def __lt__(self, other):
        return self.make_expression(f'{self.column.name}__lt', other)

    def __le__(self, other):
        return self.make_expression(f'{self.column.name}__lte', other)

    def __gt__(self, other):
        return self.make_expression(f'{self.column.name}__gt', other)

    def __ge__(self, other):
        return self.make_expression(f'{self.column.name}__gte', other)

    def make_expression(self, argument_name, value):
        return MongoQueryExpression(
            me.Q(**{argument_name: value})
        )


class MongoQueryExpression(QueryExpression):
    def __and__(self, other):
        return self.__class__(self.expr & other.expr)

    def __call__(self, query):
        return query(self.expr)

    def __or__(self, other):
        return self.__class__(self.expr | other.expr)


class MongoQueryAdapter(AbstractQueryAdapter):
    __slots__ = ()

    def __init__(self, base_query):
        if not isinstance(base_query, BaseQuerySet):
            base_query = base_query.objects
        super().__init__(base_query)

    def all(self) -> list:
        return self.make_query().all()

    def count(self) -> int:
        return self.make_query().count(with_limit_and_skip=True)

    def exists(self) -> bool:
        return bool(self.make_query().first())

    def filter_by(self, **kwargs) -> AbstractQueryAdapter:
        self._base_query = self._base_query.filter(**kwargs)
        return self

    def make_query(self):
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
    def _prepare_identifier(self, model_class, identifier):
        """
        Converts the original resource identifier to a Mongo-friendly format.

        Arguments:
            model_class: A reference to the model class.
            identifier (dict): original identifier.

        Returns:
            The transformed identifier.
        """
        if isinstance(identifier, dict):
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
        else:
            pk = identifier

        return pk

    def commit(self):
        pass

    def create(
        self,
        model_class: t.Any,
        data: t.Union[dict, t.List[dict]]
    ) -> t.Any:
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

    def delete(self, resource: t.Any) -> None:
        try:
            resource.delete()
        except OperationError as err:
            raise RuntimeError(err) from err

    def get(
        self,
        model_class: t.Type[t.Any],
        identifier: t.Union[t.Any, tuple, dict]
    ) -> t.Optional[t.Any]:
        return model_class.objects.with_id(
            self._prepare_identifier(model_class, identifier)
        )

    def update(
        self,
        resource: t.Any,
        attributes: dict
    ) -> t.Any:
        if not resource.modify(**attributes):
            raise RuntimeError('Failed to update resource.')
        return resource


class MongoEngineFactory(AbstractFactory):
    def create_model_field_adapter(self, column):
        return MongoModelField(column)

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

    def create_client_model(self, user_model):
        return type(
            'OAuth2Client',
            (AbstractOAuth2Client,),
            {
                'user': me.ReferenceField(user_model, required=True),
            }
        )

    def create_token_model(self, user_model, client_model):
        return type(
            'OAuth2Token',
            (AbstractOAuth2Token,),
            {
                'user': me.ReferenceField(user_model, required=True),
                'client': me.ReferenceField(client_model, required=True),
            }
        )

    def create_authorization_code_model(self, user_model, client_model):
        return type(
            'OAuth2Code',
            (AbstractOAuth2AuthorizationCode,),
            {
                'user': me.ReferenceField(user_model, required=True),
                'client': me.ReferenceField(client_model, required=True),

                'meta': {
                    'indexes': [
                        ('client', 'code'),
                    ],
                }
            }
        )
