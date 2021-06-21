import typing as t


class RestlibError(Exception):
    default_message = None

    def __init__(
        self,
        message: t.Optional[str] = None,
        detail: t.Optional[t.Union[dict, list]] = None
    ) -> t.NoReturn:
        self._message = message
        self._detail = detail
        super().__init__(message)

    def get_detail(self) -> t.Union[dict, list]:
        return self._detail

    def get_message(self) -> str:
        return self._message or self.default_message


class MultipleResourcesFound(RestlibError):
    default_message = 'Multiple rows were found for in persistent storage but need one.'


class NoResourcesFound(RestlibError):
    default_message = 'No row was found in persistent storage but need one.'


class DuplicateResource(RestlibError):
    pass


class LogicalError(RestlibError):
    pass


# PermissionDenied
class AuthorizationError(RestlibError):
    """There are not enough rights to perform the action."""

    def __init__(
        self,
        message: t.Optional[str] = None,
        resource: t.Optional[t.Any] = None,
        detail: t.Optional[t.Union[dict, list]] = None
    ) -> t.NoReturn:
        super().__init__(message, detail)
        self.resource = resource


class AuthenticationError(RestlibError):
    """The user did not provide credentials."""
