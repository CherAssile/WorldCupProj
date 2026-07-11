import pytest

from app.models import (
    SimulationMatchResult,
    SimulationRun,
    TrainingPrediction,
    TrainingSession,
)

FORBIDDEN_TABLES = {"matches", "predictions", "scores"}

ISOLATED_MODELS = [TrainingSession, TrainingPrediction, SimulationRun, SimulationMatchResult]


@pytest.mark.parametrize("model", ISOLATED_MODELS, ids=lambda m: m.__tablename__)
def test_no_foreign_key_to_competitive_tables(model: type) -> None:
    """Entraînement et simulation ne doivent jamais référencer matches/predictions/scores."""
    table = model.__table__
    referenced_tables = {fk.column.table.name for fk in table.foreign_keys}

    forbidden_hit = referenced_tables & FORBIDDEN_TABLES
    assert not forbidden_hit, (
        f"{table.name} a une clé étrangère vers {forbidden_hit} : "
        "l'isolation entraînement/simulation vis-à-vis du compétitif est rompue."
    )
