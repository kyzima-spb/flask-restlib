"""
https://developer.mozilla.org/ru/docs/Web/HTTP/Headers/ETag
"""

from __future__ import annotations
from abc import ABCMeta, abstractmethod
import typing as t
from urllib.parse import urlencode, parse_qs, urlsplit, urlunsplit

from flask import request, Response
if t.TYPE_CHECKING:
    from _typeshed.wsgi import StartResponse
    from _typeshed.wsgi import WSGIApplication
    from _typeshed.wsgi import WSGIEnvironment


__all__ = (
    'url_update_query_string',
    'AbstractHttpCache',
    'HttpCache',
    'HTTPMethodOverrideMiddleware',
)


def url_update_query_string(url: str, params: dict[str, t.Any]) -> str:
    """
    Given a URL, set or replace a query parameters and return the modified URL.

    >>> url_update_query_string(
    ...     'https://example.com?offset=5&limit=25',
    ...     {
    ...         'offset': 0,
    ...     }
    ... )
    'https://example.com?offset=0&limit=25'
    """
    r = urlsplit(url)
    q = parse_qs(r.query)
    q.update(params)
    r = r._replace(query=urlencode(q, doseq=True))
    return urlunsplit(r)


class AbstractHttpCache(metaclass=ABCMeta):
    def __init__(
        self,
        *,
        methods_support_caching: set[str] = None,
        methods_need_etag: set[str] = None
    ) -> None:
        self.methods_support_caching = methods_support_caching or {'GET', 'HEAD'}
        self.methods_need_etag = methods_need_etag or {'PUT', 'DELETE', 'PATCH'}

    @abstractmethod
    def add(self, etag_string: str) -> None:
        """Adds ETag to fast cache."""

    def check(self) -> bool:
        """
        Returns true if one of given ETags exists in the fast cache otherwise false.
        """
        if request.method in self.methods_support_caching:
            for etag_value in request.if_none_match:
                if self.in_cache(etag_value):
                    return True
        return False

    @abstractmethod
    def clear(self) -> None:
        """Removes all ETags associated with the resource from the fast cache."""

    @abstractmethod
    def in_cache(self, etag_string: str) -> bool:
        """Returns true if given ETag is in the fast cache otherwise false."""

    def update(self, response: Response) -> None:
        etag_string, _ = response.get_etag()

        if etag_string is not None:
            if request.method in self.methods_support_caching:
                self.add(etag_string)
                response.make_conditional(request.environ)
            elif request.method in self.methods_need_etag:
                self.clear()


class HttpCache(AbstractHttpCache):
    def add(self, etag_string: str) -> None:
        pass

    def clear(self) -> None:
        pass

    def in_cache(self, etag_string: str) -> bool:
        return False


class HTTPMethodOverrideMiddleware:
    """
    https://flask.palletsprojects.com/en/2.1.x/patterns/methodoverrides/
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

    def __init__(self, app: "WSGIApplication") -> None:
        self.app = app

    def __call__(
        self, environ: "WSGIEnvironment", start_response: "StartResponse"
    ) -> t.Iterable[bytes]:
        method = environ.get('HTTP_X_HTTP_METHOD_OVERRIDE', '').upper()
        if method in self.allowed_methods:
            environ['REQUEST_METHOD'] = method
        if method in self.bodyless_methods:
            environ['CONTENT_LENGTH'] = '0'
        return self.app(environ, start_response)


THttpCache = t.TypeVar('THttpCache', bound=AbstractHttpCache)
