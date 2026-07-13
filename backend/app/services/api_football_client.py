"""Client HTTP vers API-Football (api-sports.io).

Requiert FOOTBALL_API_KEY (aucun secret en dur, lu depuis app.config.settings). Niveau
gratuit : 100 requêtes/jour. Chaque appelant est responsable de gérer
ApiFootballQuotaExceeded proprement (arrêt propre, jamais un plantage ni une écriture de
données partielles) -- cf. services/team_details_seed.py et services/lineups_seed.py.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

BASE_URL = "https://v3.football.api-sports.io"
DEFAULT_TIMEOUT = 15.0


class ApiFootballError(Exception):
    """Erreur d'appel à API-Football (hors dépassement de quota, cf. sous-classe dédiée)."""


class ApiFootballQuotaExceeded(ApiFootballError):
    """Quota journalier atteint (100 requêtes/jour en niveau gratuit)."""


class ApiFootballNotConfigured(ApiFootballError):
    """FOOTBALL_API_KEY absente de la configuration."""


@dataclass(frozen=True)
class ApiFootballCoach:
    name: str
    photo_url: str | None


@dataclass(frozen=True)
class ApiFootballSquadPlayer:
    api_player_id: int
    name: str
    position: str | None
    shirt_number: int | None


@dataclass(frozen=True)
class LineupPlayerEntry:
    api_player_id: int
    name: str
    shirt_number: int | None
    position: str | None
    is_starter: bool


@dataclass(frozen=True)
class ApiFootballTeamLineup:
    api_team_id: int
    formation: str | None
    players: list[LineupPlayerEntry]


class ApiFootballClient:
    """Un appel HTTP = une méthode. Aucune logique de modèle ici, uniquement l'accès à la
    source et sa mise en forme en types neutres (mêmes principes que football_api.py)."""

    def __init__(self, api_key: str | None = None, timeout: float = DEFAULT_TIMEOUT) -> None:
        self._api_key = api_key if api_key is not None else settings.football_api_key
        self._timeout = timeout

    def _get(self, path: str, params: dict[str, str | int]) -> dict:
        if not self._api_key:
            raise ApiFootballNotConfigured(
                "FOOTBALL_API_KEY absente : ajoutez-la à .env pour utiliser API-Football."
            )

        try:
            response = httpx.get(
                f"{BASE_URL}{path}",
                headers={"x-apisports-key": self._api_key},
                params=params,
                timeout=self._timeout,
            )
        except httpx.HTTPError as exc:
            raise ApiFootballError(f"Appel à API-Football impossible ({path}) : {exc}") from exc

        if response.status_code == 429:
            raise ApiFootballQuotaExceeded("Quota API-Football dépassé (HTTP 429).")

        try:
            payload = response.json()
        except ValueError as exc:
            raise ApiFootballError(f"Réponse API-Football invalide sur {path} : {exc}") from exc

        errors = payload.get("errors")
        if errors:
            error_text = str(errors).lower()
            if "quota" in error_text or "rate limit" in error_text or "requests" in error_text:
                raise ApiFootballQuotaExceeded(f"Quota API-Football dépassé : {errors}")
            raise ApiFootballError(f"Erreur API-Football sur {path} : {errors}")

        return payload

    def find_team_id(self, team_name: str) -> int | None:
        """Résout le nom d'une équipe vers son identifiant API-Football. None si non trouvée."""
        payload = self._get("/teams", {"name": team_name})
        response = payload.get("response") or []
        if not response:
            return None
        return response[0]["team"]["id"]

    def get_current_coach(self, api_team_id: int) -> ApiFootballCoach | None:
        """Le endpoint renvoie l'historique complet des entraîneurs d'une équipe (passés
        et présent) : ne garde que celui dont la carrière pour cette équipe n'a pas
        (encore) de date de fin -- le titulaire actuel."""
        payload = self._get("/coachs", {"team": api_team_id})
        for coach in payload.get("response") or []:
            for stint in coach.get("career") or []:
                stint_team = stint.get("team") or {}
                if stint_team.get("id") == api_team_id and stint.get("end") is None:
                    return ApiFootballCoach(name=coach.get("name"), photo_url=coach.get("photo"))
        return None

    def get_squad(self, api_team_id: int) -> list[ApiFootballSquadPlayer]:
        """Effectif de l'équipe. Liste vide si non disponible (jamais une erreur)."""
        payload = self._get("/players/squads", {"team": api_team_id})
        response = payload.get("response") or []
        if not response:
            return []
        return [
            ApiFootballSquadPlayer(
                api_player_id=p["id"],
                name=p["name"],
                position=p.get("position"),
                shirt_number=p.get("number"),
            )
            for p in response[0].get("players") or []
        ]

    def find_fixture_id(self, api_team_id: int, date: str, season: int) -> int | None:
        """Résout un match (équipe + date + saison) vers son identifiant API-Football.

        `season` doit être une saison accessible au plan en cours : le niveau gratuit ne
        couvre qu'un sous-ensemble de saisons (2022-2024 au moment de l'écriture), ce qui
        peut faire échouer cette résolution pour un match récent -- géré comme une
        indisponibilité normale par l'appelant, jamais une erreur fatale.
        """
        payload = self._get("/fixtures", {"team": api_team_id, "date": date, "season": season})
        response = payload.get("response") or []
        if not response:
            return None
        return response[0]["fixture"]["id"]

    def get_lineups(self, api_fixture_id: int) -> list[ApiFootballTeamLineup]:
        """Compositions des deux équipes pour ce match. Liste vide si pas encore publiées
        (cas NORMAL : elles ne sortent qu'environ 1h avant le coup d'envoi), jamais une
        erreur."""
        payload = self._get("/fixtures/lineups", {"fixture": api_fixture_id})
        lineups: list[ApiFootballTeamLineup] = []
        for item in payload.get("response") or []:
            players: list[LineupPlayerEntry] = []
            for entry in item.get("startXI") or []:
                player = entry["player"]
                players.append(
                    LineupPlayerEntry(
                        api_player_id=player["id"],
                        name=player["name"],
                        shirt_number=player.get("number"),
                        position=player.get("pos"),
                        is_starter=True,
                    )
                )
            for entry in item.get("substitutes") or []:
                player = entry["player"]
                players.append(
                    LineupPlayerEntry(
                        api_player_id=player["id"],
                        name=player["name"],
                        shirt_number=player.get("number"),
                        position=player.get("pos"),
                        is_starter=False,
                    )
                )
            lineups.append(
                ApiFootballTeamLineup(
                    api_team_id=item["team"]["id"],
                    formation=item.get("formation"),
                    players=players,
                )
            )
        return lineups
