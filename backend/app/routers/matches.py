from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.models.enums import MatchPhase
from app.models.match import Match
from app.schemas.match import MatchPhaseGroup

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("", response_model=list[MatchPhaseGroup])
def list_matches_by_phase(db: Session = Depends(get_db)) -> list[MatchPhaseGroup]:
    """Liste les matchs du tournoi, groupés par phase (ordre du tournoi)."""
    matches_by_phase: dict[MatchPhase, list[Match]] = {phase: [] for phase in MatchPhase}
    for match in crud.match.list_all(db):
        matches_by_phase[match.phase].append(match)

    return [MatchPhaseGroup(phase=phase, matches=matches_by_phase[phase]) for phase in MatchPhase]
