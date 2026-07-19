"""Compare les équipes de la base au dataset du service IA.

Sert à régénérer la liste AI_UNKNOWN_TEAMS (cf. config.py) : une équipe présente dans
la base mais absente du dataset du service IA ne peut pas recevoir de vraie prédiction.
En entraînement on l'exclut du tirage, en compétitif on lui sert une prédiction de repli.

Le dataset du service IA et le contenu de la base évoluent indépendamment : relancer ce
script après un ré-import du calendrier ou une mise à jour du service IA, et reporter la
liste « inconnues APRÈS mapping » dans AI_UNKNOWN_TEAMS.

Usage (depuis le conteneur backend) :
    docker compose exec backend python -m scripts.check_ai_team_coverage
"""
from __future__ import annotations

import httpx
from sqlalchemy import select

from app.config import settings
from app.database import SessionLocal
from app.models.historical_match import HistoricalMatch
from app.models.team import Team
from app.services.ai_client import ai_team_name


def _distinct_team_names() -> list[str]:
    """Noms distincts référencés par historical_matches (le pool du mode entraînement)."""
    with SessionLocal() as db:
        stmt = select(Team.name).where(
            Team.id.in_(
                select(HistoricalMatch.home_team_id).union(select(HistoricalMatch.away_team_id))
            )
        )
        return sorted(name for name in db.execute(stmt).scalars())


def _is_known(name: str) -> bool:
    """Le service IA reconnaît-il ce nom (après mapping) ? 200 = oui, sinon inconnu."""
    response = httpx.post(
        f"{settings.ai_service_url.rstrip('/')}/predict-match",
        json={"home_team": ai_team_name(name), "away_team": "France"},
        timeout=10.0,
    )
    return response.status_code == 200


def main() -> None:
    names = _distinct_team_names()
    unknown = [name for name in names if not _is_known(name)]

    print(f"{len(names)} équipes testées, {len(unknown)} inconnue(s) après mapping :")
    for name in unknown:
        print(f"  - {name}")
    if unknown:
        print("\nÀ reporter dans AI_UNKNOWN_TEAMS (config.py / variable d'env) :")
        print("  " + ",".join(unknown))


if __name__ == "__main__":
    main()
