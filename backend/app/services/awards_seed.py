"""CLI d'alimentation des catégories de récompenses (awards).

Idempotent. La date limite (lock_at) de chaque catégorie est calée sur le coup d'envoi
de la finale du tournoi en cours : nécessite que services/seed.py ait déjà importé le
calendrier (la finale existe dès l'import, même avant que ses deux participants ne
soient connus).

Usage : python -m app.services.awards_seed
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.award import Award
from app.models.enums import AwardCategory, MatchPhase
from app.models.match import Match

logger = logging.getLogger(__name__)


@dataclass
class SeedResult:
    created: int
    updated: int


def _resolve_lock_at(db: Session) -> datetime:
    stmt = select(Match).where(Match.phase == MatchPhase.FINAL).order_by(Match.kickoff_at.desc())
    final_match = db.execute(stmt).scalars().first()
    if final_match is None:
        raise RuntimeError(
            "Aucun match de finale trouvé : lancez d'abord services/seed.py pour importer le calendrier."
        )
    return final_match.kickoff_at


def run_seed(db: Session) -> SeedResult:
    """Crée les 3 catégories si absentes, ou aligne leur date limite sur la finale."""
    lock_at = _resolve_lock_at(db)
    existing = {award.category: award for award in db.execute(select(Award)).scalars()}

    created = 0
    updated = 0

    for category in AwardCategory:
        award = existing.get(category)
        if award is None:
            db.add(Award(category=category, lock_at=lock_at))
            created += 1
        elif award.lock_at != lock_at:
            award.lock_at = lock_at
            updated += 1

    db.commit()
    return SeedResult(created=created, updated=updated)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    db = SessionLocal()
    try:
        result = run_seed(db)
        logger.info(
            "Alimentation des récompenses terminée : %d créée(s), %d mise(s) à jour.",
            result.created,
            result.updated,
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
