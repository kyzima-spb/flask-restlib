from datetime import datetime

from flask_bcrypt import Bcrypt
from flask_restlib.mixins import UserMixin
from flask_sqlalchemy import SQLAlchemy
import sqlalchemy as sa
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import relationship
from sqlalchemy_utils.models import Timestamp


db = SQLAlchemy()
bcrypt = Bcrypt()


user_games = db.Table('user_games', db.Model.metadata,
    db.Column('user_id', db.ForeignKey('user.id'), primary_key=True),
    db.Column('game_id', db.ForeignKey('game.id'), primary_key=True)
)


class Genre(Timestamp, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(
        db.String(30),
        nullable=False,
        comment='Название'
    )

    def __repr__(self):
        return f"{self.__class__.__name__}(name='{self.name}')"


class Game(Timestamp, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    genre_id = db.Column(
        db.ForeignKey('genre.id'), nullable=False
    )
    genre = relationship('Genre', backref='games')
    title = db.Column(
        db.String(500),
        nullable=False,
        comment='Название'
    )
    cost = db.Column(
        db.Float,
        nullable=False,
        comment='Стоимость'
    )
    description = db.Column(
        db.Text,
        default='',
        nullable=False,
        comment='Описание игры'
    )


class User(Timestamp, UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(
        db.String(50),
        unique=True,
        nullable=False,
        comment='Используется как логин'
    )
    _password = db.Column(
        'password',
        db.String(100),
        nullable=False,
        comment='Хешированный пароль'
    )
    is_active = db.Column(
        db.Boolean,
        default=True,
        nullable=False,
        comment='Аккаунт не заблокирован'
    )
    is_admin = db.Column(
        db.Boolean,
        default=False,
        nullable=False,
        comment='Аккаунт администратора'
    )
    display_name = db.Column(
        db.String(255),
        default='',
        nullable=False,
        comment='Отображаемое имя вместо E-Mail'
    )
    balance = db.Column(
        db.Float(precision=2),
        default=0,
        nullable=False,
        comment='Баланс'
    )
    games = relationship('Game', secondary=user_games, lazy='dynamic')

    def buy_game(self, game):
        """Купить игру."""
        if self.balance < game.cost:
            raise RuntimeError('Not enough money to buy.')

        self.games.append(game)
        self.balance -= game.cost

    def change_password(self, value):
        """Сменяет текущий пароль на указанный."""
        self._password = bcrypt.generate_password_hash(value).decode('utf-8')

    def check_password(self, password):
        """Возвращает истину, если пароль верный, иначе ложь."""
        return bcrypt.check_password_hash(self._password, password)

    password = property(fset=change_password)

    @classmethod
    def find_by_username(cls, username):
        return cls.query.filter_by(email=username).first()

    def get_id(self):
        """Возвращает идентификатор пользователя, требует UserMixin."""
        return self.id

    def is_purchased(self, game):
        """
        Возвращает истину, если игра уже куплена.

        user_games.c - атрибут таблиц SQLAlchemy, которые не определены как модели.
        Для этих таблиц колонки отображаются как субатрибуты атрибута "c".
        """
        q = self.games.filter(user_games.c.game_id == game.id)
        return db.session.query(q.exists()).scalar()
