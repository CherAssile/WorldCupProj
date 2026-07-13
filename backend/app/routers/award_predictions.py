from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.deps import get_current_user
from app.models.award_prediction import AwardPrediction
from app.models.user import User
from app.schemas.award_prediction import AwardPredictionCreate, AwardPredictionRead

router = APIRouter(prefix="/award-predictions", tags=["award-predictions"])


@router.post("", response_model=AwardPredictionRead)
def choose_award_prediction(
    prediction_in: AwardPredictionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AwardPrediction:
    """Choisit un joueur pour une récompense. Un seul choix par catégorie : un second choix
    remplace le premier plutôt que de le dupliquer. Verrouillé côté serveur à lock_at."""
    award = crud.award.get_by_id(db, prediction_in.award_id)
    if award is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Récompense introuvable.")

    if datetime.now(timezone.utc) >= award.lock_at:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="La date limite de cette récompense est dépassée.",
        )

    player = crud.player.get_by_id(db, prediction_in.predicted_player_id)
    if player is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Joueur introuvable.")

    return crud.award_prediction.upsert(
        db, user_id=current_user.id, award_id=award.id, predicted_player_id=player.id
    )


@router.get("/me", response_model=list[AwardPredictionRead])
def list_my_award_predictions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AwardPrediction]:
    """Liste les pronostics de récompenses de l'utilisateur authentifié."""
    return crud.award_prediction.list_by_user(db, current_user.id)
