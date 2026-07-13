import re
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.crud import training as training_crud
from app.models.enums import MatchPhase
from app.models.historical_match import HistoricalMatch
from app.models.team import Team
from app.models.user import User

PASSWORD = "correcthorsebattery"
SECRET_HOME_SCORE = 71
SECRET_AWAY_SCORE = 68


def _register_and_login(client: TestClient, email: str) -> dict[str, str]:
    username = email.split("@")[0]
    client.post("/auth/register", json={"email": email, "username": username, "password": PASSWORD})
    login = client.post("/auth/login", data={"username": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _flatten(value: object) -> list[object]:
    """Aplatit une structure JSON (dict/list imbriqués) en la liste de toutes ses valeurs
    scalaires, pour pouvoir vérifier qu'aucune ne correspond au vrai score, où qu'elle soit."""
    if isinstance(value, dict):
        flattened: list[object] = []
        for v in value.values():
            flattened.extend(_flatten(v))
        return flattened
    if isinstance(value, list):
        flattened = []
        for item in value:
            flattened.extend(_flatten(item))
        return flattened
    return [value]


def _clear_historical_matches(db_session: Session) -> None:
    """Le stock réel (557 matchs) fausserait le contrôle du tirage dans ces tests.
    Sans effet hors de la transaction de test."""
    db_session.query(HistoricalMatch).delete()
    db_session.flush()


def test_create_session_draws_requested_number_of_matches(db_session: Session) -> None:
    _clear_historical_matches(db_session)
    user = User(email="drawer@example.com", username="drawer", hashed_password="x")
    home = Team(name="Draw Home", fifa_code="DRH")
    away = Team(name="Draw Away", fifa_code="DRA")
    db_session.add_all([user, home, away])
    db_session.flush()

    pool_ids = set()
    for i in range(8):
        match = HistoricalMatch(
            home_team_id=home.id,
            away_team_id=away.id,
            edition_year=1990 + i,
            phase=MatchPhase.GROUP,
            played_at=datetime(1990 + i, 6, 1, tzinfo=timezone.utc),
            home_score=i,
            away_score=i,
        )
        db_session.add(match)
        db_session.flush()
        pool_ids.add(match.id)

    session = training_crud.create_session(db_session, user_id=user.id, match_count=5)

    session_matches = training_crud.get_session_matches(db_session, session.id)
    drawn_ids = [sm.historical_match_id for sm in session_matches]
    assert len(drawn_ids) == 5
    assert len(set(drawn_ids)) == 5  # pas de doublon
    assert set(drawn_ids) <= pool_ids


def test_get_session_never_leaks_real_score_anywhere_in_response(
    client: TestClient, db_session: Session
) -> None:
    """Test obligatoire (anti-triche) : le vrai score ne doit apparaître dans AUCUN champ
    de la réponse GET tant que le pronostic n'a pas été soumis."""
    _clear_historical_matches(db_session)
    home = Team(name="Secret Home", fifa_code="SCH")
    away = Team(name="Secret Away", fifa_code="SCA")
    db_session.add_all([home, away])
    db_session.flush()

    match = HistoricalMatch(
        home_team_id=home.id,
        away_team_id=away.id,
        edition_year=1994,
        phase=MatchPhase.GROUP,
        played_at=datetime(1994, 6, 20, tzinfo=timezone.utc),
        home_score=SECRET_HOME_SCORE,
        away_score=SECRET_AWAY_SCORE,
    )
    db_session.add(match)
    db_session.flush()

    # Précondition : aucun identifiant du jeu de données ne coïncide par hasard avec le
    # vrai score -- sinon le test pourrait passer par accident (faux négatif).
    assert match.id not in (SECRET_HOME_SCORE, SECRET_AWAY_SCORE)
    assert home.id not in (SECRET_HOME_SCORE, SECRET_AWAY_SCORE)
    assert away.id not in (SECRET_HOME_SCORE, SECRET_AWAY_SCORE)

    headers = _register_and_login(client, "trainee@example.com")
    created = client.post("/training/sessions", json={"match_count": 1}, headers=headers)
    assert created.status_code == 201
    session_id = created.json()["id"]
    assert session_id not in (SECRET_HOME_SCORE, SECRET_AWAY_SCORE)

    response = client.get(f"/training/sessions/{session_id}", headers=headers)
    assert response.status_code == 200

    all_values = _flatten(response.json())
    assert SECRET_HOME_SCORE not in all_values
    assert SECRET_AWAY_SCORE not in all_values
    assert str(SECRET_HOME_SCORE) not in all_values
    assert str(SECRET_AWAY_SCORE) not in all_values

    # Ceinture et bretelles : aucun champ "*_score" ne doit même exister dans la réponse,
    # et le score en clair n'apparaît nulle part dans le texte brut renvoyé -- en tant que
    # nombre isolé (bornes \D pour ne pas confondre "68" avec un id comme 680 ou 168).
    raw_lower = response.text.lower()
    assert "home_score" not in raw_lower
    assert "away_score" not in raw_lower
    assert re.search(rf"(?<!\d){SECRET_HOME_SCORE}(?!\d)", response.text) is None
    assert re.search(rf"(?<!\d){SECRET_AWAY_SCORE}(?!\d)", response.text) is None


def test_create_session_requires_auth(client: TestClient) -> None:
    response = client.post("/training/sessions", json={"match_count": 1})
    assert response.status_code == 401


def test_get_session_rejects_other_users_session(client: TestClient, db_session: Session) -> None:
    _clear_historical_matches(db_session)
    home = Team(name="Owner Home", fifa_code="OWH")
    away = Team(name="Owner Away", fifa_code="OWA")
    db_session.add_all([home, away])
    db_session.flush()
    db_session.add(
        HistoricalMatch(
            home_team_id=home.id,
            away_team_id=away.id,
            edition_year=2002,
            phase=MatchPhase.GROUP,
            played_at=datetime(2002, 6, 1, tzinfo=timezone.utc),
            home_score=1,
            away_score=0,
        )
    )
    db_session.flush()

    owner_headers = _register_and_login(client, "owner@example.com")
    created = client.post("/training/sessions", json={"match_count": 1}, headers=owner_headers)
    session_id = created.json()["id"]

    other_headers = _register_and_login(client, "intruder@example.com")
    response = client.get(f"/training/sessions/{session_id}", headers=other_headers)
    assert response.status_code == 404
