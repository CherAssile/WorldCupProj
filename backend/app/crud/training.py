from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.historical_match import HistoricalMatch
from app.models.training_session import TrainingSession
from app.models.training_session_match import TrainingSessionMatch


def create_session(db: Session, user_id: int, match_count: int) -> TrainingSession:
    """Crée la session et tire match_count matchs historiques au hasard, sans remise.

    Le tirage est figé dès la création (table dédiée, distincte des pronostics) : c'est ce
    qui permet de renvoyer les matchs à l'utilisateur avant qu'il n'ait pronostiqué, sans
    jamais exposer leur vrai score.
    """
    session = TrainingSession(user_id=user_id)
    db.add(session)
    db.flush()

    drawn_matches = db.execute(select(HistoricalMatch.id).order_by(func.random()).limit(match_count)).scalars()

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
