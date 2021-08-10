from datetime import datetime

from flask_restlib import validators
from marshmallow import fields

from .extensions import rest


class TaskSchema(rest.Schema):
    id = fields.String()
    title = fields.String(
        required=True,
        validate=validators.Length(min=1, max=255)
    )
    planned = fields.DateTime(
        required=True,
        validate=lambda dt: dt > datetime.now()
    )
    description = fields.String()
    done = fields.Boolean()
    created = fields.DateTime()
    updated = fields.DateTime()
