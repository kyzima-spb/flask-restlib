from __future__ import annotations
from importlib import import_module
import re

from flask import current_app
from werkzeug.local import LocalProxy

# from flask_restlib.core import RestLib


__all__ = (
    'current_restlib', 'F', 'query_adapter', 'resource_manager',
    'camel_to_list', 'camel_to_snake', 'snake_to_camel',
    'strip_sorting_flag',
    'import_string',
)


current_restlib = LocalProxy(lambda: current_app.extensions['restlib'])


def F(column):
    """
    An adapter for a model attribute.

    Arguments:
        column: native attribute of the model."""
    return current_restlib.factory.create_model_field_adapter(column)


def query_adapter(base_query):
    """Creates and returns a queryset for retrieving resources from persistent storage."""
    return current_restlib.factory.create_query_adapter(base_query)


def resource_manager():
    """Creates and returns a resource manager instance."""
    return current_restlib.factory.create_resource_manager()


def camel_to_list(s, lower=False):
    """Converts a camelcase string to a list."""
    s = re.findall(r'([A-Z][a-z0-9]+)', s) or [s]
    return [w.lower() for w in s] if lower else s


def camel_to_snake(name):
    """Converts a camelcase string to a snake case string."""
    return '_'.join(camel_to_list(name, lower=True))


def snake_to_camel(name):
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
