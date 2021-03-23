from __future__ import annotations
from datetime import datetime
from types import FunctionType

from flask import current_app, request
from flask_marshmallow import Marshmallow
from werkzeug.exceptions import HTTPException
from werkzeug.local import LocalProxy

from flask_restlib.routing import ApiBlueprint
from flask_restlib.utils import import_string


class RestLib:
    __slots__ = (
        '_blueprints', '_factory', '_factory_callback', 'ma',
    )

    def __init__(self, app=None):
        self._blueprints = []
        self._factory_callback = None
        self._factory = None

        self.ma = Marshmallow()

        if app is not None:
            self.init_app(app)

    @property
    def factory(self):
        if self._factory is None:
            callback = getattr(self, '_factory_callback')

            if callback is None:
                raise RuntimeError('Missing factory_loader.')

            self._factory = callback()()
        return self._factory

    def factory_loader(self, callback):
        """This sets the callback for loading default resource manager."""
        self._factory_callback = callback
        return callback

    def init_app(self, app):
        self.ma.init_app(app)

        app.config.setdefault('RESTLIB_PAGINATION_ENABLED', True)
        app.config.setdefault('RESTLIB_URL_PARAM_LIMIT', 'limit')
        app.config.setdefault('RESTLIB_URL_PARAM_OFFSET', 'offset')
        app.config.setdefault('RESTLIB_PAGINATION_LIMIT', 25)
        app.config.setdefault('RESTLIB_SORTING_ENABLED', True)
        app.config.setdefault('RESTLIB_URL_PARAM_SORT', 'sort')

        factory_class = app.config.setdefault('RESTLIB_FACTORY', None)

        if factory_class is not None:
            self.factory_loader(lambda: import_string(factory_class))

        app.extensions['restlib'] = self

        app.register_error_handler(HTTPException, self.http_exception_handler)

    def create_blueprint(self, *args, **kwargs) -> ApiBlueprint:
        bp = ApiBlueprint(*args, **kwargs)
        self._blueprints.append(bp)
        return bp

    def register_blueprints(self, app):
        for bp in self._blueprints:
            app.register_blueprint(bp)

    def http_exception_handler(self, err):
        """Return JSON instead if Content-Type application/json for HTTP errors."""
        resp = {
            'message': err.description,
            'status': err.code,
            'path': request.path,
            'timestamp': datetime.utcnow().isoformat(),
        }

        if err.code in (400, 422) and hasattr(err, 'data'): # webargs raise error
            resp['detail'] = dict(zip(
                ('location', 'errors'),
                err.data.get('messages').popitem()
            ))
            headers = err.data.get('headers')

            if headers:
                return resp, err.code, headers

        return resp, err.code


current_restlib = LocalProxy(lambda: current_app.extensions['restlib'])
