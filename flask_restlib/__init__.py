from __future__ import annotations
from types import FunctionType

from flask import current_app, request
from flask_marshmallow import Marshmallow
from werkzeug.exceptions import HTTPException
from werkzeug.local import LocalProxy

from flask_restlib.exceptions import ApiError, ValidationError
from flask_restlib.routing import ApiBlueprint
from flask_restlib.utils import import_string


class RestLib:
    __slots = ('_blueprints', 'ResourceManager',)

    def __init__(self, app=None):
        self._blueprints = []
        self._resource_manager_callback = None
        self._resource_manager_class = None

        self.ma = Marshmallow()

        if app is not None:
            self.init_app(app)

    @property
    def ResourceManager(self):
        if self._resource_manager_class is None:
            callback = getattr(self, '_resource_manager_callback')

            if callback is None:
                raise RuntimeError('Missing resource_manager_loader.')

            self._resource_manager_class = callback()

        return self._resource_manager_class

    def resource_manager_loader(self, callback):
        """This sets the callback for loading default resource manager."""
        self._resource_manager_callback = callback
        return callback

    def init_app(self, app):
        self.ma.init_app(app)

        app.config.setdefault('RESTLIB_RESOURCE_MANAGER', None)

        resource_manager_class = app.config['RESTLIB_RESOURCE_MANAGER']

        if resource_manager_class is not None:
            self.resource_manager_loader(lambda: import_string(resource_manager_class))

        app.extensions['restlib'] = self

        app.register_error_handler(HTTPException, self.http_exception_handler)
        app.register_error_handler(ValidationError, self.validation_exception_handler)

    def create_blueprint(self, *args, **kwargs) -> ApiBlueprint:
        bp = ApiBlueprint(*args, **kwargs)
        self._blueprints.append(bp)
        return bp

    def register_blueprints(self, app):
        for bp in self._blueprints:
            app.register_blueprint(bp)

    def http_exception_handler(self, err):
        """Return JSON instead if Content-Type application/json for HTTP errors."""
        if request.is_json:
            return ApiError(err.description, err.code).to_response()
        return err

    def validation_exception_handler(self, err):
        if request.is_json:
            return ApiError(err.messages, 422).to_response()
        return err


current_restlib = LocalProxy(lambda: current_app.extensions['restlib'])
