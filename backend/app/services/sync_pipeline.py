"""Chaîne complète de synchronisation du mode compétitif.

1. calendrier (résultats depuis openfootball)
2. résolution en cascade des placeholders (W101 -> vraie équipe)
3. calcul des points (table scores)
4. classement Redis

Chaque étape est idempotente et peut être rejouée sans risque (cf. app.services.seed,
app.services.scoring, app.services.leaderboard) : c'est ce qui permet à cette chaîne de
tourner en boucle depuis le scheduler (app.services.scheduler) comme depuis l'endpoint
d'administration manuel (POST /admin/sync), avec exactement le même comportement.
"""
from __future__ import annotations

from dataclasses import dataclass

from redis import Redis
from sqlalchemy.orm import Session

from app.services import leaderboard, scoring, seed
from app.services.football_api import FootballApiClient


@dataclass
class FullSyncResult:
    teams_created: int
    matches_created: int
    matches_updated: int
    placeholders_resolved: int
    scores_recalculated: int
    leaderboard_size: int


def run_full_sync(db: Session, redis_client: Redis, client: FootballApiClient | None = None) -> FullSyncResult:
    """Exécute la chaîne complète et renvoie un résumé (utilisé pour le log du scheduler
    et la réponse de l'endpoint d'administration manuel)."""
    seed_result = seed.run_seed(db, client=client)
    score_result = scoring.sync_scores(db)
    leaderboard_size = leaderboard.rebuild_leaderboard(db, redis_client)

    return FullSyncResult(
        teams_created=seed_result.teams_created,
        matches_created=seed_result.matches_created,
        matches_updated=seed_result.matches_updated,
        placeholders_resolved=seed_result.placeholders_resolved,
        scores_recalculated=score_result.users_updated,
        leaderboard_size=leaderboard_size,
    )
