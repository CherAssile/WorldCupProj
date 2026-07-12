from datetime import datetime, timezone
from pathlib import Path

import httpx
import pytest
from sqlalchemy.orm import Session

from app.models.match import Match
from app.models.team import Team
from app.services import seed as seed_service
from app.services.football_api import DEFAULT_FALLBACK_PATH, FootballApiClient

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "worldcup_test.json"

# Correspond au match "Quarter-final" France vs Spain du fixture (2026-06-20, 18:00 UTC-4).
# Date fabriquée, hors du vrai calendrier 2026 : ne peut pas coïncider avec un match réel
# déjà importé par services/seed.py sur la même base.
FIXTURE_QUARTER_FINAL_KICKOFF = datetime(2026, 6, 20, 22, 0, tzinfo=timezone.utc)


@pytest.fixture()
def unreachable_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Simule un réseau indisponible : tout appel doit passer par le repli local."""

    def _raise(*args: object, **kwargs: object) -> None:
        raise httpx.ConnectError("réseau indisponible (simulé)")

    monkeypatch.setattr("app.services.football_api.httpx.get", _raise)


@pytest.fixture()
def local_fixture_client(unreachable_network: None) -> FootballApiClient:
    return FootballApiClient(source_url="https://example.invalid/worldcup.json", fallback_path=FIXTURE_PATH)


def test_seed_falls_back_to_local_copy_on_network_failure(
    db_session: Session, local_fixture_client: FootballApiClient
) -> None:
    """Si le téléchargement échoue, le repli local est utilisé : le seed importe bien ses matchs.

    Le fixture contient 4 équipes réelles et 4 matchs. La finale référence des équipes non
    encore résolues ("W101"/"W102") : elle est importée quand même, avec les FK à NULL et
    le placeholder renseigné (bracket), plutôt que d'être ignorée.
    """
    result = seed_service.run_seed(db_session, client=local_fixture_client)
    assert result.matches_created == 4

    imported = db_session.query(Match).filter(Match.kickoff_at == FIXTURE_QUARTER_FINAL_KICKOFF).one_or_none()
    assert imported is not None
    assert (imported.home_score, imported.away_score) == (1, 1)

    final = db_session.query(Match).filter(Match.num == 9002).one_or_none()
    assert final is not None
    assert (final.home_team_id, final.away_team_id) == (None, None)
    assert (final.home_placeholder, final.away_placeholder) == ("W101", "W102")

    team_names = {
        t.name for t in db_session.query(Team).filter(Team.name.in_(["France", "Brazil", "Spain", "Argentina"]))
    }
    assert team_names == {"France", "Brazil", "Spain", "Argentina"}


def test_full_seed_produces_104_matches_with_two_unresolved(
    db_session: Session, unreachable_network: None
) -> None:
    """Le vrai calendrier 2026 (copie locale) compte 104 matchs, dont 2 pas encore résolus
    (finale, match pour la 3e place) : équipes à NULL, placeholder renseigné."""
    client = FootballApiClient(source_url="https://example.invalid/worldcup.json", fallback_path=DEFAULT_FALLBACK_PATH)
    seed_service.run_seed(db_session, client=client)

    assert db_session.query(Match).count() == 104

    unresolved = db_session.query(Match).filter(Match.home_team_id.is_(None)).all()
    assert len(unresolved) == 2
    assert all(m.away_team_id is None for m in unresolved)
    assert all(m.home_placeholder and m.away_placeholder for m in unresolved)


def test_seed_is_idempotent(db_session: Session, local_fixture_client: FootballApiClient) -> None:
    """Deux exécutions successives sur la même source ne créent aucun doublon.

    N'suppose pas une base vide au départ (le calendrier réel peut déjà être importé) :
    compare l'état après la 1ère exécution à l'état après la 2e, en delta.
    """
    seed_service.run_seed(db_session, client=local_fixture_client)
    teams_after_first = db_session.query(Team).count()
    matches_after_first = db_session.query(Match).count()

    second = seed_service.run_seed(db_session, client=local_fixture_client)

    assert (second.teams_created, second.matches_created, second.matches_updated) == (0, 0, 0)
    assert db_session.query(Team).count() == teams_after_first
    assert db_session.query(Match).count() == matches_after_first
