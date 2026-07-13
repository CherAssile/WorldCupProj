from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.award import Award


def list_all(db: Session) -> list[Award]:
    """Toutes les catégories de récompenses, triées par catégorie."""
    return list(db.execute(select(Award).order_by(Award.category)).scalars())


def get_by_id(db: Session, award_id: int) -> Award | None:
    return db.get(Award, award_id)
