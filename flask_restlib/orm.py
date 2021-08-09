from __future__ import annotations
from abc import ABCMeta, abstractmethod
import typing as t

from .types import TQueryExpression


class AbstractQueryExpression(metaclass=ABCMeta):
    """
    An adapter represent that is:

    * model column that overloads all valid operators;
    * an expression with which one of the valid operators can be used.

    For example::

        >>> from flask_restlib import Q, authorization_server
        >>> model = authorization_server.OAuth2Token
        >>> token = 'abcde12345'
        >>> (Q(model.access_token) == token) | (Q(model.refresh_token) == token)
        <flask_restlib.contrib.sqla.SQLAQueryExpression object at 0x101029dd0>

    An instance of the current class is used as a filter
    for the results of a persistent storage query.
    """

    __slots__ = ('_native_expression',)

    def __init__(self, expr: t.Any) -> None:
        self._native_expression = self.to_native(expr)

    def __repr__(self) -> str:
        return str(self._native_expression)

    @abstractmethod
    def __call__(self, q):
        """
        Applies the current filter to the given queryset and returns the native queryset.

        Arguments:
            q: native queryset.
        """

    @abstractmethod
    def __and__(self, other) -> TQueryExpression:
        """Implement the ``&`` operator."""

    @abstractmethod
    def __or__(self, other) -> TQueryExpression:
        """Implement the ``|`` operator."""

    @abstractmethod
    def __eq__(self, other: t.Any) -> TQueryExpression:
        """Implement the ``==`` operator."""

    @abstractmethod
    def __ne__(self, other: t.Any) -> TQueryExpression:
        """Implement the ``!=`` operator."""

    @abstractmethod
    def __lt__(self, other: t.Any) -> TQueryExpression:
        """Implement the ``<`` operator."""

    @abstractmethod
    def __le__(self, other: t.Any) -> TQueryExpression:
        """Implement the ``<=`` operator."""

    @abstractmethod
    def __gt__(self, other: t.Any) -> TQueryExpression:
        """Implement the ``>`` operator."""

    @abstractmethod
    def __ge__(self, other: t.Any) -> TQueryExpression:
        """Implement the ``>=`` operator."""

    def to_native(self, expr: t.Any) -> t.Any:
        if isinstance(expr, self.__class__):
            return expr._native_expression
        return expr
