from pydantic import BaseModel, ConfigDict


class TeamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    fifa_code: str
    flag_url: str | None
    group_name: str | None
