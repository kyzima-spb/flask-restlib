class RestlibError(Exception):
    pass


class MultipleResourcesFound(RestlibError):
    pass


class NoResourcesFound(RestlibError):
    pass
