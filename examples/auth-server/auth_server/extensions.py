from flask_restlib import RestLib
from flask_restlib.contrib.mongoengine import MongoEngineFactory
from flask_restlib.http import HttpCache
from flask_restlib.pagination import LimitOffsetPagination

from .models import db, bcrypt, User


__all__ = ('db', 'bcrypt', 'rest')


TRest = RestLib[MongoEngineFactory[db.Document], LimitOffsetPagination, HttpCache]

rest: TRest = RestLib(
    factory=MongoEngineFactory(),
    auth_options={
        'user_model': User,
    }
)
