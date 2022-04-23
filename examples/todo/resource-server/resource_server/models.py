from datetime import datetime

from flask_mongoengine import MongoEngine
from mongoengine import fields
from mongoengine import ValidationError


db = MongoEngine()


def validate_expires(dt):
    if datetime.now() > dt:
        raise ValidationError('Value must be great then now.')


class Task(db.Document):
    title = fields.StringField(required=True, min_length=1, max_length=255)
    expires = fields.DateTimeField(required=True, validation=validate_expires)
    description = fields.StringField(default='')
    is_done = fields.BooleanField(default=False)
    created = fields.DateTimeField(default=datetime.utcnow)
    updated = fields.DateTimeField(default=datetime.utcnow)

    def __str__(self):
        return self.title
