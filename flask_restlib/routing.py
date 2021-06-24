"""
1. Использовать Blueprint для разных версий и для одной
   Позволяет избежать проблем именования endpoint-ов
"""
from __future__ import annotations
import re
from collections.abc import Iterable
import typing as t

from flask import Blueprint
from flask.views import View

from flask_restlib.types import ViewType
from flask_restlib.utils import camel_to_snake


class Route:
    """
    В аргумент view можно передать представление на базе функции или класса.
    Если передано представление на базе класса, то автоматически вызывается метод as_view.
    Если методу as_view необходимо передать дополнительные аргументы, кроме endpoint,
    то сделайте это вручную:
    Route('users', UserView.as_view('users', *args, **kwargs))
    """

    __slots__ = (
        '_parent', '_children', 'parent_lookup_name',
        'resource', 'view', 'is_item',
        'endpoint', 'url_converter', 'lookup_name',
    )

    def __init__(
        self,
        resource: t.Any,
        view: ViewType,
        is_item: bool = False,
        endpoint: t.Optional[str] = None,
        url_converter: str = 'int',
        lookup_name: t.Union[str, bool] = 'id',
        parent: t.Optional[Route] = None,
        parent_lookup_name: t.Optional[str] = None
    ) -> None:
        """
        Arguments:
            resource (str): resource name, used as part of the URI.
            view: a function or class based view.
            is_item (bool): the route is used for the collection item.
            endpoint (str): the endpoint for the registered URL rule.
            url_converter (str): the name of the converter used for explicit type casting.
            lookup_name (str|bool): the name of the URI parameter.
            parent (:py:class:`~flask_restlib.routing.Route`): the name of the URI parameter for the parent route.
            parent_lookup_name (str): the name of the URI parameter for the parent route.
        """
        self._parent: t.Optional[Route] = None
        self._children: list[Route] = []

        self.resource = resource
        self.is_item = bool(is_item)

        if endpoint is None:
            endpoint = camel_to_snake(view.__name__)

        if isinstance(view, View):
            view = view.as_view(endpoint)

        self.endpoint = endpoint
        self.view = view

        self.url_converter = url_converter
        self.lookup_name = lookup_name
        self.parent_lookup_name = parent_lookup_name

        if parent is not None:
            parent.add(self)

    def __repr__(self):
        return '<{} rule={!r} endpoint={!r}>'.format(
            self.__class__.__name__, self.get_rule(), self.endpoint
        )

    def iter_rules(self) -> Iterable[tuple[str, str, ViewType]]:
        """
        Returns an iterator,
        each element of which is a tuple of argument values
        for the :py:meth:`~flask.Flask.add_url_rule` method.
        """
        yield self.get_rule(), self.endpoint, self.view

        for child in self._children:
            yield from child.iter_rules()

    def add(self, route: Route) -> Route:
        """Add a child route to the current route and set its parent as the current route."""
        route._parent = self
        self._children.append(route)
        return route

    def add_item_view(
        self,
        view: ViewType,
        endpoint: t.Optional[str] = None,
        url_converter: t.Optional[str] = None,
        lookup_name: t.Optional[t.Union[str, bool]] = None,
        parent_lookup_name: t.Optional[str] = None
    ) -> Route:
        """
        Creates and returns a route for a collection item.

        Arguments:
            view:
                a function or class based view.
            endpoint (str):
                the endpoint for the registered URL rule.
                If not specified, the parent's value is used.
            url_converter (str):
                the name of the converter used for explicit type casting.
                If not specified, the parent's value is used.
            lookup_name (str|bool):
                the name of the URI parameter.
                If not specified, the parent's value is used.
            parent_lookup_name (str):
                the name of the URI parameter for the parent route.
                If not specified, the parent's value is used.
        """
        return self.__class__(
            resource=self.resource,
            view=view,
            is_item=True,
            endpoint=endpoint,
            url_converter=url_converter or self.url_converter,
            lookup_name=lookup_name or self.lookup_name,
            parent=self,
            parent_lookup_name=parent_lookup_name or self.parent_lookup_name
        )

    def get_rule(self) -> str:
        """Returns the URL rule as a string."""
        rule: list[str] = []

        if self.has_parent():
            parent_rule = self._parent.get_rule()

            if self.parent_lookup_name:
                # from werkzeug.routing import parse_rule
                # print(list(parse_rule(rule)))
                pattern = re.compile(r'(.*)<(.+?:)?(.+?)>')
                replacement = r'\1<\2%s>' % self.parent_lookup_name
                parent_rule = pattern.sub(replacement, parent_rule)

            rule.extend(filter(None, parent_rule.split('/')))

        if not rule or rule[-1] != self.resource:
            rule.append(self.resource)

        if self.has_lookup():
            rule.append('<{}:{}>'.format(self.url_converter, self.lookup_name))

        return '/{}{}'.format(
            '/'.join(rule),
            '' if self.is_item else '/'
        )

    def has_children(self) -> bool:
        """Returns true if the route has a child routes."""
        return bool(self._children)

    def has_lookup(self) -> bool:
        """Returns true if the route uses an identifier for searching."""
        return self.is_item and self.lookup_name is not False

    def has_parent(self) -> bool:
        """Returns true if the route has a parent route."""
        return self._parent is not None


class ApiBlueprint(Blueprint):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.routes = []

    def add_route(self, route: Route) -> Route:
        """Adds a route for the resource."""
        self.routes.append(route)
        return route

    def register(self, app, options, first_registration=False):
        for route in self.routes:
            for rule, endpoint, view in route.iter_rules():
                self.add_url_rule(rule, endpoint, view)
        super().register(app, options, first_registration)
