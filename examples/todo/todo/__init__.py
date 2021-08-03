from flask import Flask

from todo.extensions import rest


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.url_map.strict_slashes = False

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
        app.config.from_envvar('FLASK_CONFIG', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    rest.init_app(app)

    return app
