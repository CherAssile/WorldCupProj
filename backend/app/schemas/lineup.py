from pydantic import BaseModel

from app.schemas.team import TeamRead


class LineupPlayerRead(BaseModel):
    player_id: int
    name: str
    position: str | None
    shirt_number: int | None
    is_starter: bool


class TeamLineupRead(BaseModel):
    team: TeamRead
    formation: str | None
    players: list[LineupPlayerRead]


class MatchLineupsRead(BaseModel):
    """Les compositions ne sortent qu'environ 1h avant le coup d'envoi : `available=False`
    est un état NORMAL (jamais une erreur HTTP) tant qu'elles ne sont pas annoncées."""

    match_id: int
    available: bool
    message: str | None = None
    home: TeamLineupRead | None = None
    away: TeamLineupRead | None = None
