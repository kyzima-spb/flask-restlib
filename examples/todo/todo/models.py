from datetime import datetime

from flask_mongoengine import MongoEngine
from mongoengine import fields
from mongoengine import ValidationError


db = MongoEngine()


def validate_planned_date(dt):
    if datetime.now() > dt:
        raise ValidationError('Value must be great then now.')


class Status(db.Document):
    name = fields.StringField(
        required=True,
        unique=True,
        min_length=1,
        max_length=50
    )

    def __str__(self):
        return self.name


class Task(db.Document):
    title = fields.StringField(required=True, min_length=1, max_length=255)
    planned = fields.DateTimeField(required=True, validation=validate_planned_date)
    description = fields.StringField(default='')
    status = fields.ReferenceField(Status, required=True)
    done = fields.BooleanField(default=False)
    created = fields.DateTimeField(default=datetime.utcnow)
    updated = fields.DateTimeField(default=datetime.utcnow)

    def __str__(self):
        return self.title
