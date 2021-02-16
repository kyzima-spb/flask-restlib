from abc import ABCMeta, abstractmethod
from collections import OrderedDict

from flask import request, abort, current_app
from flask.views import MethodView

from flask_restlib import current_restlib
from flask_restlib import mixins


__all__ = (
    'ApiView',
    'CreateView', 'DestroyView', 'ListView', 'RetrieveView', 'UpdateView',
)


class AbstractResourceManager(metaclass=ABCMeta):
    """
    Manager for working with REST resources.

    Attributes:
        model_class: A reference to the model class that describes the REST resource.
    """

    def __init__(self, model_class):
        self.model_class = model_class

    @abstractmethod
    def create(self, **attributes):
        """
        Creates and returns a new instance of the resource filled with data.

        Arguments:
            attributes (dict): Resource attributes.
        """

    @abstractmethod
    def create_queryset(self):
        """
        Creates and returns a queryset for retrieving resources from persistent storage.
        """

    @abstractmethod
    def create_schema(self):
        """Creates and returns an automatic schema class."""

    @abstractmethod
    def delete(self, resource):
        """
        Removes the resource from the persistent storage.

        Arguments:
            resource (object): The resource instance.
        """

    @abstractmethod
    def get(self, identifier):
        """Returns a resource based on the given identifier, or None if not found."""

    def get_or_404(self, identifier, description=None):
        """Returns a resource based on the given identifier, throws an HTTP 404 error."""
        resource = self.get(identifier)

        if resource is None:
            abort(404, description=description)

        return resource

    @abstractmethod
    def save(self, resource):
        """Saves the resource to persistent storage."""

    def update(self, resource, **attributes):
        """
        Updates the resource with the values of the passed attributes.

        Arguments:
            resource (object): The resource instance.
            attributes (dict): Resource attributes with new values.
        """
        for attr, value in attributes.items():
            setattr(resource, attr, value)


class ApiView(MethodView):
    """
    Base class for all REST resource views.

    Attributes:
        queryset: A reference to native queryset for retrieving resources.
        model_class: A reference to the class of the model.
        pk_names: The names of the primary keys in the order in which they are used in the SQL query.
        resource_manager_class: A reference to the class of the resource manager.
        schema_class: A reference to the class of the schema to use for serialization.
    """

    queryset = None
    model_class = None
    pk_names = ()
    resource_manager_class = None
    schema_class = None

    def create_queryset(self):
        """
        Creates and returns a native queryset for retrieving resources from persistent storage.
        """
        if self.queryset is not None:
            return self.queryset

        queryset = self.create_resource_manager().create_queryset()

        if queryset is None:
            raise AttributeError(
                'You must assign the value of the attribute `queryset`, '
                f'or override the `{self.__class__.__name__}.create_queryset()` method.'
            )

        return queryset

    def create_resource_manager(self):
        """
        Creates and returns a resource manager instance.
        """
        return self.get_resource_manager_class()(self.get_model_class())

    def create_schema(self, *args, **kwargs):
        """
        Creates and returns a schema instance
        that is used to validate the input and serialize the output.
        """
        return self.get_schema_class()(*args, **kwargs)

    def dispatch_request(self, *args, **kwargs):
        if self.pk_names:
            pk = OrderedDict()

            for name in self.pk_names:
                if name in kwargs:
                    pk[name] = kwargs.pop(name)

            kwargs['id'] = pk

        return super().dispatch_request(*args, **kwargs)

    def get_model_class(self):
        """
        Returns a reference to the class of the model.
        """
        if self.model_class is None:
            raise AttributeError(
                'You must assign the value of the attribute `model_class`, '
                f'or override the `{self.__class__.__name__}.get_model_class()` method.'
            )
        return self.model_class

    def get_resource_manager_class(self):
        """
        Returns a reference to the class of the resource manager.
        """
        if self.resource_manager_class is None:
            self.__class__.resource_manager_class = current_restlib.ResourceManager

        if self.resource_manager_class is None:
            raise AttributeError(
                'You must assign the value of the attribute `resource_manager_class`, '
                f'or override the `{self.__class__.__name__}.get_resource_manager_class()` method.'
            )

        return self.resource_manager_class

    def get_schema_class(self):
        """
        Returns a reference to the class of the schema to use for serialization.
        """
        if self.schema_class is None:
            self.__class__.schema_class = self.create_resource_manager().create_schema()

        if self.schema_class is None:
            raise AttributeError(
                'You must assign the value of the attribute `schema_class`, '
                f'or override the `{self.__class__.__name__}.get_schema_class()` method.'
            )

        return self.schema_class


class CreateView(mixins.CreateViewMixin, ApiView):
    pass


class DestroyView(mixins.DestroyViewMixin, ApiView):
    pass


class ListView(mixins.ListViewMixin, ApiView):
    pass


class RetrieveView(mixins.RetrieveViewMixin, ApiView):
    pass


class UpdateView(mixins.UpdateViewMixin, ApiView):
    pass
