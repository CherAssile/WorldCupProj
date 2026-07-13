from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.simulation_match_result import SimulationMatchResult
from app.models.simulation_run import SimulationRun


def list_all(db: Session) -> list[SimulationRun]:
    """Toutes les simulations, plus récentes en premier."""
    stmt = select(SimulationRun).order_by(SimulationRun.created_at.desc())
    return list(db.execute(stmt).scalars())


def get_by_id(db: Session, simulation_run_id: int) -> SimulationRun | None:
    """Une simulation avec ses résultats et les équipes associées préchargés."""
    stmt = (
        select(SimulationRun)
        .where(SimulationRun.id == simulation_run_id)
        .options(
            joinedload(SimulationRun.results).joinedload(SimulationMatchResult.home_team),
            joinedload(SimulationRun.results).joinedload(SimulationMatchResult.away_team),
            joinedload(SimulationRun.results).joinedload(SimulationMatchResult.winner_team),
        )
    )
    return db.execute(stmt).unique().scalar_one_or_none()
