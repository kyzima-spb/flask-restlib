from flask import current_app

from flask_restlib import current_restlib
from flask_restlib.mixins import RequestMixin
from flask_restlib.views import AbstractResourceManager


class ResourceManager(AbstractResourceManager):
    def create(self, **attributes):
        return self.model_class(**attributes)

    def create_queryset(self):
        return self.model_class.query

    def create_schema(self):
        class Meta:
            model = self.model_class

        name = '%sSchema' % self.model_class.__name__
        bases = (RequestMixin, current_restlib.ma.SQLAlchemyAutoSchema)

        return type(name, bases, {'Meta': Meta})

    def delete(self, resource):
        self.session.delete(resource)
        self.session.commit()

    def get(self, identifier):
        return self.model_class.query.get(identifier)

    def save(self, resource):
        self.session.add(resource)
        self.session.commit()

    @property
    def session(self):
        ext = current_app.extensions.get('sqlalchemy')

        if ext is None:
            raise RuntimeError(
                'An extension named sqlalchemy was not found '
                'in the list of registered extensions for the current application.'
            )

        return ext.db.session
