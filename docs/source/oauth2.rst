.. _oauth2:

OAuth 2.0
=========

Сервер авторизации
------------------

``Flask-Restlib`` реализует сервер авторизации, используя библиотеку Authlib_.
Он предоставляет готовые классы моделей для популярных ORM,
а также примеси или функции-фабрики для их расширения.

В том числе, он предоставляет примеси, не зависящие от ORM,
которые можно использовать для интеграции с любым хранилищем данных.

Чтобы начать использовать сервер авторизации нужно описать модель пользователя.
Рассмотрим это на примере SQLAlchemy:

.. code-block:: python

    # A module with a description of models, for example - models.py

    from flask_bcrypt import Bcrypt
    from flask_restlib.oauth2.mixins import UserMixin
    from flask_sqlalchemy import SQLAlchemy
    import sqlalchemy as sa


    db = SQLAlchemy()
    bcrypt = Bcrypt()


    class User(UserMixin, db.Model):
        id = sa.Column(sa.Integer, primary_key=True)
        email = sa.Column(sa.String(50), unique=True, nullable=False)
        _password = sa.Column('password', sa.String(100), nullable=False)
        is_active = sa.Column(sa.Boolean, default=True, nullable=False)

        def change_password(self, value):
            """[Required] Changes the current password to passed."""
            self._password = bcrypt.generate_password_hash(value).decode('utf-8')

        def check_password(self, password):
            """[Required] Returns true if the password is valid, false otherwise."""
            return bcrypt.check_password_hash(self._password, password)

        password = property(fset=change_password)

        @classmethod
        def find_by_username(cls, email):
            """[Required] Returns the user with passed username, or None."""
            return cls.query.filter_by(email=email).first()

Затем указать ссылку на класс модели пользователя в опциях сервера авторизации
в момент создания экземпляра расширения:

.. code-block:: python

    # A module with extension instances, for example - extensions.py

    from flask_restlib import RestLib
    from flask_restlib.contrib.sqla import SQLAFactory

    from .models import db, bcrypt, User


    rest = RestLib(
        factory=SQLAFactory(),
        auth_options={
            'user_model': User,
        }
    )


Пользовательская модель клиента
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Когда необходимо создать свой класс модели клиента OAuth,
можно воспользоваться фабричной функцией для выбранного ORM:

* :py:func:`~flask_restlib.contrib.sqla.create_client_model` - для SQLAlchemy
* :py:func:`~flask_restlib.contrib.mongoengine.create_client_model` - для MongoEngine

Дополним ранее рассмотренный пример для SQLAlchemy:

.. code-block:: python

    # A module with a description of models, for example - models.py
    # <... Import, instantiate extensions and user models. ...>

    class Client(create_client_model(User)):
        is_disabled = sa.Column(sa.Boolean, default=False, nullable=False)

Затем указать ссылку на класс модели клиента в опциях сервера авторизации
в момент создания экземпляра расширения:

.. code-block:: python

    # A module with extension instances, for example - extensions.py

    from flask_restlib import RestLib
    from flask_restlib.contrib.sqla import SQLAFactory

    from .models import db, bcrypt, User, Client


    rest = RestLib(
        factory=SQLAFactory(),
        auth_options={
            'user_model': User,
            'client_model': Client,
        }
    )


Пользовательская модель токена
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Когда необходимо создать свой класс модели токена OAuth,
можно воспользоваться фабричной функцией для выбранного ORM:

* :py:func:`~flask_restlib.contrib.sqla.create_token_model` - для SQLAlchemy
* :py:func:`~flask_restlib.contrib.mongoengine.create_token_model` - для MongoEngine

Дополним ранее рассмотренный пример для SQLAlchemy:

.. code-block:: python

    # A module with a description of models, for example - models.py
    # <... Import, instantiate extensions and user models. ...>

    class Token(create_token_model(User, Client)):
        user_agent = sa.Column(sa.Text, nullable=False)

Затем указать ссылку на класс модели токена в опциях сервера авторизации
в момент создания экземпляра расширения:

.. code-block:: python

    # A module with extension instances, for example - extensions.py

    from flask_restlib import RestLib
    from flask_restlib.contrib.sqla import SQLAFactory

    from .models import db, bcrypt, User, Token


    rest = RestLib(
        factory=SQLAFactory(),
        auth_options={
            'user_model': User,
            'token_model': Token,
        }
    )


Пользовательская модель кода авторизации
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Когда необходимо создать свой класс модели кода авторизации OAuth,
можно воспользоваться фабричной функцией для выбранного ORM:

* :py:func:`~flask_restlib.contrib.sqla.create_authorization_code_model` - для SQLAlchemy
* :py:func:`~flask_restlib.contrib.mongoengine.create_authorization_code_model` - для MongoEngine

Дополним ранее рассмотренный пример для SQLAlchemy:

.. code-block:: python

    # A module with a description of models, for example - models.py
    # <... Import, instantiate extensions and user models. ...>

    class AuthorizationCode(create_authorization_code_model(User, Client)):
        user_agent = sa.Column(sa.Text, nullable=False)

Затем указать ссылку на класс модели кода авторизации в опциях сервера авторизации
в момент создания экземпляра расширения:

.. code-block:: python

    # A module with extension instances, for example - extensions.py

    from flask_restlib import RestLib
    from flask_restlib.contrib.sqla import SQLAFactory

    from .models import db, bcrypt, User, AuthorizationCode


    rest = RestLib(
        factory=SQLAFactory(),
        auth_options={
            'user_model': User,
            'authorization_code_model': AuthorizationCode,
        }
    )


Представления
-------------

Список доступных представлений:

* ``index_endpoint = IndexView.as_view('index')`` - home page
* ``login_endpoint = LoginView.as_view('login')`` - account authentication
* ``logout_endpoint = LogoutView.as_view('logout')`` - logout of your account
* ``authorize_endpoint = AuthorizeView.as_view('authorize')`` - application authorization
* ``access_token_endpoint = AccessTokenView.as_view('access_token')`` - access token request (заменять не рекомендуется)
* ``revoke_token_endpoint = RevokeTokenView.as_view('revoke_token')`` - revokes a previously issued token (заменять не рекомендуется)

Любое представление можно заменить своим представлением, изменять имена представлений запрещено, например:

.. code-block:: python

    from flask_useful.views import MethodView

    from .extensions import rest


    class CustomIndexView(MethodView):
        template_name = 'custom_oauth/index.html'

        def get(self):
            return self.render_template()


    rest.authorization_server.index_endpoint = CustomIndexView.as_view('index')


Любой шаблон можно перегрузить пользовательским шаблоном,
для этого создайте новый шаблон в директории с шаблонами приложения.

Список доступных шаблонов:

* ``restlib/base.html`` - базовый шаблон, от которого наследуют все шаблоны
* ``restlib/index.html`` - шаблон главной страницы, по-умолчанию отображает кнопку выхода
* ``restlib/login.html`` - шаблон страницы входа с формой входа
* ``restlib/authorize.html`` - шаблон страницы авторизации с формой разрешения или запрета доступа

Чтобы унаследоваться от шаблона без его копирования, можно использовать следующий код:

.. code-block:: python

    from flask_restlib.oauth2 import IndexView

    from .extensions import rest


    rest.authorization_server.index_endpoint = IndexView.as_view(
        'index',
        template_name='custom_oauth/index.html'
    )


Области действия
----------------

``Scope`` - это механизм в OAuth 2.0 для ограничения доступа приложений к ресурсам.

Приложение может запросить одну или несколько областей действия,
список запрошенных областей будет отображен на странице разрешения доступа,
пользователь может выбрать к каким областям доступ разрешен, а к каким нет.
Приложению будет выдан токен доступа, ограниченный предоставленными областями.

Сервер авторизации может выдать доступ только для тех областей, которые разрешены приложению.
Например, если приложение имеет доступ к области ``profile``, а запрашивается область ``api``,
то выданный токен доступа не будет иметь ни одной области действия.

Сервер авторизации может выдать доступ только для тех областей, которые разрешены пользователю.
Например, если пользоатель имеет доступ к области ``api:read``, а запрашивается область ``api:write``,
то выданный токен доступа не будет иметь ни одной области действия.

Если используется механизм на основе ролей и пользователь имеет роль ``customer``,
то сервер авторизации может выдать доступ только для тех областей, которые разрешены покупателю,
но не администратору, даже если приложению разрешены области действия из роли ``admin``.

Важно понимать, что область действия это не тоже самое, что внутренняя система разграничения прав.
``Область действия`` - это способ ограничить то, **что приложение может делать** в контексте того,
**что может делать пользователь**.

OAuth 2.0 не определяет каких-либо конкретных значений для областей доступа,
т.к. они зависят от внутренней архитектуры и потребностей службы.


Область действия токена доступа
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Перевод (оригинал `Access Token Scope`_)

Конечные точки авторизации и токена позволяют клиенту указать область запроса доступа с помощью параметра запроса ``scope``.
В свою очередь, сервер авторизации использует параметр ответа ``scope``,
чтобы информировать клиента об области действия выданного токена доступа.

Значение параметра ``scope`` выражается в виде списка строк, разделенных пробелами и чувствительных к регистру.
Строки определяются сервером авторизации. Если значение содержит несколько строк, разделенных пробелами,
их порядок не имеет значения, и каждая строка добавляет дополнительный диапазон доступа к запрошенной области. ::

    scope       = scope-token *( SP scope-token )
    scope-token = 1*( %x21 / %x23-5B / %x5D-7E )

Сервер авторизации МОЖЕТ полностью или частично игнорировать область действия, запрошенную клиентом,
на основе политики сервера авторизации или инструкций владельца ресурса.
Если область выданного токена доступа отличается от области, запрошенной клиентом,
сервер авторизации ДОЛЖЕН включить параметр ответа ``scope``, чтобы информировать клиента о фактически предоставленной области.

Если клиент пропускает параметр области при запросе авторизации,
сервер авторизации ДОЛЖЕН либо обработать запрос, используя предварительно определенное значение по умолчанию,
либо отклонить запрос, указывая на недопустимую область действия.
Серверу авторизации СЛЕДУЕТ задокументировать свои требования к области и значение по умолчанию (если определено).


Примеры запросов токена
~~~~~~~~~~~~~~~~~~~~~~~

Допустим, что идентификатор клиента и секретный ключ равен ``test``:

.. code-block:: bash

    # Authorization Code Grant
    xdg-open "http://example.com/oauth/authorize?client_id=test&response_type=code&scope=profile"
    curl -u test:test \
         -XPOST http://example.com/oauth/token \
         -F grant_type=authorization_code \
         -F code=ZTubOeNfYBHVH8Y54sOBEUCPLi1kD45VCoYPtxUwrRQ7BgHu

    # Implicit Grant
    xdg-open "http://example.com/oauth/authorize?client_id=test&response_type=token"

    # Resource Owner Password Credentials Grant
    curl -u test:test \
         -XPOST http://example.com/oauth/token \
         -F grant_type=password \
         -F scope=profile \
         -F username=user@example.com \
         -F password=demo123

    # Client Credentials Grant
    curl -u test:test \
         -XPOST http://example.com/oauth/token \
         -F grant_type=client_credentials \
         -F scope=api

    # Refreshing an Access Token
    curl -u test:test \
         -XPOST http://example.com/oauth/token \
         -F grant_type=refresh_token \
         -F refresh_token=FSLn7Ytp6tWspYyRWgXlam4ZhsOJiV3tcVRmYD9a3Rf2gXqd

    # Token Revocation
    curl -u test:test \
         -XPOST http://example.com/oauth/revoke \
         -F token=fbZnda6CsQc0F6gOSKrybQwGnbhugRY05Pxr9A0eXf \
         -F token_type_hint=access_token


ScopeMixin
~~~~~~~~~~

Позволяет подмешать в любой класс работу с областями действия.

В классе необходимо описать свойство ``scopes`` с типом данных ``set``.
Это свойство хранит экземпляры областей действия.

Область действия может быть строкой или любым другим типом данных.
Тип данных, отличный от строки, может использоваться для хранения дополнительной информации,
такой как описание или иконка.
Если вы создаете свой тип для области действия, то он должен:

* :py:meth:`~object.__str__` - явно приводиться к строке;
* :py:meth:`~object.__hash__` - возвращать одинаковый хеш для идентичных экземпляров;
* :py:meth:`~object.__eq__` - возвращать истину для идентичных экземпляров;

В примере область действия задана в виде именованного кортежа,
он реализует методы :py:meth:`~object.__hash__` и :py:meth:`~object.__eq__` за вас:

.. code-block:: python

    # абстрактный пример

    from typing import NamedTuple

    from flask_restlib.oauth2.mixins import ScopeMixin


    class Scope(NamedTuple):
        value: str
        description: str = ''
        icon: str = ''

        def __str__(self):
            return self.value


    class DemoClass(ScopeMixin):
        def __init__(self, *scopes):
            self.scopes = set(scopes)


    obj = DemoClass(
        Scope('profile', 'Read user profile'),
        Scope('api:read', 'Read only access'),
        Scope('api:write')
    )

    obj.get_scopes() # Returns set of Scope instances
    obj.get_scope()  # Returns: 'profile api:read api:write'

    obj.get_allowed_scope('profile') # Returns: 'profile'
    obj.get_allowed_scope('api')     # Returns: ''
    obj.get_allowed_scope('nothing') # Returns: ''

Пример из реального мира, по-умолчанию, пользователю нельзя назначать разрешенные области действия,
но можно унаследовать модель пользователя от примеси :py:class:`~flask_restlib.oauth2.mixins.ScopeMixin`
и добавить свойство ``scopes``:

.. code-block:: python

    # A module with a description of models, for example - models.py

    from flask_bcrypt import Bcrypt
    from flask_restlib.oauth2.mixins import UserMixin, ScopeMixin
    from flask_sqlalchemy import SQLAlchemy
    import sqlalchemy as sa
    from sqlalchemy.ext.mutable import MutableList


    db = SQLAlchemy()
    bcrypt = Bcrypt()


    class User(UserMixin, ScopeMixin, db.Model):
        id = sa.Column(sa.Integer, primary_key=True)
        email = sa.Column(sa.String(50), unique=True, nullable=False)
        _password = sa.Column('password', sa.String(100), nullable=False)
        is_active = sa.Column(sa.Boolean, default=True, nullable=False)
        scopes = sa.Column(
            MutableList.as_mutable(sa.JSON),
            nullable=False,
            default=list
        )

        def change_password(self, value):
            """[Required] Changes the current password to passed."""
            self._password = bcrypt.generate_password_hash(value).decode('utf-8')

        def check_password(self, password):
            """[Required] Returns true if the password is valid, false otherwise."""
            return bcrypt.check_password_hash(self._password, password)

        password = property(fset=change_password)

        @classmethod
        def find_by_username(cls, email):
            """[Required] Returns the user with passed username, or None."""
            return cls.query.filter_by(email=email).first()


Области действия на основе ролей
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

`Flask-Restlib` имеет встроенную поддержку ролей.
**Основная задача роли** - группировка областей действий с целью упрощения назначения их пользователю.

Роль решает проблему `Don't Repeat Yourself`_, когда нескольким пользователям нужно назначить одинаковый набор областей.
Например, мы можем назначить область действия ``posts`` пользователю ``user1``, но забыть для пользователя ``user2``.

Одной роли можно назначить множество областей действия; одна область действия, может быть назначена множеству ролей.
У одной роли может быть множество дочерних ролей, но только один родитель.

Чтобы начать использовать роли, необходимо создать свой класс модели,
для этого нужно воспользоваться фабричной функцией или базовым классом для выбранного ORM:

* :py:func:`~flask_restlib.contrib.sqla.create_role_model` - для SQLAlchemy
* :py:class:`~flask_restlib.contrib.mongoengine.OAuth2Role` - для MongoEngine

.. code-block:: python

    from flask_sqlalchemy import SQLAlchemy
    from flask_restlib.contrib.sqla import create_role_model


    db = SQLAlchemy()

    Role = create_role_model(db.Model)


Если нужно унаследоваться от базового класса роли, но для его создания используется фабричная функция,
базовый класс нужно сделать абстрактным, для этого у фабричной функции есть аргумент ``is_abstract``:

.. code-block:: python

    from flask_sqlalchemy import SQLAlchemy
    from flask_restlib.contrib.sqla import create_role_model


    db = SQLAlchemy()

    class Role(create_role_model(db.Model, is_abstract=True)):
        """Дополнительные атрибуты модели"""

Если базовый класс не сделать абстрактным, то в базе данных могут появиться две таблицы,
либо будет выброшено исключение при попытке отображения новой сущности - поведение зависит от выбранной ORM.

Далее с помощью примеси :py:class:`~flask_restlib.oauth2.rbac.RoleMixin` добавить поддержку ролей для пользователя.
Одну роль можно назначить множеству пользователей; один пользователь может иметь множество ролей.
Необходимо описать связь многие ко многим в синтаксисе выбранной ORM, имя таблицы (коллекции) по-умолчанию ``oauth2_role``.

Итоговый пример:

.. code-block:: python

    # A module with a description of models, for example - models.py

    from flask_bcrypt import Bcrypt
    from flask_restlib.oauth2.rbac import UserMixin
    from flask_restlib.contrib.sqla import (
        create_role_model
    )
    from flask_sqlalchemy import SQLAlchemy
    import sqlalchemy as sa


    db = SQLAlchemy()
    bcrypt = Bcrypt()


    user_roles = sa.Table(
        'user_roles', db.Model.metadata,
        sa.Column('user_id', sa.ForeignKey('user.id'), primary_key=True),
        sa.Column('role_id', sa.ForeignKey('oauth2_role.id'), primary_key=True),
    )


    Role = create_role_model(db.Model)


    class User(UserMixin, db.Model):
        id = sa.Column(sa.Integer, primary_key=True)
        email = sa.Column(sa.String(50), unique=True, nullable=False)
        _password = sa.Column('password', sa.String(100), nullable=False)
        is_active = sa.Column(sa.Boolean, default=True, nullable=False)

        def change_password(self, value):
            """[Required] Changes the current password to passed."""
            self._password = bcrypt.generate_password_hash(value).decode('utf-8')

        def check_password(self, password):
            """[Required] Returns true if the password is valid, false otherwise."""
            return bcrypt.check_password_hash(self._password, password)

        password = property(fset=change_password)

        @classmethod
        def find_by_username(cls, email):
            """[Required] Returns the user with passed username, or None."""
            return cls.query.filter_by(email=email).first()


Неподдерживаемые ORM
--------------------

Если нужно выполнить интеграцию с хранилищем, которое не поддерживается из коробки,
то воспользуйтесь примесями из модуля :py:mod:`flask_restlib.oauth2.mixins`.
Каждая примесь имеет геттеры с реализацией по-умолчанию.
Геттер пытаются найти нужное свойство в текущем классе и если не находит,
то выбрасывает исключение :py:class:`NotImplementedError`.
Вы можете либо описать свойство, либо переопределить геттер.
Для более подробной информации смотрите документацию по каждой примеси:

* :py:class:`~flask_restlib.oauth2.mixins.ClientMixin` - примесь для клиента OAuth 2.0;
* :py:class:`~flask_restlib.oauth2.mixins.TokenMixin` - примесь для токена доступа OAuth 2.0;
* :py:class:`~flask_restlib.oauth2.mixins.AuthorizationCodeMixin` - примесь для кода авторизации OAuth 2.0;

.. _Authlib: https://authlib.org
.. _Access Token Scope: https://datatracker.ietf.org/doc/html/rfc6749#section-3.3
.. _Don't Repeat Yourself: https://ru.wikipedia.org/wiki/Don’t_repeat_yourself
