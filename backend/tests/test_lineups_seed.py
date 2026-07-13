from datetime import datetime, timedelta, timezone

from sqlalchemy import update
from sqlalchemy.orm import Session

from app.models.enums import MatchPhase, MatchStatus
from app.models.lineup import Lineup
from app.models.match import Match
from app.models.team import Team
from app.services import lineups_seed
from app.services.api_football_client import (
    ApiFootballQuotaExceeded,
    ApiFootballTeamLineup,
    LineupPlayerEntry,
)


class _FakeClientNoLineupsYet:
    def find_fixture_id(self, api_team_id: int, date: str, season: int) -> int:
        return 999

    def get_lineups(self, api_fixture_id: int) -> list:
        return []  # cas normal : pas encore publiées


class _FakeClientWithLineups:
    def __init__(self) -> None:
        self.lineup_calls = 0

    def find_fixture_id(self, api_team_id: int, date: str, season: int) -> int:
        return 999

    def get_lineups(self, api_fixture_id: int) -> list[ApiFootballTeamLineup]:
        self.lineup_calls += 1
        return [
            ApiFootballTeamLineup(
                api_team_id=501,
                formation="4-3-3",
                players=[
                    LineupPlayerEntry(api_player_id=1, name="Joueur A", shirt_number=10, position="F", is_starter=True)
                ],
            ),
            ApiFootballTeamLineup(
                api_team_id=502,
                formation="4-4-2",
                players=[
                    LineupPlayerEntry(api_player_id=2, name="Joueur B", shirt_number=5, position="D", is_starter=True)
                ],
            ),
        ]


class _FakeClientQuotaExceeded:
    def find_fixture_id(self, api_team_id: int, date: str, season: int) -> int:
        raise ApiFootballQuotaExceeded("quota atteint (simulé)")

    def get_lineups(self, api_fixture_id: int) -> list:
        raise AssertionError("ne devrait jamais être appelé après un dépassement de quota")


def _clear_resolved_team_ids(db_session: Session) -> None:
    """Le calendrier réel peut désormais contenir des équipes déjà résolues côté
    API-Football (services/team_details_seed.py a réellement tourné) : lineups_seed les
    traiterait aussi, faussant les comptages de ce test. Repart d'équipes non résolues,
    sans effet hors de la transaction de test. À appeler AVANT de créer les équipes
    propres au test (sans quoi leurs identifiants explicites seraient aussi effacés)."""
    db_session.execute(update(Team).values(api_football_team_id=None))
    db_session.flush()


def _create_match_with_resolved_teams(
    db_session: Session, prefix: str, api_home_id: int, api_away_id: int, kickoff_at: datetime
) -> tuple[Match, Team, Team]:
    code = prefix[:2].upper()
    home = Team(name=f"{prefix} Home", fifa_code=f"{code}H", api_football_team_id=api_home_id)
    away = Team(name=f"{prefix} Away", fifa_code=f"{code}A", api_football_team_id=api_away_id)
    db_session.add_all([home, away])
    db_session.flush()

    match = Match(
        home_team_id=home.id,
        away_team_id=away.id,
        phase=MatchPhase.GROUP,
        status=MatchStatus.SCHEDULED,
        kickoff_at=kickoff_at,
    )
    db_session.add(match)
    db_session.flush()
    return match, home, away


def test_lineups_not_yet_announced_handled_without_error(db_session: Session) -> None:
    """Test obligatoire : l'absence de composition sur un match à venir est un cas
    normal, jamais une erreur."""
    _clear_resolved_team_ids(db_session)
    match, _home, _away = _create_match_with_resolved_teams(
        db_session, "SOON", 501, 502, datetime.now(timezone.utc) + timedelta(hours=2)
    )
    client = _FakeClientNoLineupsYet()

    result = lineups_seed.run_seed(db_session, client=client)

    assert result.matches_not_yet_announced == 1
    assert result.lineups_imported == 0
    assert db_session.query(Lineup).filter(Lineup.match_id == match.id).count() == 0


def test_lineups_import_and_idempotent(db_session: Session) -> None:
    _clear_resolved_team_ids(db_session)
    match, _home, _away = _create_match_with_resolved_teams(
        db_session, "DONE", 501, 502, datetime.now(timezone.utc) - timedelta(days=1)
    )
    match.home_score = 1
    match.away_score = 0
    db_session.commit()

    client = _FakeClientWithLineups()
    first = lineups_seed.run_seed(db_session, client=client)
    assert first.lineups_imported == 1
    assert client.lineup_calls == 1
    assert db_session.query(Lineup).filter(Lineup.match_id == match.id).count() == 2

    second = lineups_seed.run_seed(db_session, client=client)
    assert second.lineups_imported == 0
    assert client.lineup_calls == 1  # déjà complet : pas re-appelé (idempotent)
    assert db_session.query(Lineup).filter(Lineup.match_id == match.id).count() == 2


def test_lineups_seed_stops_cleanly_on_quota_exceeded(db_session: Session) -> None:
    match, _home, _away = _create_match_with_resolved_teams(
        db_session, "QUO", 601, 602, datetime.now(timezone.utc) + timedelta(hours=1)
    )
    client = _FakeClientQuotaExceeded()

    result = lineups_seed.run_seed(db_session, client=client)

    assert result.quota_exceeded is True
    assert result.lineups_imported == 0
    assert db_session.query(Lineup).filter(Lineup.match_id == match.id).count() == 0
