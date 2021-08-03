import dataclasses
from datetime import datetime
import typing as t

from flask import request
from flask.views import View
from marshmallow import Schema


@dataclasses.dataclass
class ErrorResponse:
    """REST API response object on errors."""

    message: str
    status: int = 400
    detail: t.Optional[dict] = None
    headers: dict = dataclasses.field(default_factory=dict, repr=False)
    path: str = dataclasses.field(init=False, repr=False)
    timestamp: str = dataclasses.field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.headers.setdefault('Cache-Control', 'no-store')
        self.headers.setdefault('Pragma', 'no-cache')

        self.path = request.path
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self, exclude: t.Iterable[str] = ('headers',)) -> dict:
        def factory(items: t.Iterable[tuple[str, t.Any]]) -> dict:
            return {k: v for k, v in items if k not in exclude}
        return dataclasses.asdict(self, dict_factory=factory)


TFunc = t.TypeVar('TFunc', bound=t.Callable[..., t.Any])
TException = t.TypeVar('TException', bound=Exception)
CatchExceptionCallable = t.Callable[[TException, ErrorResponse], None]

TIdentifier = t.Union[t.Any, tuple, dict]
TView = t.Union[t.Callable, View]

# Uses for argument filter_callback in AbstractQueryAdapter.filter() method.
TQueryFilter = t.Callable[[t.Any], t.Any]

THttpHeader = tuple[str, str]
THttpHeaders = list[THttpHeader]

TFactory = t.TypeVar('TFactory', bound='AbstractFactory')
TQueryAdapter = t.TypeVar('TQueryAdapter', bound='AbstractQueryAdapter')
TResourceManager = t.TypeVar('TResourceManager', bound='AbstractResourceManager')
TSchema = t.TypeVar('TSchema', bound=Schema)
