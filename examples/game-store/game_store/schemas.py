from marshmallow import fields, validate, validates, ValidationError
from marshmallow_sqlalchemy import auto_field
from marshmallow_sqlalchemy.fields import Nested, Related

from . import models
from .extensions import rest


class GenreSchema(rest.AutoSchema):
    class Meta:
        model = models.Genre

    name = auto_field(validate=validate.Length(min=1, max=30))


class GameSchema(rest.AutoSchema):
    class Meta:
        model = models.Game
        dump_only = ('genre',)

    title = auto_field(validate=validate.Length(min=1, max=500))
    cost = auto_field(validate=validate.Range(min=0))
    genre_id = auto_field(load_only=True)
    genre = Related('name', dump_only=True)

    @validates('genre_id')
    def validate_genre_id(self, id):
        rm = rest.factory.create_resource_manager(models.Genre)
        if not rm.get(id):
            raise ValidationError(['Genre does not exists.'])


class UserSchema(rest.AutoSchema):
    class Meta:
        model = models.User
        exclude = ('_password',)
        dump_only = ('balance', 'active', 'is_admin')

    email = auto_field(field_class=fields.Email)
    password = auto_field(
        '_password',
        validate=validate.Length(min=8),
        load_only=True,
        attribute='password'
    )

    @validates('email')
    def validate_email(self, email):
        user = self.context.get('resource')

        if user is None or user.email != email:
            if self.opts.model.get_by_email(email):
                raise ValidationError(['E-Mail is already in use by another user.'])


class BalanceSchema(rest.Schema):
    """Баланс пользователя."""
    balance = fields.Integer(validate=validate.Range(min=1))
