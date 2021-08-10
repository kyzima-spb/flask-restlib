from flask_restlib import RestLib
from flask_restlib.contrib.mongoengine import MongoEngineFactory


rest = RestLib(factory=MongoEngineFactory())
