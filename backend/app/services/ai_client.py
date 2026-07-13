"""Client HTTP vers le service IA (ai-service), séparé et statistique (CLAUDE.md : pas
d'intégration LLM pour l'instant). Ne persiste rien : se contente d'interroger le service
et de renvoyer le résultat, ou None si celui-ci est indisponible ou répond une erreur.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 5.0


@dataclass(frozen=True)
class MatchPrediction:
    predicted_home_score: int
    predicted_away_score: int


class AIClient:
    """Client vers ai-service. Toute erreur (timeout, service indisponible, réponse
    invalide) est absorbée et journalisée : l'appelant ne doit jamais planter à cause d'un
    service IA indisponible, qui reste une fonctionnalité annexe (pas de persistance ici)."""

    def __init__(self, base_url: str | None = None, timeout: float = DEFAULT_TIMEOUT) -> None:
        self._base_url = (base_url or settings.ai_service_url).rstrip("/")
        self._timeout = timeout

    def predict_match(
        self, home_team_id: int, away_team_id: int, match_id: int | None = None
    ) -> MatchPrediction | None:
        """Demande une prédiction de score à ai-service. None si le service ne répond pas
        (ou répond mal) plutôt que de lever une exception."""
        payload = {"home_team_id": home_team_id, "away_team_id": away_team_id, "match_id": match_id}

        try:
            response = httpx.post(f"{self._base_url}/predict-match", json=payload, timeout=self._timeout)
            response.raise_for_status()
            data = response.json()
            return MatchPrediction(
                predicted_home_score=data["predicted_home_score"],
                predicted_away_score=data["predicted_away_score"],
            )
        except httpx.TimeoutException:
            logger.warning(
                "Le service IA n'a pas répondu à temps (délai %.1fs) pour le match %s vs %s.",
                self._timeout,
                home_team_id,
                away_team_id,
            )
            return None
        except httpx.HTTPError as exc:
            logger.warning(
                "Le service IA est indisponible ou en erreur pour le match %s vs %s : %s",
                home_team_id,
                away_team_id,
                exc,
            )
            return None
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning(
                "Réponse du service IA invalide pour le match %s vs %s : %s", home_team_id, away_team_id, exc
            )
            return None
