from __future__ import annotations
from collections import OrderedDict
import typing

from flask import abort
from flask.views import MethodView

from flask_restlib import current_restlib
from flask_restlib import mixins
from flask_restlib.core import AbstractFactory, AbstractResourceManager
from flask_restlib.permissions import (
    Permission,
    AuthorizationError,
    AuthenticationError
)


__all__ = (
    'ApiView',
    'CreateView', 'DestroyView', 'ListView', 'RetrieveView', 'UpdateView',
)


class ApiView(MethodView):
    """
    Base class for all REST resource views.

    Attributes:
        factory_class (AbstractFactory): A reference to the class of the factory being used.
        queryset: A reference to native queryset for retrieving resources.
        lookup_names (tuple):
            Names of the fields to retrieve resource in persistent storage.
            For example, names of primary keys in order in which they are used in SQL query.
        model_class: A reference to the class of the model.
        schema_class: A reference to the class of the schema to use for serialization.
    """

    factory_class = None
    queryset = None
    lookup_names = ()
    model_class = None
    permissions: list[Permission] = []
    schema_class = None

    def get_factory(self) -> AbstractFactory:
        """Returns an instance of the abstract factory."""
        if self.factory_class is None:
            return current_restlib.factory
        return self.factory_class()

    def check_permissions(self) -> typing.NoReturn:
        """
        Check if the request should be permitted.
        Raises an exception if the request is not permitted.
        """
        try:
            for permission in self.permissions:
                permission.check_permission(self)
        except AuthenticationError as err:
            self.permission_denied(401, err)
        except AuthorizationError as err:
            self.permission_denied(403, err)

    def check_resource_permissions(self, resource) -> typing.NoReturn:
        """
        Check if the request should be permitted for a given resource.
        Raises an exception if the request is not permitted.
        """
        try:
            for permission in self.permissions:
                permission.check_resource_permission(self, resource)
        except AuthorizationError as err:
            self.permission_denied(403, err)

    def create_queryset(self):
        """
        Creates and returns a native queryset for retrieving resources from persistent storage.
        """
        factory = self.get_factory()

        if self.queryset is not None:
            queryset = factory.create_query_adapter(self.queryset)
        else:
            queryset = factory.create_query_adapter(self.get_model_class())

        return queryset

    def create_resource_manager(self) -> AbstractResourceManager:
        """Creates and returns a resource manager instance."""
        return self.get_factory().create_resource_manager()

    def create_schema(self, *args, **kwargs):
        """
        Creates and returns a schema instance
        that is used to validate the input and serialize the output.
        """
        return self.get_schema_class()(*args, **kwargs)

    def dispatch_request(self, *args, **kwargs):
        if self.lookup_names:
            lookup = OrderedDict()

            for name in self.lookup_names:
                if name in kwargs:
                    lookup[name] = kwargs.pop(name)

            kwargs['id'] = lookup

        self.check_permissions()

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

    def get_or_404(
            self,
            identifier: typing.Union[typing.Any, tuple, dict],
            description: typing.Optional[str] = None,
            model_class: typing.Optional[typing.Any] = None
    ) -> typing.Any:
        """
        Returns a resource based on the given identifier, throws an HTTP 404 error.

        Arguments:
            model_class (type): A reference to the model class that describes the REST resource.
            identifier: A scalar, tuple, or dictionary representing the primary key.
            description (str):
        """
        resource = self.get_factory().create_resource_manager().get(
            model_class or self.get_model_class(), identifier
        )

        if resource is None:
            abort(404, description=description)

        self.check_resource_permissions(resource)

        return resource

    def get_schema_class(self):
        """
        Returns a reference to the class of the schema to use for serialization.
        """
        if self.schema_class is None:
            self.__class__.schema_class = self.get_factory().create_schema(
                self.get_model_class()
            )

        if self.schema_class is None:
            raise AttributeError(
                'You must assign the value of the attribute `schema_class`, '
                f'or override the `{self.__class__.__name__}.get_schema_class()` method.'
            )

        return self.schema_class

    def permission_denied(self, status_code, err):
        """Raises an exception if the request is not permitted."""
        abort(status_code, err.reason)


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
