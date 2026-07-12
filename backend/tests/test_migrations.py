from sqlalchemy import inspect

import app.models  # noqa: F401 -- charge tous les modèles pour peupler Base.metadata
from app.database import Base, engine

# CLAUDE.md annonce 15 tables mais la répartition par catégorie n'en liste que 14 ;
# c'est le nombre réellement mappé dans app.models à date.
EXPECTED_TABLE_COUNT = 14


def test_all_tables_exist_after_migration() -> None:
    """Chaque table déclarée dans les modèles SQLAlchemy existe bien en base après `alembic upgrade head`."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    expected_tables = set(Base.metadata.tables.keys())

    assert len(expected_tables) == EXPECTED_TABLE_COUNT
    assert expected_tables <= existing_tables
