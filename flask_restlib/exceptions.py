import typing as t


class RestlibError(Exception):
    default_message: t.ClassVar[t.Optional[str]] = None

    def __init__(
        self,
        message: t.Optional[str] = None,
        detail: t.Optional[dict] = None
    ) -> None:
        message = message or self.default_message

        if not message:
            raise ValueError(
                'You must assign a value to the `message` argument, '
                f'or override the `{self.__class__.__name__}.default_message` attribute.'
            )

        super().__init__(message)

        self._message = message
        self._detail = detail or {}

    def get_detail(self) -> dict:
        return self._detail

    def get_message(self) -> str:
        return self._message


class MultipleResourcesFound(RestlibError):
    default_message = 'Multiple rows were found for in persistent storage but need one.'


class NoResourcesFound(RestlibError):
    default_message = 'No row was found in persistent storage but need one.'


class DuplicateResource(RestlibError):
    default_message = 'Resource already exists.'


class LogicalError(RestlibError):
    default_message = 'The operation could not be performed due to a logical error.'

    def __init__(
        self,
        message: t.Optional[str] = None,
        detail: t.Optional[dict] = None
    ) -> None:
        super().__init__(message, {
            'errors': detail,
        })


class AuthorizationError(RestlibError):
    """There are not enough rights to perform the action."""
    default_message = 'There are not enough rights to perform the action.'

    def __init__(
        self,
        message: t.Optional[str] = None,
        resource: t.Optional[t.Any] = None,
        detail: t.Optional[dict] = None
    ) -> None:
        super().__init__(message, detail)
        self.resource = resource


class AuthenticationError(RestlibError):
    """The user did not provide credentials."""
    default_message = 'Authentication is required to complete this action.'
