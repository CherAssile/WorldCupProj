"""CLI d'alimentation des compositions d'équipe, via API-Football.

Confort d'affichage uniquement : n'entre dans AUCUN calcul de points, ne touche ni au
scoring ni au verrouillage ni à l'isolation entre modes.

Les compositions ne sont publiées qu'environ 1h avant le coup d'envoi : leur absence pour
un match à venir est un cas NORMAL (l'API renvoie une liste vide), jamais une erreur.

Quota (niveau gratuit, 100 requêtes/jour) : chaque composition coûte 1 requête
(+ 1 requête de résolution de fixture la première fois pour un match donné). Seuls les
matchs pertinents sont interrogés : les matchs à venir dans les 24h (priorité, données
périssables) puis les matchs déjà joués si le quota le permet. Un match dont les deux
compositions sont déjà enregistrées n'est jamais re-interrogé (idempotent). Dépendance
douce : nécessite que services/team_details_seed.py ait déjà résolu l'identifiant
API-Football des équipes du match, sinon celui-ci est ignoré proprement.

Usage : python -m app.services.lineups_seed
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.lineup import Lineup
from app.models.lineup_player import LineupPlayer
from app.models.match import Match
from app.models.player import Player
from app.services.api_football_client import (
    ApiFootballClient,
    ApiFootballError,
    ApiFootballQuotaExceeded,
    ApiFootballTeamLineup,
    LineupPlayerEntry,
)

logger = logging.getLogger(__name__)

UPCOMING_WINDOW = timedelta(hours=24)

# Constaté empiriquement (2026-07) : au-delà d'environ 3 requêtes rapprochées, l'API
# renvoie un 429 bien avant le quota journalier de 100 -- une limite par minute distincte,
# non documentée. Un délai proactif entre les appels évite de la déclencher inutilement.
DEFAULT_REQUEST_DELAY_SECONDS = 7.0


@dataclass
class SeedResult:
    lineups_imported: int = 0
    matches_not_yet_announced: int = 0
    matches_skipped_unresolved: int = 0
    quota_exceeded: bool = False


def _select_matches_to_process(db: Session) -> list[Match]:
    """Matchs à venir dans les 24h (priorité), puis matchs déjà joués."""
    now = datetime.now(timezone.utc)

    upcoming = db.execute(
        select(Match)
        .where(
            Match.kickoff_at >= now,
            Match.kickoff_at <= now + UPCOMING_WINDOW,
            Match.home_team_id.is_not(None),
            Match.away_team_id.is_not(None),
        )
        .order_by(Match.kickoff_at)
    ).scalars()

    played = db.execute(
        select(Match)
        .where(
            Match.home_score.is_not(None),
            Match.home_team_id.is_not(None),
            Match.away_team_id.is_not(None),
        )
        .order_by(Match.kickoff_at)
    ).scalars()

    seen_ids: set[int] = set()
    ordered: list[Match] = []
    for match in list(upcoming) + list(played):
        if match.id not in seen_ids:
            seen_ids.add(match.id)
            ordered.append(match)
    return ordered


def _lineup_count(db: Session, match_id: int) -> int:
    stmt = select(func.count()).select_from(Lineup).where(Lineup.match_id == match_id)
    return db.execute(stmt).scalar_one()


def _resolve_our_team_id(match: Match, api_team_id: int) -> int | None:
    if match.home_team.api_football_team_id == api_team_id:
        return match.home_team_id
    if match.away_team.api_football_team_id == api_team_id:
        return match.away_team_id
    return None


def _get_or_create_player(db: Session, team_id: int, entry: LineupPlayerEntry) -> Player:
    existing = db.execute(
        select(Player).where(Player.api_football_player_id == entry.api_player_id)
    ).scalar_one_or_none()
    if existing is not None:
        return existing

    player = Player(
        team_id=team_id,
        name=entry.name,
        position=entry.position,
        shirt_number=entry.shirt_number,
        api_football_player_id=entry.api_player_id,
    )
    db.add(player)
    db.flush()
    return player


def _write_lineup(
    db: Session, match: Match, team_id: int, api_fixture_id: int, api_lineup: ApiFootballTeamLineup
) -> None:
    lineup = Lineup(match_id=match.id, team_id=team_id, formation=api_lineup.formation, api_fixture_id=api_fixture_id)
    db.add(lineup)
    db.flush()
    for entry in api_lineup.players:
        player = _get_or_create_player(db, team_id, entry)
        db.add(
            LineupPlayer(
                lineup_id=lineup.id,
                player_id=player.id,
                position=entry.position,
                shirt_number=entry.shirt_number,
                is_starter=entry.is_starter,
            )
        )


def run_seed(
    db: Session, client: ApiFootballClient | None = None, request_delay_seconds: float = 0.0
) -> SeedResult:
    """`request_delay_seconds` : pause entre deux appels réels à API-Football (0 par
    défaut, pour ne pas ralentir les tests) -- voir main(), qui utilise une valeur prudente."""
    client = client or ApiFootballClient()
    result = SeedResult()

    for match in _select_matches_to_process(db):
        if _lineup_count(db, match.id) >= 2:
            continue  # déjà complet : aucune requête consommée

        if match.home_team is None or match.away_team is None:
            continue  # équipes pas encore connues (placeholder)

        home_api_id = match.home_team.api_football_team_id
        if home_api_id is None:
            logger.info(
                "Match %d ignoré : %s pas encore résolue côté API-Football "
                "(lancez d'abord services/team_details_seed.py).",
                match.id,
                match.home_team.name,
            )
            result.matches_skipped_unresolved += 1
            continue

        season = match.kickoff_at.year
        date_str = match.kickoff_at.date().isoformat()

        try:
            api_fixture_id = client.find_fixture_id(home_api_id, date_str, season)
            time.sleep(request_delay_seconds)
        except ApiFootballQuotaExceeded:
            result.quota_exceeded = True
            logger.warning(
                "Quota API-Football atteint après %d composition(s) importée(s) : arrêt "
                "propre, relancez le script plus tard pour continuer.",
                result.lineups_imported,
            )
            break
        except ApiFootballError as exc:
            time.sleep(request_delay_seconds)
            logger.info("Match %d : résolution du fixture API-Football impossible (%s).", match.id, exc)
            result.matches_skipped_unresolved += 1
            continue

        if api_fixture_id is None:
            logger.info("Match %d : fixture introuvable sur API-Football.", match.id)
            result.matches_skipped_unresolved += 1
            continue

        try:
            api_lineups = client.get_lineups(api_fixture_id)
            time.sleep(request_delay_seconds)
        except ApiFootballQuotaExceeded:
            result.quota_exceeded = True
            logger.warning(
                "Quota API-Football atteint après %d composition(s) importée(s) : arrêt "
                "propre, relancez le script plus tard pour continuer.",
                result.lineups_imported,
            )
            break
        except ApiFootballError as exc:
            time.sleep(request_delay_seconds)
            logger.info("Match %d : erreur lors de la récupération des compositions (%s).", match.id, exc)
            continue

        if not api_lineups:
            # Cas NORMAL : les compositions ne sortent qu'environ 1h avant le coup d'envoi.
            logger.info("Match %d : composition non encore annoncée.", match.id)
            result.matches_not_yet_announced += 1
            continue

        for api_lineup in api_lineups:
            our_team_id = _resolve_our_team_id(match, api_lineup.api_team_id)
            if our_team_id is None:
                logger.warning(
                    "Match %d : équipe API-Football %d non reconnue parmi les deux équipes du match.",
                    match.id,
                    api_lineup.api_team_id,
                )
                continue
            _write_lineup(db, match, our_team_id, api_fixture_id, api_lineup)

        db.commit()
        result.lineups_imported += 1

    return result


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    db = SessionLocal()
    try:
        result = run_seed(db, request_delay_seconds=DEFAULT_REQUEST_DELAY_SECONDS)
        logger.info(
            "Alimentation des compositions terminée : %d match(s) importé(s), "
            "%d composition(s) pas encore annoncée(s), %d match(s) ignoré(s)%s.",
            result.lineups_imported,
            result.matches_not_yet_announced,
            result.matches_skipped_unresolved,
            " -- quota atteint, à relancer plus tard" if result.quota_exceeded else "",
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
