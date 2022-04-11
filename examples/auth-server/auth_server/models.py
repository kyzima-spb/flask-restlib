from flask_bcrypt import Bcrypt
from flask_mongoengine import MongoEngine
from flask_restlib.contrib.mongoengine import OAuth2Role
from flask_restlib.oauth2.rbac import UserMixin
import mongoengine as me


db = MongoEngine()
bcrypt = Bcrypt()


class PasswordField(me.StringField):
    def to_mongo(self, value):
        if value:
            value = bcrypt.generate_password_hash(value).decode('utf-8')
        return super().to_mongo(value)


class Scope(db.Document):
    name = me.StringField(required=True, max_length=255)
    description = me.StringField(required=True)

    def __str__(self):
        return self.name


class Role(OAuth2Role):
    scope = me.ListField(me.ReferenceField(Scope))

    def _get_role_scope(self) -> set[str]:
        return {s.name for s in self.scope}


class User(UserMixin, db.Document):
    email = me.EmailField(required=True, max_length=50, unique=True)
    password = PasswordField(required=True, max_length=100)
    is_active = me.BooleanField(default=True)
    roles = me.ListField(me.ReferenceField(Role))

    meta = {
        'strict': False,
    }

    def change_password(self, value):
        """Changes the current password to passed."""
        self.password = bcrypt.generate_password_hash(value).decode('utf-8')

    def check_password(self, password):
        """Returns true if the password is valid, false otherwise."""
        return bcrypt.check_password_hash(self.password, password)

    @classmethod
    def find_by_username(cls, email):
        """Returns the user with passed username, or None."""
        return cls.objects(email=email).first()
