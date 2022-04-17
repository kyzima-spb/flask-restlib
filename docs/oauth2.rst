.. _oauth2:

OAuth2
======

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

Scope - это механизм в OAuth 2.0 для ограничения доступа приложения к учетной записи пользователя.
Приложение может запросить одну или несколько областей,
затем эта информация будет отображена пользователю на странице разрешения доступа,
а токен доступа, выданный приложению, будет ограничен предоставленными областями.

Спецификация OAuth позволяет серверу авторизации или пользователю изменять области,
предоставленные приложению, по сравнению с запрошенными,
хотя на практике не так много примеров служб, делающих это.

OAuth не определяет каких-либо конкретных значений для областей,
поскольку они сильно зависят от внутренней архитектуры и потребностей службы.

Важно помнить, что область действия - это не то же самое, что внутренняя система разрешений API.
Область действия - это способ ограничить то,
что приложение может делать в контексте того, что может делать пользователь.
Например, если у вас есть пользователь в группе ``customer``,
а приложение запрашивает область ``admin``,
сервер OAuth не будет создавать токен доступа с областью ``admin``,
потому что этому пользователю не разрешено использовать эту область.

Область действия токена доступа
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Конечные точки авторизации и токена позволяют клиенту указать область запроса доступа с помощью параметра запроса ``scope``. В свою очередь, сервер авторизации использует параметр ответа ``scope``, чтобы информировать клиента об области действия выданного токена доступа.

Значение параметра ``scope`` выражается в виде списка строк, разделенных пробелами и чувствительных к регистру. Строки определяются сервером авторизации. Если значение содержит несколько строк, разделенных пробелами, их порядок не имеет значения, и каждая строка добавляет дополнительный диапазон доступа к запрошенной области. ::

    scope       = scope-token *( SP scope-token )
    scope-token = 1*( %x21 / %x23-5B / %x5D-7E )

Сервер авторизации МОЖЕТ полностью или частично игнорировать область действия, запрошенную клиентом, на основе политики сервера авторизации или инструкций владельца ресурса. Если область выданного токена доступа отличается от области, запрошенной клиентом, сервер авторизации ДОЛЖЕН включить параметр ответа "scope", чтобы информировать клиента о фактически предоставленной области.

Если клиент пропускает параметр области при запросе авторизации, сервер авторизации ДОЛЖЕН либо обработать запрос, используя предварительно определенное значение по умолчанию, либо отклонить запрос, указывая на недопустимую область действия. Серверу авторизации СЛЕДУЕТ задокументировать свои требования к области и значение по умолчанию (если определено).




Authorization Code Grant
------------------------

.. code-block:: bash

    $ export CLIENT_ID=4d0a829fd95b8ee77893808a91b51171dcc1b36422bbcf61
    $ export CLIENT_SECRET=b536e10d18df0679343c340c626bac6a62cabd72a3a559cfb750c182480873bde67d25ada8e669ae008ed4aae3813dd539744c87697fca54d65003ff
    $ xdg-open "http://127.0.0.1:8000/oauth/authorize?client_id=${CLIENT_ID}&response_type=code&scope=profile"
    $ curl -u ${CLIENT_ID}:${CLIENT_SECRET} \
          -XPOST http://127.0.0.1:8000/oauth/token \
          -F grant_type=authorization_code \
          -F code=ZTubOeNfYBHVH8Y54sOBEUCPLi1kD45VCoYPtxUwrRQ7BgHu

Implicit Grant
--------------

.. code-block:: bash

    $ export CLIENT_ID=2dc0f46b4b76f08a1bcaa6ba567c583dda723f478ccb7dc3
    $ xdg-open "http://127.0.0.1:8000/oauth/authorize?client_id=${CLIENT_ID}&response_type=token"


Resource Owner Password Credentials Grant
-----------------------------------------

.. code-block:: bash

    $ export CLIENT_ID=7b9dbab3a7641cef0e520429d30fc57de2fad4245fbcd26a
    $ export CLIENT_SECRET=ff173f49b697fd86bc4e20effaf71391e677fb368ca6977036bae358b98b6cb06144edf2c5bf5f8c35c0c1b81c7ef2a7ca4d3cd620ddee458afcb837
    $ curl -u ${CLIENT_ID}:${CLIENT_SECRET} \
          -XPOST http://127.0.0.1:8000/oauth/token \
          -F grant_type=password \
          -F scope=profile \
          -F username=office@kyzima-spb.com \
          -F password=cdpo123!

Client Credentials Grant
------------------------

.. code-block:: bash

    $ export CLIENT_ID=89c652eface2bf7ae2498613c644956a81e3144858b4012b
    $ export CLIENT_SECRET=1c60b2b77a3a2d649c29e66c59352a983aaca23f1c9384a97fb9ed8bc0c72227b48a697113dbe6d8288782d03e7b02a77f120638696deb109261a77e
    $ curl -u ${CLIENT_ID}:${CLIENT_SECRET} \
          -XPOST http://127.0.0.1:8000/oauth/token \
          -F grant_type=client_credentials


Refreshing an Access Token
--------------------------

.. code-block:: bash

    $ export CLIENT_ID=4d0a829fd95b8ee77893808a91b51171dcc1b36422bbcf61
    $ export CLIENT_SECRET=b536e10d18df0679343c340c626bac6a62cabd72a3a559cfb750c182480873bde67d25ada8e669ae008ed4aae3813dd539744c87697fca54d65003ff
    $ curl -u ${CLIENT_ID}:${CLIENT_SECRET} \
          -XPOST http://127.0.0.1:8000/oauth/token \
          -F grant_type=refresh_token \
          -F refresh_token=FSLn7Ytp6tWspYyRWgXlam4ZhsOJiV3tcVRmYD9a3Rf2gXqd

Token Revocation
----------------

.. code-block:: bash

    $ export CLIENT_ID=7149b9592ad89c6bf3f777ff6ec7280c
    $ export CLIENT_SECRET=ff14b0815c91465ef758a3277a50611ab35db0bafa28caad25f68ad5ca005ed0
    $ curl -u ${CLIENT_ID}:${CLIENT_SECRET} \
          -XPOST http://127.0.0.1:8000/oauth/revoke \
          -F token=fbZnda6CsQc0F6gOSKrybQwGnbhugRY05Pxr9A0eXf \
          -F token_type_hint=access_token


.. _Authlib: https://authlib.org
