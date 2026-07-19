from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.match import Match


class AiPrediction(Base):
    """Pronostic de l'IA pour un match compétitif, point-in-time. Un seul par match."""

    __tablename__ = "ai_predictions"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), unique=True, nullable=False)
    predicted_home_score: Mapped[int] = mapped_column(nullable=False)
    predicted_away_score: Mapped[int] = mapped_column(nullable=False)
    # True = prédiction de repli neutre, servie parce que le modèle ne connaît pas une
    # équipe du match (cf. ai_client.NEUTRAL_FALLBACK_PREDICTION). Reste honnête sur sa
    # nature : le frontend peut l'indiquer, et ça facilite le diagnostic.
    is_fallback: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    match: Mapped["Match"] = relationship(back_populates="ai_prediction")
