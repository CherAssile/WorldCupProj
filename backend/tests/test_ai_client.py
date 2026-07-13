import httpx
import pytest

from app.services.ai_client import AIClient, MatchPrediction


def test_predict_match_calls_real_mock_endpoint() -> None:
    """Contre le vrai service IA (mock /predict-match du conteneur ai-service)."""
    client = AIClient()

    prediction = client.predict_match(home_team_id=1, away_team_id=2)

    assert prediction is not None
    assert isinstance(prediction, MatchPrediction)
    assert isinstance(prediction.predicted_home_score, int)
    assert isinstance(prediction.predicted_away_score, int)


def test_predict_match_handles_timeout_without_raising(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*args: object, **kwargs: object) -> None:
        raise httpx.TimeoutException("délai dépassé (simulé)")

    monkeypatch.setattr("app.services.ai_client.httpx.post", _raise)

    client = AIClient()
    prediction = client.predict_match(home_team_id=1, away_team_id=2)

    assert prediction is None


def test_predict_match_handles_connection_error_without_raising(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*args: object, **kwargs: object) -> None:
        raise httpx.ConnectError("service indisponible (simulé)")

    monkeypatch.setattr("app.services.ai_client.httpx.post", _raise)

    client = AIClient()
    prediction = client.predict_match(home_team_id=1, away_team_id=2)

    assert prediction is None


def test_predict_match_handles_http_error_status_without_raising(monkeypatch: pytest.MonkeyPatch) -> None:
    """Le service répond, mais avec une erreur serveur (5xx) : ne doit pas planter l'appelant."""
    request = httpx.Request("POST", "http://ai-service:8001/predict-match")
    error_response = httpx.Response(500, request=request)

    def _post(*args: object, **kwargs: object) -> httpx.Response:
        return error_response

    monkeypatch.setattr("app.services.ai_client.httpx.post", _post)

    client = AIClient()
    prediction = client.predict_match(home_team_id=1, away_team_id=2)

    assert prediction is None


def test_predict_match_handles_malformed_response_without_raising(monkeypatch: pytest.MonkeyPatch) -> None:
    """Réponse 200 mais au contenu inattendu : ne doit pas planter l'appelant."""
    request = httpx.Request("POST", "http://ai-service:8001/predict-match")
    malformed_response = httpx.Response(200, json={"unexpected": "shape"}, request=request)

    def _post(*args: object, **kwargs: object) -> httpx.Response:
        return malformed_response

    monkeypatch.setattr("app.services.ai_client.httpx.post", _post)

    client = AIClient()
    prediction = client.predict_match(home_team_id=1, away_team_id=2)

    assert prediction is None
