"""Classement global compétitif, servi depuis un sorted set Redis alimenté par `scores`.

Départage : total de points, puis nombre de scores exacts, puis date de création du
compte (le plus ancien devant). Les trois niveaux sont encodés dans un unique score
Redis pondéré, pour que ZREVRANGE renvoie directement le classement complet et correct.
"""
from __future__ import annotations

from dataclasses import dataclass

from redis import Redis
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.score import Score
from app.models.user import User

LEADERBOARD_KEY = "leaderboard"

# Poids du score combiné : chaque palier de départage doit dominer entièrement le
# suivant, même aux bornes hautes réalistes (des centaines de points/scores exacts,
# jusqu'à 10^6 comptes). Marge large pour rester très en dessous de 2^53 (précision
# entière exacte d'un double), au-delà de laquelle Redis perdrait en précision.
_POINTS_WEIGHT = 10**10
_EXACT_SCORES_WEIGHT = 10**7
_MAX_USERS = 10**6


@dataclass
class LeaderboardEntry:
    rank: int
    user_id: int
    username: str
    total_points: int
    exact_scores_count: int


def _combined_score(total_points: int, exact_scores_count: int, age_rank: int) -> float:
    """Plus la valeur est grande, meilleur est le classement. `age_rank` vaut 0 pour le
    compte le plus ancien : il doit donc contribuer le plus fort parmi les ex æquo."""
    return total_points * _POINTS_WEIGHT + exact_scores_count * _EXACT_SCORES_WEIGHT + (_MAX_USERS - age_rank)


def rebuild_leaderboard(db: Session, redis_client: Redis) -> int:
    """Recalcule entièrement le sorted set Redis depuis la table scores.

    Remplace le classement précédent (ne l'accumule jamais) : rejouable sans effet de bord.
    """
    rows = db.execute(
        select(Score, User).join(User, Score.user_id == User.id).order_by(User.created_at.asc(), User.id.asc())
    ).all()

    redis_client.delete(LEADERBOARD_KEY)
    if not rows:
        return 0

    mapping = {
        str(score.user_id): _combined_score(score.total_points, score.exact_scores_count, age_rank)
        for age_rank, (score, _user) in enumerate(rows)
    }
    redis_client.zadd(LEADERBOARD_KEY, mapping)
    return len(mapping)


def get_leaderboard(db: Session, redis_client: Redis) -> list[LeaderboardEntry]:
    """Classement complet, du sorted set Redis vers des entrées enrichies (username, rang)."""
    ranked_user_ids = redis_client.zrevrange(LEADERBOARD_KEY, 0, -1)
    if not ranked_user_ids:
        return []

    user_ids = [int(uid) for uid in ranked_user_ids]
    rows = {
        score.user_id: (score, user)
        for score, user in db.execute(
            select(Score, User).join(User, Score.user_id == User.id).where(Score.user_id.in_(user_ids))
        ).all()
    }

    entries: list[LeaderboardEntry] = []
    for rank, user_id in enumerate(user_ids, start=1):
        score, user = rows[user_id]
        entries.append(
            LeaderboardEntry(
                rank=rank,
                user_id=user_id,
                username=user.username,
                total_points=score.total_points,
                exact_scores_count=score.exact_scores_count,
            )
        )
    return entries
