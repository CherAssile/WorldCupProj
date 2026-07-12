from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import crud
from app.database import get_db
from app.models.player import Player
from app.models.team import Team
from app.schemas.player import TeamPlayersGroup

router = APIRouter(prefix="/players", tags=["players"])


@router.get("", response_model=list[TeamPlayersGroup])
def search_players(
    search: str | None = Query(default=None, description="Filtre sur le nom du joueur"),
    team_id: int | None = Query(default=None, description="Filtre sur une équipe précise"),
    db: Session = Depends(get_db),
) -> list[TeamPlayersGroup]:
    """Recherche de joueurs, groupés par équipe."""
    groups: dict[int, tuple[Team, list[Player]]] = {}
    for player in crud.player.search(db, name=search, team_id=team_id):
        _, team_players = groups.setdefault(player.team_id, (player.team, []))
        team_players.append(player)

    return [TeamPlayersGroup(team=team, players=team_players) for team, team_players in groups.values()]
