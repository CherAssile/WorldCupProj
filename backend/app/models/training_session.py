from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.training_prediction import TrainingPrediction
    from app.models.training_session_match import TrainingSessionMatch
    from app.models.user import User


class TrainingSession(Base):
    """Session d'entraînement d'un utilisateur (joueur contre la machine).

    Isolée du mode compétitif : aucune clé étrangère vers matches/predictions/scores.
    """

    __tablename__ = "training_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship(back_populates="training_sessions")
    predictions: Mapped[list["TrainingPrediction"]] = relationship(back_populates="training_session")
    session_matches: Mapped[list["TrainingSessionMatch"]] = relationship(
        back_populates="training_session", order_by="TrainingSessionMatch.position"
    )
