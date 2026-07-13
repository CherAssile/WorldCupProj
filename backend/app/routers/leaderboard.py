from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_admin
from app.models.user import User
from app.redis_client import redis_client
from app.schemas.leaderboard import LeaderboardEntryRead, LeaderboardRecomputeResult
from app.services import leaderboard as leaderboard_service

router = APIRouter(prefix="/leaderboard", tags=["leaderboard"])


@router.get("", response_model=list[LeaderboardEntryRead])
def get_leaderboard(db: Session = Depends(get_db)) -> list[leaderboard_service.LeaderboardEntry]:
    """Classement global, servi depuis le sorted set Redis (alimenté par la table scores)."""
    return leaderboard_service.get_leaderboard(db, redis_client)


@router.post("/recompute", response_model=LeaderboardRecomputeResult)
def recompute_leaderboard(
    db: Session = Depends(get_db),
    _admin: User = Depends(require_admin),
) -> LeaderboardRecomputeResult:
    """Recalcule entièrement le classement depuis la table scores. Réservé aux administrateurs."""
    users_ranked = leaderboard_service.rebuild_leaderboard(db, redis_client)
    return LeaderboardRecomputeResult(users_ranked=users_ranked)
