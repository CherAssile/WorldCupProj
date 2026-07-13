from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.award import Award
from app.models.enums import AwardCategory
from app.models.player import Player
from app.models.team import Team

PASSWORD = "correcthorsebattery"
FUTURE_LOCK = datetime.now(timezone.utc) + timedelta(days=7)
PAST_LOCK = datetime.now(timezone.utc) - timedelta(days=1)


def _register_and_login(client: TestClient, email: str) -> dict[str, str]:
    username = email.split("@")[0]
    client.post("/auth/register", json={"email": email, "username": username, "password": PASSWORD})
    login = client.post("/auth/login", data={"username": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create_award(db_session: Session, category: AwardCategory, lock_at: datetime) -> Award:
    """`category` est unique en base : le calendrier réel peut déjà contenir une récompense
    pour cette catégorie (services/awards_seed.py). Repart d'une base sans elle pour ce test,
    sans effet hors de la transaction de test."""
    db_session.query(Award).filter(Award.category == category).delete()
    db_session.flush()

    award = Award(category=category, lock_at=lock_at)
    db_session.add(award)
    db_session.flush()
    return award


def _create_players(db_session: Session, prefix: str) -> tuple[Player, Player]:
    team = Team(name=f"{prefix} Team", fifa_code=f"{prefix[:3].upper()}")
    db_session.add(team)
    db_session.flush()
    player_a = Player(team_id=team.id, name=f"{prefix} Player A")
    player_b = Player(team_id=team.id, name=f"{prefix} Player B")
    db_session.add_all([player_a, player_b])
    db_session.flush()
    return player_a, player_b


def test_get_awards_lists_categories_with_lock_at(client: TestClient, db_session: Session) -> None:
    _create_award(db_session, AwardCategory.TOP_SCORER, FUTURE_LOCK)
    db_session.commit()

    response = client.get("/awards")
    assert response.status_code == 200
    categories = {a["category"] for a in response.json()}
    assert "top_scorer" in categories


def test_choose_award_prediction_before_lock_succeeds(client: TestClient, db_session: Session) -> None:
    headers = _register_and_login(client, "fan1@example.com")
    award = _create_award(db_session, AwardCategory.TOP_SCORER, FUTURE_LOCK)
    player_a, _ = _create_players(db_session, "CHO")

    response = client.post(
        "/award-predictions",
        json={"award_id": award.id, "predicted_player_id": player_a.id},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["predicted_player_id"] == player_a.id


def test_choose_award_prediction_after_lock_rejected(client: TestClient, db_session: Session) -> None:
    headers = _register_and_login(client, "fan2@example.com")
    award = _create_award(db_session, AwardCategory.TOP_ASSIST, PAST_LOCK)
    player_a, _ = _create_players(db_session, "LCK")

    response = client.post(
        "/award-predictions",
        json={"award_id": award.id, "predicted_player_id": player_a.id},
        headers=headers,
    )
    assert response.status_code == 409


def test_second_choice_replaces_first_instead_of_duplicating(client: TestClient, db_session: Session) -> None:
    headers = _register_and_login(client, "fan3@example.com")
    award = _create_award(db_session, AwardCategory.BEST_PLAYER, FUTURE_LOCK)
    player_a, player_b = _create_players(db_session, "SWP")

    first = client.post(
        "/award-predictions",
        json={"award_id": award.id, "predicted_player_id": player_a.id},
        headers=headers,
    )
    assert first.status_code == 200
    first_id = first.json()["id"]

    second = client.post(
        "/award-predictions",
        json={"award_id": award.id, "predicted_player_id": player_b.id},
        headers=headers,
    )
    assert second.status_code == 200
    assert second.json()["id"] == first_id
    assert second.json()["predicted_player_id"] == player_b.id

    listed = client.get("/award-predictions/me", headers=headers)
    assert len(listed.json()) == 1
    assert listed.json()[0]["predicted_player_id"] == player_b.id


def test_list_my_award_predictions(client: TestClient, db_session: Session) -> None:
    headers = _register_and_login(client, "fan4@example.com")
    award = _create_award(db_session, AwardCategory.TOP_SCORER, FUTURE_LOCK)
    player_a, _ = _create_players(db_session, "LST")

    client.post(
        "/award-predictions",
        json={"award_id": award.id, "predicted_player_id": player_a.id},
        headers=headers,
    )

    response = client.get("/award-predictions/me", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["award_id"] == award.id
