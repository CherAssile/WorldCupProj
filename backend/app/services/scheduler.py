"""Planifie la chaîne complète de synchronisation (app.services.sync_pipeline) en tâche
de fond, pour que le jeu vive sans intervention manuelle.

Une seule instance de backend est supposée (APScheduler en processus, pas de verrou
distribué) : si plusieurs instances du backend tournaient un jour en parallèle, chacune
planifierait sa propre tâche et la chaîne s'exécuterait en double (idempotente, donc sans
corruption de données, mais du travail redondant). À traiter avec un verrou distribué
(ex. Redis) ou un scheduler externe le jour où le backend est répliqué.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.match import Match
from app.redis_client import redis_client
from app.services.sync_pipeline import run_full_sync

logger = logging.getLogger(__name__)

JOB_ID = "full_sync"


def _has_match_needing_sync(db_session: Session) -> bool:
    """Un match dont le coup d'envoi est passé mais qui n'a toujours pas de score en base :
    en cours (un match dure ~2h, donc la fenêtre utile après le coup d'envoi est étroite),
    ou terminé mais pas encore synchronisé. Dans les deux cas, et dans ceux-là seulement,
    resynchroniser maintenant peut changer quelque chose -- inutile de retélécharger le
    calendrier et de recalculer tout le classement à chaque tick sinon.

    Aucune borne sur l'ancienneté du coup d'envoi : un match jamais encore synchronisé (ex.
    au tout premier démarrage de ce scheduler, alors que le tournoi est déjà bien avancé)
    doit être rattrapé quel que soit le retard, pas seulement s'il tombe dans une fenêtre
    glissante récente. Une fois son score connu, il sort définitivement de ce filtre : aucun
    travail répété une fois rattrapé.
    """
    now = datetime.now(timezone.utc)
    stmt = select(Match.id).where(Match.kickoff_at <= now, Match.home_score.is_(None)).limit(1)
    return db_session.execute(stmt).first() is not None


def run_sync_tick() -> None:
    """Un tick du scheduler. Ne relance la chaîne complète que si nécessaire (cf.
    _has_match_needing_sync) -- inutile de re-télécharger le calendrier et de recalculer
    tout le classement toutes les SYNC_INTERVAL_MINUTES quand rien n'a pu changer.

    Ne laisse jamais d'écriture partielle ni d'exception remonter au scheduler : une
    exécution en échec (source injoignable, réponse partielle) est journalisée, la session
    est annulée, et le tick suivant réessaiera -- chaque étape de la chaîne est idempotente.
    """
    db = SessionLocal()
    try:
        if not _has_match_needing_sync(db):
            logger.debug("Synchro ignorée : aucun match en cours ni en attente de résultat.")
            return

        result = run_full_sync(db, redis_client)
        logger.info(
            "Synchro automatique : %d match(s) mis à jour, %d placeholder(s) résolu(s), "
            "%d score(s) recalculé(s), %d joueur(s) classé(s).",
            result.matches_updated,
            result.placeholders_resolved,
            result.scores_recalculated,
            result.leaderboard_size,
        )
    except Exception:
        db.rollback()
        logger.exception("Échec de la synchro automatique -- le prochain tick réessaiera.")
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler | None:
    """Démarre le scheduler, sauf si désactivé (settings.sync_scheduler_enabled=False,
    notamment pendant les tests -- cf. tests/conftest.py)."""
    if not settings.sync_scheduler_enabled:
        logger.info("Scheduler de synchro désactivé (SYNC_SCHEDULER_ENABLED=false).")
        return None

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_sync_tick,
        trigger=IntervalTrigger(minutes=settings.sync_interval_minutes),
        id=JOB_ID,
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler de synchro démarré (toutes les %d minutes).", settings.sync_interval_minutes)
    return scheduler
