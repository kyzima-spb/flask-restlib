from __future__ import annotations
from abc import ABCMeta, abstractmethod
from copy import copy
from functools import partial
import typing as t

from authlib.integrations.flask_oauth2 import ResourceProtector
from flask import Flask
from flask_cors import CORS
from flask_marshmallow import Marshmallow
from flask_wtf import CSRFProtect
from marshmallow import SchemaOpts
from marshmallow.base import SchemaABC
from werkzeug.exceptions import HTTPException

from . import exceptions
from .cli import api_cli
from .http import THttpCache, HttpCache, HTTPMethodOverrideMiddleware
from .oauth2.authorization_server import (
    AuthorizationServer,
    BearerTokenValidator
)
from .oauth2.mixins import (
    AuthorizationCodeMixin,
    ClientMixin,
    TokenMixin,
    UserMixin,
)
from .orm import (
    TQueryExpression,
    TQueryAdapter,
    TResourceManager,
)
from .pagination import (
    LimitOffsetPagination,
    TPagination,
)
from .routing import Router
from .types import (
    ErrorResponse,
    CatchExceptionCallable,
    TFunc,
)


__all__ = ('AbstractFactory', 'RestLib')


TModel = t.TypeVar('TModel')
TSchema = t.TypeVar('TSchema', bound=SchemaABC)
TSchemaOpts = t.TypeVar('TSchemaOpts', bound=SchemaOpts)
TFactory = t.TypeVar('TFactory', bound='AbstractFactory')

DEFAULT_HTTP_ERROR_STATUS = 400


class AbstractFactory(
    t.Generic[
        TQueryExpression,
        TQueryAdapter,
        TResourceManager,
        TSchema,
        TSchemaOpts,
        TModel
    ],
    metaclass=ABCMeta
):
    """
    Abstract factory.

    Is used for:
    1. create a persistent storage query adapter
    2. creating a resource manager
    3. creating an automatically generated schema
    """

    @abstractmethod
    def create_query_adapter(self, base_query: t.Any) -> TQueryAdapter:
        """
        Creates and returns a queryset for retrieving resources from persistent storage.
        """

    @abstractmethod
    def create_query_expression(self, expr: t.Any) -> TQueryExpression:
        """
        Creates and returns an adapter for a model attribute.

        Arguments:
            expr: :class:`.orm.AbstractQueryExpression` or native expression.
        """

    @abstractmethod
    def create_resource_manager(self) -> TResourceManager:
        """Creates and returns a resource manager instance."""

    @abstractmethod
    def create_schema(self, model_class: t.Type[TModel]) -> t.Type[TSchema]:
        """
        Creates and returns an automatic schema class.

        Arguments:
            model_class: A reference to the model class that describes the REST resource.
        """

    @abstractmethod
    def get_auto_schema_class(self) -> t.Type[TSchema]:
        """
        Returns a reference to the base class of the schema
        used in serialization and validation.
        """

    @abstractmethod
    def get_auto_schema_options_class(self) -> t.Type[TSchemaOpts]:
        """Returns a reference to the base auto schema options class."""

    @abstractmethod
    def get_schema_class(self) -> t.Type[TSchema]:
        """
        Returns a reference to the base class of the schema
        used in serialization and validation.
        """

    @abstractmethod
    def get_schema_options_class(self) -> t.Type[TSchemaOpts]:
        """Returns a reference to the base schema options class."""

    @abstractmethod
    def create_client_model(self, user_model: t.Type[UserMixin]) -> t.Type[ClientMixin]:
        """Creates and returns the OAuth2 client class."""

    @abstractmethod
    def create_token_model(
        self,
        user_model: t.Type[UserMixin],
        client_model: t.Type[ClientMixin]
    ) -> t.Type[TokenMixin]:
        """Creates and returns the OAuth2 token class."""

    @abstractmethod
    def create_authorization_code_model(
        self,
        user_model: t.Type[UserMixin],
        client_model: t.Type[ClientMixin]
    ) -> t.Type[AuthorizationCodeMixin]:
        """Creates and returns the OAuth2 code class."""


class RestLib(
    t.Generic[TFactory, TPagination, THttpCache]
):
    __slots__ = (
        '_deferred_error_handlers',
        'app',
        'cors',
        'csrf',
        'factory',
        'pagination_handler',
        'http_cache_instance',
        'router',
        'resource_protector',
        'authorization_server',
        'ma',
        'Schema',
        'AutoSchema',
    )

    def __init__(
        self,
        app: t.Optional[Flask] = None,
        *,
        factory: TFactory,
        pagination_handler: t.Optional[TPagination] = None,
        http_cache_instance: t.Optional[THttpCache] = None,
        auth_options: t.Optional[dict] = None
    ) -> None:
        self._deferred_error_handlers: dict[t.Type[Exception], CatchExceptionCallable] = {}

        self.app = app
        self.cors = CORS()
        self.csrf = CSRFProtect()
        self.factory = factory

        if pagination_handler is None:
            self.pagination_handler = LimitOffsetPagination()
        else:
            self.pagination_handler = pagination_handler #or LimitOffsetPagination()

        self.http_cache_instance = http_cache_instance or HttpCache()
        self.router = Router('api')

        self.Schema = factory.get_schema_class()
        self.AutoSchema = factory.get_auto_schema_class()

        self.resource_protector = ResourceProtector()
        # only bearer token is supported currently
        self.resource_protector.register_token_validator(BearerTokenValidator())

        self.authorization_server = None
        self.ma = Marshmallow()

        if auth_options is not None:
            self.authorization_server = self._create_authorization_server(**auth_options)

        self.catch_exception(exceptions.RestlibError, callback=self.handle_api_exception)
        self.catch_exception(exceptions.AuthenticationError, 401, self.handle_api_exception)
        self.catch_exception(exceptions.AuthorizationError, 403, self.handle_api_exception)
        self.catch_exception(exceptions.DuplicateResource, 409, self.handle_api_exception)
        self.catch_exception(exceptions.LogicalError, 422, self.handle_api_exception)
        self.catch_exception(HTTPException, callback=self.handle_http_exception)

        if app is not None:
            self.init_app(app)

    def _create_authorization_server(
        self,
        user_model: t.Type[UserMixin],
        client_model: t.Optional[t.Type[ClientMixin]] = None,
        token_model: t.Optional[t.Type[TokenMixin]] = None,
        authorization_code_model: t.Optional[t.Type[AuthorizationCodeMixin]] = None,
        query_client: t.Optional[t.Callable] = None,
        save_token: t.Optional[t.Callable] = None
    ) -> AuthorizationServer:
        """
        Arguments:
            user_model: Reference to the User model class.
            client_model: OAuth client model class.
            token_model: OAuth token model class.
            authorization_code_model: OAuth code model class.
            query_client: A function to get client by client_id.
            save_token: A function to save tokens.
        """
        if client_model is None:
            client_model = self.factory.create_client_model(user_model)

        if token_model is None:
            token_model = self.factory.create_token_model(user_model, client_model)

        if authorization_code_model is None:
            authorization_code_model = self.factory.create_authorization_code_model(
                user_model, client_model
            )

        return AuthorizationServer(
            user_model=user_model,
            client_model=client_model,
            token_model=token_model,
            authorization_code_model=authorization_code_model,
            query_client=query_client,
            save_token=save_token
        )

    def _exception_handler(
        self,
        err: Exception,
        status_code: int,
        callback: t.Optional[CatchExceptionCallable] = None
    ) -> tuple[dict, int, dict[str, str]]:
        """
        Handler for all uncaught exceptions.

        Arguments:
            err (Exception): an instance of the raised exception.
            status_code (int): HTTP response code.
            callback: custom exception handler.
        """
        resp = ErrorResponse(str(err), status_code)

        if callback is not None:
            callback(err, resp)

        return resp.to_dict(), resp.status, resp.headers

    def catch_exception(
        self,
        exc_type: t.Type[Exception],
        status_code: int = DEFAULT_HTTP_ERROR_STATUS,
        callback: t.Optional[CatchExceptionCallable] = None
    ) -> None:
        """
        Catch and handle all exceptions of this type.

        Arguments:
            exc_type: the type of exception to catch.
            status_code (int): HTTP response code, defaults to 400.
            callback: custom exception handler.
        """
        handler = partial(self._exception_handler, status_code=status_code, callback=callback)

        if self.app is not None:
            self.app.register_error_handler(exc_type, handler)
        else:
            self._deferred_error_handlers[exc_type] = handler

    def init_app(self, app: Flask) -> None:
        app.wsgi_app = HTTPMethodOverrideMiddleware(app.wsgi_app)

        app.config.setdefault('WTF_CSRF_CHECK_DEFAULT', False)

        self.cors.init_app(app)
        self.csrf.init_app(app)
        self.ma.init_app(app)

        app.config.setdefault('RESTLIB_URL_PREFIX', '')
        app.config.setdefault('RESTLIB_PAGINATION_ENABLED', True)
        app.config.setdefault('RESTLIB_PAGINATION_LIMIT', 25)
        app.config.setdefault('RESTLIB_URL_PARAM_LIMIT', 'limit')
        app.config.setdefault('RESTLIB_URL_PARAM_OFFSET', 'offset')
        app.config.setdefault('RESTLIB_SORTING_ENABLED', True)
        app.config.setdefault('RESTLIB_URL_PARAM_SORT', 'sort')
        app.config.setdefault('RESTLIB_REMEMBER_ME', False)
        app.config.setdefault('RESTLIB_URL_PARAM_LOGOUT', 'logout_uri')
        app.config.setdefault('RESTLIB_HTTP_CACHE_DISABLE', False)
        app.config.setdefault('RESTLIB_CONCURRENCY_CONTROL_DISABLE', False)
        app.config.setdefault('RESTLIB_PUBLIC_METHODS', set())

        app.config.setdefault('RESTLIB_ID_FIELD', 'id')
        app.config.setdefault('RESTLIB_CREATED_FIELD', 'created')
        app.config.setdefault('RESTLIB_UPDATED_FIELD', 'updated')
        app.config.setdefault('RESTLIB_DUMP_ONLY', ())
        app.config.setdefault('RESTLIB_LOAD_ONLY', ())
        app.config.setdefault('RESTLIB_DEFAULT_SCOPE', '')

        app.extensions['restlib'] = self

        for exc_type, handler in self._deferred_error_handlers.items():
            app.register_error_handler(exc_type, handler)

        app.register_blueprint(self.router.bp, url_prefix=app.config['RESTLIB_URL_PREFIX'])
        app.cli.add_command(api_cli)

        if not hasattr(app.jinja_env, 'install_gettext_callables'):
            app.jinja_env.add_extension('jinja2.ext.i18n')
            app.jinja_env.install_null_translations(True)

        if self.authorization_server is not None:
            self.authorization_server.init_app(app)

    def handle_api_exception(
        self,
        err: exceptions.RestlibError,
        resp: ErrorResponse
    ) -> None:
        """Handle an API exception."""
        resp.message = err.get_message()
        resp.detail = err.get_detail()

    def handle_http_exception(self, err: HTTPException, resp: ErrorResponse) -> None:
        """Handle an HTTP exception."""
        if err.code in (400, 422) and hasattr(err, 'data') and hasattr(err, 'exc'):
            # webargs raise error
            messages = err.data.get('messages')

            if messages is None:
                location, errors = None, ['Invalid request.']
            elif len(messages) == 1:
                location, errors = messages.popitem()
            else:
                assert False, 'webargs found errors for more then one location.'

            resp.detail = {
                'location': location,
                'errors': errors,
            }
            resp.headers.update(err.data.get('headers') or {})

        if err.code is not None:
            resp.status = err.code

        if err.description is not None:
            resp.message = err.description

    def register_exception_handler(
        self,
        exc_type: t.Type[Exception],
        status_code: int = DEFAULT_HTTP_ERROR_STATUS
    ) -> t.Callable[[TFunc], TFunc]:
        """
        The decorator registers the function as a handler for given type of exception.

        Arguments:
            exc_type: the type of exception to catch.
            status_code (int): HTTP response code, defaults to 400.
        """
        def decorator(callback: TFunc) -> TFunc:
            self.catch_exception(exc_type, status_code, callback)
            return callback
        return decorator
