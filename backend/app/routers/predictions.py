from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.deps import get_current_user
from app.models.enums import MatchPhase, PredictedWinnerSide
from app.models.match import Match
from app.models.prediction import Prediction
from app.models.user import User
from app.schemas.prediction import PredictionCreate, PredictionRead, PredictionUpdate

router = APIRouter(prefix="/predictions", tags=["pronostics"])


def _ensure_prediction_allowed(match: Match) -> None:
    """Verrouillage serveur, jamais côté client : seul le coup d'envoi verrouille. Un match
    aux équipes encore inconnues (placeholders) reste pronostiquable — « le vainqueur de la
    demi-finale 1 gagne la finale 2-1 » est un pronostic parfaitement défini."""
    if datetime.now(timezone.utc) >= match.kickoff_at:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Le coup d'envoi est déjà passé.")


def _validate_predicted_winner(
    predicted_winner_team_id: int | None,
    predicted_winner_side: PredictedWinnerSide | None,
    match: Match,
) -> None:
    """Qualifié obligatoire à élimination directe, interdit en poule. Deux formes
    mutuellement exclusives selon l'état du match : par équipe quand les deux équipes
    sont connues, par côté (HOME/AWAY) tant qu'au moins une reste un placeholder."""
    is_knockout = match.phase != MatchPhase.GROUP
    teams_known = match.home_team_id is not None and match.away_team_id is not None

    if predicted_winner_team_id is not None and predicted_winner_side is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Qualifié par équipe et par côté sont mutuellement exclusifs : fournis l'un ou l'autre.",
        )

    if not is_knockout:
        if predicted_winner_team_id is not None or predicted_winner_side is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Le qualifié ne peut pas être renseigné pour un match de groupe.",
            )
        return

    if teams_known:
        if predicted_winner_side is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Les équipes de ce match sont connues : désigne le qualifié par predicted_winner_team_id.",
            )
        if predicted_winner_team_id is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Le qualifié est obligatoire pour un match à élimination directe.",
            )
        if predicted_winner_team_id not in (match.home_team_id, match.away_team_id):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Le qualifié pronostiqué doit être l'une des deux équipes du match.",
            )
    else:
        if predicted_winner_team_id is not None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Les équipes de ce match ne sont pas encore connues : désigne le qualifié par predicted_winner_side.",
            )
        if predicted_winner_side is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Le qualifié est obligatoire pour un match à élimination directe.",
            )


@router.post("", response_model=PredictionRead, status_code=status.HTTP_201_CREATED)
def create_prediction(
    prediction_in: PredictionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Prediction:
    """Crée un pronostic. Verrouillé au coup d'envoi, un seul pronostic par (user, match)."""
    match = crud.match.get_by_id(db, prediction_in.match_id)
    if match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Match introuvable.")

    _ensure_prediction_allowed(match)
    _validate_predicted_winner(prediction_in.predicted_winner_team_id, prediction_in.predicted_winner_side, match)

    if crud.prediction.get_by_user_and_match(db, current_user.id, match.id) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Un pronostic existe déjà pour ce match."
        )

    return crud.prediction.create(db, user_id=current_user.id, match_id=match.id, prediction_in=prediction_in)


@router.put("/{prediction_id}", response_model=PredictionRead)
def update_prediction(
    prediction_id: int,
    prediction_in: PredictionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Prediction:
    """Modifie un pronostic existant. Verrouillé au coup d'envoi comme à la création."""
    prediction = crud.prediction.get_by_id(db, prediction_id)
    if prediction is None or prediction.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Pronostic introuvable.")

    match = crud.match.get_by_id(db, prediction.match_id)
    _ensure_prediction_allowed(match)
    _validate_predicted_winner(prediction_in.predicted_winner_team_id, prediction_in.predicted_winner_side, match)

    return crud.prediction.update(db, prediction=prediction, prediction_in=prediction_in)


@router.get("/me", response_model=list[PredictionRead])
def list_my_predictions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Prediction]:
    """Liste les pronostics de l'utilisateur authentifié."""
    return crud.prediction.list_by_user(db, current_user.id)
