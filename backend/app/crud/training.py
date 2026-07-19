from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.config import settings
from app.models.historical_match import HistoricalMatch
from app.models.team import Team
from app.models.training_prediction import TrainingPrediction
from app.models.training_session import TrainingSession
from app.models.training_session_match import TrainingSessionMatch


def create_session(db: Session, user_id: int, match_count: int) -> TrainingSession:
    """Crée la session et tire match_count matchs historiques au hasard, sans remise.

    Le tirage est figé dès la création (table dédiée, distincte des pronostics) : c'est ce
    qui permet de renvoyer les matchs à l'utilisateur avant qu'il n'ait pronostiqué, sans
    jamais exposer leur vrai score.

    Exclut les matchs impliquant une équipe absente du dataset du service IA
    (settings.ai_unknown_teams) : l'IA ne pourrait pas les pronostiquer et le duel serait
    une impasse. Poignée de matchs sur des centaines, invisible pour l'utilisateur.
    """
    session = TrainingSession(user_id=user_id)
    db.add(session)
    db.flush()

    unknown_teams = settings.ai_unknown_teams_set
    stmt = select(HistoricalMatch.id)
    if unknown_teams:
        excluded_team_ids = select(Team.id).where(Team.name.in_(unknown_teams)).scalar_subquery()
        stmt = stmt.where(
            HistoricalMatch.home_team_id.not_in(excluded_team_ids),
            HistoricalMatch.away_team_id.not_in(excluded_team_ids),
        )
    drawn_matches = db.execute(stmt.order_by(func.random()).limit(match_count)).scalars()

    for position, historical_match_id in enumerate(drawn_matches, start=1):
        db.add(
            TrainingSessionMatch(
                training_session_id=session.id,
                historical_match_id=historical_match_id,
                position=position,
            )
        )

    db.commit()
    db.refresh(session)
    return session


def get_session(db: Session, session_id: int) -> TrainingSession | None:
    return db.get(TrainingSession, session_id)


def get_session_matches(db: Session, session_id: int) -> list[TrainingSessionMatch]:
    """Matchs tirés pour la session, équipes préchargées, dans l'ordre du tirage."""
    stmt = (
        select(TrainingSessionMatch)
        .options(
            joinedload(TrainingSessionMatch.historical_match).joinedload(HistoricalMatch.home_team),
            joinedload(TrainingSessionMatch.historical_match).joinedload(HistoricalMatch.away_team),
        )
        .where(TrainingSessionMatch.training_session_id == session_id)
        .order_by(TrainingSessionMatch.position)
    )
    return list(db.execute(stmt).unique().scalars())


def get_session_match(db: Session, training_session_id: int, historical_match_id: int) -> TrainingSessionMatch | None:
    """Le match, s'il fait bien partie du tirage de cette session (équipes préchargées)."""
    stmt = (
        select(TrainingSessionMatch)
        .options(
            joinedload(TrainingSessionMatch.historical_match).joinedload(HistoricalMatch.home_team),
            joinedload(TrainingSessionMatch.historical_match).joinedload(HistoricalMatch.away_team),
        )
        .where(
            TrainingSessionMatch.training_session_id == training_session_id,
            TrainingSessionMatch.historical_match_id == historical_match_id,
        )
    )
    return db.execute(stmt).unique().scalar_one_or_none()


def get_prediction(db: Session, training_session_id: int, historical_match_id: int) -> TrainingPrediction | None:
    stmt = select(TrainingPrediction).where(
        TrainingPrediction.training_session_id == training_session_id,
        TrainingPrediction.historical_match_id == historical_match_id,
    )
    return db.execute(stmt).scalar_one_or_none()


def count_session_matches(db: Session, training_session_id: int) -> int:
    stmt = (
        select(func.count())
        .select_from(TrainingSessionMatch)
        .where(TrainingSessionMatch.training_session_id == training_session_id)
    )
    return db.execute(stmt).scalar_one()


def count_predictions(db: Session, training_session_id: int) -> int:
    stmt = (
        select(func.count())
        .select_from(TrainingPrediction)
        .where(TrainingPrediction.training_session_id == training_session_id)
    )
    return db.execute(stmt).scalar_one()


def create_prediction(
    db: Session,
    training_session_id: int,
    historical_match_id: int,
    predicted_home_score: int,
    predicted_away_score: int,
    ai_predicted_home_score: int,
    ai_predicted_away_score: int,
    user_points: int,
    ai_points: int,
) -> TrainingPrediction:
    """Écrit UNIQUEMENT dans training_predictions : jamais dans predictions/scores/
    classement (isolation du mode entraînement, cf. CLAUDE.md)."""
    prediction = TrainingPrediction(
        training_session_id=training_session_id,
        historical_match_id=historical_match_id,
        predicted_home_score=predicted_home_score,
        predicted_away_score=predicted_away_score,
        ai_predicted_home_score=ai_predicted_home_score,
        ai_predicted_away_score=ai_predicted_away_score,
        user_points=user_points,
        ai_points=ai_points,
        revealed_at=func.now(),
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction


def mark_session_completed(db: Session, session: TrainingSession) -> None:
    session.completed_at = func.now()
    db.commit()


def get_predictions_with_matches(db: Session, training_session_id: int) -> list[TrainingPrediction]:
    """Pronostics déjà soumis pour la session, dans l'ordre de soumission, équipes et match
    historique préchargés (le vrai score peut désormais être révélé, il a été soumis)."""
    stmt = (
        select(TrainingPrediction)
        .options(
            joinedload(TrainingPrediction.historical_match).joinedload(HistoricalMatch.home_team),
            joinedload(TrainingPrediction.historical_match).joinedload(HistoricalMatch.away_team),
        )
        .where(TrainingPrediction.training_session_id == training_session_id)
        .order_by(TrainingPrediction.created_at)
    )
    return list(db.execute(stmt).unique().scalars())
