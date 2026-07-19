from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.deps import get_ai_client, get_current_user
from app.models.training_session import TrainingSession
from app.models.user import User
from app.schemas.team import TeamRead
from app.schemas.training import (
    TrainingMatchRead,
    TrainingMatchResultRead,
    TrainingPredictionCreate,
    TrainingSessionCreate,
    TrainingSessionRead,
    TrainingSessionResultsRead,
)
from app.services import scoring
from app.services.ai_client import AIClient, UnknownTeamError

router = APIRouter(prefix="/training/sessions", tags=["entraînement"])


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


@router.post("/{session_id}/predictions/{match_id}", response_model=TrainingMatchResultRead)
def submit_training_prediction(
    session_id: int,
    match_id: int,
    prediction_in: TrainingPredictionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    ai_client: AIClient = Depends(get_ai_client),
) -> TrainingMatchResultRead:
    """Soumet le pronostic pour ce match de la session.

    Récupère ensuite le pronostic de l'IA via ai_client -- appelée point-in-time (date du
    match passé transmise, jamais le résultat) avec les NOMS des équipes -- révèle le vrai
    score et note les deux avec le barème de scoring.py. N'écrit QUE dans
    training_predictions : jamais dans predictions, scores ni le classement (isolation).
    """
    session = crud.training.get_session(db, session_id)
    if session is None or session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session introuvable.")

    session_match = crud.training.get_session_match(db, session_id, match_id)
    if session_match is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ce match ne fait pas partie de la session.")

    if crud.training.get_prediction(db, session_id, match_id) is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Pronostic déjà soumis pour ce match.")

    historical_match = session_match.historical_match

    # Point-in-time : le service IA ne calcule qu'avec les données antérieures à la date du
    # match, sinon il « verrait le futur » qu'il est censé prédire (cf. CLAUDE.md).
    try:
        ai_prediction = ai_client.predict_match(
            home_team=historical_match.home_team.name,
            away_team=historical_match.away_team.name,
            reference_date=historical_match.played_at.date(),
            match_id=historical_match.id,
        )
    except UnknownTeamError as exc:
        # Ne devrait pas arriver : ces matchs sont exclus du tirage (settings.ai_unknown_teams).
        # Défense en profondeur avec un message clair nommant l'équipe, jamais un 503 opaque.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Le service IA ne peut pas pronostiquer ce match : {exc.detail}",
        ) from exc
    if ai_prediction is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service IA indisponible, réessayez."
        )

    user_points = scoring.score_training_guess(
        prediction_in.predicted_home_score, prediction_in.predicted_away_score, historical_match
    )
    ai_points = scoring.score_training_guess(
        ai_prediction.predicted_home_score, ai_prediction.predicted_away_score, historical_match
    )

    training_prediction = crud.training.create_prediction(
        db,
        training_session_id=session_id,
        historical_match_id=match_id,
        predicted_home_score=prediction_in.predicted_home_score,
        predicted_away_score=prediction_in.predicted_away_score,
        ai_predicted_home_score=ai_prediction.predicted_home_score,
        ai_predicted_away_score=ai_prediction.predicted_away_score,
        user_points=user_points,
        ai_points=ai_points,
    )

    if crud.training.count_predictions(db, session_id) >= crud.training.count_session_matches(db, session_id):
        crud.training.mark_session_completed(db, session)

    return TrainingMatchResultRead(
        historical_match_id=historical_match.id,
        home_team=TeamRead.model_validate(historical_match.home_team),
        away_team=TeamRead.model_validate(historical_match.away_team),
        home_score=historical_match.home_score,
        away_score=historical_match.away_score,
        predicted_home_score=training_prediction.predicted_home_score,
        predicted_away_score=training_prediction.predicted_away_score,
        ai_predicted_home_score=training_prediction.ai_predicted_home_score,
        ai_predicted_away_score=training_prediction.ai_predicted_away_score,
        user_points=training_prediction.user_points,
        ai_points=training_prediction.ai_points,
    )


@router.get("/{session_id}/results", response_model=TrainingSessionResultsRead)
def get_training_session_results(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TrainingSessionResultsRead:
    """Duel utilisateur contre IA pour chaque match déjà pronostiqué de la session (les
    matchs pas encore soumis n'apparaissent pas ici : leur score reste caché)."""
    session = crud.training.get_session(db, session_id)
    if session is None or session.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session introuvable.")

    predictions = crud.training.get_predictions_with_matches(db, session_id)
    results = [
        TrainingMatchResultRead(
            historical_match_id=p.historical_match_id,
            home_team=TeamRead.model_validate(p.historical_match.home_team),
            away_team=TeamRead.model_validate(p.historical_match.away_team),
            home_score=p.historical_match.home_score,
            away_score=p.historical_match.away_score,
            predicted_home_score=p.predicted_home_score,
            predicted_away_score=p.predicted_away_score,
            ai_predicted_home_score=p.ai_predicted_home_score,
            ai_predicted_away_score=p.ai_predicted_away_score,
            user_points=p.user_points,
            ai_points=p.ai_points,
        )
        for p in predictions
    ]

    return TrainingSessionResultsRead(
        session_id=session.id,
        completed=session.completed_at is not None,
        results=results,
        user_total_points=sum(r.user_points for r in results),
        ai_total_points=sum(r.ai_points for r in results),
    )
