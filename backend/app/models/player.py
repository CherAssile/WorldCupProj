from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.award import Award
    from app.models.award_prediction import AwardPrediction
    from app.models.lineup_player import LineupPlayer
    from app.models.team import Team


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    position: Mapped[str | None] = mapped_column(String(20))
    shirt_number: Mapped[int | None]
    # Clé de dédoublonnage pour les imports (effectifs, compositions) : évite de recréer
    # le même joueur à chaque exécution des scripts de seed.
    api_football_player_id: Mapped[int | None] = mapped_column(unique=True, nullable=True)

    team: Mapped["Team"] = relationship(back_populates="players")
    award_predictions: Mapped[list["AwardPrediction"]] = relationship(back_populates="predicted_player")
    awards_won: Mapped[list["Award"]] = relationship(back_populates="actual_player")
    lineup_entries: Mapped[list["LineupPlayer"]] = relationship(back_populates="player")
