from flask import request, abort, jsonify


__all__ = (
    'RequestMixin',
    'CreateMixin', 'CreateViewMixin',
    'DestroyMixin', 'DestroyViewMixin',
    'ListMixin', 'ListViewMixin',
    'RetrieveMixin', 'RetrieveViewMixin',
    'UpdateMixin', 'UpdateViewMixin',
)


class RequestMixin:
    """The mixin allows you to automatically fetch data from the request object."""

    def load_from_request(self, **kwargs):
        """Returns a validated JSON document retrieved from the request object."""
        if request.json is None:
            abort(400, 'Invalid input')
        return self.load(request.json, **kwargs)


class CreateMixin:
    """A mixin to add a new resource to the collection."""

    def create(self):
        schema = self.create_schema()
        data = schema.load_from_request()

        rm = self.create_resource_manager()
        resource = rm.create(**data)
        rm.save(resource)

        return schema.dump(resource), 201


class DestroyMixin:
    """A mixin for removing a resource from a collection."""

    def destroy(self, identifier):
        rm = self.create_resource_manager()
        resource = rm.get_or_404(identifier)
        rm.delete(resource)
        return '', 204


class ListMixin:
    """Mixin for getting all resources from the collection."""

    def list(self):
        return jsonify(
            self.create_schema(many=True).dump(self.create_queryset())
        )


class RetrieveMixin:
    """Mixin to get one resource from a collection"""

    def retrieve(self, identifier):
        return self.create_schema().dump(
            self.create_resource_manager().get_or_404(identifier)
        )


class UpdateMixin:
    """A mixin for editing a resource in a collection."""

    def update(self, identifier):
        rm = self.create_resource_manager()
        resource = rm.get_or_404(identifier)

        schema = self.create_schema()
        data = schema.load_from_request()

        rm.update(resource, **data)
        rm.save(resource)

        return schema.dump(resource)


class CreateViewMixin(CreateMixin):
    def post(self):
        return self.create()


class DestroyViewMixin(DestroyMixin):
    def delete(self, id):
        return self.destroy(id)


class ListViewMixin(ListMixin):
    def get(self):
        return self.list()


class RetrieveViewMixin(RetrieveMixin):
    def get(self, id):
        return self.retrieve(id)


class UpdateViewMixin(UpdateMixin):
    def put(self, id):
        return self.update(id)
