from pydantic import BaseModel, ConfigDict


class LeaderboardEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    rank: int
    user_id: int
    username: str
    is_ai: bool
    total_points: int
    exact_scores_count: int


class LeaderboardRecomputeResult(BaseModel):
    users_ranked: int
