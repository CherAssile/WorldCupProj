from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import func, select, text
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


def _shrink_historical_matches_pool(db_session: Session) -> int:
    """Ne supprime que les matchs non référencés par une session déjà jouée par un vrai
    utilisateur (contrainte de clé étrangère) : réduit le pool à un minimum contrôlable
    sans jamais toucher à de vraies données. Renvoie la taille du pool restant."""
    db_session.execute(
        text(
            "DELETE FROM historical_matches WHERE id NOT IN "
            "(SELECT DISTINCT historical_match_id FROM training_session_matches)"
        )
    )
    db_session.flush()
    return db_session.execute(select(func.count()).select_from(HistoricalMatch)).scalar_one()


def _get_user_id(db_session: Session, email: str) -> int:
    return db_session.execute(select(User).where(User.email == email)).scalar_one().id


def test_create_session_draws_requested_number_of_matches(db_session: Session) -> None:
    user = User(email="drawer@example.com", username="drawer", hashed_password="x")
    db_session.add(user)
    db_session.flush()

    session = training_crud.create_session(db_session, user_id=user.id, match_count=5)

    session_matches = training_crud.get_session_matches(db_session, session.id)
    drawn_ids = [sm.historical_match_id for sm in session_matches]
    assert len(drawn_ids) == 5
    assert len(set(drawn_ids)) == 5  # pas de doublon


def test_get_session_never_leaks_real_score_anywhere_in_response(
    client: TestClient, db_session: Session
) -> None:
    """Test obligatoire (anti-triche) : le vrai score ne doit apparaître dans AUCUN champ
    de la réponse GET tant que le pronostic n'a pas été soumis."""
    remaining = _shrink_historical_matches_pool(db_session)
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
    user_id = _get_user_id(db_session, "trainee@example.com")

    # Tire tout le pool restant (les quelques matchs déjà référencés par une vraie session
    # + notre match secret) : garantit son inclusion sans toucher aux données existantes.
    session = training_crud.create_session(db_session, user_id=user_id, match_count=remaining + 1)
    assert session.id not in (SECRET_HOME_SCORE, SECRET_AWAY_SCORE)

    response = client.get(f"/training/sessions/{session.id}", headers=headers)
    assert response.status_code == 200

    all_values = _flatten(response.json())
    assert SECRET_HOME_SCORE not in all_values
    assert SECRET_AWAY_SCORE not in all_values
    assert str(SECRET_HOME_SCORE) not in all_values
    assert str(SECRET_AWAY_SCORE) not in all_values

    # Ceinture et bretelles : aucun champ "*_score" ne doit même exister dans la réponse.
    raw_lower = response.text.lower()
    assert "home_score" not in raw_lower
    assert "away_score" not in raw_lower


def test_create_session_requires_auth(client: TestClient) -> None:
    response = client.post("/training/sessions", json={"match_count": 1})
    assert response.status_code == 401


def test_get_session_rejects_other_users_session(client: TestClient, db_session: Session) -> None:
    owner_headers = _register_and_login(client, "owner@example.com")
    created = client.post("/training/sessions", json={"match_count": 1}, headers=owner_headers)
    session_id = created.json()["id"]

    other_headers = _register_and_login(client, "intruder@example.com")
    response = client.get(f"/training/sessions/{session_id}", headers=other_headers)
    assert response.status_code == 404
