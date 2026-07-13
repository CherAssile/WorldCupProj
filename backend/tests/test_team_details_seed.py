from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.player import Player
from app.models.team import Team
from app.services import team_details_seed
from app.services.api_football_client import ApiFootballCoach, ApiFootballQuotaExceeded, ApiFootballSquadPlayer


class _FakeClient:
    def __init__(self) -> None:
        self.team_id_calls = 0
        self.coach_calls = 0
        self.squad_calls = 0

    def find_team_id(self, team_name: str) -> int:
        self.team_id_calls += 1
        return 1000 + self.team_id_calls

    def get_current_coach(self, api_team_id: int) -> ApiFootballCoach:
        self.coach_calls += 1
        return ApiFootballCoach(name="Coach Test", photo_url="https://example.com/coach.png")

    def get_squad(self, api_team_id: int) -> list[ApiFootballSquadPlayer]:
        self.squad_calls += 1
        return [
            ApiFootballSquadPlayer(api_player_id=api_team_id * 100 + 1, name="Joueur A", position="Attacker", shirt_number=9),
            ApiFootballSquadPlayer(api_player_id=api_team_id * 100 + 2, name="Joueur B", position="Midfielder", shirt_number=8),
        ]


class _QuotaExceededClient:
    def find_team_id(self, team_name: str) -> int:
        raise ApiFootballQuotaExceeded("quota atteint (simulé)")

    def get_current_coach(self, api_team_id: int) -> None:
        raise AssertionError("ne devrait jamais être appelé après un dépassement de quota")

    def get_squad(self, api_team_id: int) -> list:
        raise AssertionError("ne devrait jamais être appelé après un dépassement de quota")


class _QuotaAfterOneClient:
    def __init__(self) -> None:
        self.calls = 0

    def find_team_id(self, team_name: str) -> int:
        self.calls += 1
        if self.calls > 1:
            raise ApiFootballQuotaExceeded("quota atteint (simulé)")
        return 2000 + self.calls

    def get_current_coach(self, api_team_id: int) -> None:
        return None

    def get_squad(self, api_team_id: int) -> list:
        return []


def _create_team(db_session: Session, name: str, code: str) -> Team:
    team = Team(name=name, fifa_code=code)
    db_session.add(team)
    db_session.flush()
    return team


def _neutralize_ambient_teams(db_session: Session) -> None:
    """Le calendrier réel peut déjà contenir des équipes non résolues : run_seed les
    traiterait aussi, faussant les comptages de ce test. Leur donne un identifiant, un
    entraîneur et un joueur factices pour qu'elles soient ignorées (déjà résolues), sans
    jamais y toucher réellement (sans effet hors de la transaction de test)."""
    for team in db_session.execute(select(Team)).scalars():
        if team.api_football_team_id is None:
            team.api_football_team_id = -team.id
        if team.coach_name is None:
            team.coach_name = "(déjà résolu pour le test)"
        has_player = db_session.execute(select(Player).where(Player.team_id == team.id)).first()
        if has_player is None:
            db_session.add(Player(team_id=team.id, name=f"Filler {team.id}"))
    db_session.flush()


def test_seed_resolves_team_coach_and_squad(db_session: Session) -> None:
    _neutralize_ambient_teams(db_session)
    team = _create_team(db_session, "Testland", "TSL")
    client = _FakeClient()

    result = team_details_seed.run_seed(db_session, client=client)

    db_session.refresh(team)
    assert team.api_football_team_id is not None
    assert team.coach_name == "Coach Test"
    assert team.coach_photo_url == "https://example.com/coach.png"
    assert result.teams_resolved == 1
    assert result.coaches_updated == 1
    assert result.squads_imported == 1
    assert result.players_created == 2
    assert db_session.query(Player).filter(Player.team_id == team.id).count() == 2


def test_seed_is_idempotent(db_session: Session) -> None:
    team = _create_team(db_session, "Testland Two", "TS2")
    client = _FakeClient()

    team_details_seed.run_seed(db_session, client=client)
    calls_after_first = (client.team_id_calls, client.coach_calls, client.squad_calls)

    second_result = team_details_seed.run_seed(db_session, client=client)

    assert (client.team_id_calls, client.coach_calls, client.squad_calls) == calls_after_first
    assert (second_result.teams_resolved, second_result.coaches_updated, second_result.squads_imported) == (0, 0, 0)
    assert db_session.query(Player).filter(Player.team_id == team.id).count() == 2


def test_seed_stops_cleanly_on_quota_exceeded(db_session: Session) -> None:
    team = _create_team(db_session, "Testland Three", "TS3")
    client = _QuotaExceededClient()

    result = team_details_seed.run_seed(db_session, client=client)

    assert result.quota_exceeded is True
    assert result.teams_resolved == 0
    db_session.refresh(team)
    assert team.api_football_team_id is None  # rien écrit : aucune donnée partielle


def test_seed_preserves_progress_made_before_quota_exceeded(db_session: Session) -> None:
    _neutralize_ambient_teams(db_session)
    team_a = _create_team(db_session, "Alpha Land", "ALP")
    team_b = _create_team(db_session, "Beta Land", "BET")
    client = _QuotaAfterOneClient()

    result = team_details_seed.run_seed(db_session, client=client)

    assert result.quota_exceeded is True
    assert result.teams_resolved == 1

    db_session.refresh(team_a)
    db_session.refresh(team_b)
    resolved_flags = sorted([team_a.api_football_team_id is not None, team_b.api_football_team_id is not None])
    assert resolved_flags == [False, True]
