from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import MatchPhase, MatchStatus
from app.schemas.team import TeamRead


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
    # Libellés résolus côté serveur, d'un niveau : « France ou Espagne » quand la demie
    # référencée est connue, sinon repli « Vainqueur du match 101 ». Version courte pour
    # les emplacements contraints en largeur (« FRA/ESP »). Renseignés par le router, qui
    # dispose de l'ensemble des matchs pour remonter la chaîne des placeholders ; None
    # hors placeholder.
    home_placeholder_label: str | None = None
    away_placeholder_label: str | None = None
    home_placeholder_label_short: str | None = None
    away_placeholder_label_short: str | None = None
    home_score: int | None
    away_score: int | None
    extra_time_home_score: int | None
    extra_time_away_score: int | None
    penalties_home_score: int | None
    penalties_away_score: int | None
    winner_team: TeamRead | None


class MatchPhaseGroup(BaseModel):
    phase: MatchPhase
    matches: list[MatchRead]
