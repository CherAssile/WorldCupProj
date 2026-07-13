from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import Session

from app.models.award import Award
from app.models.enums import AwardCategory, MatchPhase, MatchStatus
from app.models.match import Match
from app.services import awards_seed

# Date fabriquée, hors du vrai calendrier importé par services/seed.py : évite toute
# ambiguïté avec une éventuelle vraie finale déjà en base.
FINAL_KICKOFF = datetime(2031, 7, 19, 15, 0, tzinfo=timezone.utc)


def _clear_matches_and_create_final(db_session: Session, kickoff_at: datetime) -> Match:
    """Repart d'une base sans match ni récompense : le calendrier et les récompenses réels
    peuvent déjà exister (services/seed.py, services/awards_seed.py), ce qui rendrait ce
    test ambigu. Sans effet hors de la transaction de test."""
    db_session.query(Match).delete()
    db_session.query(Award).delete()
    db_session.flush()

    match = Match(
        home_team_id=None,
        away_team_id=None,
        home_placeholder="W101",
        away_placeholder="W102",
        phase=MatchPhase.FINAL,
        status=MatchStatus.SCHEDULED,
        kickoff_at=kickoff_at,
    )
    db_session.add(match)
    db_session.flush()
    return match


def test_awards_seed_requires_a_final_match(db_session: Session) -> None:
    """Sans finale connue dans le calendrier, impossible de caler la date limite."""
    db_session.query(Match).delete()
    db_session.flush()

    with pytest.raises(RuntimeError):
        awards_seed.run_seed(db_session)


def test_awards_seed_creates_three_categories_locked_at_final_kickoff(db_session: Session) -> None:
    _clear_matches_and_create_final(db_session, FINAL_KICKOFF)

    result = awards_seed.run_seed(db_session)
    assert result.created == 3

    awards = db_session.query(Award).all()
    assert {a.category for a in awards} == set(AwardCategory)
    assert all(a.lock_at == FINAL_KICKOFF for a in awards)


def test_awards_seed_is_idempotent(db_session: Session) -> None:
    _clear_matches_and_create_final(db_session, FINAL_KICKOFF)

    awards_seed.run_seed(db_session)
    second = awards_seed.run_seed(db_session)

    assert (second.created, second.updated) == (0, 0)
    assert db_session.query(Award).count() == 3
