from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import PredictedWinnerSide

if TYPE_CHECKING:
    from app.models.match import Match
    from app.models.team import Team
    from app.models.user import User


class Prediction(Base):
    """Pronostic compétitif d'un utilisateur pour un match. Verrouillé à kickoff_at côté serveur."""

    __tablename__ = "predictions"
    __table_args__ = (UniqueConstraint("user_id", "match_id", name="uq_predictions_user_match"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False)
    predicted_home_score: Mapped[int] = mapped_column(nullable=False)
    predicted_away_score: Mapped[int] = mapped_column(nullable=False)
    # Qualifié pronostiqué, tous prolongements confondus. Obligatoire à élimination directe,
    # interdit en phase de groupe (imposé côté application, pas en base).
    # Deux formes mutuellement exclusives : par équipe (équipes connues) ou par côté
    # (équipes encore en placeholders, ex. la finale avant la fin des demies).
    predicted_winner_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    predicted_winner_side: Mapped[PredictedWinnerSide | None] = mapped_column(
        SqlEnum(PredictedWinnerSide, name="predicted_winner_side"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship(back_populates="predictions")
    match: Mapped["Match"] = relationship(back_populates="predictions")
    predicted_winner_team: Mapped[Optional["Team"]] = relationship(foreign_keys=[predicted_winner_team_id])
