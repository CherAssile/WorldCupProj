from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.prediction import Prediction
from app.schemas.prediction import PredictionCreate, PredictionUpdate


def get_by_id(db: Session, prediction_id: int) -> Prediction | None:
    return db.get(Prediction, prediction_id)


def get_by_user_and_match(db: Session, user_id: int, match_id: int) -> Prediction | None:
    stmt = select(Prediction).where(Prediction.user_id == user_id, Prediction.match_id == match_id)
    return db.execute(stmt).scalar_one_or_none()


def list_by_user(db: Session, user_id: int) -> list[Prediction]:
    stmt = select(Prediction).where(Prediction.user_id == user_id).order_by(Prediction.created_at)
    return list(db.execute(stmt).scalars())


def create(db: Session, user_id: int, match_id: int, prediction_in: PredictionCreate) -> Prediction:
    prediction = Prediction(
        user_id=user_id,
        match_id=match_id,
        predicted_home_score=prediction_in.predicted_home_score,
        predicted_away_score=prediction_in.predicted_away_score,
        predicted_winner_team_id=prediction_in.predicted_winner_team_id,
    )
    db.add(prediction)
    db.commit()
    db.refresh(prediction)
    return prediction


def update(db: Session, prediction: Prediction, prediction_in: PredictionUpdate) -> Prediction:
    prediction.predicted_home_score = prediction_in.predicted_home_score
    prediction.predicted_away_score = prediction_in.predicted_away_score
    prediction.predicted_winner_team_id = prediction_in.predicted_winner_team_id
    db.commit()
    db.refresh(prediction)
    return prediction
