import typing

from authlib.integrations.flask_oauth2 import current_token
from flask_login import login_user
from flask_restlib import views
from flask_restlib.core import AbstractUrlQueryFilter
from flask_restlib.permissions import Permission, AuthorizationError, IsAuthenticated, TokenHasScope
from flask_restlib.routing import Route
from webargs.flaskparser import use_args, parser
from webargs import fields
from webargs import validate as validators

from . import models
from . import schemas
from .extensions import rest


class CustomPermission(Permission):
    def check_resource_permission(self, view, resource) -> typing.NoReturn:
        if resource.id == 1:
            raise AuthorizationError('Stupid condition')


class Genres(views.ListView, views.CreateView):
    # class Filter(UrlQueryFilter):
    #     def _do_apply(self, q, input_data: dict):
    #         return q.filter_by(**input_data)

    model_class = models.Genre
    schema_class = schemas.GenreSchema
    # filter_instance = Filter(schemas.GenreSchema(only=('name',)))
    sorting_fields = ('name', 'created', 'updated')


class GenresItem(views.RetrieveView, views.UpdateView, views.DestroyView):
    model_class = models.Genre
    schema_class = schemas.GenreSchema


class Games(views.ListView, views.CreateView):
    model_class = models.Game
    schema_class = schemas.GameSchema
    permissions = [TokenHasScope('games')]


class GamesItem(views.RetrieveView, views.UpdateView, views.DestroyView):
    model_class = models.Game
    schema_class = schemas.GameSchema
    permissions = [IsAuthenticated(), CustomPermission()]

    def get(self, id):
        print(current_token)
        return super().get(id)


class Users(views.ListView, views.CreateView):
    model_class = models.User


class UsersItem(views.RetrieveView, views.UpdateView, views.DestroyView):
    model_class = models.User


class Profile(views.RetrieveView):
    model_class = models.User
    permissions = [TokenHasScope('profile')]


class UserGames(views.ListView):
    model_class = models.Game


class Purchase(views.ApiView):
    def put(self, id):
        # current_user.buy_game(
        #     Game.query.get_or_404(game_id)
        # )
        # db.session.commit()
        return '', 201


with rest.router.collection('genres') as c:
    c.add_view(Genres)
    c.add_item_view(GenresItem)

with rest.router.collection('games') as c:
    c.add_view(Games)
    c.add_item_view(GamesItem)
    # games = genres_item.add(Route('games', Games))
    # games_item = games.add_item_view(GamesItem, parent_lookup_name='genre_id')

# users = bp.add_route(Route('users', Users))
# users_item = users.add_item_view(UsersItem)
#
# profile = bp.add_route(Route('profile', Profile, is_item=True, lookup_name=False))
# user_games = profile.add(Route('games', UserGames))
# purchase = user_games.add_item_view(Purchase)