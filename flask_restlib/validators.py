from marshmallow.validate import (
    Validator, ValidationError,
    URL, Email, Range, Length, Equal, Regexp, Predicate,
    NoneOf, OneOf, ContainsOnly, ContainsNoneOf
)

from flask_restlib.utils import current_restlib, query_adapter


__all__ = (
    'Validator', 'ValidationError',
    'URL', 'Email', 'Range', 'Length', 'Equal', 'Regexp', 'Predicate',
    'NoneOf', 'OneOf', 'ContainsOnly', 'ContainsNoneOf',
    'ExistsEntity', 'UniqueEntity',
)


class ExistsEntity(Validator):
    """
    The validator checks that an entity with the specified attributes exists.
    """

    default_message = 'An instance with {value} attributes does not exist.'

    def __init__(self, model_class, fields='id', resource_manager=None, error=None):
        """
        Arguments:
            model_class:
                Reference to the model class.
            fields (str|iterable):
                Model attributes that must be unique.
            resource_manager:
                Custom resource manager.
                If not specified, it is used by default from the extension.
            error (str):
                Error message.
        """
        self.model_class = model_class
        self.fields = (fields,) if isinstance(fields, str) else fields
        self.resource_manager = resource_manager
        self.error = error or self.default_message

    def __call__(self, *values):
        criteria = dict(zip(self.fields, values))
        q = query_adapter(self.model_class).filter_by(**criteria)

        if not q.exists():
            value = ', '.join(f'{n}={v}' for n, v in criteria.items())
            raise ValidationError(self.error.format(value=value))


class UniqueEntity(Validator):
    """
    The validator checks the attributes of an entity for uniqueness.
    """

    default_message = 'An instance with unique {value} attributes already exists.'

    def __init__(self, model_class, fields, entity=None, resource_manager=None, error=None):
        """
        Arguments:
            model_class:
                Reference to the model class.
            fields (str|iterable):
                Model attributes that must be unique.
            entity:
                The entity to check for uniqueness.
                The argument is needed in case of editing,
                when the entered value can belong to the entity being edited.
            resource_manager:
                Custom resource manager.
                If not specified, it is used by default from the extension.
            error (str):
                Error message.
        """
        self.model_class = model_class
        self.fields = (fields,) if isinstance(fields, str) else fields
        self.entity = entity
        self.resource_manager = resource_manager
        self.error = error or self.default_message

    def __call__(self, *values):
        is_valid = False

        if self.entity is not None:
            is_valid = True

            for name, value in zip(self.fields, values):
                if getattr(self.entity, name) != value:
                    is_valid = False
                    break

        if not is_valid:
            criteria = dict(zip(self.fields, values))
            q = query_adapter(self.model_class).filter_by(**criteria)

            if q.exists():
                value = ', '.join(f'{n}={v}' for n, v in criteria.items())
                raise ValidationError(self.error.format(value=value))
