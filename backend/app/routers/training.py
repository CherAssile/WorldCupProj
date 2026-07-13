from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.deps import get_current_user
from app.models.training_session import TrainingSession
from app.models.user import User
from app.schemas.team import TeamRead
from app.schemas.training import TrainingMatchRead, TrainingSessionCreate, TrainingSessionRead

router = APIRouter(prefix="/training/sessions", tags=["training"])


def _build_session_read(db: Session, session: TrainingSession) -> TrainingSessionRead:
    """Construit la réponse champ par champ (jamais par conversion automatique de l'objet
    HistoricalMatch complet) : c'est ce qui garantit structurellement que home_score/
    away_score ne peuvent pas fuiter, même si le modèle évolue plus tard."""
    session_matches = crud.training.get_session_matches(db, session.id)
    return TrainingSessionRead(
        id=session.id,
        started_at=session.started_at,
        completed_at=session.completed_at,
        matches=[
            TrainingMatchRead(
                historical_match_id=session_match.historical_match_id,
                position=session_match.position,
                home_team=TeamRead.model_validate(session_match.historical_match.home_team),
                away_team=TeamRead.model_validate(session_match.historical_match.away_team),
                edition_year=session_match.historical_match.edition_year,
                phase=session_match.historical_match.phase,
                played_at=session_match.historical_match.played_at,
            )
            for session_match in session_matches
        ],
    )


@router.post("", response_model=TrainingSessionRead, status_code=status.HTTP_201_CREATED)
def create_training_session(
    session_in: TrainingSessionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TrainingSessionRead:
    """Crée une session d'entraînement : tire match_count matchs historiques au hasard."""
    session = crud.training.create_session(db, user_id=current_user.id, match_count=session_in.match_count)
    return _build_session_read(db, session)


@router.get("/{session_id}", response_model=TrainingSessionRead)
def get_training_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TrainingSessionRead:
    """Détail d'une session : les matchs tirés, JAMAIS leur vrai score avant que
    l'utilisateur n'ait soumis son pronostic (anti-triche)."""
    session = crud.training.get_session(db, session_id)
    if session is None or session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session introuvable.")

    return _build_session_read(db, session)
