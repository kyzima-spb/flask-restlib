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

    def to_dict(self, exclude: t.Optional[t.Iterable[str]] = None) -> dict:
        def factory(items: t.Mapping[str, t.Any]) -> dict:
            return {k: v for k, v in items if k not in exclude}
        exclude = exclude or ('headers',)
        return dataclasses.asdict(self, dict_factory=factory)


Func = t.TypeVar('Func', bound=t.Callable[..., t.Any])
AnyException = t.TypeVar('AnyException', bound=Exception)
CatchExceptionCallable = t.Callable[[AnyException, ErrorResponse], None]

ViewType = t.Union[t.Callable, View]
TSchema = t.TypeVar('TSchema', bound=Schema)

# QueryAdapterType = t.TypeVar('QueryAdapterType', bound='AbstractQueryAdapter')
# ResourceManagerType = t.TypeVar('ResourceManagerType', bound='AbstractResourceManager')
# AbstractFactoryType = t.TypeVar('AbstractFactoryType', bound='AbstractFactory')
