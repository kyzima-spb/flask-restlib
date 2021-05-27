import pytest

from flask_restlib.contrib.sqla import (
    SQLAModelField,
    QueryAdapter,
    ResourceManager
)


@pytest.fixture
def single_genre(db, Genre):
    genre = Genre(name='Action')
    db.session.add(genre)
    db.session.commit()
    return genre


class TestSQLAFactory:
    def test_create_model_field_adapter(self, factory, Genre):
        """Tests the creation of an adapter for a SQLAlchemy model attribute."""
        column = factory.create_model_field_adapter(Genre.id)
        assert isinstance(column, SQLAModelField)

    def test_create_query_adapter(self, app, factory, Genre):
        """Tests the creation a queryset for a SQLAlchemy."""
        with app.app_context():
            q = factory.create_query_adapter(Genre)
            assert isinstance(q, QueryAdapter)

    def test_create_resource_manager(self, factory):
        """Tests the creation a resource manager for a SQLAlchemy."""
        rm = factory.create_resource_manager()
        assert isinstance(rm, ResourceManager)


class TestSQLAResourceManager:
    def test_create(self, resource_manager, Genre):
        with resource_manager as rm:
            saved = rm.create(Genre, {
                'name': 'Action',
            })
        loaded = Genre.query.get(saved.id)
        assert saved == loaded

    def test_delete(self, resource_manager, single_genre, Genre):
        with resource_manager:
            resource_manager.delete(single_genre)
        assert Genre.query.get(single_genre.id) is None

    def test_get(self, resource_manager, single_genre, Genre):
        with resource_manager:
            loaded = resource_manager.get(Genre, single_genre.id)
        assert loaded == single_genre
