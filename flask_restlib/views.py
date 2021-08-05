from __future__ import annotations
from collections import OrderedDict
import typing
import typing as t

from flask import (
    current_app, json,
    abort, request, Response, jsonify
)
from flask.views import MethodView
from flask.typing import ResponseValue, ResponseReturnValue
from marshmallow import Schema
from werkzeug.datastructures import Headers
from werkzeug.exceptions import (
    PreconditionRequired,
    PreconditionFailed
)
from webargs.flaskparser import parser
from werkzeug.http import generate_etag

from flask_restlib import current_restlib
from flask_restlib import mixins
from flask_restlib.core import AbstractFactory, AbstractResourceManager
from flask_restlib.http import THttpCache
from flask_restlib.oauth2 import authorization_server, save_client
from flask_restlib.permissions import Permission, TokenHasScope
from flask_restlib.schemas import ClientSchema
from flask_restlib.types import TIdentifier, TSchema


__all__ = (
    'ApiView',
    'CreateView', 'DestroyView', 'ListView', 'RetrieveView', 'UpdateView',
)


class ApiView(MethodView):
    """
    Base class for all REST resource views.

    Attributes:
        factory_class (AbstractFactory): A reference to the class of the factory being used.
        queryset: A reference to native queryset for retrieving resources.
        lookup_names (tuple):
            Names of the fields to retrieve resource in persistent storage.
            For example, names of primary keys in order in which they are used in SQL query.
        model_class: A reference to the class of the model.
        schema_class: A reference to the class of the schema to use for serialization.
    """

    concurrency_control_disable: t.ClassVar[bool] = False
    factory_class = None
    http_cache_instance = None
    http_cache_disable: t.ClassVar[bool] = False
    queryset = None
    lookup_names: t.ClassVar[tuple[str, ...]] = ()
    methods_returning_etag: t.ClassVar[set[str]] = {'GET', 'HEAD', 'POST', 'PUT', 'PATCH'}
    model_class = None
    permissions: list[Permission] = []
    schema_class = None

    def get_factory(self) -> AbstractFactory:
        """Returns an instance of the abstract factory."""
        if self.factory_class is None:
            return current_restlib.factory
        return self.factory_class()

    def check_permissions(self) -> None:
        """
        Check if the request should be permitted.
        Raises an exception if the request is not permitted.
        """
        for permission in self.permissions:
            permission.check_permission(self)

    def check_resource_permissions(self, resource: typing.Any) -> None:
        """
        Check if the request should be permitted for a given resource.
        Raises an exception if the request is not permitted.
        """
        for permission in self.permissions:
            permission.check_resource_permission(self, resource)

    def create_queryset(self):
        """
        Creates and returns a native queryset for retrieving resources from persistent storage.
        """
        factory = self.get_factory()

        if self.queryset is not None:
            queryset = factory.create_query_adapter(self.queryset)
        else:
            queryset = factory.create_query_adapter(self.get_model_class())

        return queryset

    def create_resource_manager(self) -> AbstractResourceManager:
        """Creates and returns a resource manager instance."""
        return self.get_factory().create_resource_manager()

    def create_schema(self, *args, **kwargs) -> TSchema:
        """
        Creates and returns a schema instance
        that is used to validate the input and serialize the output.
        """
        return self.get_schema_class()(*args, **kwargs)

    def dispatch_request(self, *args: t.Any, **kwargs: t.Any) -> ResponseReturnValue:
        self.check_permissions()

        cache = self.get_http_cache()

        if cache and cache.check():
            return '', 304

        if self.lookup_names:
            kwargs['id'] = OrderedDict(
                (name, kwargs.pop(name)) for name in self.lookup_names if name in kwargs
            )

        resp = self.normalize_response_value(
            super().dispatch_request(*args, **kwargs)
        )

        if cache:
            cache.update(resp)

        return resp

    def generate_etag(
        self, data: t.Any, schema: Schema = None, **extra_data: t.Any
    ) -> str:
        """
        Generates and returns an ETag from data.

        Arguments:
            data (typing.Any): data to use to generate ETag.
            schema (Schema): marshmallow schema to dump data with before hashing.
            extra_data (dict): extra data to add before hashing.

        Note:
            Idea borrowed from flask-smorest.
        """
        if schema is not None:
            data = schema.dump(data)
        if extra_data:
            data = (data, extra_data)
        data = json.dumps(data, sort_keys=True)
        return generate_etag(bytes(data, 'utf-8'))

    def get_http_cache(self) -> t.Optional[THttpCache]:
        """Returns an instance of the ETag."""
        if self.http_cache_disable or current_app.config['RESTLIB_HTTP_CACHE_DISABLE']:
            return None

        if self.http_cache_instance is None:
            return current_restlib.http_cache_instance

        return self.http_cache_instance

    def get_model_class(self):
        """
        Returns a reference to the class of the model.
        """
        if self.model_class is None:
            raise AttributeError(
                'You must assign the value of the attribute `model_class`, '
                f'or override the `{self.__class__.__name__}.get_model_class()` method.'
            )
        return self.model_class

    def get_for_update(
        self,
        identifier: TIdentifier,
        description: t.Optional[str] = None,
        model_class: t.Optional[t.Any] = None,
        as_create: bool = False
    ) -> t.Any:
        """
        Returns a resource based on the given identifier to perform an unsafe operation.

        If concurrency control is disabled, then the behavior is the same as `ApiView.get_or_404()`.

        Arguments:
            model_class (type): A reference to the model class that describes the REST resource.
            identifier: A scalar, tuple, or dictionary representing the primary key.
            description (str):
            as_create (bool):

        Raises:
            PreconditionRequired: If the request does not contain If-Match headers.
            PreconditionFailed: If the request cannot be fulfilled.
        """
        if self.concurrency_control_disable or current_app.config['RESTLIB_CONCURRENCY_CONTROL_DISABLE']:
            return self.get_or_404(identifier, description, model_class)

        if not as_create and not request.if_match:
            raise PreconditionRequired('ETag not provided for resource operation.')

        resource = self.get_or_404(identifier, description, model_class)
        etag = self.generate_etag(resource, self.create_schema())

        if not request.if_match.is_weak(etag):
            raise PreconditionFailed(
                'The If-Match header value does not match the ETag '
                'computed to represent the resource that is currently stored on the server.'
            )

        return resource

    def get_or_404(
        self,
        identifier: TIdentifier,
        description: t.Optional[str] = None,
        model_class: t.Optional[t.Any] = None
    ) -> t.Any:
        """
        Returns a resource based on the given identifier, throws an HTTP 404 error.

        Arguments:
            model_class (type): A reference to the model class that describes the REST resource.
            identifier: A scalar, tuple, or dictionary representing the primary key.
            description (str):
        """
        resource = self.get_factory().create_resource_manager().get(
            model_class or self.get_model_class(), identifier
        )

        if resource is None:
            abort(404, description=description)

        self.check_resource_permissions(resource)

        return resource

    def get_schema_class(self) -> typing.Type[TSchema]:
        """
        Returns a reference to the class of the schema to use for serialization.
        """
        if self.schema_class is None:
            self.__class__.schema_class = self.get_factory().create_schema(
                self.get_model_class()
            )

        if self.schema_class is None:
            raise AttributeError(
                'You must assign the value of the attribute `schema_class`, '
                f'or override the `{self.__class__.__name__}.get_schema_class()` method.'
            )

        return self.schema_class

    def normalize_response_value(self, rv: ResponseReturnValue) -> Response:
        """Converts the return value from a view to an instance of Response class."""
        status_code = 200
        headers = None

        if isinstance(rv, tuple):
            count = len(rv)

            if count == 3:
                rv, status_code, headers = rv
            elif count == 2:
                if isinstance(rv[1], int):
                    rv, status_code = rv
                else:
                    rv, headers = rv
            else:
                rv = rv[0]

        if isinstance(rv, current_app.response_class):
            if status_code != 200:
                rv.status_code = status_code
            if headers is not None:
                rv.headers.update(headers)
        else:
            rv = self.make_response(
                rv, status_code=status_code, headers=Headers(headers)
            )

        return rv

    def make_response(
        self,
        rv: ResponseValue,
        status_code: int = 200,
        headers: Headers = None
    ) -> Response:
        """Creates and returns an instance of Response class."""
        # response_class = current_app.response_class
        resp = jsonify(rv)
        resp.status_code = status_code

        if headers is not None:
            resp.headers.update(headers)

        if request.method in self.methods_returning_etag:
            if 'ETag' not in resp.headers:
                resp.set_etag(self.generate_etag(rv), weak=True)

        return resp


class CreateView(mixins.CreateViewMixin, ApiView):
    pass


class DestroyView(mixins.DestroyViewMixin, ApiView):
    pass


class ListView(mixins.ListViewMixin, ApiView):
    pass


class RetrieveView(mixins.RetrieveViewMixin, ApiView):
    pass


class UpdateView(mixins.UpdateViewMixin, ApiView):
    pass


class ClientView(CreateView):
    schema_class = ClientSchema
    permissions = [TokenHasScope('oauth')]

    def get_model_class(self):
        return authorization_server.OAuth2Client

    def create(self) -> ResponseReturnValue:
        schema = self.create_schema()  # type: ignore
        data = parser.parse(schema, location='json_or_form')
        client = save_client(**data)
        return schema.dump(client), 201, self.get_creation_headers(data)
