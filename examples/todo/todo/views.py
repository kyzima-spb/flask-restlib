from flask_restlib import Q
from flask_restlib import validators
from flask_restlib import views
from flask_restlib.core import AbstractUrlQueryFilter
from marshmallow import fields

from . import models
from . import schemes
from .extensions import rest


class Tasks(views.ListView, views.CreateView):
    class MyFilter(AbstractUrlQueryFilter):
        def __call__(self, q, input_data):
            return q.filter_by(**input_data)

    model_class = models.Task
    schema_class = schemes.TaskSchema
    filters = [
        MyFilter({
            'title': fields.Str(),
            'done': fields.Boolean(),
        })
    ]


class TasksItem(views.RetrieveView, views.UpdateView, views.DestroyView):
    model_class = models.Task
    schema_class = schemes.TaskSchema


with rest.router.collection('tasks') as c:
    c.add_view(Tasks)
    c.add_item_view(TasksItem)
