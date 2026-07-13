from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AwardPredictionCreate(BaseModel):
    award_id: int
    predicted_player_id: int


class AwardPredictionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    award_id: int
    predicted_player_id: int
    created_at: datetime
