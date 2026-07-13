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


class TrainingPredictionCreate(BaseModel):
    predicted_home_score: int = Field(ge=0)
    predicted_away_score: int = Field(ge=0)


class TrainingMatchResultRead(BaseModel):
    """Duel utilisateur contre IA pour un match : le vrai score n'apparaît ici qu'une fois
    le pronostic soumis, jamais avant (cf. TrainingMatchRead)."""

    historical_match_id: int
    home_team: TeamRead
    away_team: TeamRead
    home_score: int
    away_score: int
    predicted_home_score: int
    predicted_away_score: int
    ai_predicted_home_score: int
    ai_predicted_away_score: int
    user_points: int
    ai_points: int


class TrainingSessionResultsRead(BaseModel):
    session_id: int
    completed: bool
    results: list[TrainingMatchResultRead]
    user_total_points: int
    ai_total_points: int
