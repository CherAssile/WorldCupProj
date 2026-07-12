from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import MatchPhase, MatchStatus
from app.schemas.team import TeamRead


class MatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    num: int | None
    phase: MatchPhase
    status: MatchStatus
    kickoff_at: datetime
    home_team: TeamRead | None
    away_team: TeamRead | None
    home_placeholder: str | None
    away_placeholder: str | None
    home_score: int | None
    away_score: int | None
    extra_time_home_score: int | None
    extra_time_away_score: int | None
    penalties_home_score: int | None
    penalties_away_score: int | None
    winner_team: TeamRead | None


class MatchPhaseGroup(BaseModel):
    phase: MatchPhase
    matches: list[MatchRead]
