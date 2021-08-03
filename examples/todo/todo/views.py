from flask_restlib import views

from todo import models
from todo.extensions import rest


class Tasks(views.ListView, views.CreateView):
    model_class = models.Task
    # schema_class = schemes.EducationSchema


class TasksItem(views.RetrieveView, views.UpdateView, views.DestroyView):
    model_class = models.Task
    # schema_class = schemes.EducationSchema


with rest.router.collection('tasks') as c:
    c.add_view(Tasks)
    c.add_item_view(TasksItem)
