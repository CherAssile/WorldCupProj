from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_prediction import AiPrediction


def get_by_match_id(db: Session, match_id: int) -> AiPrediction | None:
    stmt = select(AiPrediction).where(AiPrediction.match_id == match_id)
    return db.execute(stmt).scalar_one_or_none()
