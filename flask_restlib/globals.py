from __future__ import annotations
import typing as t

from flask import current_app
from werkzeug.local import LocalProxy

from .orm import (
    AbstractQueryExpression,
    AbstractResourceManager,
    AbstractQueryAdapter
)

if t.TYPE_CHECKING:
    from .core import RestLib
    from .oauth2 import AuthorizationServer


current_restlib: RestLib = LocalProxy(  # type: ignore
    lambda: current_app.extensions['restlib']
)

authorization_server: AuthorizationServer = LocalProxy(  # type: ignore
    lambda: current_restlib.authorization_server
)


def Q(expr: t.Any) -> AbstractQueryExpression:
    """
    An adapter for a model attribute.

    Arguments:
        column: native attribute of the model."""
    return current_restlib.factory.create_query_expression(expr)


def query_adapter(base_query) -> AbstractQueryAdapter:
    """Creates and returns a queryset for retrieving resources from persistent storage."""
    return current_restlib.factory.create_query_adapter(base_query)


def resource_manager() -> AbstractResourceManager:
    """Creates and returns a resource manager instance."""
    return current_restlib.factory.create_resource_manager()
