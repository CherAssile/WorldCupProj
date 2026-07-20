from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_football_api_client, require_admin
from app.models.user import User
from app.redis_client import redis_client
from app.schemas.admin import FullSyncResultRead
from app.services.football_api import FootballApiClient
from app.services.sync_pipeline import run_full_sync

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/sync", response_model=FullSyncResultRead)
def trigger_full_sync(
    db: Session = Depends(get_db),
    client: FootballApiClient = Depends(get_football_api_client),
    _admin: User = Depends(require_admin),
) -> FullSyncResultRead:
    """Force la chaîne complète de synchronisation (calendrier, placeholders, scores,
    classement) sans attendre le prochain tick du scheduler -- même chaîne, mêmes garanties
    d'idempotence (cf. app.services.sync_pipeline). Réservé aux administrateurs."""
    result = run_full_sync(db, redis_client, client=client)
    return FullSyncResultRead(
        teams_created=result.teams_created,
        matches_created=result.matches_created,
        matches_updated=result.matches_updated,
        placeholders_resolved=result.placeholders_resolved,
        scores_recalculated=result.scores_recalculated,
        leaderboard_size=result.leaderboard_size,
    )
