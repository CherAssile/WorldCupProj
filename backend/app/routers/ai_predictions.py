from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_admin
from app.models.user import User
from app.schemas.ai_prediction import AiPredictionGenerationResult
from app.services.ai_predictions import generate_ai_predictions

router = APIRouter(prefix="/ai-predictions", tags=["admin"])


@router.post("/regenerate", response_model=AiPredictionGenerationResult)
def regenerate_ai_predictions(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> AiPredictionGenerationResult:
    """(Re)génère les pronostics IA de tous les matchs à venir. Réservé aux administrateurs."""
    result = generate_ai_predictions(db)
    return AiPredictionGenerationResult(
        created=result.created,
        updated=result.updated,
        removed_stale=result.removed_stale,
        skipped_unresolved_teams=result.skipped_unresolved_teams,
        skipped_ai_unavailable=result.skipped_ai_unavailable,
        fallback_predictions=result.fallback_predictions,
    )
