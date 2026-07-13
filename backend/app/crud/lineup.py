from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.lineup import Lineup
from app.models.lineup_player import LineupPlayer


def get_by_match(db: Session, match_id: int) -> list[Lineup]:
    """Les compositions déjà enregistrées pour ce match (0, 1 ou 2 : une par équipe)."""
    stmt = (
        select(Lineup)
        .options(joinedload(Lineup.team), joinedload(Lineup.players).joinedload(LineupPlayer.player))
        .where(Lineup.match_id == match_id)
    )
    return list(db.execute(stmt).unique().scalars())
