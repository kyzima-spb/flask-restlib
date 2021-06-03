class RestlibError(Exception):
    pass


class MultipleResourcesFound(RestlibError):
    pass


class NoResourcesFound(RestlibError):
    pass


class AuthorizationError(RestlibError, RuntimeError):
    def __init__(self, reason=None, resource=None):
        super().__init__(reason)
        self.reason = reason
        self.resource = resource


class AuthenticationError(RestlibError, RuntimeError):
    def __init__(self, reason=None):
        super().__init__(reason)
        self.reason = reason
