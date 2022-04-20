.. _api_reference:

API Reference
=============

Core
----

.. autoclass:: flask_restlib.core.AbstractFactory
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.core.RestLib
    :members:
    :show-inheritance:

Decorators
----------

.. autofunction:: flask_restlib.decorators.getattr_or_implement

Exceptions
----------

.. autoclass:: flask_restlib.exceptions.RestlibError
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.exceptions.AuthenticationError
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.exceptions.AuthorizationError
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.exceptions.DuplicateResource
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.exceptions.LogicalError
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.exceptions.MultipleResourcesFound
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.exceptions.NoResourcesFound
    :members:
    :show-inheritance:

Filters
-------

.. autoclass:: flask_restlib.filters.AbstractFilter
    :members:
    :show-inheritance:

Forms
-----

.. autoclass:: flask_restlib.forms.LoginForm
    :members:
    :show-inheritance:

Globals
-------

.. autofunction:: flask_restlib.globals.Q

HTTP
----

.. autofunction:: flask_restlib.http.url_update_query_string

.. autoclass:: flask_restlib.http.AbstractHttpCache
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.http.HttpCache
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.http.HTTPMethodOverrideMiddleware
    :members:
    :show-inheritance:

Mixins
------

OAuth2
------

Authorization Server
~~~~~~~~~~~~~~~~~~~~

.. autoclass:: flask_restlib.oauth2.authorization_server.AuthorizationServer
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.oauth2.authorization_server.BearerTokenValidator
    :members:
    :show-inheritance:

Mixins
~~~~~~

.. autoclass:: flask_restlib.oauth2.mixins.AuthorizationCodeMixin
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.oauth2.mixins.ClientMixin
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.oauth2.mixins.TokenMixin
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.oauth2.mixins.ScopeMixin
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.oauth2.mixins.UserMixin
    :members:
    :show-inheritance:

RBAC
~~~~

.. autoclass:: flask_restlib.oauth2.rbac.RoleMixin
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.oauth2.rbac.UserMixin
    :members:
    :show-inheritance:

Views
~~~~~

.. autoclass:: flask_restlib.oauth2.views.AccessTokenView
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.oauth2.views.AuthorizeView
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.oauth2.views.IndexView
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.oauth2.views.LoginView
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.oauth2.views.LogoutView
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.oauth2.views.RevokeTokenEndpoint
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.oauth2.views.RevokeTokenView
    :members:
    :show-inheritance:

ORM
---

.. autoclass:: flask_restlib.orm.AbstractQueryAdapter
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.orm.AbstractQueryExpression
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.orm.AbstractResourceManager
    :members:
    :show-inheritance:

Pagination
----------

.. autoclass:: flask_restlib.pagination.AbstractPagination
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.pagination.LimitOffsetPagination
    :members:
    :show-inheritance:

Permissions
-----------

.. autoclass:: flask_restlib.permissions.Permission
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.permissions.IsAuthenticated
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.permissions.PublicMethods
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.permissions.TokenHasScope
    :members:
    :show-inheritance:

Routing
-------

.. autoclass:: flask_restlib.routing.Route
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.routing.Router
    :members:
    :show-inheritance:

Schemas
-------

.. autoclass:: flask_restlib.schemas.RestlibMixin
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.schemas.RestlibSchemaOpts
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.schemas.RestlibSchema
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.schemas.ClientSchema
    :members:
    :show-inheritance:

Sorting
-------

.. autoclass:: flask_restlib.sorting.SortHandler
    :members:
    :show-inheritance:

Types
-----

Utilities
---------

.. autofunction:: flask_restlib.utils.camel_to_list

.. autofunction:: flask_restlib.utils.camel_to_snake

.. autofunction:: flask_restlib.utils.snake_to_camel

.. autofunction:: flask_restlib.utils.iter_to_scope

.. autofunction:: flask_restlib.utils.scope_to_set

Validators
----------

Views
-----

Contrib
-------

SQLAlchemy
~~~~~~~~~~

.. autofunction:: flask_restlib.contrib.sqla.create_authorization_code_model

.. autofunction:: flask_restlib.contrib.sqla.create_client_model

.. autofunction:: flask_restlib.contrib.sqla.create_role_model

.. autofunction:: flask_restlib.contrib.sqla.create_token_model

.. autoclass:: flask_restlib.contrib.sqla.SQLAQueryAdapter
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.contrib.sqla.SQLAResourceManager
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.contrib.sqla.SQLAFactory
    :members:
    :show-inheritance:


MongoEngine
~~~~~~~~~~~

.. autofunction:: flask_restlib.contrib.mongoengine.create_authorization_code_model

.. autofunction:: flask_restlib.contrib.mongoengine.create_client_model

.. autofunction:: flask_restlib.contrib.mongoengine.create_role_model

.. autofunction:: flask_restlib.contrib.mongoengine.create_token_model

.. autoclass:: flask_restlib.contrib.mongoengine.MongoQueryAdapter
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.contrib.mongoengine.MongoResourceManager
    :members:
    :show-inheritance:

.. autoclass:: flask_restlib.contrib.mongoengine.MongoEngineFactory
    :members:
    :show-inheritance:
