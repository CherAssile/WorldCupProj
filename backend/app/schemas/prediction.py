from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import PredictedWinnerSide


class PredictionCreate(BaseModel):
    match_id: int
    predicted_home_score: int = Field(ge=0)
    predicted_away_score: int = Field(ge=0)
    # Qualifié : par équipe (équipes connues) OU par côté (placeholders), jamais les deux.
    predicted_winner_team_id: int | None = None
    predicted_winner_side: PredictedWinnerSide | None = None


class PredictionUpdate(BaseModel):
    predicted_home_score: int = Field(ge=0)
    predicted_away_score: int = Field(ge=0)
    predicted_winner_team_id: int | None = None
    predicted_winner_side: PredictedWinnerSide | None = None


class PredictionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    match_id: int
    predicted_home_score: int
    predicted_away_score: int
    predicted_winner_team_id: int | None
    predicted_winner_side: PredictedWinnerSide | None
    created_at: datetime
    updated_at: datetime
