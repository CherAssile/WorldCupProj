from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import settings
from app.models.enums import MatchPhase
from app.models.match import Match
from app.services import scheduler
from app.services.sync_pipeline import FullSyncResult

NOW = datetime.now(timezone.utc)


def _clear_unsynced_past_matches(db_session: Session) -> None:
    """Le calendrier réel peut déjà contenir un match passé sans score (c'est précisément
    le bug que ce scheduler corrige, cf. match 104 -- il peut donc être présent au moment
    des tests) : à vider avant chaque scénario contrôlé, avec exactement le prédicat de
    _has_match_needing_sync, sinon le résultat dépendrait de l'état réel du calendrier
    plutôt que du seul match fabriqué par le test."""
    db_session.execute(
        text(
            "DELETE FROM predictions WHERE match_id IN "
            "(SELECT id FROM matches WHERE kickoff_at <= :now AND home_score IS NULL)"
        ),
        {"now": NOW},
    )
    db_session.execute(
        text(
            "DELETE FROM ai_predictions WHERE match_id IN "
            "(SELECT id FROM matches WHERE kickoff_at <= :now AND home_score IS NULL)"
        ),
        {"now": NOW},
    )
    db_session.execute(
        text("DELETE FROM matches WHERE kickoff_at <= :now AND home_score IS NULL"), {"now": NOW}
    )
    db_session.flush()


def _match(*, kickoff_at: datetime, home_score: int | None) -> Match:
    return Match(
        phase=MatchPhase.GROUP,
        kickoff_at=kickoff_at,
        home_score=home_score,
        away_score=home_score,
    )


def test_has_match_needing_sync_true_for_recent_match_without_score(db_session: Session) -> None:
    _clear_unsynced_past_matches(db_session)
    db_session.add(_match(kickoff_at=NOW - timedelta(hours=1), home_score=None))
    db_session.flush()

    assert scheduler._has_match_needing_sync(db_session) is True


def test_has_match_needing_sync_true_for_old_backlog_match_never_synced(db_session: Session) -> None:
    """Un match jamais synchronisé doit être rattrapé quel que soit son ancienneté (ex. au
    tout premier démarrage du scheduler, alors que le tournoi est déjà bien avancé) -- pas
    seulement s'il tombe dans une fenêtre glissante récente."""
    _clear_unsynced_past_matches(db_session)
    db_session.add(_match(kickoff_at=NOW - timedelta(days=30), home_score=None))
    db_session.flush()

    assert scheduler._has_match_needing_sync(db_session) is True


def test_has_match_needing_sync_false_when_kickoff_in_future(db_session: Session) -> None:
    _clear_unsynced_past_matches(db_session)
    db_session.add(_match(kickoff_at=NOW + timedelta(hours=1), home_score=None))
    db_session.flush()

    assert scheduler._has_match_needing_sync(db_session) is False


def test_has_match_needing_sync_false_once_score_recorded(db_session: Session) -> None:
    _clear_unsynced_past_matches(db_session)
    db_session.add(_match(kickoff_at=NOW - timedelta(hours=1), home_score=2))
    db_session.flush()

    assert scheduler._has_match_needing_sync(db_session) is False


def test_run_sync_tick_skips_full_sync_when_gate_is_false(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(scheduler, "SessionLocal", lambda: MagicMock())
    monkeypatch.setattr(scheduler, "_has_match_needing_sync", lambda db: False)
    fake_run_full_sync = MagicMock()
    monkeypatch.setattr(scheduler, "run_full_sync", fake_run_full_sync)

    scheduler.run_sync_tick()

    fake_run_full_sync.assert_not_called()


def test_run_sync_tick_runs_full_sync_when_gate_is_true(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_db = MagicMock()
    monkeypatch.setattr(scheduler, "SessionLocal", lambda: mock_db)
    monkeypatch.setattr(scheduler, "_has_match_needing_sync", lambda db: True)
    fake_result = FullSyncResult(
        teams_created=0, matches_created=0, matches_updated=1, placeholders_resolved=2,
        scores_recalculated=3, leaderboard_size=4,
    )
    fake_run_full_sync = MagicMock(return_value=fake_result)
    monkeypatch.setattr(scheduler, "run_full_sync", fake_run_full_sync)

    scheduler.run_sync_tick()

    fake_run_full_sync.assert_called_once()
    assert fake_run_full_sync.call_args.args[0] is mock_db
    mock_db.close.assert_called_once()
    mock_db.rollback.assert_not_called()


def test_run_sync_tick_rolls_back_and_swallows_exception_on_failure(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    """Une exécution en échec (source injoignable, réponse partielle) ne doit jamais faire
    planter le backend : elle est journalisée, la session annulée, le tick suivant réessaiera."""
    mock_db = MagicMock()
    monkeypatch.setattr(scheduler, "SessionLocal", lambda: mock_db)
    monkeypatch.setattr(scheduler, "_has_match_needing_sync", lambda db: True)
    monkeypatch.setattr(scheduler, "run_full_sync", MagicMock(side_effect=RuntimeError("source injoignable")))

    with caplog.at_level("ERROR"):
        scheduler.run_sync_tick()  # ne doit lever aucune exception

    mock_db.rollback.assert_called_once()
    mock_db.close.assert_called_once()
    assert "Échec de la synchro automatique" in caplog.text


def test_start_scheduler_returns_none_when_disabled() -> None:
    """Comportement réel pendant les tests (SYNC_SCHEDULER_ENABLED=false, cf. conftest.py) :
    vérifie à la fois le cas et l'absence d'effet de bord (aucun scheduler ne tourne)."""
    assert settings.sync_scheduler_enabled is False
    assert scheduler.start_scheduler() is None


def test_start_scheduler_schedules_job_when_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "sync_scheduler_enabled", True)
    monkeypatch.setattr(settings, "sync_interval_minutes", 7)

    started = scheduler.start_scheduler()
    try:
        assert started is not None
        job = started.get_job(scheduler.JOB_ID)
        assert job is not None
    finally:
        if started is not None:
            started.shutdown(wait=False)
