from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import MatchPhase, MatchStatus
from app.models.match import Match
from app.models.team import Team


def test_matches_grouped_by_phase_structure(client: TestClient) -> None:
    """/matches renvoie toujours une entrée par phase du tournoi, dans l'ordre canonique.

    N'suppose pas une base vide : le calendrier réel peut déjà être alimenté (services/seed.py).
    """
    response = client.get("/matches")
    assert response.status_code == 200

    body = response.json()
    assert [group["phase"] for group in body] == [phase.value for phase in MatchPhase]
    assert all(isinstance(group["matches"], list) for group in body)


def test_matches_grouped_by_phase_with_data(client: TestClient, db_session: Session) -> None:
    """Un match créé dans une phase donnée apparaît dans le bon groupe, avec les équipes imbriquées."""
    home = Team(name="Testland Alpha", fifa_code="TLA")
    away = Team(name="Testland Beta", fifa_code="TLB")
    db_session.add_all([home, away])
    db_session.flush()

    match = Match(
        home_team_id=home.id,
        away_team_id=away.id,
        phase=MatchPhase.QUARTER_FINAL,
        status=MatchStatus.SCHEDULED,
        kickoff_at=datetime(2026, 7, 1, 18, 0, tzinfo=timezone.utc),
    )
    db_session.add(match)
    db_session.commit()

    response = client.get("/matches")
    assert response.status_code == 200

    group_by_phase = {group["phase"]: group["matches"] for group in response.json()}
    quarter_final_matches = group_by_phase["quarter_final"]

    created = next(m for m in quarter_final_matches if m["home_team"]["name"] == "Testland Alpha")
    assert created["away_team"]["name"] == "Testland Beta"
