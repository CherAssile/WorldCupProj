from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.historical_match import HistoricalMatch
    from app.models.training_session import TrainingSession


class TrainingPrediction(Base):
    """Pronostic d'entraînement (utilisateur + IA) sur un match déjà joué.

    Le vrai score de `historical_match` ne doit être exposé côté API qu'après
    soumission (revealed_at renseigné) — anti-triche du mode entraînement.
    Isolée du mode compétitif : aucune clé étrangère vers matches/predictions/scores.
    """

    __tablename__ = "training_predictions"
    __table_args__ = (
        UniqueConstraint("training_session_id", "historical_match_id", name="uq_training_predictions_session_match"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    training_session_id: Mapped[int] = mapped_column(ForeignKey("training_sessions.id"), nullable=False)
    historical_match_id: Mapped[int] = mapped_column(ForeignKey("historical_matches.id"), nullable=False)

    predicted_home_score: Mapped[int] = mapped_column(nullable=False)
    predicted_away_score: Mapped[int] = mapped_column(nullable=False)
    ai_predicted_home_score: Mapped[int] = mapped_column(nullable=False)
    ai_predicted_away_score: Mapped[int] = mapped_column(nullable=False)

    user_points: Mapped[int | None] = mapped_column(nullable=True)
    ai_points: Mapped[int | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    revealed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    training_session: Mapped["TrainingSession"] = relationship(back_populates="predictions")
    historical_match: Mapped["HistoricalMatch"] = relationship(back_populates="training_predictions")
