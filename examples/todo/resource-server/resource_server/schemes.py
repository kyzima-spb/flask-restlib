from datetime import datetime

from flask_restlib import validators
from marshmallow import fields
from marshmallow import validates

from . import models
from .extensions import rest


class TaskSchema(rest.Schema):
    class Meta:
        model = models.Task

    # planned = fields.DateTime(
    #     required=True,
    #     validate=lambda dt: dt > datetime.now()
    # )

    # status = fields.String(
    #     required=True,
    #     validate=validators.ExistsEntity(models.Status)
    # )
