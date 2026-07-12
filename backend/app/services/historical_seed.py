"""CLI d'alimentation de historical_matches, réserve du mode entraînement.

Source : dataset public "International football results from 1872 to 2026" (mirror
du dataset Kaggle du même nom), filtré aux matchs de Coupe du Monde. Idempotent :
peut être relancé sans créer de doublon (utile pour récupérer des scores mis à jour).

N'importe que les matchs entre deux équipes déjà présentes dans `teams` (alimentée par
services/seed.py) : les nations disparues ou absentes du tournoi 2026 (Yougoslavie,
Tchécoslovaquie, Italie...) sont ignorées plutôt que de fabriquer des données pour elles.

Usage : python -m app.services.historical_seed
"""
from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import httpx
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.enums import MatchPhase
from app.models.historical_match import HistoricalMatch
from app.models.team import Team

logger = logging.getLogger(__name__)

DEFAULT_SOURCE_URL = "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
DEFAULT_FALLBACK_PATH = Path(__file__).resolve().parent.parent / "data" / "fifa_world_cup_results_fallback.csv"

# Le dataset orthographie certaines équipes différemment de notre table teams
# (alimentée depuis openfootball) : ce sont pourtant les mêmes nations.
_TEAM_NAME_ALIASES: dict[str, str] = {
    "United States": "USA",
    "Bosnia and Herzegovina": "Bosnia & Herzegovina",
}

# Le dataset ne renseigne pas le tour (poule, quart, finale...) : phase par défaut.
# Sans incidence sur le mode entraînement, qui ne fait pas jouer le multiplicateur
# x2 (réservé aux phases finales du tournoi en cours) de la même façon qu'au compétitif.
_DEFAULT_PHASE = MatchPhase.GROUP


@dataclass
class SeedResult:
    matches_created: int
    matches_updated: int
    skipped_unknown_teams: int


def _normalize_team_name(name: str) -> str:
    return _TEAM_NAME_ALIASES.get(name, name)


def _played_at(date_str: str) -> datetime:
    return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def _load_rows(source_url: str, fallback_path: Path, timeout: float = 15.0) -> list[dict[str, str]]:
    try:
        response = httpx.get(source_url, timeout=timeout)
        response.raise_for_status()
        text = response.text
    except httpx.HTTPError as exc:
        logger.warning(
            "Téléchargement du dataset impossible (%s), repli sur la copie locale %s.",
            exc,
            fallback_path,
        )
        text = fallback_path.read_text(encoding="utf-8")

    return list(csv.DictReader(io.StringIO(text)))


def run_seed(
    db: Session,
    source_url: str = DEFAULT_SOURCE_URL,
    fallback_path: Path = DEFAULT_FALLBACK_PATH,
) -> SeedResult:
    """Importe les matchs de Coupe du Monde passés entre équipes déjà connues. Idempotent."""
    rows = _load_rows(source_url, fallback_path)

    team_ids = {team.name: team.id for team in db.query(Team).all()}
    existing = {(m.home_team_id, m.away_team_id, m.played_at): m for m in db.query(HistoricalMatch).all()}

    created = 0
    updated = 0
    skipped_unknown_teams = 0

    for row in rows:
        if row["tournament"] != "FIFA World Cup":
            continue
        if row["home_score"] in ("NA", "") or row["away_score"] in ("NA", ""):
            continue

        home_id = team_ids.get(_normalize_team_name(row["home_team"]))
        away_id = team_ids.get(_normalize_team_name(row["away_team"]))
        if home_id is None or away_id is None:
            skipped_unknown_teams += 1
            continue

        played_at = _played_at(row["date"])
        home_score = int(row["home_score"])
        away_score = int(row["away_score"])
        key = (home_id, away_id, played_at)

        match = existing.get(key)
        if match is None:
            match = HistoricalMatch(
                home_team_id=home_id,
                away_team_id=away_id,
                edition_year=played_at.year,
                phase=_DEFAULT_PHASE,
                played_at=played_at,
                home_score=home_score,
                away_score=away_score,
            )
            db.add(match)
            existing[key] = match
            created += 1
        elif (match.home_score, match.away_score) != (home_score, away_score):
            match.home_score = home_score
            match.away_score = away_score
            updated += 1

    db.commit()
    return SeedResult(matches_created=created, matches_updated=updated, skipped_unknown_teams=skipped_unknown_teams)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    db = SessionLocal()
    try:
        result = run_seed(db)
        logger.info(
            "Alimentation historique terminée : %d match(s) créé(s), %d mis à jour, "
            "%d ignoré(s) (équipe inconnue de notre table teams).",
            result.matches_created,
            result.matches_updated,
            result.skipped_unknown_teams,
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
