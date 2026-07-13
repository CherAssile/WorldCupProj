from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import MatchPhase

if TYPE_CHECKING:
    from app.models.simulation_run import SimulationRun
    from app.models.team import Team


class SimulationMatchResult(Base):
    """Résultat simulé d'un affrontement hypothétique entre deux équipes.

    Ne référence pas `matches` : une simulation définit son propre fixture
    (home_team/away_team), indépendant des matchs réels du tournoi.
    Isolée du mode compétitif : aucune clé étrangère vers matches/predictions/scores.
    """

    __tablename__ = "simulation_match_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    simulation_run_id: Mapped[int] = mapped_column(ForeignKey("simulation_runs.id"), nullable=False)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    phase: Mapped[MatchPhase | None] = mapped_column(SqlEnum(MatchPhase, name="match_phase"), nullable=True)
    simulated_home_score: Mapped[int] = mapped_column(nullable=False)
    simulated_away_score: Mapped[int] = mapped_column(nullable=False)
    # NULL pour un match de groupe nul (aucun vainqueur) ; toujours renseigné en phase
    # finale (départage déterministe si l'IA prédit une égalité, cf. services/simulation.py).
    winner_team_id: Mapped[int | None] = mapped_column(ForeignKey("teams.id"), nullable=True)
    # Vrai si ce résultat provient d'un match réel déjà joué (gelé), faux s'il a été simulé
    # par le service IA (mode réaliste : CLAUDE.md, on ne rejoue jamais un match déjà décidé).
    is_frozen_real_result: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    simulation_run: Mapped["SimulationRun"] = relationship(back_populates="results")
    home_team: Mapped["Team"] = relationship(
        foreign_keys=[home_team_id], back_populates="home_simulation_match_results"
    )
    away_team: Mapped["Team"] = relationship(
        foreign_keys=[away_team_id], back_populates="away_simulation_match_results"
    )
    winner_team: Mapped["Team | None"] = relationship(foreign_keys=[winner_team_id])
