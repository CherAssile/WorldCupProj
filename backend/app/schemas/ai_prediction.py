from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AiPredictionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    match_id: int
    predicted_home_score: int
    predicted_away_score: int
    created_at: datetime


class AiPredictionGenerationResult(BaseModel):
    created: int
    updated: int
    removed_stale: int
    skipped_unresolved_teams: int
    skipped_ai_unavailable: int
