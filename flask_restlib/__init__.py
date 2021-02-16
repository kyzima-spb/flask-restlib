from __future__ import annotations
from types import FunctionType

from flask import current_app
from flask_marshmallow import Marshmallow
from werkzeug.local import LocalProxy

from flask_restlib.routing import ApiBlueprint
from flask_restlib.utils import import_string


class RestLib:
    __slots = ('_blueprints', 'ResourceManager',)

    def __init__(self, app=None):
        self._blueprints = []
        self.ResourceManager = None

        self.ma = Marshmallow()

        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        self.ma.init_app(app)

        app.config.setdefault('RESTLIB_RESOURCE_MANAGER', None)

        resource_manager_class = app.config['RESTLIB_RESOURCE_MANAGER']

        if resource_manager_class is not None:
            self.ResourceManager = import_string(resource_manager_class)

        app.extensions['restlib'] = self

    def create_blueprint(self, *args, **kwargs) -> ApiBlueprint:
        bp = ApiBlueprint(*args, **kwargs)
        self._blueprints.append(bp)
        return bp

    def register_blueprints(self, app):
        for bp in self._blueprints:
            app.register_blueprint(bp)


current_restlib = LocalProxy(lambda: current_app.extensions['restlib'])
