"""CLI d'alimentation du calendrier (équipes + matchs) depuis la source football_api.

Idempotent : peut être relancé à tout moment (ex. pour récupérer les scores des
matchs joués depuis la dernière exécution) sans créer de doublons.

Usage : python -m app.services.seed
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.enums import MatchPhase, MatchStatus
from app.models.match import Match
from app.models.team import Team
from app.services.football_api import FootballApiClient, Match as ApiMatch, Team as ApiTeam

logger = logging.getLogger(__name__)

# Round of 32, Round of 16, Quarter-final, Semi-final, Final = phases finales.
# "Matchday N" (phase de poules) est traité séparément, cf. _resolve_phase.
_ROUND_TO_PHASE: dict[str, MatchPhase] = {
    "Round of 32": MatchPhase.ROUND_OF_32,
    "Round of 16": MatchPhase.ROUND_OF_16,
    "Quarter-final": MatchPhase.QUARTER_FINAL,
    "Semi-final": MatchPhase.SEMI_FINAL,
    "Match for third place": MatchPhase.THIRD_PLACE,
    "Final": MatchPhase.FINAL,
}

# La source (openfootball) ne fournit pas de code FIFA à 3 lettres : référentiel fixe
# pour les 48 équipes du format 2026, propre à notre alimentation (pas à football_api.py).
_FIFA_CODES: dict[str, str] = {
    "Algeria": "ALG",
    "Argentina": "ARG",
    "Australia": "AUS",
    "Austria": "AUT",
    "Belgium": "BEL",
    "Bosnia & Herzegovina": "BIH",
    "Brazil": "BRA",
    "Canada": "CAN",
    "Cape Verde": "CPV",
    "Colombia": "COL",
    "Croatia": "CRO",
    "Curaçao": "CUW",
    "Czech Republic": "CZE",
    "DR Congo": "COD",
    "Ecuador": "ECU",
    "Egypt": "EGY",
    "England": "ENG",
    "France": "FRA",
    "Germany": "GER",
    "Ghana": "GHA",
    "Haiti": "HAI",
    "Iran": "IRN",
    "Iraq": "IRQ",
    "Ivory Coast": "CIV",
    "Japan": "JPN",
    "Jordan": "JOR",
    "Mexico": "MEX",
    "Morocco": "MAR",
    "Netherlands": "NED",
    "New Zealand": "NZL",
    "Norway": "NOR",
    "Panama": "PAN",
    "Paraguay": "PAR",
    "Portugal": "POR",
    "Qatar": "QAT",
    "Saudi Arabia": "KSA",
    "Scotland": "SCO",
    "Senegal": "SEN",
    "South Africa": "RSA",
    "South Korea": "KOR",
    "Spain": "ESP",
    "Sweden": "SWE",
    "Switzerland": "SUI",
    "Tunisia": "TUN",
    "Turkey": "TUR",
    "USA": "USA",
    "Uruguay": "URU",
    "Uzbekistan": "UZB",
}


@dataclass
class SeedResult:
    teams_created: int
    matches_created: int
    matches_updated: int


def _resolve_phase(round_label: str) -> MatchPhase:
    if round_label.startswith("Matchday"):
        return MatchPhase.GROUP
    try:
        return _ROUND_TO_PHASE[round_label]
    except KeyError as exc:
        raise ValueError(f"Round inconnu, impossible de le rattacher à une phase : {round_label!r}") from exc


def _resolve_fifa_code(team_name: str) -> str:
    try:
        return _FIFA_CODES[team_name]
    except KeyError as exc:
        raise ValueError(f"Aucun code FIFA connu pour l'équipe {team_name!r}") from exc


def _upsert_teams(db: Session, api_teams: list[ApiTeam]) -> tuple[dict[str, int], int]:
    """Renvoie (nom -> id, nombre créés). Met aussi à jour le groupe si désormais connu."""
    existing = {team.name: team for team in db.query(Team).all()}
    created = 0

    for api_team in api_teams:
        team = existing.get(api_team.name)
        if team is None:
            team = Team(name=api_team.name, fifa_code=_resolve_fifa_code(api_team.name), group_name=api_team.group)
            db.add(team)
            db.flush()
            existing[api_team.name] = team
            created += 1
        elif api_team.group and team.group_name != api_team.group:
            team.group_name = api_team.group

    return {name: team.id for name, team in existing.items()}, created


def _resolve_team_id(team_ids: dict[str, int], team_name: str | None) -> int | None:
    """None si l'équipe n'est pas encore connue (placeholder) ; lève si un nom réel est inconnu."""
    if team_name is None:
        return None
    try:
        return team_ids[team_name]
    except KeyError as exc:
        raise ValueError(f"Équipe inconnue en base : {team_name!r}") from exc


def _upsert_matches(db: Session, api_matches: list[ApiMatch], team_ids: dict[str, int]) -> tuple[int, int]:
    """Dédoublonne par `num` quand disponible (stable même pour des équipes encore
    inconnues), sinon par (équipes, coup d'envoi). Le repli par équipes+coup d'envoi
    couvre aussi la ré-alimentation d'une base où `num` n'était pas encore renseigné.
    """
    all_existing = db.query(Match).all()
    existing_by_num = {m.num: m for m in all_existing if m.num is not None}
    existing_by_teams_kickoff = {(m.home_team_id, m.away_team_id, m.kickoff_at): m for m in all_existing}

    created = 0
    updated = 0

    for api_match in api_matches:
        home_id = _resolve_team_id(team_ids, api_match.home_team)
        away_id = _resolve_team_id(team_ids, api_match.away_team)
        phase = _resolve_phase(api_match.round_label)
        status = MatchStatus.FINISHED if api_match.home_score is not None else MatchStatus.SCHEDULED

        match = existing_by_num.get(api_match.num) if api_match.num is not None else None
        if match is None:
            match = existing_by_teams_kickoff.get((home_id, away_id, api_match.kickoff_at))

        values = {
            "phase": phase,
            "status": status,
            "home_team_id": home_id,
            "away_team_id": away_id,
            "home_placeholder": api_match.home_placeholder,
            "away_placeholder": api_match.away_placeholder,
            "num": api_match.num,
            "home_score": api_match.home_score,
            "away_score": api_match.away_score,
        }

        if match is None:
            match = Match(kickoff_at=api_match.kickoff_at, **values)
            db.add(match)
            created += 1
        elif any(getattr(match, field) != value for field, value in values.items()):
            for field, value in values.items():
                setattr(match, field, value)
            updated += 1

        if api_match.num is not None:
            existing_by_num[api_match.num] = match
        existing_by_teams_kickoff[(home_id, away_id, api_match.kickoff_at)] = match

    return created, updated


def run_seed(db: Session, client: FootballApiClient | None = None) -> SeedResult:
    """Importe équipes et matchs. Rejouable sans créer de doublons."""
    client = client or FootballApiClient()
    tournament = client.fetch_tournament()

    team_ids, teams_created = _upsert_teams(db, tournament.teams)
    matches_created, matches_updated = _upsert_matches(db, tournament.matches, team_ids)

    db.commit()
    return SeedResult(teams_created=teams_created, matches_created=matches_created, matches_updated=matches_updated)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    db = SessionLocal()
    try:
        result = run_seed(db)
        logger.info(
            "Alimentation terminée : %d équipe(s) créée(s), %d match(s) créé(s), %d match(s) mis à jour.",
            result.teams_created,
            result.matches_created,
            result.matches_updated,
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
