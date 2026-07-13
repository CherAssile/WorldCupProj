from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.lineup_player import LineupPlayer
    from app.models.match import Match
    from app.models.team import Team


class Lineup(Base):
    """Composition d'une équipe pour un match. Contexte sportif (confort d'affichage) :
    n'entre dans AUCUN calcul de points, ne touche ni au scoring ni à l'isolation.

    Les compositions ne sont publiées qu'environ 1h avant le coup d'envoi : son absence
    pour un match à venir est un cas normal, pas une erreur (cf. services/lineups_seed.py).
    """

    __tablename__ = "lineups"
    __table_args__ = (UniqueConstraint("match_id", "team_id", name="uq_lineups_match_team"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(ForeignKey("matches.id"), nullable=False)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    formation: Mapped[str | None] = mapped_column(String(20), nullable=True)
    # Référence côté source, utile pour déboguer un import sans re-résoudre le fixture.
    api_fixture_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    match: Mapped["Match"] = relationship()
    team: Mapped["Team"] = relationship()
    players: Mapped[list["LineupPlayer"]] = relationship(back_populates="lineup")
