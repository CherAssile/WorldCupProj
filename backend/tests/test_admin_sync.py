from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.deps import get_football_api_client
from app.main import app
from app.models.match import Match
from app.models.user import User
from app.redis_client import redis_client
from app.services import leaderboard
from app.services.football_api import FootballApiClient

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "worldcup_test.json"


@pytest.fixture(autouse=True)
def _clean_leaderboard_key() -> None:
    redis_client.delete(leaderboard.LEADERBOARD_KEY)
    yield
    redis_client.delete(leaderboard.LEADERBOARD_KEY)


@pytest.fixture()
def _use_local_fixture_client(monkeypatch: pytest.MonkeyPatch):
    """L'endpoint admin appelle la vraie source par défaut : injecte le repli local de
    test (cf. tests/test_seed.py), jamais un vrai appel réseau dans la suite pytest."""

    def _raise(*args: object, **kwargs: object) -> None:
        raise httpx.ConnectError("réseau indisponible (simulé)")

    monkeypatch.setattr("app.services.football_api.httpx.get", _raise)
    client = FootballApiClient(source_url="https://example.invalid/worldcup.json", fallback_path=FIXTURE_PATH)
    app.dependency_overrides[get_football_api_client] = lambda: client
    yield
    app.dependency_overrides.pop(get_football_api_client, None)


def test_sync_endpoint_requires_admin(client: TestClient, db_session: Session) -> None:
    non_admin = User(email="regular-sync@example.com", username="regularsync", hashed_password="x", is_admin=False)
    db_session.add(non_admin)
    db_session.flush()
    token = create_access_token(subject=str(non_admin.id))

    response = client.post("/admin/sync", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_sync_endpoint_runs_full_chain_for_admin(
    client: TestClient, db_session: Session, _use_local_fixture_client: None
) -> None:
    admin = User(email="admin-sync@example.com", username="adminsync", hashed_password="x", is_admin=True)
    db_session.add(admin)
    db_session.flush()
    token = create_access_token(subject=str(admin.id))

    response = client.post("/admin/sync", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    body = response.json()
    assert body["matches_created"] == 4
    assert body["matches_updated"] == 0
    assert set(body) == {
        "teams_created",
        "matches_created",
        "matches_updated",
        "placeholders_resolved",
        "scores_recalculated",
        "leaderboard_size",
    }

    quarter_final = db_session.query(Match).filter(Match.num == 9001).one()
    assert (quarter_final.home_score, quarter_final.away_score) == (1, 1)
