from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.models.enums import MatchPhase, SimulationMode
from app.schemas.team import TeamRead


class SimulationCreate(BaseModel):
    # realiste : matchs déjà joués gelés. alternatif : tout resimulé (cf. services/simulation.py).
    mode: Literal["realiste", "alternatif"] = "realiste"
    label: str | None = None


class SimulationMatchResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    phase: MatchPhase | None
    home_team: TeamRead
    away_team: TeamRead
    simulated_home_score: int
    simulated_away_score: int
    winner_team: TeamRead | None
    is_frozen_real_result: bool


class SimulationRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    mode: SimulationMode
    seed: str
    label: str | None
    created_at: datetime
    created_by_user_id: int


class SimulationRunDetailRead(SimulationRunRead):
    results: list[SimulationMatchResultRead]
