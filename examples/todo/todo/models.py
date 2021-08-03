from datetime import datetime

from flask_sqlalchemy import SQLAlchemy
import sqlalchemy as sa


db = SQLAlchemy()


class Task(db.Model):
    id = sa.Column(sa.Integer, primary_key=True)
    title = sa.Column(sa.String(255), nullable=False)
    planned = sa.Column(sa.DateTime(), nullable=False)
    description = sa.Column(sa.Text, nullable=False, default='')
    done = sa.Column(sa.Boolean, nullable=False, default=False)
    created = sa.Column(sa.DateTime, default=datetime.utcnow, nullable=False)
    updated = sa.Column(sa.DateTime, default=datetime.utcnow, nullable=False)

    def __str__(self):
        return self.title
