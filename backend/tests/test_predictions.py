from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import MatchPhase, MatchStatus
from app.models.match import Match
from app.models.team import Team

PASSWORD = "correcthorsebattery"
FUTURE_KICKOFF = datetime.now(timezone.utc) + timedelta(days=1)
PAST_KICKOFF = datetime.now(timezone.utc) - timedelta(days=1)


def _register_and_login(client: TestClient, email: str) -> dict[str, str]:
    username = email.split("@")[0]
    client.post("/auth/register", json={"email": email, "username": username, "password": PASSWORD})
    login = client.post("/auth/login", data={"username": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create_teams(db_session: Session, prefix: str) -> tuple[Team, Team, Team]:
    code = prefix[:2].upper()
    home = Team(name=f"{prefix} Home", fifa_code=f"{code}H")
    away = Team(name=f"{prefix} Away", fifa_code=f"{code}A")
    other = Team(name=f"{prefix} Other", fifa_code=f"{code}O")
    db_session.add_all([home, away, other])
    db_session.flush()
    return home, away, other


def _create_match(db_session: Session, home: Team, away: Team, phase: MatchPhase, kickoff_at: datetime) -> Match:
    match = Match(
        home_team_id=home.id,
        away_team_id=away.id,
        phase=phase,
        status=MatchStatus.SCHEDULED,
        kickoff_at=kickoff_at,
    )
    db_session.add(match)
    db_session.flush()
    return match


def test_create_prediction_before_kickoff_succeeds(client: TestClient, db_session: Session) -> None:
    headers = _register_and_login(client, "joueur1@example.com")
    home, away, _ = _create_teams(db_session, "GRP")
    match = _create_match(db_session, home, away, MatchPhase.GROUP, FUTURE_KICKOFF)

    response = client.post(
        "/predictions",
        json={"match_id": match.id, "predicted_home_score": 2, "predicted_away_score": 1},
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["predicted_home_score"] == 2
    assert body["predicted_away_score"] == 1
    assert body["predicted_winner_team_id"] is None


def test_update_after_kickoff_rejected(client: TestClient, db_session: Session) -> None:
    headers = _register_and_login(client, "joueur2@example.com")
    home, away, _ = _create_teams(db_session, "UPD")
    match = _create_match(db_session, home, away, MatchPhase.GROUP, FUTURE_KICKOFF)

    created = client.post(
        "/predictions",
        json={"match_id": match.id, "predicted_home_score": 1, "predicted_away_score": 1},
        headers=headers,
    )
    assert created.status_code == 201
    prediction_id = created.json()["id"]

    match.kickoff_at = PAST_KICKOFF
    db_session.commit()

    response = client.put(
        f"/predictions/{prediction_id}",
        json={"predicted_home_score": 2, "predicted_away_score": 0},
        headers=headers,
    )
    assert response.status_code == 409


def test_create_prediction_after_kickoff_rejected(client: TestClient, db_session: Session) -> None:
    """Verrouillage côté serveur dès la création, pas seulement à la modification : le
    coup d'envoi est déjà passé au moment même de la tentative de pronostic."""
    headers = _register_and_login(client, "joueur2b@example.com")
    home, away, _ = _create_teams(db_session, "PST")
    match = _create_match(db_session, home, away, MatchPhase.GROUP, PAST_KICKOFF)

    response = client.post(
        "/predictions",
        json={"match_id": match.id, "predicted_home_score": 1, "predicted_away_score": 1},
        headers=headers,
    )
    assert response.status_code == 409


def test_update_other_users_prediction_rejected(client: TestClient, db_session: Session) -> None:
    """Un pronostic n'appartient qu'à son auteur : un autre utilisateur authentifié ne doit
    jamais pouvoir le modifier (404, pas 403, pour ne pas même révéler qu'il existe)."""
    owner_headers = _register_and_login(client, "owner-pred@example.com")
    home, away, _ = _create_teams(db_session, "OWN")
    match = _create_match(db_session, home, away, MatchPhase.GROUP, FUTURE_KICKOFF)

    created = client.post(
        "/predictions",
        json={"match_id": match.id, "predicted_home_score": 1, "predicted_away_score": 1},
        headers=owner_headers,
    )
    assert created.status_code == 201
    prediction_id = created.json()["id"]

    intruder_headers = _register_and_login(client, "intruder-pred@example.com")
    response = client.put(
        f"/predictions/{prediction_id}",
        json={"predicted_home_score": 5, "predicted_away_score": 0},
        headers=intruder_headers,
    )
    assert response.status_code == 404


def test_double_prediction_same_match_rejected(client: TestClient, db_session: Session) -> None:
    headers = _register_and_login(client, "joueur3@example.com")
    home, away, _ = _create_teams(db_session, "DBL")
    match = _create_match(db_session, home, away, MatchPhase.GROUP, FUTURE_KICKOFF)
    payload = {"match_id": match.id, "predicted_home_score": 1, "predicted_away_score": 0}

    first = client.post("/predictions", json=payload, headers=headers)
    assert first.status_code == 201

    second = client.post("/predictions", json=payload, headers=headers)
    assert second.status_code == 409


def test_predicted_winner_rejected_on_group_match(client: TestClient, db_session: Session) -> None:
    headers = _register_and_login(client, "joueur4@example.com")
    home, away, _ = _create_teams(db_session, "GRW")
    match = _create_match(db_session, home, away, MatchPhase.GROUP, FUTURE_KICKOFF)

    response = client.post(
        "/predictions",
        json={
            "match_id": match.id,
            "predicted_home_score": 1,
            "predicted_away_score": 1,
            "predicted_winner_team_id": home.id,
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_predicted_winner_required_on_knockout_match(client: TestClient, db_session: Session) -> None:
    headers = _register_and_login(client, "joueur5@example.com")
    home, away, _ = _create_teams(db_session, "KOK")
    match = _create_match(db_session, home, away, MatchPhase.QUARTER_FINAL, FUTURE_KICKOFF)

    response = client.post(
        "/predictions",
        json={"match_id": match.id, "predicted_home_score": 1, "predicted_away_score": 1},
        headers=headers,
    )
    assert response.status_code == 422


def test_predicted_winner_must_be_one_of_match_teams(client: TestClient, db_session: Session) -> None:
    headers = _register_and_login(client, "joueur6@example.com")
    home, away, other = _create_teams(db_session, "OTR")
    match = _create_match(db_session, home, away, MatchPhase.QUARTER_FINAL, FUTURE_KICKOFF)

    response = client.post(
        "/predictions",
        json={
            "match_id": match.id,
            "predicted_home_score": 1,
            "predicted_away_score": 1,
            "predicted_winner_team_id": other.id,
        },
        headers=headers,
    )
    assert response.status_code == 422


def _create_placeholder_final(db_session: Session, kickoff_at: datetime) -> Match:
    match = Match(
        home_team_id=None,
        away_team_id=None,
        home_placeholder="W101",
        away_placeholder="W102",
        phase=MatchPhase.FINAL,
        status=MatchStatus.SCHEDULED,
        kickoff_at=kickoff_at,
    )
    db_session.add(match)
    db_session.flush()
    return match


def test_full_prediction_on_unresolved_final_accepted(client: TestClient, db_session: Session) -> None:
    """« Le vainqueur de la demi-finale 1 gagne la finale 2-1 » est un pronostic parfaitement
    défini : un match à placeholders est pronostiquable, le qualifié s'exprime par le côté."""
    match = _create_placeholder_final(db_session, FUTURE_KICKOFF)

    headers = _register_and_login(client, "joueur7@example.com")
    response = client.post(
        "/predictions",
        json={
            "match_id": match.id,
            "predicted_home_score": 2,
            "predicted_away_score": 1,
            "predicted_winner_side": "home",
        },
        headers=headers,
    )
    assert response.status_code == 201
    body = response.json()
    assert body["predicted_winner_side"] == "home"
    assert body["predicted_winner_team_id"] is None


def test_qualifier_still_required_on_placeholder_knockout(client: TestClient, db_session: Session) -> None:
    """Le qualifié reste obligatoire en phase finale, placeholders ou pas."""
    match = _create_placeholder_final(db_session, FUTURE_KICKOFF)

    headers = _register_and_login(client, "joueur7b@example.com")
    response = client.post(
        "/predictions",
        json={"match_id": match.id, "predicted_home_score": 1, "predicted_away_score": 1},
        headers=headers,
    )
    assert response.status_code == 422


def test_both_qualifier_forms_together_rejected(client: TestClient, db_session: Session) -> None:
    """predicted_winner_team_id et predicted_winner_side sont mutuellement exclusifs."""
    headers = _register_and_login(client, "joueur7c@example.com")
    home, away, _ = _create_teams(db_session, "XOR")
    match = _create_match(db_session, home, away, MatchPhase.SEMI_FINAL, FUTURE_KICKOFF)

    response = client.post(
        "/predictions",
        json={
            "match_id": match.id,
            "predicted_home_score": 1,
            "predicted_away_score": 0,
            "predicted_winner_team_id": home.id,
            "predicted_winner_side": "home",
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_side_rejected_when_teams_are_known(client: TestClient, db_session: Session) -> None:
    """Équipes connues → le qualifié se désigne par équipe, pas par côté."""
    headers = _register_and_login(client, "joueur7d@example.com")
    home, away, _ = _create_teams(db_session, "SDK")
    match = _create_match(db_session, home, away, MatchPhase.SEMI_FINAL, FUTURE_KICKOFF)

    response = client.post(
        "/predictions",
        json={
            "match_id": match.id,
            "predicted_home_score": 1,
            "predicted_away_score": 0,
            "predicted_winner_side": "home",
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_team_id_rejected_when_teams_unresolved(client: TestClient, db_session: Session) -> None:
    """Équipes inconnues → impossible de désigner une équipe précise comme qualifiée."""
    match = _create_placeholder_final(db_session, FUTURE_KICKOFF)
    headers = _register_and_login(client, "joueur7e@example.com")
    _, _, other = _create_teams(db_session, "TIU")

    response = client.post(
        "/predictions",
        json={
            "match_id": match.id,
            "predicted_home_score": 1,
            "predicted_away_score": 0,
            "predicted_winner_team_id": other.id,
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_side_rejected_on_group_match(client: TestClient, db_session: Session) -> None:
    headers = _register_and_login(client, "joueur7f@example.com")
    home, away, _ = _create_teams(db_session, "SGR")
    match = _create_match(db_session, home, away, MatchPhase.GROUP, FUTURE_KICKOFF)

    response = client.post(
        "/predictions",
        json={
            "match_id": match.id,
            "predicted_home_score": 1,
            "predicted_away_score": 1,
            "predicted_winner_side": "away",
        },
        headers=headers,
    )
    assert response.status_code == 422


def test_kickoff_lock_still_applies_on_placeholder_match(client: TestClient, db_session: Session) -> None:
    """Le verrouillage au coup d'envoi reste strictement inchangé, placeholders compris."""
    match = _create_placeholder_final(db_session, PAST_KICKOFF)

    headers = _register_and_login(client, "joueur7g@example.com")
    response = client.post(
        "/predictions",
        json={
            "match_id": match.id,
            "predicted_home_score": 2,
            "predicted_away_score": 1,
            "predicted_winner_side": "home",
        },
        headers=headers,
    )
    assert response.status_code == 409


def test_list_my_predictions(client: TestClient, db_session: Session) -> None:
    headers = _register_and_login(client, "joueur8@example.com")
    home, away, _ = _create_teams(db_session, "LST")
    match = _create_match(db_session, home, away, MatchPhase.GROUP, FUTURE_KICKOFF)
    client.post(
        "/predictions",
        json={"match_id": match.id, "predicted_home_score": 3, "predicted_away_score": 2},
        headers=headers,
    )

    response = client.get("/predictions/me", headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["match_id"] == match.id
