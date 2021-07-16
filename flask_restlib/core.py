from __future__ import annotations
from abc import ABCMeta, abstractmethod
import copy

from functools import partial
import typing as t

from authlib.integrations.flask_oauth2 import ResourceProtector
from flask import Flask
from flask_cors import CORS
from flask_marshmallow import Marshmallow
from marshmallow import Schema
from webargs.flaskparser import parser
from werkzeug.exceptions import HTTPException

from flask_restlib import exceptions
from flask_restlib.mixins import (
    AuthorizationCodeType,
    ClientType,
    TokenType,
    UserType
)
from flask_restlib.oauth2 import (
    AuthorizationServer,
    BearerTokenValidator
)
from flask_restlib.pagination import LimitOffsetPagination, TPagination
from flask_restlib.routing import Router
from flask_restlib.types import (
    Func,
    ErrorResponse,
    CatchExceptionCallable,
    TSchema
)


__all__ = (
    'AbstractQueryAdapter',
    'AbstractResourceManager',
    'AbstractFactory',
    'AbstractFilter',
)


DEFAULT_HTTP_ERROR_STATUS = 400


QueryAdapterType = t.TypeVar('QueryAdapterType', bound='AbstractQueryAdapter')
ResourceManagerType = t.TypeVar('ResourceManagerType', bound='AbstractResourceManager')
AbstractFactoryType = t.TypeVar('AbstractFactoryType', bound='AbstractFactory')


class AbstractFilter(metaclass=ABCMeta):
    """
    An instance of the current class is used as a filter
    for the results of a persistent storage query.
    """

    @abstractmethod
    def __and__(self, other):
        pass

    @abstractmethod
    def __call__(self, q):
        """
        Applies the current filter to the given queryset and returns the native queryset.

        Arguments:
            q: native queryset.
        """

    @abstractmethod
    def __or__(self, other):
        pass


class QueryExpression(AbstractFilter):
    def __init__(self, expr):
        self.expr = expr


class UrlQueryFilter(AbstractFilter):
    """
    The filter uses a URL query string and schema to collect and validate input data.

    Filtering your results use a unique query parameter for each of your fields.

    For example, to filter users based on their username:
    GET /users?username=admin

    If you would like to add full text search to your API,
    use a q query parameter, for example:
    GET /users?q=Admin
    """

    def __init__(self, filter_schema: t.Union[type, Schema]):
        """
        Arguments:
            filter_schema (type|Schema):
                A reference to a schema class, or an instance for collecting and validating input data.
        """
        if isinstance(filter_schema, type):
            filter_schema = filter_schema(partial=True)
        else:
            if not filter_schema.partial:
                filter_schema.partial = True

        self._filter_schema = filter_schema

    def __call__(self, q):
        input_data = self.get_input_data()
        return self._do_apply(q, input_data)

    @abstractmethod
    def _do_apply(self, q, input_data: dict):
        """
        Applies the current filter to the given queryset and returns the native queryset.

        Arguments:
            q: native queryset.
            input_data (dict): the input used for filtering.
        """

    def get_input_data(self) -> dict:
        """Returns the input used for filtering."""
        return parser.parse(self._filter_schema, location='query')


class AbstractQueryAdapter(metaclass=ABCMeta):
    __slots__ = (
        '_base_query',
        '_limit',
        '_offset',
        '_order_by',
    )

    def __init__(self, base_query: t.Any) -> None:
        """
        Arguments:
            base_query: native queryset or a reference to the model class.
        """
        if isinstance(base_query, self.__class__):
            base_query = base_query.make_query()

        self._base_query = base_query
        self._limit: t.Optional[int] = None
        self._offset: t.Optional[int] = None
        self._order_by: list[t.Iterable] = [] # fixme: уточнить тип

    def __iter__(self):
        yield from self.all()

    @abstractmethod
    def all(self) -> list:
        """Returns the results represented by this query as a list."""

    @abstractmethod
    def count(self) -> int:
        """Returns the number of rows that should be returned from the query."""

    @abstractmethod
    def exists(self) -> bool:
        """Returns true if a resource with the specified search criteria exists in persistent storage."""

    def filter(self, filter_callback):
        """Applies this filter to the current queryset."""
        self._base_query = filter_callback(self.make_query())
        return self

    @abstractmethod
    def filter_by(self, **kwargs: t.Any) -> AbstractQueryAdapter:
        """Applies these criteria to the current queryset."""

    def first(self) -> t.Optional[t.Any]:
        """
        Return the first result of this query or None if the result doesn’t contain any row.
        """
        result = copy.copy(self).limit(1).all()
        return result[0] if len(result) > 0 else None

    def limit(self, value: int) -> AbstractQueryAdapter:
        """Applies a limit on the number of rows selected by the query."""
        self._limit = value
        return self

    @abstractmethod
    def make_query(self) -> t.Any:
        """Creates and returns a native query object."""

    def one(self) -> t.Any:
        """Return exactly one result or raise an exception."""
        try:
            result = self.one_or_none()
        except exceptions.MultipleResourcesFound as err:
            raise exceptions.MultipleResourcesFound(
                f"Multiple rows were found for `{self.__class__.__name__}.one()`."
            ) from err
        else:
            if result is None:
                raise exceptions.NoResourcesFound(
                    f'No row was found for `{self.__class__.__name__}.one()`.'
                )
            return result

    def one_or_none(self) -> t.Optional[t.Any]:
        """
        Return at most one result or raise an exception.
        Returns None if the query selects no rows.
        """
        result = copy.copy(self).limit(2).all()
        found = len(result)

        if found == 0:
            return None

        if found > 1:
            raise exceptions.MultipleResourcesFound(
                f"Multiple rows were found for `{self.__class__.__name__}.one_or_none()`."
            )

        return result[0]

    def offset(self, value: int) -> AbstractQueryAdapter:
        """Applies the offset from which the query will select rows."""
        self._offset = value
        return self

    def order_by(
        self,
        column: str,
        *columns: t.Tuple[str]
    ) -> AbstractQueryAdapter:
        """Applies sorting by attribute."""
        self._order_by.append((column, *columns))
        return self


class AbstractResourceManager(metaclass=ABCMeta):
    """Manager for working with REST resources."""

    def __enter__(self):
        return self

    def __exit__(self, err_type, err, traceback):
        if err is None:
            self.commit()

    @abstractmethod
    def commit(self):
        """Saves the changes to persistent storage."""

    @abstractmethod
    def create(
        self,
        model_class: t.Any,
        data: t.Union[dict, list[dict]]
    ) -> t.Any:
        """
        Creates and returns a new instance of the resource filled with data.

        Arguments:
            model_class: A reference to the model class that describes the REST resource.
            data (dict|list): Resource attributes.
        """

    @abstractmethod
    def delete(self, resource: t.Any) -> None:
        """
        Removes the resource from the persistent storage.

        Arguments:
            resource (object): The resource instance.
        """

    @abstractmethod
    def get(
        self,
        model_class: t.Type[t.Any],
        identifier: t.Union[t.Any, tuple, dict]
    ) -> t.Optional[t.Any]:
        """
        Returns a resource based on the given identifier, or None if not found.

        Arguments:
            model_class (type): A reference to the model class that describes the REST resource.
            identifier: A scalar, tuple, or dictionary representing the primary key.
        """

    def populate_obj(
        self,
        resource: t.Any,
        attributes: dict
    ) -> None:
        """
        Populates the attributes of the given resource with data from the given attributes argument.

        Arguments:
            resource (object): The resource instance.
            attributes (dict): Resource attributes with new values.
        """
        for attr, value in attributes.items():
            setattr(resource, attr, value)

    @abstractmethod
    def update(
        self,
        resource: t.Any,
        attributes: dict
    ) -> t.Any:
        """
        Updates the resource with the values of the passed attributes.

        Arguments:
            resource (object): The resource instance.
            attributes (dict): Resource attributes with new values.
        """


class AbstractFactory(metaclass=ABCMeta):
    """
    Abstract factory.

    Is used for:
    1. create a persistent storage query adapter
    2. creating a resource manager
    3. creating an automatically generated schema
    """

    @abstractmethod
    def create_model_field_adapter(self, column):
        """
        Creates and returns an adapter for a model attribute.

        Arguments:
            column: native attribute of the model.
        """

    @abstractmethod
    def create_query_adapter(self, base_query: t.Any) -> AbstractQueryAdapter:
        """
        Creates and returns a queryset for retrieving resources from persistent storage.
        """

    @abstractmethod
    def create_resource_manager(self):
        """Creates and returns a resource manager instance."""

    @abstractmethod
    def create_schema(self, model_class) -> t.Type[TSchema]:
        """
        Creates and returns an automatic schema class.

        Arguments:
            model_class: A reference to the model class that describes the REST resource.
        """

    @abstractmethod
    def get_schema_class(self):
        """
        Returns a reference to the base class of the schema
        used in serialization and validation.
        """

    @abstractmethod
    def get_schema_options_class(self):
        """Returns a reference to the base schema options class."""

    @abstractmethod
    def create_client_model(self, user_model):
        """Creates and returns the OAuth2 client class."""

    @abstractmethod
    def create_token_model(self, user_model, client_model):
        """Creates and returns the OAuth2 token class."""

    @abstractmethod
    def create_authorization_code_model(self, user_model, client_model):
        """Creates and returns the OAuth2 code class."""


class HTTPMethodOverrideMiddleware:
    """
    https://flask.palletsprojects.com/en/2.0.x/patterns/methodoverrides/
    """

    allowed_methods = frozenset([
        'GET',
        'HEAD',
        'POST',
        'DELETE',
        'PUT',
        'PATCH',
        'OPTIONS'
    ])
    bodyless_methods = frozenset(['GET', 'HEAD', 'OPTIONS', 'DELETE'])

    def __init__(self, app: t.Any) -> None:
        self.app = app

    def __call__(self, environ, start_response):
        method = environ.get('HTTP_X_HTTP_METHOD_OVERRIDE', '').upper()
        if method in self.allowed_methods:
            environ['REQUEST_METHOD'] = method
        if method in self.bodyless_methods:
            environ['CONTENT_LENGTH'] = '0'
        return self.app(environ, start_response)


class RestLib:
    __slots__ = (
        '_deferred_error_handlers',
        'app',
        'cors',
        'factory',
        'pagination_instance',
        'router',
        'resource_protector',
        'authorization_server',
        'ma',
    )

    def __init__(
        self,
        app: t.Optional[Flask] = None,
        *,
        factory: AbstractFactoryType,
        pagination_instance: TPagination = LimitOffsetPagination(),
        auth_options: t.Optional[dict] = None
    ) -> None:
        self._deferred_error_handlers: dict[t.Type[Exception], CatchExceptionCallable] = {}

        self.app = app
        self.cors = CORS()
        self.factory = factory
        self.pagination_instance = pagination_instance
        self.router = Router('api')

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
        user_model: UserType,
        client_model: t.Optional[ClientType] = None,
        token_model: t.Optional[TokenType] = None,
        authorization_code_model: t.Optional[AuthorizationCodeType] = None,
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

        return resp.to_dict(), status_code, resp.headers

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

        self.cors.init_app(app)
        self.ma.init_app(app)

        app.config.setdefault('RESTLIB_URL_PREFIX', '')
        app.config.setdefault('RESTLIB_PAGINATION_ENABLED', True)
        app.config.setdefault('RESTLIB_PAGINATION_LIMIT', 25)
        app.config.setdefault('RESTLIB_URL_PARAM_LIMIT', 'limit')
        app.config.setdefault('RESTLIB_URL_PARAM_OFFSET', 'offset')
        app.config.setdefault('RESTLIB_SORTING_ENABLED', True)
        app.config.setdefault('RESTLIB_URL_PARAM_SORT', 'sort')
        app.config.setdefault('RESTLIB_REMEMBER_ME', False)

        app.extensions['restlib'] = self

        for exc_type, handler in self._deferred_error_handlers.items():
            app.register_error_handler(exc_type, handler)

        app.register_blueprint(self.router.bp, url_prefix=app.config['RESTLIB_URL_PREFIX'])

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
    ) -> t.Callable[[Func], Func]:
        """
        The decorator registers the function as a handler for given type of exception.

        Arguments:
            exc_type: the type of exception to catch.
            status_code (int): HTTP response code, defaults to 400.
        """
        def decorator(callback: Func) -> Func:
            self.catch_exception(exc_type, status_code, callback)
            return callback
        return decorator
