from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.award import Award
    from app.models.player import Player
    from app.models.user import User


class AwardPrediction(Base):
    """Pronostic d'un utilisateur pour une catégorie de récompense. Un par (user, award)."""

    __tablename__ = "award_predictions"
    __table_args__ = (UniqueConstraint("user_id", "award_id", name="uq_award_predictions_user_award"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    award_id: Mapped[int] = mapped_column(ForeignKey("awards.id"), nullable=False)
    predicted_player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="award_predictions")
    award: Mapped["Award"] = relationship(back_populates="predictions")
    predicted_player: Mapped["Player"] = relationship(back_populates="award_predictions")
