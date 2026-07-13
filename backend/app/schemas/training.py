from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import MatchPhase
from app.schemas.team import TeamRead


class TrainingSessionCreate(BaseModel):
    match_count: int = Field(default=5, ge=1, le=20)


class TrainingMatchRead(BaseModel):
    """Un match d'entraînement tel qu'exposé au navigateur : jamais son vrai score
    (home_score/away_score), tant que l'utilisateur n'a pas soumis son pronostic."""

    historical_match_id: int
    position: int
    home_team: TeamRead
    away_team: TeamRead
    edition_year: int
    phase: MatchPhase
    played_at: datetime


class TrainingSessionRead(BaseModel):
    id: int
    started_at: datetime
    completed_at: datetime | None
    matches: list[TrainingMatchRead]
