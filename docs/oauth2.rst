.. _oauth2:


OAuth2
======

Authorization Code Grant
------------------------

.. code-block:: bash

    $ export CLIENT_ID=5fcc7cd5f92a79eb7d63040c25263def
    $ export CLIENT_SECRET=02a52f676f4ffe52d0c5d59a3feb70f2ac343fa60ec6e06ba06c5cd4ded1c0ec
    $ xdg-open "http://127.0.0.1:8000/oauth/authorize?client_id=${CLIENT_ID}&response_type=code"
    $ curl -u ${CLIENT_ID}:${CLIENT_SECRET} \
          -XPOST http://127.0.0.1:8000/oauth/token \
          -F grant_type=authorization_code \
          -F code=xtzFw2o7FBqBexUGKWpf2aIR813uEHB39QQDkAYaSM7ywT0b

Implicit Grant
--------------

.. code-block:: bash

    $ export CLIENT_ID=4fd83df800d639105291365c7c9179f1
    $ export CLIENT_SECRET=5c90977bc86935cc074df9399580331027dadc99ee8a29eb083b98857752ed5b
    $ xdg-open "http://127.0.0.1:8000/oauth/authorize?client_id=${CLIENT_ID}&response_type=token"


Resource Owner Password Credentials Grant
-----------------------------------------

.. code-block:: bash

    $ export CLIENT_ID=7149b9592ad89c6bf3f777ff6ec7280c
    $ export CLIENT_SECRET=ff14b0815c91465ef758a3277a50611ab35db0bafa28caad25f68ad5ca005ed0
    $ curl -u ${CLIENT_ID}:${CLIENT_SECRET} \
          -XPOST http://127.0.0.1:8000/oauth/token \
          -F grant_type=password \
          -F username=office@kyzima-spb.com \
          -F password=cdpo123!

Client Credentials Grant
------------------------

.. code-block:: bash

    $ export CLIENT_ID=779e26994f0532b3c68c0c0b7a21973b
    $ export CLIENT_SECRET=11cfd539b236fda46219e0e02de7ee6b631cc9baafa8f1bac9f27e63c0659d35
    $ curl -u ${CLIENT_ID}:${CLIENT_SECRET} \
          -XPOST http://127.0.0.1:8000/oauth/token \
          -F grant_type=client_credentials


Refreshing an Access Token
--------------------------

.. code-block:: bash

    $ export CLIENT_ID=7149b9592ad89c6bf3f777ff6ec7280c
    $ export CLIENT_SECRET=ff14b0815c91465ef758a3277a50611ab35db0bafa28caad25f68ad5ca005ed0
    $ curl -u ${CLIENT_ID}:${CLIENT_SECRET} \
          -XPOST http://127.0.0.1:8000/oauth/token \
          -F grant_type=refresh_token \
          -F refresh_token=KC0HzpNxqRUIJSvpV6H9SFLQTUSjCKFqvdjb5CgXlKo5LSIj

Token Revocation
----------------

.. code-block:: bash

    $ export CLIENT_ID=7149b9592ad89c6bf3f777ff6ec7280c
    $ export CLIENT_SECRET=ff14b0815c91465ef758a3277a50611ab35db0bafa28caad25f68ad5ca005ed0
    $ curl -u ${CLIENT_ID}:${CLIENT_SECRET} \
          -XPOST http://127.0.0.1:8000/oauth/revoke \
          -F token=fbZnda6CsQc0F6gOSKrybQwGnbhugRY05Pxr9A0eXf \
          -F token_type_hint=access_token
