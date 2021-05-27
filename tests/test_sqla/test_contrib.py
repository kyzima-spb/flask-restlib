import pytest

from flask_restlib.contrib.sqla import (
    SQLAModelField,
    QueryAdapter,
    ResourceManager
)


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
    def test_create(self, app, db, Genre):
        with app.app_context():
            with ResourceManager(db.session) as rm:
                saved = rm.create(Genre, {
                    'name': 'Action',
                })
            selected = Genre.query.get(saved.id)
            assert saved == selected
