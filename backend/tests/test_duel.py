from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.ai_prediction import AiPrediction
from app.models.enums import MatchPhase, MatchStatus
from app.models.match import Match
from app.models.prediction import Prediction
from app.models.team import Team

PASSWORD = "correcthorsebattery"
PAST_KICKOFF = datetime.now(timezone.utc) - timedelta(days=1)


def _register_and_login(client: TestClient, email: str) -> dict[str, str]:
    username = email.split("@")[0].replace("-", "_")
    client.post("/auth/register", json={"email": email, "username": username, "password": PASSWORD})
    login = client.post("/auth/login", data={"username": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create_teams(db_session: Session, prefix: str) -> tuple[Team, Team]:
    code = prefix[:2].upper()
    home = Team(name=f"{prefix} Home", fifa_code=f"{code}H")
    away = Team(name=f"{prefix} Away", fifa_code=f"{code}A")
    db_session.add_all([home, away])
    db_session.flush()
    return home, away


def _finished_match(
    db_session: Session, home: Team, away: Team, phase: MatchPhase, home_score: int, away_score: int
) -> Match:
    match = Match(
        home_team_id=home.id,
        away_team_id=away.id,
        phase=phase,
        status=MatchStatus.FINISHED,
        kickoff_at=PAST_KICKOFF,
        home_score=home_score,
        away_score=away_score,
        winner_team_id=home.id if home_score > away_score else away.id,
    )
    db_session.add(match)
    db_session.flush()
    return match


def test_duel_totals_match_sum_of_per_match_points(client: TestClient, db_session: Session) -> None:
    """Le duel cumulé est exactement la somme des points par match des deux
    compétiteurs -- l'exigence de vérification en live, exercée ici en test."""
    headers = _register_and_login(client, "duel-sum@example.com")
    me = client.get("/auth/me", headers=headers).json()

    home1, away1 = _create_teams(db_session, "AA1")
    match1 = _finished_match(db_session, home1, away1, MatchPhase.GROUP, 2, 1)  # non doublé

    home2, away2 = _create_teams(db_session, "BB2")
    match2 = _finished_match(db_session, home2, away2, MatchPhase.QUARTER_FINAL, 1, 1)  # doublé

    # Match 1 : utilisateur exact (3 pts), IA issue correcte seulement (1 pt).
    db_session.add(Prediction(user_id=me["id"], match_id=match1.id, predicted_home_score=2, predicted_away_score=1))
    db_session.add(AiPrediction(match_id=match1.id, predicted_home_score=1, predicted_away_score=0, is_fallback=False))
    # Match 2 (doublé) : utilisateur exact (3*2=6), IA aussi exacte (3*2=6) -> égalité.
    db_session.add(Prediction(user_id=me["id"], match_id=match2.id, predicted_home_score=1, predicted_away_score=1))
    db_session.add(AiPrediction(match_id=match2.id, predicted_home_score=1, predicted_away_score=1, is_fallback=False))
    db_session.flush()

    response = client.get("/me/duel-ia", headers=headers)
    assert response.status_code == 200
    body = response.json()

    my_result1 = next(r for r in body["results"] if r["match_id"] == match1.id)
    my_result2 = next(r for r in body["results"] if r["match_id"] == match2.id)
    assert my_result1["user_points"] == 3
    assert my_result1["ai_points"] == 1
    assert my_result2["user_points"] == 6
    assert my_result2["ai_points"] == 6
    assert my_result2["doubled"] is True

    # Vérification exacte demandée : le total cumulé = somme des points par match.
    assert body["user_total_points"] == my_result1["user_points"] + my_result2["user_points"] == 9
    assert body["ai_total_points"] == my_result1["ai_points"] + my_result2["ai_points"] == 7
    assert body["gap"] == 2
    assert body["matches_compared"] == 2
    assert body["matches_user_ahead"] == 1  # match1
    assert body["matches_tied"] == 1  # match2
    assert body["matches_ai_ahead"] == 0


def test_duel_lists_unpredicted_finished_match_without_counting_it(client: TestClient, db_session: Session) -> None:
    """Un match terminé non pronostiqué par l'utilisateur apparaît dans results (user_points
    = None, distinct de 0), mais ne compte pas dans les totaux/comparaisons cumulés."""
    headers = _register_and_login(client, "duel-skip@example.com")
    home, away = _create_teams(db_session, "DSK")
    match = _finished_match(db_session, home, away, MatchPhase.GROUP, 1, 0)
    db_session.add(AiPrediction(match_id=match.id, predicted_home_score=1, predicted_away_score=0, is_fallback=False))
    db_session.flush()

    response = client.get("/me/duel-ia", headers=headers)
    assert response.status_code == 200
    body = response.json()

    result = next(r for r in body["results"] if r["match_id"] == match.id)
    assert result["user_points"] is None
    assert result["ai_points"] == 3  # l'IA, elle, a bien un pronostic ici

    assert body["matches_compared"] == 0
    assert body["user_total_points"] == 0
    assert body["ai_total_points"] == 0


def test_duel_missing_ai_prediction_shows_none(client: TestClient, db_session: Session) -> None:
    """Aucun pronostic IA pour ce match (historique pas encore comblé) : ai_points est
    None, pas 0 -- distinct d'un pronostic IA à 0 point."""
    headers = _register_and_login(client, "duel-noai@example.com")
    home, away = _create_teams(db_session, "NOA")
    match = _finished_match(db_session, home, away, MatchPhase.GROUP, 2, 0)

    me = client.get("/auth/me", headers=headers).json()
    db_session.add(
        Prediction(user_id=me["id"], match_id=match.id, predicted_home_score=2, predicted_away_score=0)
    )
    db_session.flush()

    response = client.get("/me/duel-ia", headers=headers)
    result = next(r for r in response.json()["results"] if r["match_id"] == match.id)
    assert result["user_points"] == 3
    assert result["ai_predicted_home_score"] is None
    assert result["ai_points"] is None
    assert response.json()["matches_compared"] == 0  # pas de vraie confrontation sans les deux


def test_duel_endpoint_never_writes_to_scores_or_leaderboard(client: TestClient, db_session: Session) -> None:
    """Test obligatoire (isolation) : consulter le duel est une lecture pure, aucune
    écriture dans scores/predictions/ai_predictions."""
    from sqlalchemy import select

    from app.models.ai_prediction import AiPrediction as AiPredictionModel
    from app.models.score import Score

    headers = _register_and_login(client, "duel-readonly@example.com")
    home, away = _create_teams(db_session, "DRO")
    match = _finished_match(db_session, home, away, MatchPhase.GROUP, 1, 1)
    me = client.get("/auth/me", headers=headers).json()
    db_session.add(Prediction(user_id=me["id"], match_id=match.id, predicted_home_score=1, predicted_away_score=1))
    db_session.flush()

    scores_before = sorted(
        (s.id, s.user_id, s.total_points) for s in db_session.execute(select(Score)).scalars()
    )
    ai_predictions_before = sorted(
        (a.id, a.match_id, a.predicted_home_score) for a in db_session.execute(select(AiPredictionModel)).scalars()
    )

    response = client.get("/me/duel-ia", headers=headers)
    assert response.status_code == 200

    scores_after = sorted(
        (s.id, s.user_id, s.total_points) for s in db_session.execute(select(Score)).scalars()
    )
    ai_predictions_after = sorted(
        (a.id, a.match_id, a.predicted_home_score) for a in db_session.execute(select(AiPredictionModel)).scalars()
    )
    assert scores_after == scores_before
    assert ai_predictions_after == ai_predictions_before
