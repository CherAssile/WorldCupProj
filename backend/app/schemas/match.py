from datetime import datetime

from pydantic import BaseModel, ConfigDict, computed_field

from app.models.enums import MatchPhase, MatchStatus
from app.schemas.team import TeamRead
from app.services.placeholders import placeholder_label


class MatchRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    num: int | None
    phase: MatchPhase
    status: MatchStatus
    kickoff_at: datetime
    home_team: TeamRead | None
    away_team: TeamRead | None
    home_placeholder: str | None
    away_placeholder: str | None
    home_score: int | None
    away_score: int | None
    extra_time_home_score: int | None
    extra_time_away_score: int | None
    penalties_home_score: int | None
    penalties_away_score: int | None
    winner_team: TeamRead | None

    # Libellés résolus côté serveur (« Vainqueur du match 101 ») : le frontend ne décode
    # jamais les codes bruts W/L lui-même.
    @computed_field  # type: ignore[prop-decorator]
    @property
    def home_placeholder_label(self) -> str | None:
        return placeholder_label(self.home_placeholder)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def away_placeholder_label(self) -> str | None:
        return placeholder_label(self.away_placeholder)


class MatchPhaseGroup(BaseModel):
    phase: MatchPhase
    matches: list[MatchRead]
