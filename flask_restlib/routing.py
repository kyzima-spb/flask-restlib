"""
1. Использовать Blueprint для разных версий и для одной
   Позволяет избежать проблем именования endpoint-ов
"""
from __future__ import annotations
from contextlib import contextmanager
import typing as t

from flask.blueprints import Blueprint, BlueprintSetupState
from flask.views import View

from flask_restlib.types import TView
from flask_restlib.utils import camel_to_snake


class Collection:
    """
    Represents a collection or REST resource.
    Used as syntactic sugar for building routes.
    """

    __slots__ = ('_resource_name', '_routes')

    def __init__(self, resource_name: str) -> None:
        """
        Arguments:
            resource_name (str): resource name, used as part of the URI.
        """
        self._resource_name = resource_name
        self._routes: list[Route] = []

    def __repr__(self) -> str:
        return f'{self.__class__.__name__}({self._resource_name!r})'

    def __iter__(self) -> t.Iterator[Route]:
        return iter(self._routes)

    def add_view(self, view: TView, endpoint: str = None) -> Route:
        """
        Creates and returns a `Route` object for a collection.

        Arguments:
            view: a function or class based view.
            endpoint (str): the endpoint for the registered URL rule.
        """
        route = Route(self._resource_name, view, endpoint, lookup_name=None)
        self._routes.append(route)
        return route

    def add_item_view(
        self,
        view: TView,
        endpoint: str = None,
        *,
        url_converter: str = 'int',
        lookup_name: t.Optional[str] = 'id'
    ) -> Route:
        """
        Creates and returns a `Route` object for a collection item.

        Arguments:
            view: a function or class based view.
            endpoint (str): the endpoint for the registered URL rule.
            url_converter (str): the name of the converter used for explicit type casting.
            lookup_name (str|bool): the name of the URI parameter.
        """
        route = Route(
            self._resource_name,
            view,
            endpoint,
            is_item=True,
            url_converter=url_converter,
            lookup_name=lookup_name
        )
        self._routes.append(route)
        return route

    def add_route(self, route: Route) -> Route:
        """
        Adds a route to the current collection and sets URL prefix as the resource name.

        Arguments:
            route (Route): route instance.
        """
        route.url_prefix = f'/{self._resource_name}'
        self._routes.append(route)
        return route


class Route:
    """
    В аргумент view можно передать представление на базе функции или класса.
    Если передано представление на базе класса, то автоматически вызывается метод as_view.
    Если методу as_view необходимо передать дополнительные аргументы, кроме endpoint,
    то сделайте это вручную:
    Route('users', UserView.as_view('users', *args, **kwargs))
    """

    __slots__ = (
        'resource_name', 'view', 'is_item',
        'endpoint', 'url_converter', 'lookup_name', 'url_prefix',
        'router',
    )

    def __init__(
        self,
        resource_name: str,
        view: TView,
        endpoint: t.Optional[str] = None,
        *,
        is_item: bool = False,
        url_converter: str = 'int',
        lookup_name: t.Optional[str] = 'id',
        url_prefix: str = ''
    ) -> None:
        """
        Arguments:
            resource_name (str): resource name, used as part of the URI.
            view: a function or class based view.
            endpoint (str): the endpoint for the registered URL rule.
            is_item (bool): the route is used for the collection item.
            url_converter (str): the name of the converter used for explicit type casting.
            lookup_name (str|bool): the name of the URI parameter.
            url_prefix (str): prefix used as part of the URI.
        """
        self.resource_name = resource_name
        self.is_item = bool(is_item)
        self.url_converter = url_converter
        self.lookup_name = lookup_name if is_item else None
        self.url_prefix = url_prefix
        self.router: t.Optional[Router] = None

        if endpoint is None:
            endpoint = camel_to_snake(view.__name__)

        if isinstance(view, type):
            if not issubclass(view, View):
                raise TypeError('view must be a subclass of `View`.')
            view = view.as_view(endpoint) # type: ignore

        self.endpoint = endpoint
        self.view = view

    def __repr__(self) -> str:
        return '<{} rule={!r} endpoint={!r}>'.format(
            self.__class__.__name__, self.get_rule(), self.endpoint
        )

    def create_router(self, name: str, parent_lookup_name: str = None) -> Router:
        router = Router(name, self.get_rule(parent_lookup_name))

        if self.router is not None:
            self.router.bp.register_blueprint(router.bp)

        return router

    def get_rule(self, replace_lookup_name: str = None) -> str:
        """Returns the URL rule as a string."""
        rule = self.url_prefix.rstrip('/') + '/{}{}'.format(
            self.resource_name,
            '' if self.is_item else '/'
        )

        if self.has_lookup():
            if replace_lookup_name is None:
                replace_lookup_name = self.lookup_name
            rule += f'/<{self.url_converter}:{replace_lookup_name}>'

        return rule

    def has_lookup(self) -> bool:
        """Returns true if the route uses an identifier for searching."""
        return self.is_item and self.lookup_name is not None


class Router:
    __slots__ = ('bp', '_bp_state', 'name', 'url_prefix', 'routes')

    def __init__(
        self,
        name: str,
        url_prefix: str = None
    ) -> None:
        self.name = name
        self.url_prefix = url_prefix
        self.routes: list[Route] = []

        self.bp = Blueprint(name, __name__, url_prefix=url_prefix)
        self._bp_state: t.Optional[BlueprintSetupState] = None

        self.bp.record(self._save_bp_state)  # once ?

    def __repr__(self) -> str:
        return '<{} name={!r} url_prefix={!r}>'.format(
            self.__class__.__name__, self.name, self.url_prefix
        )

    def _save_bp_state(self, state: BlueprintSetupState) -> None:
        self._bp_state = state

    def add_route(self, route: Route) -> Route:
        """Adds a route for the resource."""
        route.router = self
        self.routes.append(route)
        self.add_url_rule(route.get_rule(), view_func=route.view)
        return route

    def add_url_rule(
        self,
        rule: str,
        endpoint: t.Optional[str] = None,
        view_func: t.Optional[t.Callable] = None,
        **options: t.Any,
    ) -> None:
        obj = self.bp if self._bp_state is None else self._bp_state
        obj.add_url_rule(rule, endpoint, view_func, **options)

    @contextmanager
    def collection(self, resource_name: str) -> t.Iterator[Collection]:
        collection = Collection(resource_name)
        try:
            yield collection
        finally:
            for route in collection:
                self.add_route(route)
