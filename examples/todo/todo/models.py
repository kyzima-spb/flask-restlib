from datetime import datetime

from flask_mongoengine import MongoEngine
from mongoengine import fields


db = MongoEngine()


class Task(db.Document):
    title = fields.StringField(required=True, max_length=255)
    planned = fields.DateTimeField(required=True)
    description = fields.StringField(default='')
    done = fields.BooleanField(default=False)
    created = fields.DateTimeField(default=datetime.utcnow, nullable=False)
    updated = fields.DateTimeField(default=datetime.utcnow, nullable=False)

    def __str__(self):
        return self.title
