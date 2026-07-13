from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import SimulationMode

if TYPE_CHECKING:
    from app.models.simulation_match_result import SimulationMatchResult
    from app.models.user import User


class SimulationRun(Base):
    """Simulation admin (bac à sable) : n'affecte jamais predictions/scores/classement.

    Isolée du mode compétitif : aucune clé étrangère vers matches/predictions/scores.
    """

    __tablename__ = "simulation_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    mode: Mapped[SimulationMode] = mapped_column(SqlEnum(SimulationMode, name="simulation_mode"), nullable=False)
    # Graine du départage déterministe des matchs à élimination directe simulés par l'IA
    # sur une égalité (cf. services/simulation.py). Toujours renseignée (générée si non
    # fournie à l'appel) : conservée pour permettre de reproduire exactement un run donné.
    seed: Mapped[str] = mapped_column(String(64), nullable=False)
    label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    created_by: Mapped["User"] = relationship(back_populates="simulation_runs")
    results: Mapped[list["SimulationMatchResult"]] = relationship(back_populates="simulation_run")
