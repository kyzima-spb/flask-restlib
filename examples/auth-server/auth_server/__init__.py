from __future__ import annotations
import typing as t

from flask import Flask
from flask_useful import register_commands, register_extensions

# from . import views
from .extensions import rest


def create_app(test_config: t.Optional[t.Mapping[str, t.Any]] = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
        app.config.from_envvar('FLASK_CONFIG', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    register_extensions(app, 'extensions')
    register_commands(app, 'cli')

    return app
