from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import AwardCategory

if TYPE_CHECKING:
    from app.models.award_prediction import AwardPrediction
    from app.models.player import Player


class Award(Base):
    """Catégorie de récompense du tournoi (meilleur buteur, passeur, joueur)."""

    __tablename__ = "awards"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[AwardCategory] = mapped_column(
        SqlEnum(AwardCategory, name="award_category"), unique=True, nullable=False
    )
    lock_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actual_player_id: Mapped[int | None] = mapped_column(ForeignKey("players.id"), nullable=True)

    actual_player: Mapped[Optional["Player"]] = relationship(back_populates="awards_won")
    predictions: Mapped[list["AwardPrediction"]] = relationship(back_populates="award")
