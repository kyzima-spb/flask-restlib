from __future__ import annotations
from abc import ABCMeta, abstractmethod
import copy
from datetime import datetime
import typing

from flask import request, Flask
from flask_marshmallow import Marshmallow
from marshmallow import Schema
from webargs.flaskparser import parser
from werkzeug.exceptions import HTTPException

from flask_restlib.exceptions import (
    NoResourcesFound,
    MultipleResourcesFound
)
from flask_restlib.mixins import (
    AuthorizationCodeType,
    ClientType,
    TokenType,
    UserType
)
from flask_restlib.oauth2 import AuthorizationServer
from flask_restlib.routing import ApiBlueprint


__all__ = (
    'AbstractQueryAdapter',
    'AbstractResourceManager',
    'AbstractFactory',
    'AbstractFilter',
)


QueryAdapterType = typing.TypeVar('QueryAdapterType', bound='AbstractQueryAdapter')
ResourceManagerType = typing.TypeVar('ResourceManagerType', bound='AbstractResourceManager')
AbstractFactoryType = typing.TypeVar('AbstractFactoryType', bound='AbstractFactory')


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

    def __init__(self, filter_schema: typing.Union[type, Schema]):
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
        '_limit', '_offset',
        '_order_by',
    )

    def __init__(self, base_query) -> typing.NoReturn:
        """
        Arguments:
            base_query: native queryset or a reference to the model class.
        """
        if isinstance(base_query, self.__class__):
            base_query = base_query.make_query()

        self._base_query = base_query
        self._limit = None
        self._offset = None
        self._order_by = []

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
    def filter_by(self, **kwargs) -> AbstractQueryAdapter:
        """Applies these criteria to the current queryset."""

    def first(self) -> typing.Union[typing.Any, None]:
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
    def make_query(self) -> typing.Any:
        """Creates and returns a native query object."""

    def one(self) -> typing.Any:
        """Return exactly one result or raise an exception."""
        try:
            result = self.one_or_none()
        except MultipleResourcesFound as err:
            raise MultipleResourcesFound(
                f"Multiple rows were found for `{self.__class__.__name__}.one()`."
            ) from err
        else:
            if result is None:
                raise NoResourcesFound(
                    f'No row was found for `{self.__class__.__name__}.one()`.'
                )
            return result

    def one_or_none(self) -> typing.Union[typing.Any, None]:
        """
        Return at most one result or raise an exception.
        Returns None if the query selects no rows.
        """
        result = copy.copy(self).limit(2).all()
        found = len(result)

        if found == 0:
            return None

        if found > 1:
            raise MultipleResourcesFound(
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
        *columns: typing.Tuple[str]
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
        model_class: typing.Any,
        data: typing.Union[dict, typing.List[dict]]
    ) -> typing.Any:
        """
        Creates and returns a new instance of the resource filled with data.

        Arguments:
            model_class: A reference to the model class that describes the REST resource.
            data (dict|list): Resource attributes.
        """

    @abstractmethod
    def delete(self, resource: typing.Any) -> typing.NoReturn:
        """
        Removes the resource from the persistent storage.

        Arguments:
            resource (object): The resource instance.
        """

    @abstractmethod
    def get(
        self,
        model_class: type,
        identifier: typing.Union[typing.Any, tuple, dict]
    ) -> typing.Union[typing.Any, None]:
        """
        Returns a resource based on the given identifier, or None if not found.

        Arguments:
            model_class (type): A reference to the model class that describes the REST resource.
            identifier: A scalar, tuple, or dictionary representing the primary key.
        """

    def populate_obj(
        self,
        resource: typing.Any,
        attributes: dict
    ) -> typing.NoReturn:
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
        resource: typing.Any,
        attributes: dict
    ) -> typing.Any:
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
    def create_query_adapter(self, base_query) -> AbstractQueryAdapter:
        """
        Creates and returns a queryset for retrieving resources from persistent storage.
        """

    @abstractmethod
    def create_resource_manager(self):
        """Creates and returns a resource manager instance."""

    @abstractmethod
    def create_schema(self, model_class):
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


class RestLib:
    __slots__ = (
        '_blueprints', 'factory', 'authorization_server', 'ma',
    )

    def __init__(
        self,
        app: typing.Optional[Flask] = None,
        *,
        factory: AbstractFactoryType,
        auth_options: typing.Optional[dict] = None
    ) -> typing.NoReturn:
        self._blueprints = []

        self.factory = factory
        self.authorization_server = None
        self.ma = Marshmallow()

        if auth_options is not None:
            self.authorization_server = self._create_authorization_server(**auth_options)

        if app is not None:
            self.init_app(app)

    def _create_authorization_server(
        self,
        user_model: UserType,
        client_model: typing.Optional[ClientType] = None,
        token_model: typing.Optional[TokenType] = None,
        authorization_code_model: typing.Optional[AuthorizationCodeType] = None,
        query_client: typing.Optional[typing.Callable] = None,
        save_token: typing.Optional[typing.Callable] = None
    ):
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

    def init_app(self, app: Flask) -> typing.NoReturn:
        self.ma.init_app(app)

        app.config.setdefault('RESTLIB_PAGINATION_ENABLED', True)
        app.config.setdefault('RESTLIB_URL_PARAM_LIMIT', 'limit')
        app.config.setdefault('RESTLIB_URL_PARAM_OFFSET', 'offset')
        app.config.setdefault('RESTLIB_PAGINATION_LIMIT', 25)
        app.config.setdefault('RESTLIB_SORTING_ENABLED', True)
        app.config.setdefault('RESTLIB_URL_PARAM_SORT', 'sort')

        app.extensions['restlib'] = self

        app.register_error_handler(HTTPException, self.http_exception_handler)

        if not hasattr(app.jinja_env, 'install_gettext_callables'):
            app.jinja_env.add_extension('jinja2.ext.i18n')
            app.jinja_env.install_null_translations(True)

        if self.authorization_server is not None:
            self.authorization_server.init_app(app)

    def create_blueprint(self, *args, **kwargs) -> ApiBlueprint:
        bp = ApiBlueprint(*args, **kwargs)
        self._blueprints.append(bp)
        return bp

    def register_blueprints(self, app: Flask) -> None:
        for bp in self._blueprints:
            app.register_blueprint(bp)

    def http_exception_handler(self, err: HTTPException):
        """Return JSON instead if Content-Type application/json for HTTP errors."""
        resp = {
            'message': err.description,
            'status': err.code,
            'path': request.path,
            'timestamp': datetime.utcnow().isoformat(),
        }

        if err.code in (400, 422) and hasattr(err, 'data'): # webargs raise error
            resp['detail'] = dict(zip(
                ('location', 'errors'),
                err.data.get('messages').popitem()
            ))
            headers = err.data.get('headers')

            if headers:
                return resp, err.code, headers

        return resp, err.code
