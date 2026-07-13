from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.models.ai_prediction import AiPrediction
from app.models.enums import MatchPhase
from app.models.match import Match
from app.schemas.ai_prediction import AiPredictionRead
from app.schemas.match import MatchPhaseGroup

router = APIRouter(prefix="/matches", tags=["matches"])


@router.get("", response_model=list[MatchPhaseGroup])
def list_matches_by_phase(db: Session = Depends(get_db)) -> list[MatchPhaseGroup]:
    """Liste les matchs du tournoi, groupés par phase (ordre du tournoi)."""
    matches_by_phase: dict[MatchPhase, list[Match]] = {phase: [] for phase in MatchPhase}
    for match in crud.match.list_all(db):
        matches_by_phase[match.phase].append(match)

    return [MatchPhaseGroup(phase=phase, matches=matches_by_phase[phase]) for phase in MatchPhase]


@router.get("/{match_id}/ai-prediction", response_model=AiPredictionRead)
def get_match_ai_prediction(match_id: int, db: Session = Depends(get_db)) -> AiPrediction:
    """Pronostic IA pour ce match, s'il a déjà été généré (voir POST /ai-predictions/regenerate)."""
    match = crud.match.get_by_id(db, match_id)
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match introuvable.")

    prediction = crud.ai_prediction.get_by_match_id(db, match_id)
    if prediction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Aucun pronostic IA pour ce match.")

    return prediction
