from __future__ import annotations
from importlib import import_module
import re
import typing as t

from authlib.oauth2.rfc6749.util import scope_to_list, list_to_scope


__all__ = (
    'camel_to_list',
    'camel_to_snake',
    'snake_to_camel',
    'iter_to_scope',
    'scope_to_set',
    'strip_sorting_flag',
    'import_string',
)


def camel_to_list(s: str, lower: bool = False) -> list[str]:
    """Converts a camelcase string to a list."""
    lst = re.findall(r'([A-Z][a-z0-9]+)', s) or [s]
    return [w.lower() for w in lst] if lower else lst


def camel_to_snake(name: str) -> str:
    """Converts a camelcase string to a snake case string."""
    return '_'.join(camel_to_list(name, lower=True))


def iter_to_scope(scope: t.Iterable[str]) -> str:
    """Convert a list of scopes to a space separated string."""
    return list_to_scope(set(scope))


def scope_to_set(scope: str) -> set[str]:
    """Convert a space separated string to a set of scopes."""
    return set(scope_to_list(scope))


def snake_to_camel(name: str) -> str:
    """Converts a snake case string to a camelcase string."""
    return ''.join(name.title().split('_'))


def import_string(dotted_path):
    """
    Import a dotted module path and return the attribute/class designated by the
    last name in the path. Raise ImportError if the import failed.

    from django.utils.module_loading import import_string
    """
    try:
        module_path, class_name = dotted_path.rsplit('.', 1)
    except ValueError as err:
        raise ImportError("%s doesn't look like a module path" % dotted_path) from err

    module = import_module(module_path)

    try:
        return getattr(module, class_name)
    except AttributeError as err:
        raise ImportError('Module "%s" does not define a "%s" attribute/class' % (
            module_path, class_name)
        ) from err


def strip_sorting_flag(column_name: str) -> str:
    """Removes the first character from the name if it is `+` or `-`. """
    return re.sub(r'[-+]', '', column_name, count=1)
