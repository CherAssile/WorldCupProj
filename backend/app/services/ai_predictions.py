"""Génère et stocke les pronostics IA des matchs compétitifs, via ai_client.

Aucune logique de modèle ici : ai-service est seul responsable de la prédiction elle-même
(cf. services/ai_client.py). Ce module se contente d'appeler le service puis de persister
le résultat dans `ai_predictions`.

Deux catégories de matchs traitées, différemment :
- À venir : (re)générées à chaque appel (le pronostic évolue avec les données
  disponibles), reference_date=None -- tout l'historique est légitime.
- Déjà joués : générées UNE SEULE FOIS (backfill, jamais réécrites ensuite -- le
  pronostic est un instantané figé de "ce que l'IA pensait à l'époque"), avec
  reference_date = date du match : sans cette date, une génération après coup verrait le
  résultat qu'elle est censée avoir prédit (même principe point-in-time qu'en
  entraînement, cf. CLAUDE.md). Sert au duel joueur/IA (GET /me/duel-ia) et à l'affichage
  du pronostic IA sur un match terminé.

Ne purge plus les pronostics devenus "obsolètes" (le match a depuis été joué) : cet
historique est précisément ce dont le duel a besoin -- le supprimer le détruirait.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.ai_prediction import AiPrediction
from app.models.match import Match
from app.services.ai_client import NEUTRAL_FALLBACK_PREDICTION, AIClient, UnknownTeamError

logger = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    created: int = 0
    updated: int = 0
    backfilled: int = 0
    skipped_unresolved_teams: int = 0
    skipped_ai_unavailable: int = 0
    fallback_predictions: int = 0


def _upcoming_matches(db: Session) -> list[Match]:
    """Matchs pas encore joués (résultat inconnu) dont les deux équipes sont connues,
    équipes préchargées (leurs noms partent au service IA)."""
    stmt = (
        select(Match)
        .options(joinedload(Match.home_team), joinedload(Match.away_team))
        .where(
            Match.home_score.is_(None),
            Match.home_team_id.is_not(None),
            Match.away_team_id.is_not(None),
        )
    )
    return list(db.execute(stmt).scalars())


def _finished_matches_missing_prediction(db: Session) -> list[Match]:
    """Matchs déjà joués sans pronostic IA enregistré : cible du backfill (une seule fois
    chacun, jamais régénérés ensuite)."""
    stmt = (
        select(Match)
        .options(joinedload(Match.home_team), joinedload(Match.away_team))
        .outerjoin(AiPrediction, AiPrediction.match_id == Match.id)
        .where(
            Match.home_score.is_not(None),
            Match.home_team_id.is_not(None),
            Match.away_team_id.is_not(None),
            AiPrediction.id.is_(None),
        )
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


def _predict_or_fallback(
    ai_client: AIClient, match: Match, *, reference_date, result: GenerationResult
):
    """Prédiction IA pour ce match, ou repli neutre si l'équipe est absente du dataset
    (l'IA doit TOUJOURS produire une prédiction en compétitif, cf. CLAUDE.md). None si le
    service est réellement indisponible (panne transitoire)."""
    try:
        prediction = ai_client.predict_match(
            home_team=match.home_team.name,
            away_team=match.away_team.name,
            reference_date=reference_date,
            match_id=match.id,
        )
        return prediction, False
    except UnknownTeamError:
        result.fallback_predictions += 1
        return NEUTRAL_FALLBACK_PREDICTION, True


def generate_ai_predictions(db: Session, ai_client: AIClient | None = None) -> GenerationResult:
    """(Re)génère les pronostics IA des matchs à venir, et comble ceux manquants pour les
    matchs déjà joués (backfill point-in-time, une seule fois chacun). Idempotent : un
    match déjà pronostiqué voit sa prédiction remplacée (à venir) ou ignorée (déjà joué),
    jamais dupliquée (unique par match_id)."""
    ai_client = ai_client or AIClient()
    result = GenerationResult(skipped_unresolved_teams=_count_unresolved_upcoming(db))

    upcoming = _upcoming_matches(db)
    existing_upcoming = (
        {
            prediction.match_id: prediction
            for prediction in db.execute(
                select(AiPrediction).where(AiPrediction.match_id.in_([m.id for m in upcoming]))
            ).scalars()
        }
        if upcoming
        else {}
    )

    for match in upcoming:
        # Match à venir : pas de date de référence (tout l'historique est légitime).
        prediction, is_fallback = _predict_or_fallback(ai_client, match, reference_date=None, result=result)
        if prediction is None:
            result.skipped_ai_unavailable += 1
            continue

        row = existing_upcoming.get(match.id)
        if row is None:
            db.add(
                AiPrediction(
                    match_id=match.id,
                    predicted_home_score=prediction.predicted_home_score,
                    predicted_away_score=prediction.predicted_away_score,
                    is_fallback=is_fallback,
                )
            )
            result.created += 1
        else:
            row.predicted_home_score = prediction.predicted_home_score
            row.predicted_away_score = prediction.predicted_away_score
            row.is_fallback = is_fallback
            result.updated += 1

    for match in _finished_matches_missing_prediction(db):
        # Match déjà joué : reference_date = date du match, sinon l'IA verrait le résultat
        # qu'elle est censée avoir prédit (point-in-time, même hors mode entraînement).
        prediction, is_fallback = _predict_or_fallback(
            ai_client, match, reference_date=match.kickoff_at.date(), result=result
        )
        if prediction is None:
            result.skipped_ai_unavailable += 1
            continue

        db.add(
            AiPrediction(
                match_id=match.id,
                predicted_home_score=prediction.predicted_home_score,
                predicted_away_score=prediction.predicted_away_score,
                is_fallback=is_fallback,
            )
        )
        result.backfilled += 1

    db.commit()
    return result
