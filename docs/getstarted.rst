.. _getstarted:


Get started
===========

.. code-block:: python

    from flask_restlib import RestLib
    from flask_restlib.contrib.sqla import SQLAFactory

    rest = RestLib(factory=SQLAFactory())


.. code-block:: python

    from flask_restlib import RestLib
    from flask_restlib.contrib.mongoengine import MongoEngineFactory

    rest = RestLib()

    @rest.factory_loader
    def factory_loader():
        return MongoEngineFactory
