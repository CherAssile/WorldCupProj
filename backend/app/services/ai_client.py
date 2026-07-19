"""Client HTTP vers le service IA (ai-service), séparé et statistique (CLAUDE.md : pas
d'intégration LLM pour l'instant).

Contrat (cf. CLAUDE.md « Contrat backend ↔ ai-service ») : le service est autonome et ne
connaît pas le schéma de la base. On lui envoie des NOMS d'équipes (jamais des IDs), et
une date de référence pour les matchs passés (point-in-time). Toute erreur transitoire
(timeout, service indisponible, 5xx) est absorbée et renvoie None ; en revanche une
équipe que le modèle ne reconnaît pas (4xx) lève UnknownTeamError, pour que l'appelant
la traite explicitement (exclusion au tirage en entraînement, prédiction de repli en
compétitif) plutôt que de la confondre avec une panne.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 5.0
# Un calcul point-in-time (reference_date) refait le modèle sur les seules données
# antérieures : coûteux au premier appel pour une date donnée (~25s), puis mis en cache
# côté ai-service. On lui laisse donc un délai bien plus large que les appels ordinaires.
REFERENCE_DATE_TIMEOUT = 40.0

# Correspondance des noms de la table teams vers ceux du dataset du service IA, pour les
# quelques cas où ils diffèrent. Relevé empiriquement ; régénérer avec
# `python -m scripts.check_ai_team_coverage` si la base ou le service IA évoluent.
_AI_TEAM_NAME_OVERRIDES = {
    "USA": "United States",
    "Bosnia & Herzegovina": "Bosnia and Herzegovina",
}

@dataclass(frozen=True)
class MatchPrediction:
    predicted_home_score: int
    predicted_away_score: int


# Prédiction de repli neutre (match nul 1-1) quand le modèle ne connaît pas une équipe :
# des probabilités égales entre les trois issues donnent un nul comme résultat neutre. En
# compétitif, l'IA doit TOUJOURS produire une prédiction (elle concourt au classement, cf.
# CLAUDE.md) : on la persiste marquée is_fallback plutôt que de l'omettre.
NEUTRAL_FALLBACK_PREDICTION = MatchPrediction(predicted_home_score=1, predicted_away_score=1)


class UnknownTeamError(Exception):
    """Le service IA ne reconnaît pas une (ou les deux) équipe(s) : aucun historique, donc
    aucune vraie prédiction possible. Distinct d'une indisponibilité transitoire (None)."""

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


def ai_team_name(name: str) -> str:
    """Nom d'équipe tel que le dataset du service IA l'attend (mapping des cas divergents)."""
    return _AI_TEAM_NAME_OVERRIDES.get(name, name)


class AIClient:
    """Client vers ai-service. Une panne transitoire renvoie None (l'appelant ne plante
    jamais pour un service annexe indisponible) ; une équipe inconnue lève UnknownTeamError."""

    def __init__(self, base_url: str | None = None, timeout: float = DEFAULT_TIMEOUT) -> None:
        self._base_url = (base_url or settings.ai_service_url).rstrip("/")
        self._timeout = timeout

    def predict_match(
        self,
        home_team: str,
        away_team: str,
        reference_date: date | None = None,
        match_id: int | None = None,
    ) -> MatchPrediction | None:
        """Demande une prédiction de score à ai-service, par NOMS d'équipes.

        `reference_date` : date d'un match passé (entraînement) pour que le modèle ne
        calcule qu'avec l'antérieur (point-in-time) ; None pour un match à venir. Renvoie
        None si le service est indisponible/en erreur transitoire, lève UnknownTeamError
        si une équipe n'est pas reconnue (4xx)."""
        payload = {
            "home_team": ai_team_name(home_team),
            "away_team": ai_team_name(away_team),
            "reference_date": reference_date.isoformat() if reference_date is not None else None,
            "match_id": match_id,
        }
        label = f"{home_team} vs {away_team}"
        # Le refit point-in-time peut être long au premier appel pour une date : délai élargi.
        timeout = REFERENCE_DATE_TIMEOUT if reference_date is not None else self._timeout

        try:
            response = httpx.post(f"{self._base_url}/predict-match", json=payload, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            return MatchPrediction(
                predicted_home_score=data["predicted_home_score"],
                predicted_away_score=data["predicted_away_score"],
            )
        except httpx.HTTPStatusError as exc:
            # 4xx = requête non satisfiable pour ces équipes (équipe sans historique) : on
            # le remonte explicitement. 5xx = panne serveur transitoire : None.
            if exc.response.status_code in (400, 404):
                detail = _extract_detail(exc.response) or f"équipe(s) inconnue(s) ({label})"
                logger.info("Le service IA ne reconnaît pas une équipe (%s) : %s", label, detail)
                raise UnknownTeamError(detail) from exc
            logger.warning("Le service IA est en erreur (%s) pour %s : %s", exc.response.status_code, label, exc)
            return None
        except httpx.TimeoutException:
            logger.warning("Le service IA n'a pas répondu à temps (%.1fs) pour %s.", timeout, label)
            return None
        except httpx.HTTPError as exc:
            logger.warning("Le service IA est indisponible pour %s : %s", label, exc)
            return None
        except (KeyError, TypeError, ValueError) as exc:
            logger.warning("Réponse du service IA invalide pour %s : %s", label, exc)
            return None


def _extract_detail(response: httpx.Response) -> str | None:
    """Message d'erreur lisible renvoyé par le service IA (champ `detail` FastAPI), si présent."""
    try:
        detail = response.json().get("detail")
    except ValueError:
        return None
    return detail if isinstance(detail, str) else None
