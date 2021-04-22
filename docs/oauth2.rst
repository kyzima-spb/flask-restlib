.. _oauth2:


OAuth2
======

Authorization Code Grant
------------------------

.. code-block:: bash

    $ export CLIENT_ID=4d0a829fd95b8ee77893808a91b51171dcc1b36422bbcf61
    $ export CLIENT_SECRET=b536e10d18df0679343c340c626bac6a62cabd72a3a559cfb750c182480873bde67d25ada8e669ae008ed4aae3813dd539744c87697fca54d65003ff
    $ xdg-open "http://127.0.0.1:8000/oauth/authorize?client_id=${CLIENT_ID}&response_type=code"
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
