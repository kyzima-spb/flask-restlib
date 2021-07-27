"""
https://developer.mozilla.org/ru/docs/Web/HTTP/Headers/ETag
"""

from __future__ import annotations
from abc import ABCMeta, abstractmethod
import typing as t

from flask import request, Response


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


THttpCache = t.TypeVar('THttpCache', bound=AbstractHttpCache)
