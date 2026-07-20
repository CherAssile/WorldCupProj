from pathlib import Path

import httpx
import pytest
from sqlalchemy.orm import Session

from app.models.match import Match
from app.models.prediction import Prediction
from app.models.score import Score
from app.models.team import Team
from app.models.user import User
from app.redis_client import redis_client
from app.services import leaderboard
from app.services.football_api import FootballApiClient
from app.services.sync_pipeline import run_full_sync

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "worldcup_test.json"


@pytest.fixture(autouse=True)
def _clean_leaderboard_key() -> None:
    """rebuild_leaderboard écrit directement dans Redis, hors de la transaction SQL de
    test (cf. test_leaderboard.py) : à nettoyer explicitement pour ne pas polluer le vrai
    classement, ni être pollué par lui."""
    redis_client.delete(leaderboard.LEADERBOARD_KEY)
    yield
    redis_client.delete(leaderboard.LEADERBOARD_KEY)


@pytest.fixture()
def local_fixture_client(monkeypatch: pytest.MonkeyPatch) -> FootballApiClient:
    """Simule un réseau indisponible (repli sur la copie locale de test), comme
    tests/test_seed.py : la chaîne complète ne doit jamais dépendre d'un vrai appel réseau
    dans les tests."""

    def _raise(*args: object, **kwargs: object) -> None:
        raise httpx.ConnectError("réseau indisponible (simulé)")

    monkeypatch.setattr("app.services.football_api.httpx.get", _raise)
    return FootballApiClient(source_url="https://example.invalid/worldcup.json", fallback_path=FIXTURE_PATH)


def test_run_full_sync_executes_full_chain_and_scores_predictions(
    db_session: Session, local_fixture_client: FootballApiClient
) -> None:
    """Les 4 étapes bout en bout : calendrier -> placeholders -> scores -> classement.

    Le fixture contient un quart de finale déjà joué (France-Espagne, 1-1 aux 90 minutes,
    France qualifiée aux tirs au but) : un pronostic exact + bon qualifié y vaut
    (3 + 2) x 2 (quart de finale) = 10 points, un chiffre entièrement vérifiable à la main.
    """
    first = run_full_sync(db_session, redis_client, client=local_fixture_client)
    assert first.matches_created == 4
    assert first.matches_updated == 0

    quarter_final = db_session.query(Match).filter(Match.num == 9001).one()
    assert (quarter_final.home_score, quarter_final.away_score) == (1, 1)
    france = db_session.query(Team).filter(Team.name == "France").one()
    assert quarter_final.winner_team_id == france.id

    user = User(email="sync-pipeline@example.com", username="syncpipeline", hashed_password="x")
    db_session.add(user)
    db_session.flush()
    prediction = Prediction(
        user_id=user.id,
        match_id=quarter_final.id,
        predicted_home_score=1,
        predicted_away_score=1,
        predicted_winner_team_id=france.id,
    )
    db_session.add(prediction)
    db_session.flush()

    # 2e passage : le calendrier n'a pas changé (idempotent), mais le pronostic tout juste
    # créé est désormais noté et reflété au classement -- sans re-synchroniser le calendrier
    # à la main entre les deux, exactement comme un tick planifié qui se répète.
    second = run_full_sync(db_session, redis_client, client=local_fixture_client)
    assert (second.matches_created, second.matches_updated) == (0, 0)
    assert second.scores_recalculated >= 1
    assert second.leaderboard_size >= 1

    score = db_session.query(Score).filter(Score.user_id == user.id).one()
    assert score.total_points == 10

    entries = leaderboard.get_leaderboard(db_session, redis_client)
    assert any(e.user_id == user.id and e.total_points == 10 for e in entries)


def test_run_full_sync_never_leaves_partial_write_on_source_failure(
    db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Si la source est injoignable ET la copie locale absente (cas limite), run_seed lève
    -- run_full_sync doit laisser l'exception se propager (pas d'écriture masquée), à charge
    de l'appelant (scheduler ou endpoint admin) de gérer l'échec."""

    def _raise(*args: object, **kwargs: object) -> None:
        raise httpx.ConnectError("réseau indisponible (simulé)")

    monkeypatch.setattr("app.services.football_api.httpx.get", _raise)
    broken_client = FootballApiClient(
        source_url="https://example.invalid/worldcup.json", fallback_path=Path("/nonexistent/fallback.json")
    )

    with pytest.raises(RuntimeError):
        run_full_sync(db_session, redis_client, client=broken_client)
