from collections import OrderedDict

from flask.views import MethodView

from flask_restlib import current_restlib
from flask_restlib import mixins
from flask_restlib.core import AbstractFactory, AbstractResourceManager


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
        model_class: A reference to the class of the model.
        pk_names (tuple): The names of the primary keys in the order in which they are used in the SQL query.
        schema_class: A reference to the class of the schema to use for serialization.
    """

    factory_class = None
    queryset = None
    model_class = None
    pk_names = ()
    schema_class = None

    def get_factory(self) -> AbstractFactory:
        """Returns an instance of the abstract factory."""
        if self.factory_class is None:
            return current_restlib.factory
        return self.factory_class()

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

    def get_or_404(self, identifier, description=None, model_class=None):
        """Returns a resource based on the given identifier, throws an HTTP 404 error."""
        return self.get_factory().create_resource_manager().get_or_404(
            model_class or self.get_model_class(),
            identifier,
            description
        )

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
