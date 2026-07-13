from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import MatchPhase

if TYPE_CHECKING:
    from app.models.team import Team
    from app.models.training_prediction import TrainingPrediction


class HistoricalMatch(Base):
    """Match déjà joué au résultat connu (Mondial en cours ou éditions passées).

    Réservoir de données pour le mode entraînement, isolé de `matches`.
    """

    __tablename__ = "historical_matches"

    id: Mapped[int] = mapped_column(primary_key=True)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    edition_year: Mapped[int] = mapped_column(Integer, nullable=False)
    phase: Mapped[MatchPhase] = mapped_column(SqlEnum(MatchPhase, name="match_phase"), nullable=False)
    played_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    home_score: Mapped[int] = mapped_column(nullable=False)
    away_score: Mapped[int] = mapped_column(nullable=False)

    home_team: Mapped["Team"] = relationship(
        foreign_keys=[home_team_id], back_populates="home_historical_matches"
    )
    away_team: Mapped["Team"] = relationship(
        foreign_keys=[away_team_id], back_populates="away_historical_matches"
    )
    training_predictions: Mapped[list["TrainingPrediction"]] = relationship(back_populates="historical_match")
