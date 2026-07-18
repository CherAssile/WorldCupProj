from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.award import Award
from app.models.player import Player


def list_all(db: Session) -> list[Award]:
    """Toutes les catégories de récompenses, triées par catégorie."""
    stmt = (
        select(Award)
        .options(joinedload(Award.actual_player).joinedload(Player.team))
        .order_by(Award.category)
    )
    return list(db.execute(stmt).unique().scalars())


def get_by_id(db: Session, award_id: int) -> Award | None:
    return db.get(Award, award_id)
