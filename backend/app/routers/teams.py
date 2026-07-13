from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.schemas.team import TeamRead

router = APIRouter(prefix="/teams", tags=["matchs"])


@router.get("", response_model=list[TeamRead])
def list_teams(db: Session = Depends(get_db)) -> list:
    """Liste toutes les équipes."""
    return crud.team.list_all(db)


@router.get("/{team_id}", response_model=TeamRead)
def get_team(team_id: int, db: Session = Depends(get_db)) -> TeamRead:
    """Détail d'une équipe, entraîneur inclus (contexte sportif, confort d'affichage)."""
    team = crud.team.get_by_id(db, team_id)
    if team is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Équipe introuvable.")
    return team
