from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import settings
from app.crud import training as training_crud
from app.deps import get_ai_client
from app.main import app
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
from app.services.ai_client import MatchPrediction

PASSWORD = "correcthorsebattery"

# Score IA déterministe (jamais le vrai service) : le duel dépend d'une prédiction fixe,
# pas du dataset du modèle. Distinct d'un score exact courant pour rester probant.
_FAKE_AI_SCORE = (1, 0)


class _FakeAIClient:
    def predict_match(self, home_team: str, away_team: str, reference_date=None, match_id=None) -> MatchPrediction:
        return MatchPrediction(predicted_home_score=_FAKE_AI_SCORE[0], predicted_away_score=_FAKE_AI_SCORE[1])


@pytest.fixture(autouse=True)
def _use_fake_ai_client():
    """Remplace le client du service IA par un faux, pour tout ce module : les tests du
    duel ne doivent pas dépendre du vrai dataset (cf. injection de dépendance get_ai_client)."""
    app.dependency_overrides[get_ai_client] = lambda: _FakeAIClient()
    yield
    app.dependency_overrides.pop(get_ai_client, None)


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

    # L'IA (faux client injecté) prédit _FAKE_AI_SCORE : on en dérive ses points attendus.
    expected_ai_points = scoring.score_training_guess(_FAKE_AI_SCORE[0], _FAKE_AI_SCORE[1], match)

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
    assert body["ai_predicted_home_score"] == _FAKE_AI_SCORE[0]
    assert body["ai_predicted_away_score"] == _FAKE_AI_SCORE[1]
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


def test_draw_excludes_teams_unknown_to_ai(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Un match dont une équipe est inconnue du service IA n'est jamais tiré : le duel
    serait une impasse (l'IA ne peut pas pronostiquer). Les autres restent tirables."""
    unknown = Team(name="ZZ Unknown To AI", fifa_code="ZZU")
    opponent = Team(name="ZZ Known Opponent", fifa_code="ZZK")
    db_session.add_all([unknown, opponent])
    db_session.flush()
    monkeypatch.setattr(settings, "ai_unknown_teams", "ZZ Unknown To AI")

    excluded = HistoricalMatch(
        home_team_id=unknown.id, away_team_id=opponent.id, edition_year=2002,
        phase=MatchPhase.GROUP, played_at=datetime(2002, 6, 1, tzinfo=timezone.utc),
        home_score=1, away_score=0,
    )
    db_session.add(excluded)
    db_session.flush()
    normal, _h, _a = _create_historical_match(db_session, "ZOK", 2, 2)

    headers = _register_and_login(client, "drawexcl@example.com")
    user_id = _get_user_id(db_session, "drawexcl@example.com")
    session = _draw_full_pool_session(db_session, user_id)

    drawn_ids = {sm.historical_match_id for sm in training_crud.get_session_matches(db_session, session.id)}
    assert excluded.id not in drawn_ids  # exclu du tirage
    assert normal.id in drawn_ids  # équipe connue : bien tiré


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
