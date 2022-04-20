from functools import wraps
import typing as t


_F = t.TypeVar('_F', bound=t.Callable[..., t.Any])


__all__ = ('getattr_or_implement',)


def getattr_or_implement(getter: _F) -> _F:
    """
    Used in mixins to get the value of a property in a getter method
    when the property is not known to exist or not.

    If the property does not exist, the getter method must be implemented.

    The getter method never takes any arguments.
    """
    @wraps(getter)
    def wrapper(self: t.Any) -> t.Any:
        try:
            return getter(self)
        except AttributeError as err:
            raise NotImplementedError(
                f'{err} - override the `{self.__class__.__name__}.{getter.__name__}()` method.'
            )
    return t.cast(_F, wrapper)
