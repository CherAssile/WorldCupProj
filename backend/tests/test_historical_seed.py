from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
from sqlalchemy.orm import Session

from app.models.historical_match import HistoricalMatch
from app.services import historical_seed

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "historical_results_test.csv"
FIXTURE_SOURCE_URL = "https://example.invalid/results.csv"


@pytest.fixture()
def unreachable_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simule un réseau indisponible : tout appel doit passer par le repli local."""

    def _raise(*args: object, **kwargs: object) -> None:
        raise httpx.ConnectError("réseau indisponible (simulé)")

    monkeypatch.setattr("app.services.historical_seed.httpx.get", _raise)


def test_seed_skips_matches_without_a_score(db_session: Session, unreachable_network: None) -> None:
    """Un match sans score renseigné (pas encore joué) ne doit jamais être importé.

    Le fixture contient 6 lignes : un match sans score (à ignorer), un match hors
    Coupe du Monde (à ignorer), un match entre une équipe inconnue et une équipe connue
    (à ignorer), et 3 matchs valides -> seuls ces 3 doivent apparaître en base.
    """
    result = historical_seed.run_seed(db_session, source_url=FIXTURE_SOURCE_URL, fallback_path=FIXTURE_PATH)

    imported = db_session.query(HistoricalMatch).filter(HistoricalMatch.edition_year == 2031).all()
    assert len(imported) == result.matches_created == 3
    assert all(m.home_score is not None and m.away_score is not None for m in imported)

    unplayed = (
        db_session.query(HistoricalMatch)
        .filter(HistoricalMatch.played_at == datetime(2031, 6, 3, tzinfo=timezone.utc))
        .one_or_none()
    )
    assert unplayed is None


def test_seed_is_idempotent(db_session: Session, unreachable_network: None) -> None:
    """Deux exécutions successives sur la même source ne créent aucun doublon."""
    first = historical_seed.run_seed(db_session, source_url=FIXTURE_SOURCE_URL, fallback_path=FIXTURE_PATH)
    assert first.matches_created == 3
    assert first.skipped_unknown_teams == 1

    total_after_first = db_session.query(HistoricalMatch).count()

    second = historical_seed.run_seed(db_session, source_url=FIXTURE_SOURCE_URL, fallback_path=FIXTURE_PATH)
    assert (second.matches_created, second.matches_updated) == (0, 0)
    assert db_session.query(HistoricalMatch).count() == total_after_first
