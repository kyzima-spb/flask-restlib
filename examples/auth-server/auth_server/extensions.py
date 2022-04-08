from flask_restlib import RestLib
from flask_restlib.contrib.sqla import SQLAFactory
from flask_restlib.http import HttpCache
from flask_restlib.pagination import LimitOffsetPagination

from .models import db, bcrypt, User


__all__ = ('db', 'bcrypt', 'rest')


TRest = RestLib[SQLAFactory[db.Model], LimitOffsetPagination, HttpCache]

rest: TRest = RestLib(
    factory=SQLAFactory(),
    auth_options={
        'user_model': User,
    }
)
