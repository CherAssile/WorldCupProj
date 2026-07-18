from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import AwardCategory
from app.schemas.player import PlayerRead


class AwardRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category: AwardCategory
    lock_at: datetime
    actual_player_id: int | None
    actual_player: PlayerRead | None
