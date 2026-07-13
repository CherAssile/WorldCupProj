from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.crud import training as training_crud
from app.models.enums import MatchPhase, MatchStatus
from app.models.historical_match import HistoricalMatch
from app.models.match import Match
from app.models.prediction import Prediction
from app.models.score import Score
from app.models.team import Team
from app.models.training_session import TrainingSession
from app.models.user import User
from app.redis_client import redis_client
from app.services import leaderboard, scoring
from app.services.ai_client import AIClient

PASSWORD = "correcthorsebattery"


def _register_and_login(client: TestClient, email: str) -> dict[str, str]:
    username = email.split("@")[0]
    client.post("/auth/register", json={"email": email, "username": username, "password": PASSWORD})
    login = client.post("/auth/login", data={"username": email, "password": PASSWORD})
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create_historical_match(
    db_session: Session, prefix: str, home_score: int, away_score: int
) -> tuple[HistoricalMatch, Team, Team]:
    code = prefix[:2].upper()
    home = Team(name=f"{prefix} Home", fifa_code=f"{code}H")
    away = Team(name=f"{prefix} Away", fifa_code=f"{code}A")
    db_session.add_all([home, away])
    db_session.flush()

    match = HistoricalMatch(
        home_team_id=home.id,
        away_team_id=away.id,
        edition_year=1998,
        phase=MatchPhase.GROUP,
        played_at=datetime(1998, 6, 1, tzinfo=timezone.utc),
        home_score=home_score,
        away_score=away_score,
    )
    db_session.add(match)
    db_session.flush()
    return match, home, away


def _draw_full_pool_session(db_session: Session, user_id: int) -> TrainingSession:
    """Tire TOUT le pool de matchs historiques disponibles à cet instant.

    Le vrai stock (557 matchs, plus d'éventuelles vraies sessions déjà jouées par de
    vrais utilisateurs) ne peut pas être supprimé pour ces tests -- une session réelle
    y référence déjà des lignes (contrainte de clé étrangère). Tirer l'intégralité du
    pool garantit de façon déterministe qu'un match créé juste avant est bien inclus,
    sans jamais toucher aux données existantes.
    """
    total = db_session.execute(select(func.count()).select_from(HistoricalMatch)).scalar_one()
    return training_crud.create_session(db_session, user_id=user_id, match_count=total)


def _get_user_id(db_session: Session, email: str) -> int:
    return db_session.execute(select(User).where(User.email == email)).scalar_one().id


def test_submit_prediction_reveals_score_and_computes_points(client: TestClient, db_session: Session) -> None:
    match, home, away = _create_historical_match(db_session, "SUB", home_score=2, away_score=1)
    headers = _register_and_login(client, "scorer@example.com")
    user_id = _get_user_id(db_session, "scorer@example.com")
    session = _draw_full_pool_session(db_session, user_id)

    expected_ai = AIClient().predict_match(home_team_id=home.id, away_team_id=away.id)
    assert expected_ai is not None
    expected_ai_points = scoring.score_training_guess(
        expected_ai.predicted_home_score, expected_ai.predicted_away_score, match
    )

    response = client.post(
        f"/training/sessions/{session.id}/predictions/{match.id}",
        json={"predicted_home_score": 2, "predicted_away_score": 1},  # score exact
        headers=headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["home_score"] == 2
    assert body["away_score"] == 1
    assert body["user_points"] == 3
    assert body["ai_predicted_home_score"] == expected_ai.predicted_home_score
    assert body["ai_predicted_away_score"] == expected_ai.predicted_away_score
    assert body["ai_points"] == expected_ai_points


def test_double_submission_rejected(client: TestClient, db_session: Session) -> None:
    match, _home, _away = _create_historical_match(db_session, "DBL", 1, 1)
    headers = _register_and_login(client, "doubletrain@example.com")
    user_id = _get_user_id(db_session, "doubletrain@example.com")
    session = _draw_full_pool_session(db_session, user_id)

    payload = {"predicted_home_score": 1, "predicted_away_score": 1}
    first = client.post(f"/training/sessions/{session.id}/predictions/{match.id}", json=payload, headers=headers)
    assert first.status_code == 200

    second = client.post(f"/training/sessions/{session.id}/predictions/{match.id}", json=payload, headers=headers)
    assert second.status_code == 409


def test_submit_prediction_for_match_not_in_session_rejected(client: TestClient, db_session: Session) -> None:
    headers = _register_and_login(client, "outsider@example.com")
    user_id = _get_user_id(db_session, "outsider@example.com")
    session = _draw_full_pool_session(db_session, user_id)

    # Créé APRÈS le tirage : ne peut structurellement pas faire partie de la session.
    match_outside, _home, _away = _create_historical_match(db_session, "OUT", 2, 2)

    response = client.post(
        f"/training/sessions/{session.id}/predictions/{match_outside.id}",
        json={"predicted_home_score": 0, "predicted_away_score": 0},
        headers=headers,
    )
    assert response.status_code == 404


def test_submit_prediction_rejects_other_users_session(client: TestClient, db_session: Session) -> None:
    """Test obligatoire (isolation/anti-triche) : un utilisateur ne peut ni consulter ni
    pronostiquer dans la session d'entraînement d'un autre (404, jamais 403, pour ne pas
    même révéler que la session existe)."""
    match, _home, _away = _create_historical_match(db_session, "INT", 1, 0)
    owner_headers = _register_and_login(client, "owner-train@example.com")
    owner_id = _get_user_id(db_session, "owner-train@example.com")
    session = _draw_full_pool_session(db_session, owner_id)

    intruder_headers = _register_and_login(client, "intruder-train@example.com")
    response = client.post(
        f"/training/sessions/{session.id}/predictions/{match.id}",
        json={"predicted_home_score": 1, "predicted_away_score": 0},
        headers=intruder_headers,
    )
    assert response.status_code == 404

    # Rien n'a été écrit sous le nom de l'intrus, ni sous celui du propriétaire.
    results = client.get(f"/training/sessions/{session.id}/results", headers=owner_headers)
    assert results.json()["results"] == []


def test_results_endpoint_shows_only_submitted_matches_and_totals(client: TestClient, db_session: Session) -> None:
    match1, _h1, _a1 = _create_historical_match(db_session, "RX1", 1, 1)
    match2, _h2, _a2 = _create_historical_match(db_session, "YZ2", 3, 0)
    headers = _register_and_login(client, "results@example.com")
    user_id = _get_user_id(db_session, "results@example.com")
    session = _draw_full_pool_session(db_session, user_id)

    before = client.get(f"/training/sessions/{session.id}/results", headers=headers)
    assert before.status_code == 200
    assert before.json()["results"] == []
    assert before.json()["completed"] is False

    client.post(
        f"/training/sessions/{session.id}/predictions/{match1.id}",
        json={"predicted_home_score": 1, "predicted_away_score": 1},
        headers=headers,
    )
    partial = client.get(f"/training/sessions/{session.id}/results", headers=headers)
    assert len(partial.json()["results"]) == 1
    assert partial.json()["completed"] is False

    client.post(
        f"/training/sessions/{session.id}/predictions/{match2.id}",
        json={"predicted_home_score": 3, "predicted_away_score": 0},
        headers=headers,
    )
    after = client.get(f"/training/sessions/{session.id}/results", headers=headers)
    body = after.json()
    assert len(body["results"]) == 2
    assert {r["historical_match_id"] for r in body["results"]} == {match1.id, match2.id}
    submitted_ids = {r["historical_match_id"] for r in body["results"]}
    assert submitted_ids == {match1.id, match2.id}
    assert body["user_total_points"] == 3 + 3
    # completed=True n'est garanti que si la session tirée == exactement ces 2 matchs ;
    # ici la session couvre tout le pool, donc completed reste False tant que le reste
    # n'est pas pronostiqué -- seul le comptage par match nous intéresse ici.


def test_training_session_never_writes_to_competitive_tables_or_leaderboard(
    client: TestClient, db_session: Session
) -> None:
    """Test obligatoire : jouer une session d'entraînement (tirage -> pronostic ->
    résultats) ne doit STRICTEMENT rien changer dans predictions, scores, ou le classement
    Redis (isolation du mode entraînement, cf. CLAUDE.md).

    Pré-remplit du contenu compétitif réel avant l'instantané, pour que le test soit
    probant : un avant/après sur des tables vides ne prouverait pas grand-chose.
    """
    dummy_user = User(email="dummy_competitive@example.com", username="dummycomp", hashed_password="x")
    dummy_home = Team(name="Dummy Competitive Home", fifa_code="DCH")
    dummy_away = Team(name="Dummy Competitive Away", fifa_code="DCA")
    db_session.add_all([dummy_user, dummy_home, dummy_away])
    db_session.flush()

    dummy_match = Match(
        home_team_id=dummy_home.id,
        away_team_id=dummy_away.id,
        phase=MatchPhase.GROUP,
        status=MatchStatus.SCHEDULED,
        kickoff_at=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db_session.add(dummy_match)
    db_session.flush()

    db_session.add(
        Prediction(user_id=dummy_user.id, match_id=dummy_match.id, predicted_home_score=2, predicted_away_score=1)
    )
    db_session.add(Score(user_id=dummy_user.id, total_points=42, exact_scores_count=3))
    db_session.flush()

    redis_client.delete(leaderboard.LEADERBOARD_KEY)
    leaderboard.rebuild_leaderboard(db_session, redis_client)

    try:
        predictions_before = sorted(
            (p.id, p.user_id, p.match_id, p.predicted_home_score, p.predicted_away_score, p.predicted_winner_team_id)
            for p in db_session.execute(select(Prediction)).scalars()
        )
        scores_before = sorted(
            (s.id, s.user_id, s.total_points, s.exact_scores_count)
            for s in db_session.execute(select(Score)).scalars()
        )
        leaderboard_before = redis_client.zrange(leaderboard.LEADERBOARD_KEY, 0, -1, withscores=True)

        # Joue une session d'entraînement complète (tirage -> pronostic pour chaque match
        # tiré -> résultats), via l'API telle qu'un vrai utilisateur l'utiliserait. Peu
        # importe quels matchs historiques sont tirés : seule l'isolation nous intéresse ici.
        headers = _register_and_login(client, "trainee_isolation@example.com")
        created = client.post("/training/sessions", json={"match_count": 2}, headers=headers)
        assert created.status_code == 201
        session_id = created.json()["id"]

        for drawn_match in created.json()["matches"]:
            submitted = client.post(
                f"/training/sessions/{session_id}/predictions/{drawn_match['historical_match_id']}",
                json={"predicted_home_score": 1, "predicted_away_score": 0},
                headers=headers,
            )
            assert submitted.status_code == 200

        results = client.get(f"/training/sessions/{session_id}/results", headers=headers)
        assert results.status_code == 200
        assert results.json()["completed"] is True

        predictions_after = sorted(
            (p.id, p.user_id, p.match_id, p.predicted_home_score, p.predicted_away_score, p.predicted_winner_team_id)
            for p in db_session.execute(select(Prediction)).scalars()
        )
        scores_after = sorted(
            (s.id, s.user_id, s.total_points, s.exact_scores_count)
            for s in db_session.execute(select(Score)).scalars()
        )
        leaderboard_after = redis_client.zrange(leaderboard.LEADERBOARD_KEY, 0, -1, withscores=True)

        assert predictions_after == predictions_before
        assert scores_after == scores_before
        assert leaderboard_after == leaderboard_before
    finally:
        redis_client.delete(leaderboard.LEADERBOARD_KEY)
