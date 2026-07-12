from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

DEFAULT_SOURCE_URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"
DEFAULT_FALLBACK_PATH = Path(__file__).resolve().parent.parent / "data" / "worldcup_2026_fallback.json"

_TIME_PATTERN = re.compile(r"^(\d{2}):(\d{2}) UTC([+-]\d+)$")
_PLACEHOLDER_TEAM_PATTERN = re.compile(r"^[WL]\d+$")


@dataclass(frozen=True)
class Team:
    """Équipe telle que dérivée du calendrier, indépendamment du fournisseur."""

    name: str
    group: str | None


@dataclass(frozen=True)
class Match:
    """Match du calendrier, indépendant du fournisseur.

    `round_label` reste le libellé brut de la source (ex. "Matchday 3", "Round of 16") :
    sa correspondance avec notre enum MatchPhase est une décision métier laissée à l'appelant.

    `home_team`/`away_team` valent None tant que l'équipe n'est pas encore connue (ex. la
    finale, avant la fin des demies) : `home_placeholder`/`away_placeholder` portent alors
    la référence brute de la source (ex. "W101" = vainqueur du match 101).

    `home_score`/`away_score` sont le score du temps réglementaire (seul utilisé pour le
    scoring des pronostics). `extra_time_*`/`penalties_*` ne servent qu'à déterminer
    `winner_team`, l'équipe qualifiée tous prolongements confondus.
    """

    round_label: str
    kickoff_at: datetime
    num: int | None
    home_team: str | None
    away_team: str | None
    home_placeholder: str | None
    away_placeholder: str | None
    home_score: int | None
    away_score: int | None
    extra_time_home_score: int | None
    extra_time_away_score: int | None
    penalties_home_score: int | None
    penalties_away_score: int | None
    winner_team: str | None


@dataclass(frozen=True)
class Tournament:
    teams: list[Team]
    matches: list[Match]


def _is_placeholder_team(name: str) -> bool:
    """Avant qu'un tour éliminatoire ne soit joué, la source référence l'équipe qualifiée
    par le numéro du match dont elle est issue (ex. "W101" = vainqueur du match 101)."""
    return bool(_PLACEHOLDER_TEAM_PATTERN.match(name))


def _parse_kickoff_at(date: str, time_str: str) -> datetime:
    match = _TIME_PATTERN.match(time_str)
    if match is None:
        raise ValueError(f"Format d'heure inattendu : {time_str!r}")
    hour, minute, offset_hours = match.groups()
    tz = timezone(timedelta(hours=int(offset_hours)))
    naive = datetime.strptime(f"{date} {hour}:{minute}", "%Y-%m-%d %H:%M")
    return naive.replace(tzinfo=tz)


def _resolve_winner(
    home_team: str | None,
    away_team: str | None,
    full_time: list[int] | None,
    extra_time: list[int] | None,
    penalties: list[int] | None,
) -> str | None:
    """Équipe qualifiée tous prolongements confondus : tirs au but > prolongation > temps
    réglementaire. None si les deux équipes ne sont pas encore connues, ou si le match
    (de groupe) se termine sur un nul sans qu'aucun des trois scores ne le départage."""
    if home_team is None or away_team is None:
        return None
    for score in (penalties, extra_time, full_time):
        if score is None:
            continue
        home_goals, away_goals = score
        if home_goals > away_goals:
            return home_team
        if away_goals > home_goals:
            return away_team
    return None


def _parse_match(raw: dict) -> Match:
    # Le pronostic porte sur le temps réglementaire (règle du projet) : "ft" (full time)
    # alimente seul home_score/away_score. "et"/"p" ne servent qu'à déterminer le vainqueur.
    score = raw.get("score") or {}
    full_time = score.get("ft")
    extra_time = score.get("et")
    penalties = score.get("p")

    home_score, away_score = (full_time[0], full_time[1]) if full_time else (None, None)
    extra_time_home_score, extra_time_away_score = (extra_time[0], extra_time[1]) if extra_time else (None, None)
    penalties_home_score, penalties_away_score = (penalties[0], penalties[1]) if penalties else (None, None)

    team1, team2 = raw["team1"], raw["team2"]
    home_team = None if _is_placeholder_team(team1) else team1
    away_team = None if _is_placeholder_team(team2) else team2

    return Match(
        round_label=raw["round"],
        kickoff_at=_parse_kickoff_at(raw["date"], raw["time"]),
        num=raw.get("num"),
        home_team=home_team,
        away_team=away_team,
        home_placeholder=team1 if home_team is None else None,
        away_placeholder=team2 if away_team is None else None,
        home_score=home_score,
        away_score=away_score,
        extra_time_home_score=extra_time_home_score,
        extra_time_away_score=extra_time_away_score,
        penalties_home_score=penalties_home_score,
        penalties_away_score=penalties_away_score,
        winner_team=_resolve_winner(home_team, away_team, full_time, extra_time, penalties),
    )


def _derive_teams(raw_matches: list[dict]) -> list[Team]:
    """Équipes distinctes des matchs, avec leur groupe (connu dès la phase de poules)."""
    groups_by_team: dict[str, str | None] = {}

    for raw in raw_matches:
        group = raw.get("group")
        if group is None:
            continue
        for team_name in (raw["team1"], raw["team2"]):
            if not _is_placeholder_team(team_name):
                groups_by_team.setdefault(team_name, group)

    for raw in raw_matches:
        for team_name in (raw["team1"], raw["team2"]):
            if not _is_placeholder_team(team_name):
                groups_by_team.setdefault(team_name, None)

    return [Team(name=name, group=group) for name, group in sorted(groups_by_team.items())]


class FootballApiClient:
    """Encapsule la source du calendrier (actuellement openfootball, JSON public sans clé API).

    Le reste de l'application ne manipule que les types Team/Match définis dans ce module :
    changer de fournisseur se limite à réécrire l'analyse faite ici.
    """

    def __init__(
        self,
        source_url: str = DEFAULT_SOURCE_URL,
        fallback_path: Path = DEFAULT_FALLBACK_PATH,
        timeout: float = 10.0,
    ) -> None:
        self._source_url = source_url
        self._fallback_path = fallback_path
        self._timeout = timeout

    def fetch_tournament(self) -> Tournament:
        payload = self._load_payload()
        raw_matches = payload["matches"]

        matches = [_parse_match(raw) for raw in raw_matches]
        teams = _derive_teams(raw_matches)
        return Tournament(teams=teams, matches=matches)

    def _load_payload(self) -> dict:
        try:
            response = httpx.get(self._source_url, timeout=self._timeout)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as exc:
            logger.warning(
                "Téléchargement du calendrier impossible (%s), repli sur la copie locale %s.",
                exc,
                self._fallback_path,
            )
            return self._load_fallback()

    def _load_fallback(self) -> dict:
        try:
            with self._fallback_path.open(encoding="utf-8") as f:
                return json.load(f)
        except OSError as exc:
            raise RuntimeError(
                "Impossible de charger le calendrier : ni le réseau ni la copie locale "
                f"({self._fallback_path}) ne sont disponibles."
            ) from exc
