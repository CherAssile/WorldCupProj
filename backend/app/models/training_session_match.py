from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.historical_match import HistoricalMatch
    from app.models.training_session import TrainingSession


class TrainingSessionMatch(Base):
    """Un des N matchs tirés pour une session d'entraînement, avant tout pronostic.

    Distincte de training_predictions : cette table fixe le tirage (immuable dès la
    création de la session) ; training_predictions n'existe qu'une fois le pronostic
    soumis (étape suivante). Cette séparation est ce qui permet à GET /training/sessions/{id}
    de renvoyer les matchs tirés sans jamais exposer leur vrai score avant soumission.
    """

    __tablename__ = "training_session_matches"
    __table_args__ = (
        UniqueConstraint(
            "training_session_id", "historical_match_id", name="uq_training_session_matches_session_match"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    training_session_id: Mapped[int] = mapped_column(ForeignKey("training_sessions.id"), nullable=False)
    historical_match_id: Mapped[int] = mapped_column(ForeignKey("historical_matches.id"), nullable=False)
    position: Mapped[int] = mapped_column(Integer, nullable=False)

    training_session: Mapped["TrainingSession"] = relationship(back_populates="session_matches")
    historical_match: Mapped["HistoricalMatch"] = relationship()
