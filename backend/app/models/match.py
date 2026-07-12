from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import MatchPhase, MatchStatus

if TYPE_CHECKING:
    from app.models.ai_prediction import AiPrediction
    from app.models.prediction import Prediction
    from app.models.team import Team


class Match(Base):
    """Match du tournoi en cours (mode compétitif). Verrouillé côté serveur à kickoff_at."""

    __tablename__ = "matches"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Nullable : un match de phase finale existe (date, terrain) avant que ses deux
    # participants ne soient connus (ex. la finale, tant que les demies ne sont pas jouées).
    home_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    away_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    # Référence l'équipe non encore résolue (ex. "W101" = vainqueur du match 101),
    # le temps que home_team_id/away_team_id puissent être renseignés.
    home_placeholder: Mapped[str | None] = mapped_column(String(50), nullable=True)
    away_placeholder: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # Numéro de match côté source : sert à résoudre les placeholders et à dédoublonner
    # les matchs de phase finale de façon stable, indépendamment des équipes.
    num: Mapped[int | None] = mapped_column(Integer, nullable=True, unique=True)
    phase: Mapped[MatchPhase] = mapped_column(SqlEnum(MatchPhase, name="match_phase"), nullable=False)
    status: Mapped[MatchStatus] = mapped_column(
        SqlEnum(MatchStatus, name="match_status"), default=MatchStatus.SCHEDULED, nullable=False
    )
    kickoff_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    home_score: Mapped[int | None] = mapped_column(nullable=True)
    away_score: Mapped[int | None] = mapped_column(nullable=True)

    home_team: Mapped[Optional["Team"]] = relationship(foreign_keys=[home_team_id], back_populates="home_matches")
    away_team: Mapped[Optional["Team"]] = relationship(foreign_keys=[away_team_id], back_populates="away_matches")
    predictions: Mapped[list["Prediction"]] = relationship(back_populates="match")
    ai_prediction: Mapped[Optional["AiPrediction"]] = relationship(back_populates="match")
