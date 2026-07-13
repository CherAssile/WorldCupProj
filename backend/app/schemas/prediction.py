from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PredictionCreate(BaseModel):
    match_id: int
    predicted_home_score: int = Field(ge=0)
    predicted_away_score: int = Field(ge=0)
    predicted_winner_team_id: int | None = None


class PredictionUpdate(BaseModel):
    predicted_home_score: int = Field(ge=0)
    predicted_away_score: int = Field(ge=0)
    predicted_winner_team_id: int | None = None


class PredictionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    match_id: int
    predicted_home_score: int
    predicted_away_score: int
    predicted_winner_team_id: int | None
    created_at: datetime
    updated_at: datetime
