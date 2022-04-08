from flask_bcrypt import Bcrypt
from flask_restlib.oauth2.rbac import UserMixin
from flask_restlib.contrib.sqla import (
    AbstractOAuth2Role
)
from flask_sqlalchemy import SQLAlchemy
import sqlalchemy as sa
from sqlalchemy.orm import relationship


db = SQLAlchemy()
bcrypt = Bcrypt()


role_scopes = sa.Table(
    'role_scopes', db.Model.metadata,
    sa.Column('role_id', sa.ForeignKey('oauth2_role.id'), primary_key=True),
    sa.Column('scope_id', sa.ForeignKey('oauth2_scope.id'), primary_key=True),
)

user_roles = sa.Table(
    'user_roles', db.Model.metadata,
    sa.Column('user_id', sa.ForeignKey('user.id'), primary_key=True),
    sa.Column('role_id', sa.ForeignKey('oauth2_role.id'), primary_key=True),
)


class Scope(db.Model):
    __tablename__ = 'oauth2_scope'

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(255), nullable=False)
    description = sa.Column(sa.Text(), nullable=False)
    icon = sa.Column(sa.String(30), default='', nullable=False)

    def __str__(self):
        return self.name


class Role(AbstractOAuth2Role(db.Model)):
    scope = relationship('Scope', secondary=role_scopes, backref='roles', lazy='dynamic')

    def _get_role_scope(self) -> set[str]:
        return {s.name for s in self.scope}


class User(UserMixin, db.Model):
    id = sa.Column(sa.Integer, primary_key=True)
    email = sa.Column(sa.String(50), unique=True, nullable=False)
    _password = sa.Column(
        'password', sa.String(100), nullable=False, comment='Хешированный пароль'
    )
    is_active = sa.Column(
        sa.Boolean, default=True, nullable=False, comment='Аккаунт не заблокирован'
    )
    roles = relationship('Role', secondary=user_roles, backref='users', lazy=True)

    def change_password(self, value):
        """Changes the current password to passed."""
        self._password = bcrypt.generate_password_hash(value).decode('utf-8')

    def check_password(self, password):
        """Returns true if the password is valid, false otherwise."""
        return bcrypt.check_password_hash(self._password, password)

    password = property(fset=change_password)

    @classmethod
    def find_by_username(cls, email):
        """Returns the user with passed username, or None."""
        return cls.query.filter_by(email=email).first()
