from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.team import Team


def list_all(db: Session) -> list[Team]:
    """Toutes les équipes, triées par nom."""
    return list(db.execute(select(Team).order_by(Team.name)).scalars())


def get_by_id(db: Session, team_id: int) -> Team | None:
    return db.get(Team, team_id)
