from sqlalchemy import inspect

import app.models  # noqa: F401 -- charge tous les modèles pour peupler Base.metadata
from app.database import Base, engine

# CLAUDE.md annonce 15 tables ; training_session_matches (tirage avant pronostic) et
# lineups/lineup_players (contexte sportif, absents de la répartition par catégorie du
# document) portent le compte réel à ce total.
EXPECTED_TABLE_COUNT = 17


def test_all_tables_exist_after_migration() -> None:
    """Chaque table déclarée dans les modèles SQLAlchemy existe bien en base après `alembic upgrade head`."""
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    expected_tables = set(Base.metadata.tables.keys())

    assert len(expected_tables) == EXPECTED_TABLE_COUNT
    assert expected_tables <= existing_tables
