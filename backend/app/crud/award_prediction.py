from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.award_prediction import AwardPrediction
from app.models.player import Player

_WITH_PREDICTED_PLAYER = joinedload(AwardPrediction.predicted_player).joinedload(Player.team)


def get_by_user_and_award(db: Session, user_id: int, award_id: int) -> AwardPrediction | None:
    stmt = (
        select(AwardPrediction)
        .where(AwardPrediction.user_id == user_id, AwardPrediction.award_id == award_id)
        .options(_WITH_PREDICTED_PLAYER)
    )
    return db.execute(stmt).unique().scalar_one_or_none()


def list_by_user(db: Session, user_id: int) -> list[AwardPrediction]:
    stmt = (
        select(AwardPrediction)
        .where(AwardPrediction.user_id == user_id)
        .options(_WITH_PREDICTED_PLAYER)
        .order_by(AwardPrediction.created_at)
    )
    return list(db.execute(stmt).unique().scalars())


def upsert(db: Session, user_id: int, award_id: int, predicted_player_id: int) -> AwardPrediction:
    """Un pronostic par (user, award) : un second choix remplace le premier, ne le duplique pas."""
    existing = get_by_user_and_award(db, user_id, award_id)
    if existing is not None:
        existing.predicted_player_id = predicted_player_id
        db.commit()
        db.refresh(existing)
        return existing

    prediction = AwardPrediction(user_id=user_id, award_id=award_id, predicted_player_id=predicted_player_id)
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction
