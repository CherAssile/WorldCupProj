from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.player import Player
from app.models.team import Team


def search(db: Session, name: str | None = None, team_id: int | None = None) -> list[Player]:
    """Recherche de joueurs (nom, équipe), triés par équipe puis par nom."""
    stmt = select(Player).join(Team).options(joinedload(Player.team)).order_by(Team.name, Player.name)

    if name:
        stmt = stmt.where(Player.name.ilike(f"%{name}%"))
    if team_id is not None:
        stmt = stmt.where(Player.team_id == team_id)

    return list(db.execute(stmt).unique().scalars())


def get_by_id(db: Session, player_id: int) -> Player | None:
    return db.get(Player, player_id)
