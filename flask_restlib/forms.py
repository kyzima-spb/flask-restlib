import typing as t

from flask import current_app
from flask_wtf import FlaskForm
from wtforms import fields
from wtforms import validators


__all__ = ('LoginForm',)


def trim(s: t.Optional[str]) -> t.Optional[str]:
    return s.strip() if s is not None else None


class LoginForm(FlaskForm):
    """Login form."""
    username = fields.StringField('Username', filters=[trim], validators=[
        validators.DataRequired(),
        validators.Length(min=1),
    ])
    password = fields.PasswordField('Password', validators=[
        validators.InputRequired(),
        validators.Length(min=1),
    ])
    remember_me = fields.BooleanField(
        'Remember Me',
        default=lambda: current_app.config['RESTLIB_REMEMBER_ME'],
        validators=[validators.Optional(),]
    )
