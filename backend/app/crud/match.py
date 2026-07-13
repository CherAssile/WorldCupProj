from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.match import Match


def list_all(db: Session) -> list[Match]:
    """Tous les matchs du tournoi, triés par coup d'envoi, équipes préchargées."""
    stmt = (
        select(Match)
        .options(joinedload(Match.home_team), joinedload(Match.away_team), joinedload(Match.winner_team))
        .order_by(Match.kickoff_at)
    )
    return list(db.execute(stmt).unique().scalars())


def get_by_id(db: Session, match_id: int) -> Match | None:
    return db.get(Match, match_id)
