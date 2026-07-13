from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.deps import require_admin
from app.models.user import User
from app.schemas.simulation import SimulationCreate, SimulationRunDetailRead, SimulationRunRead
from app.services.simulation import AIServiceUnavailable, run_realistic_simulation

router = APIRouter(prefix="/simulations", tags=["simulations"])


@router.post("", response_model=SimulationRunDetailRead, status_code=status.HTTP_201_CREATED)
def create_simulation(
    payload: SimulationCreate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
) -> SimulationRunDetailRead:
    """Lance une simulation complète du tournoi (bac à sable admin, mode réaliste). Réservé
    aux administrateurs -- n'affecte jamais matches/predictions/scores/classement."""
    try:
        run = run_realistic_simulation(db, created_by_user_id=admin.id, label=payload.label)
    except AIServiceUnavailable as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return crud.simulation.get_by_id(db, run.id)


@router.get("", response_model=list[SimulationRunRead])
def list_simulations(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> list[SimulationRunRead]:
    """Historique des simulations lancées. Réservé aux administrateurs."""
    return crud.simulation.list_all(db)


@router.get("/{simulation_run_id}", response_model=SimulationRunDetailRead)
def get_simulation(
    simulation_run_id: int,
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> SimulationRunDetailRead:
    """Détail d'une simulation, avec tous ses résultats. Réservé aux administrateurs."""
    run = crud.simulation.get_by_id(db, simulation_run_id)
    if run is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Simulation introuvable.")
    return run
