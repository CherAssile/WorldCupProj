"""Génère et stocke les pronostics IA des matchs à venir, via ai_client.

Aucune logique de modèle ici : ai-service est seul responsable de la prédiction elle-même
(cf. services/ai_client.py). Ce module se contente d'appeler le service puis de persister
le résultat dans `ai_predictions` -- un par match à venir, jamais pour un match déjà joué.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ai_prediction import AiPrediction
from app.models.match import Match
from app.services.ai_client import AIClient

logger = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    created: int = 0
    updated: int = 0
    removed_stale: int = 0
    skipped_unresolved_teams: int = 0
    skipped_ai_unavailable: int = 0


def _upcoming_matches(db: Session) -> list[Match]:
    """Matchs pas encore joués (résultat inconnu) dont les deux équipes sont connues."""
    stmt = select(Match).where(
        Match.home_score.is_(None),
        Match.home_team_id.is_not(None),
        Match.away_team_id.is_not(None),
    )
    return list(db.execute(stmt).scalars())


def _count_unresolved_upcoming(db: Session) -> int:
    """Matchs pas encore joués mais dont une équipe reste un placeholder (ex. la finale
    avant la fin des demies) : pas de pronostic IA possible tant que non résolus."""
    stmt = select(func.count()).select_from(Match).where(
        Match.home_score.is_(None),
        (Match.home_team_id.is_(None)) | (Match.away_team_id.is_(None)),
    )
    return db.execute(stmt).scalar_one()


def generate_ai_predictions(db: Session, ai_client: AIClient | None = None) -> GenerationResult:
    """(Re)génère une prédiction IA pour chaque match à venir. Idempotent : un match déjà
    pronostiqué voit sa prédiction remplacée, jamais dupliquée (unique par match_id).

    Purge aussi tout pronostic IA devenu obsolète (le match a depuis été joué) : après
    génération, ai_predictions ne contient jamais d'entrée pour un match déjà joué.
    """
    ai_client = ai_client or AIClient()
    result = GenerationResult(skipped_unresolved_teams=_count_unresolved_upcoming(db))

    matches = _upcoming_matches(db)
    match_ids = [match.id for match in matches]
    existing = (
        {
            prediction.match_id: prediction
            for prediction in db.execute(
                select(AiPrediction).where(AiPrediction.match_id.in_(match_ids))
            ).scalars()
        }
        if match_ids
        else {}
    )

    for match in matches:
        prediction = ai_client.predict_match(
            home_team_id=match.home_team_id, away_team_id=match.away_team_id, match_id=match.id
        )
        if prediction is None:
            result.skipped_ai_unavailable += 1
            continue

        row = existing.get(match.id)
        if row is None:
            db.add(
                AiPrediction(
                    match_id=match.id,
                    predicted_home_score=prediction.predicted_home_score,
                    predicted_away_score=prediction.predicted_away_score,
                )
            )
            result.created += 1
        else:
            row.predicted_home_score = prediction.predicted_home_score
            row.predicted_away_score = prediction.predicted_away_score
            result.updated += 1

    stale_rows = db.execute(
        select(AiPrediction).join(Match, AiPrediction.match_id == Match.id).where(Match.home_score.is_not(None))
    ).scalars()
    for row in stale_rows:
        db.delete(row)
        result.removed_stale += 1

    db.commit()
    return result
