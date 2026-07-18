from pydantic import BaseModel, ConfigDict

from app.schemas.team import TeamRead


class PlayerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    position: str | None
    shirt_number: int | None
    team: TeamRead


class TeamPlayersGroup(BaseModel):
    team: TeamRead
    players: list[PlayerRead]
