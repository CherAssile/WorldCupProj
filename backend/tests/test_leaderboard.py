from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.score import Score
from app.models.user import User
from app.redis_client import redis_client
from app.services import leaderboard

BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def _clean_leaderboard_key() -> None:
    """Le sorted set Redis n'est pas couvert par le rollback SQL de db_session : on le
    nettoie explicitement avant/après chaque test pour ne pas polluer le vrai classement."""
    redis_client.delete(leaderboard.LEADERBOARD_KEY)
    yield
    redis_client.delete(leaderboard.LEADERBOARD_KEY)


def _create_user_with_score(
    db_session: Session,
    email: str,
    created_at: datetime,
    total_points: int,
    exact_scores_count: int,
) -> User:
    user = User(email=email, username=email.split("@")[0], hashed_password="x", created_at=created_at)
    db_session.add(user)
    db_session.flush()
    db_session.add(Score(user_id=user.id, total_points=total_points, exact_scores_count=exact_scores_count))
    db_session.flush()
    return user


def _clear_scores(db_session: Session) -> None:
    """Le classement recalcule à partir de TOUTE la table scores : si un pronostic réel a
    déjà été noté (services/scoring.py), il apparaîtrait dans ces tests d'égalité stricte.
    Repart d'une table sans score, sans effet hors de la transaction de test."""
    db_session.query(Score).delete()
    db_session.flush()


def test_leaderboard_reflects_scores_table_after_recompute(db_session: Session) -> None:
    _clear_scores(db_session)
    alice = _create_user_with_score(db_session, "alice@example.com", BASE_TIME, 30, 5)
    bob = _create_user_with_score(db_session, "bob@example.com", BASE_TIME + timedelta(days=1), 45, 3)

    leaderboard.rebuild_leaderboard(db_session, redis_client)
    entries = leaderboard.get_leaderboard(db_session, redis_client)

    assert [e.user_id for e in entries] == [bob.id, alice.id]
    assert [e.rank for e in entries] == [1, 2]
    assert entries[0].total_points == 45
    assert entries[1].total_points == 30


def test_tiebreak_by_exact_scores_count_when_points_equal(db_session: Session) -> None:
    _clear_scores(db_session)
    low_exact = _create_user_with_score(db_session, "low@example.com", BASE_TIME, 20, 2)
    high_exact = _create_user_with_score(db_session, "high@example.com", BASE_TIME + timedelta(days=1), 20, 7)

    leaderboard.rebuild_leaderboard(db_session, redis_client)
    entries = leaderboard.get_leaderboard(db_session, redis_client)

    assert [e.user_id for e in entries] == [high_exact.id, low_exact.id]


def test_tiebreak_by_account_age_when_points_and_exact_scores_equal(db_session: Session) -> None:
    _clear_scores(db_session)
    older = _create_user_with_score(db_session, "older@example.com", BASE_TIME, 20, 4)
    newer = _create_user_with_score(db_session, "newer@example.com", BASE_TIME + timedelta(days=30), 20, 4)

    leaderboard.rebuild_leaderboard(db_session, redis_client)
    entries = leaderboard.get_leaderboard(db_session, redis_client)

    assert [e.user_id for e in entries] == [older.id, newer.id]


def test_full_tiebreak_ordering_across_all_three_levels(db_session: Session) -> None:
    """Points d'abord, puis scores exacts, puis ancienneté du compte (le plus ancien devant)."""
    _clear_scores(db_session)
    a = _create_user_with_score(db_session, "a@example.com", BASE_TIME, 50, 1)
    b = _create_user_with_score(db_session, "b@example.com", BASE_TIME + timedelta(days=1), 30, 10)
    c = _create_user_with_score(db_session, "c@example.com", BASE_TIME + timedelta(days=2), 30, 5)
    d = _create_user_with_score(db_session, "d@example.com", BASE_TIME + timedelta(days=3), 30, 5)

    leaderboard.rebuild_leaderboard(db_session, redis_client)
    entries = leaderboard.get_leaderboard(db_session, redis_client)

    assert [e.user_id for e in entries] == [a.id, b.id, c.id, d.id]


def test_get_leaderboard_endpoint_is_public_and_ranked(client: TestClient, db_session: Session) -> None:
    _clear_scores(db_session)
    alice = _create_user_with_score(db_session, "pub1@example.com", BASE_TIME, 10, 1)
    bob = _create_user_with_score(db_session, "pub2@example.com", BASE_TIME + timedelta(days=1), 20, 1)
    leaderboard.rebuild_leaderboard(db_session, redis_client)

    response = client.get("/leaderboard")
    assert response.status_code == 200
    body = response.json()
    assert [e["user_id"] for e in body] == [bob.id, alice.id]


def test_recompute_endpoint_requires_admin(client: TestClient, db_session: Session) -> None:
    non_admin = User(email="regular@example.com", username="regular", hashed_password="x", is_admin=False)
    db_session.add(non_admin)
    db_session.flush()
    token = create_access_token(subject=str(non_admin.id))

    response = client.post("/leaderboard/recompute", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_recompute_endpoint_succeeds_for_admin(client: TestClient, db_session: Session) -> None:
    admin = User(email="admin@example.com", username="admin", hashed_password="x", is_admin=True)
    db_session.add(admin)
    db_session.flush()
    db_session.add(Score(user_id=admin.id, total_points=5, exact_scores_count=1))
    db_session.flush()
    token = create_access_token(subject=str(admin.id))

    response = client.post("/leaderboard/recompute", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["users_ranked"] >= 1
