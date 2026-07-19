from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import create_access_token
from app.models.ai_prediction import AiPrediction
from app.models.enums import MatchPhase, MatchStatus
from app.models.match import Match
from app.models.prediction import Prediction
from app.models.team import Team
from app.models.user import User
from app.services.ai_client import MatchPrediction, UnknownTeamError
from app.services.ai_predictions import generate_ai_predictions

FUTURE_KICKOFF = datetime.now(timezone.utc) + timedelta(days=1)
PAST_KICKOFF = datetime.now(timezone.utc) - timedelta(days=1)


class _FakeAIClient:
    """Prédiction déterministe par noms d'équipes : ne dépend pas du vrai dataset IA."""

    def predict_match(self, home_team: str, away_team: str, reference_date=None, match_id=None) -> MatchPrediction:
        return MatchPrediction(predicted_home_score=2, predicted_away_score=1)


class _UnknownTeamAIClient:
    """Simule une équipe inconnue du modèle : lève systématiquement UnknownTeamError."""

    def predict_match(self, home_team: str, away_team: str, reference_date=None, match_id=None) -> MatchPrediction:
        raise UnknownTeamError(f"Équipe(s) inconnue(s) : {home_team}.")


def _clear_matches(db_session: Session) -> None:
    """Le calendrier réel peut déjà contenir des matchs à venir (les demies, tant qu'elles
    ne sont pas jouées) : generate_ai_predictions les traiterait aussi, faussant les
    comptages de ce test. Purge d'abord ai_predictions (FK vers matches), sans effet hors
    de la transaction de test."""
    # predictions ET ai_predictions référencent matches : purger les deux avant les matchs
    # (un vrai utilisateur a pu pronostiquer un match ; sans effet hors transaction de test).
    db_session.query(Prediction).delete()
    db_session.query(AiPrediction).delete()
    db_session.query(Match).delete()
    db_session.flush()


def _create_teams(db_session: Session, prefix: str) -> tuple[Team, Team]:
    code = prefix[:2].upper()
    home = Team(name=f"{prefix} Home", fifa_code=f"{code}H")
    away = Team(name=f"{prefix} Away", fifa_code=f"{code}A")
    db_session.add_all([home, away])
    db_session.flush()
    return home, away


def _create_match(
    db_session: Session,
    home: Team | None,
    away: Team | None,
    kickoff_at: datetime,
    home_score: int | None = None,
    away_score: int | None = None,
) -> Match:
    match = Match(
        home_team_id=home.id if home else None,
        away_team_id=away.id if away else None,
        home_placeholder=None if home else "W101",
        away_placeholder=None if away else "W102",
        phase=MatchPhase.GROUP,
        status=MatchStatus.FINISHED if home_score is not None else MatchStatus.SCHEDULED,
        kickoff_at=kickoff_at,
        home_score=home_score,
        away_score=away_score,
    )
    db_session.add(match)
    db_session.flush()
    return match


def test_generate_creates_predictions_for_upcoming_and_none_for_played(db_session: Session) -> None:
    _clear_matches(db_session)
    home1, away1 = _create_teams(db_session, "UPA")
    upcoming = _create_match(db_session, home1, away1, FUTURE_KICKOFF)

    home2, away2 = _create_teams(db_session, "PLY")
    played = _create_match(db_session, home2, away2, PAST_KICKOFF, home_score=2, away_score=1)

    result = generate_ai_predictions(db_session, ai_client=_FakeAIClient())
    assert result.created == 1
    assert result.skipped_ai_unavailable == 0
    assert result.fallback_predictions == 0

    upcoming_prediction = (
        db_session.query(AiPrediction).filter(AiPrediction.match_id == upcoming.id).one_or_none()
    )
    assert upcoming_prediction is not None

    played_prediction = db_session.query(AiPrediction).filter(AiPrediction.match_id == played.id).one_or_none()
    assert played_prediction is None
    assert db_session.query(AiPrediction).count() == 1


def test_generate_skips_matches_with_unresolved_teams(db_session: Session) -> None:
    _clear_matches(db_session)
    home, _away = _create_teams(db_session, "UNR")
    final = _create_match(db_session, home, None, FUTURE_KICKOFF)  # équipe "away" pas encore connue

    result = generate_ai_predictions(db_session, ai_client=_FakeAIClient())
    assert result.skipped_unresolved_teams == 1
    assert result.created == 0

    prediction = db_session.query(AiPrediction).filter(AiPrediction.match_id == final.id).one_or_none()
    assert prediction is None


def test_generate_serves_neutral_fallback_for_unknown_team(db_session: Session) -> None:
    """Équipe non reconnue par le modèle : l'IA sert quand même une prédiction (repli
    neutre marqué is_fallback), jamais un trou — elle concourt au classement (CLAUDE.md)."""
    _clear_matches(db_session)
    home, away = _create_teams(db_session, "FBK")
    match = _create_match(db_session, home, away, FUTURE_KICKOFF)

    result = generate_ai_predictions(db_session, ai_client=_UnknownTeamAIClient())
    assert result.created == 1
    assert result.fallback_predictions == 1
    assert result.skipped_ai_unavailable == 0

    prediction = db_session.query(AiPrediction).filter(AiPrediction.match_id == match.id).one()
    assert prediction.is_fallback is True
    assert prediction.predicted_home_score == prediction.predicted_away_score  # nul neutre


def test_regenerate_is_idempotent_and_updates_existing_prediction(db_session: Session) -> None:
    _clear_matches(db_session)
    home, away = _create_teams(db_session, "IDM")
    match = _create_match(db_session, home, away, FUTURE_KICKOFF)

    first = generate_ai_predictions(db_session, ai_client=_FakeAIClient())
    assert first.created == 1

    second = generate_ai_predictions(db_session, ai_client=_FakeAIClient())
    assert second.created == 0
    assert second.updated == 1

    assert db_session.query(AiPrediction).filter(AiPrediction.match_id == match.id).count() == 1


def test_regenerate_removes_stale_prediction_once_match_is_played(db_session: Session) -> None:
    _clear_matches(db_session)
    home, away = _create_teams(db_session, "STL")
    match = _create_match(db_session, home, away, FUTURE_KICKOFF)

    generate_ai_predictions(db_session, ai_client=_FakeAIClient())
    assert db_session.query(AiPrediction).filter(AiPrediction.match_id == match.id).count() == 1

    match.home_score = 3
    match.away_score = 0
    db_session.commit()

    result = generate_ai_predictions(db_session, ai_client=_FakeAIClient())
    assert result.removed_stale == 1
    assert db_session.query(AiPrediction).filter(AiPrediction.match_id == match.id).count() == 0


def test_get_ai_prediction_endpoint_404_then_200_after_generation(client: TestClient, db_session: Session) -> None:
    _clear_matches(db_session)
    home, away = _create_teams(db_session, "API")
    match = _create_match(db_session, home, away, FUTURE_KICKOFF)

    before = client.get(f"/matches/{match.id}/ai-prediction")
    assert before.status_code == 404

    generate_ai_predictions(db_session, ai_client=_FakeAIClient())

    after = client.get(f"/matches/{match.id}/ai-prediction")
    assert after.status_code == 200
    assert after.json()["match_id"] == match.id
    assert after.json()["is_fallback"] is False


def test_regenerate_endpoint_requires_admin(client: TestClient, db_session: Session) -> None:
    non_admin = User(email="regularai@example.com", username="regularai", hashed_password="x", is_admin=False)
    db_session.add(non_admin)
    db_session.flush()
    token = create_access_token(subject=str(non_admin.id))

    response = client.post("/ai-predictions/regenerate", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 403


def test_regenerate_endpoint_succeeds_for_admin(client: TestClient, db_session: Session) -> None:
    _clear_matches(db_session)
    admin = User(email="adminai@example.com", username="adminai", hashed_password="x", is_admin=True)
    db_session.add(admin)
    db_session.flush()
    home, away = _create_teams(db_session, "ADM")
    _create_match(db_session, home, away, FUTURE_KICKOFF)
    token = create_access_token(subject=str(admin.id))

    response = client.post("/ai-predictions/regenerate", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["created"] == 1
