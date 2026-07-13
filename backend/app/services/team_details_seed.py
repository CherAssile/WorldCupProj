"""CLI d'alimentation du contexte sportif : entraîneurs et effectifs, via API-Football.

Confort d'affichage uniquement : n'entre dans AUCUN calcul de points, ne touche ni au
scoring ni au verrouillage ni à l'isolation entre modes.

Idempotent et résumable -- l'identifiant API-Football de chaque équipe est mis en cache
dès sa première résolution (teams.api_football_team_id), pour ne jamais re-consommer de
quota inutilement sur les exécutions suivantes. Une équipe déjà pourvue d'un entraîneur,
ou d'au moins un joueur, n'est pas re-interrogée.

Niveau gratuit : 100 requêtes/jour. Un plein passage sur les 48 équipes nécessite jusqu'à
3 requêtes chacune la toute première fois (résolution + entraîneur + effectif), soit
jusqu'à 144 requêtes -- plus que le quota journalier. Le script s'arrête proprement dès
que le quota est atteint (chaque équipe traitée est validée avant de passer à la
suivante : jamais de donnée partielle écrite) et peut être relancé le lendemain pour
reprendre là où il s'est arrêté.

Usage : python -m app.services.team_details_seed
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.player import Player
from app.models.team import Team
from app.services.api_football_client import ApiFootballClient, ApiFootballQuotaExceeded

logger = logging.getLogger(__name__)

# Constaté empiriquement (2026-07) : au-delà d'environ 3 requêtes rapprochées, l'API
# renvoie un 429 bien avant le quota journalier de 100 -- une limite par minute distincte,
# non documentée. Un délai proactif entre les appels évite de la déclencher inutilement.
DEFAULT_REQUEST_DELAY_SECONDS = 7.0


@dataclass
class SeedResult:
    teams_resolved: int = 0
    coaches_updated: int = 0
    squads_imported: int = 0
    players_created: int = 0
    quota_exceeded: bool = False


def _has_players(db: Session, team_id: int) -> bool:
    stmt = select(func.count()).select_from(Player).where(Player.team_id == team_id)
    return db.execute(stmt).scalar_one() > 0


def run_seed(
    db: Session, client: ApiFootballClient | None = None, request_delay_seconds: float = 0.0
) -> SeedResult:
    """Résout l'identifiant API-Football de chaque équipe, renseigne son entraîneur actuel
    et importe son effectif. S'arrête proprement au premier dépassement de quota.

    `request_delay_seconds` : pause entre deux appels réels à API-Football (0 par défaut,
    pour ne pas ralentir les tests) -- voir main(), qui utilise une valeur prudente.
    """
    client = client or ApiFootballClient()
    result = SeedResult()
    teams = list(db.execute(select(Team).order_by(Team.id)).scalars())

    for team in teams:
        try:
            if team.api_football_team_id is None:
                api_team_id = client.find_team_id(team.name)
                time.sleep(request_delay_seconds)
                if api_team_id is None:
                    logger.warning("Équipe introuvable sur API-Football : %s", team.name)
                    continue
                team.api_football_team_id = api_team_id
                db.commit()
                result.teams_resolved += 1

            if team.coach_name is None:
                coach = client.get_current_coach(team.api_football_team_id)
                time.sleep(request_delay_seconds)
                if coach is None:
                    logger.info("Aucun entraîneur actuel trouvé pour %s.", team.name)
                else:
                    team.coach_name = coach.name
                    team.coach_photo_url = coach.photo_url
                    db.commit()
                    result.coaches_updated += 1

            if not _has_players(db, team.id):
                squad = client.get_squad(team.api_football_team_id)
                time.sleep(request_delay_seconds)
                for squad_player in squad:
                    db.add(
                        Player(
                            team_id=team.id,
                            name=squad_player.name,
                            position=squad_player.position,
                            shirt_number=squad_player.shirt_number,
                            api_football_player_id=squad_player.api_player_id,
                        )
                    )
                if squad:
                    db.commit()
                    result.squads_imported += 1
                    result.players_created += len(squad)
        except ApiFootballQuotaExceeded:
            # Aucun rollback nécessaire : chaque étape (résolution, entraîneur, effectif)
            # n'écrit qu'après un appel réussi, jamais avant -- l'exception est toujours
            # levée avant la moindre écriture pour l'itération en cours.
            result.quota_exceeded = True
            logger.warning(
                "Quota API-Football atteint après %d équipe(s) résolue(s), %d entraîneur(s), "
                "%d effectif(s) importé(s) : arrêt propre, relancez le script plus tard "
                "(quota réinitialisé chaque jour) pour continuer là où il s'est arrêté.",
                result.teams_resolved,
                result.coaches_updated,
                result.squads_imported,
            )
            break

    return result


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    db = SessionLocal()
    try:
        result = run_seed(db, request_delay_seconds=DEFAULT_REQUEST_DELAY_SECONDS)
        logger.info(
            "Alimentation du contexte sportif terminée : %d équipe(s) résolue(s), "
            "%d entraîneur(s) renseigné(s), %d effectif(s) importé(s) (%d joueur(s) créés)%s.",
            result.teams_resolved,
            result.coaches_updated,
            result.squads_imported,
            result.players_created,
            " -- quota atteint, à relancer plus tard" if result.quota_exceeded else "",
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
