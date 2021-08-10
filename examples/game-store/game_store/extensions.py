from flask_restlib import RestLib
from flask_restlib.contrib.sqla import SQLAFactory

from game_store.models import db, bcrypt, User


__all__ = ('db', 'bcrypt', 'rest')


rest = RestLib(factory=SQLAFactory(), auth_options={
    'user_model': User,
})
