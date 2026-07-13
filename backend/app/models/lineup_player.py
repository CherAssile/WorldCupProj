from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.lineup import Lineup
    from app.models.player import Player


class LineupPlayer(Base):
    """Un joueur au sein d'une composition (titulaire ou remplaçant)."""

    __tablename__ = "lineup_players"
    __table_args__ = (UniqueConstraint("lineup_id", "player_id", name="uq_lineup_players_lineup_player"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    lineup_id: Mapped[int] = mapped_column(ForeignKey("lineups.id"), nullable=False)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    position: Mapped[str | None] = mapped_column(String(20), nullable=True)
    shirt_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_starter: Mapped[bool] = mapped_column(Boolean, nullable=False)

    lineup: Mapped["Lineup"] = relationship(back_populates="players")
    player: Mapped["Player"] = relationship(back_populates="lineup_entries")
