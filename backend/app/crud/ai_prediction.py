from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.ai_prediction import AiPrediction


def get_by_match_id(db: Session, match_id: int) -> AiPrediction | None:
    stmt = select(AiPrediction).where(AiPrediction.match_id == match_id)
    return db.execute(stmt).scalar_one_or_none()


def list_all(db: Session) -> list[AiPrediction]:
    """Tous les pronostics IA (tous matchs confondus) -- sert au duel joueur/IA, qui
    compare aux pronostics d'un utilisateur pour l'ensemble du calendrier."""
    return list(db.execute(select(AiPrediction)).scalars())
