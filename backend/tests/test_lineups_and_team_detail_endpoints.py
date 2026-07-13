from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.enums import MatchPhase, MatchStatus
from app.models.lineup import Lineup
from app.models.lineup_player import LineupPlayer
from app.models.match import Match
from app.models.player import Player
from app.models.team import Team


def _create_team(db_session: Session, prefix: str) -> Team:
    team = Team(
        name=f"{prefix} Team",
        fifa_code=f"{prefix[:3].upper()}",
        coach_name="Coach Test",
        coach_photo_url="https://example.com/coach.png",
    )
    db_session.add(team)
    db_session.flush()
    return team


def test_get_team_includes_coach(client: TestClient, db_session: Session) -> None:
    team = _create_team(db_session, "COA")

    response = client.get(f"/teams/{team.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["coach_name"] == "Coach Test"
    assert body["coach_photo_url"] == "https://example.com/coach.png"


def test_get_team_not_found(client: TestClient) -> None:
    response = client.get("/teams/999999999")
    assert response.status_code == 404


def test_get_match_lineups_not_yet_announced_is_not_an_error(client: TestClient, db_session: Session) -> None:
    home = Team(name="LinA Home", fifa_code="LAH")
    away = Team(name="LinA Away", fifa_code="LAA")
    db_session.add_all([home, away])
    db_session.flush()
    match = Match(
        home_team_id=home.id,
        away_team_id=away.id,
        phase=MatchPhase.GROUP,
        status=MatchStatus.SCHEDULED,
        kickoff_at=datetime.now(timezone.utc) + timedelta(hours=2),
    )
    db_session.add(match)
    db_session.flush()

    response = client.get(f"/matches/{match.id}/lineups")
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["home"] is None
    assert body["away"] is None


def test_get_match_lineups_returns_players_when_available(client: TestClient, db_session: Session) -> None:
    home = Team(name="LinB Home", fifa_code="LBH")
    away = Team(name="LinB Away", fifa_code="LBA")
    db_session.add_all([home, away])
    db_session.flush()
    match = Match(
        home_team_id=home.id,
        away_team_id=away.id,
        phase=MatchPhase.GROUP,
        status=MatchStatus.SCHEDULED,
        kickoff_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    db_session.add(match)
    db_session.flush()

    player = Player(team_id=home.id, name="Joueur Titulaire", position="F", shirt_number=9)
    db_session.add(player)
    db_session.flush()

    lineup = Lineup(match_id=match.id, team_id=home.id, formation="4-3-3")
    db_session.add(lineup)
    db_session.flush()
    db_session.add(
        LineupPlayer(lineup_id=lineup.id, player_id=player.id, position="F", shirt_number=9, is_starter=True)
    )
    db_session.commit()

    response = client.get(f"/matches/{match.id}/lineups")
    assert response.status_code == 200
    body = response.json()
    assert body["available"] is True
    assert body["home"]["formation"] == "4-3-3"
    assert body["home"]["players"][0]["name"] == "Joueur Titulaire"
    assert body["away"] is None


def test_get_match_lineups_match_not_found(client: TestClient) -> None:
    response = client.get("/matches/999999999/lineups")
    assert response.status_code == 404
