from datetime import date

import httpx
import pytest

from app.services.ai_client import AIClient, MatchPrediction, UnknownTeamError, ai_team_name


def test_predict_match_calls_real_mock_endpoint() -> None:
    """Contre le vrai service IA : par NOMS d'équipes présents dans son dataset."""
    client = AIClient()

    prediction = client.predict_match(home_team="France", away_team="Brazil")

    assert prediction is not None
    assert isinstance(prediction, MatchPrediction)
    assert isinstance(prediction.predicted_home_score, int)
    assert isinstance(prediction.predicted_away_score, int)


def test_predict_match_sends_names_reference_date_and_match_id(monkeypatch: pytest.MonkeyPatch) -> None:
    """Le payload envoyé au service contient bien des noms (mappés), la date de référence
    au format ISO et le match_id."""
    captured: dict[str, object] = {}

    def _post(url: str, json: dict, timeout: float) -> httpx.Response:
        captured.update(json)
        request = httpx.Request("POST", url)
        return httpx.Response(200, json={"predicted_home_score": 1, "predicted_away_score": 0}, request=request)

    monkeypatch.setattr("app.services.ai_client.httpx.post", _post)

    AIClient().predict_match(home_team="USA", away_team="France", reference_date=date(1998, 6, 10), match_id=7)

    assert captured["home_team"] == "United States"  # mapping appliqué
    assert captured["away_team"] == "France"
    assert captured["reference_date"] == "1998-06-10"
    assert captured["match_id"] == 7


def test_predict_match_null_reference_date_for_upcoming(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def _post(url: str, json: dict, timeout: float) -> httpx.Response:
        captured.update(json)
        request = httpx.Request("POST", url)
        return httpx.Response(200, json={"predicted_home_score": 2, "predicted_away_score": 2}, request=request)

    monkeypatch.setattr("app.services.ai_client.httpx.post", _post)

    AIClient().predict_match(home_team="France", away_team="Brazil")
    assert captured["reference_date"] is None


def test_predict_match_unknown_team_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Une équipe non reconnue (404 du service) lève UnknownTeamError, pas un None opaque."""
    request = httpx.Request("POST", "http://ai-service:8001/predict-match")
    response = httpx.Response(404, json={"detail": "Équipe(s) inconnue(s) : Nowherestan."}, request=request)

    monkeypatch.setattr("app.services.ai_client.httpx.post", lambda *a, **k: response)

    with pytest.raises(UnknownTeamError) as exc_info:
        AIClient().predict_match(home_team="Nowherestan", away_team="France")
    assert "Nowherestan" in exc_info.value.detail


def test_predict_match_handles_timeout_without_raising(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*args: object, **kwargs: object) -> None:
        raise httpx.TimeoutException("délai dépassé (simulé)")

    monkeypatch.setattr("app.services.ai_client.httpx.post", _raise)

    prediction = AIClient().predict_match(home_team="France", away_team="Brazil")
    assert prediction is None


def test_predict_match_handles_connection_error_without_raising(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(*args: object, **kwargs: object) -> None:
        raise httpx.ConnectError("service indisponible (simulé)")

    monkeypatch.setattr("app.services.ai_client.httpx.post", _raise)

    prediction = AIClient().predict_match(home_team="France", away_team="Brazil")
    assert prediction is None


def test_predict_match_handles_http_500_without_raising(monkeypatch: pytest.MonkeyPatch) -> None:
    """5xx = panne serveur transitoire : None (contrairement à un 4xx d'équipe inconnue)."""
    request = httpx.Request("POST", "http://ai-service:8001/predict-match")
    error_response = httpx.Response(500, request=request)

    monkeypatch.setattr("app.services.ai_client.httpx.post", lambda *a, **k: error_response)

    prediction = AIClient().predict_match(home_team="France", away_team="Brazil")
    assert prediction is None


def test_predict_match_handles_malformed_response_without_raising(monkeypatch: pytest.MonkeyPatch) -> None:
    request = httpx.Request("POST", "http://ai-service:8001/predict-match")
    malformed_response = httpx.Response(200, json={"unexpected": "shape"}, request=request)

    monkeypatch.setattr("app.services.ai_client.httpx.post", lambda *a, **k: malformed_response)

    prediction = AIClient().predict_match(home_team="France", away_team="Brazil")
    assert prediction is None


def test_ai_team_name_maps_known_divergences() -> None:
    assert ai_team_name("USA") == "United States"
    assert ai_team_name("Bosnia & Herzegovina") == "Bosnia and Herzegovina"
    assert ai_team_name("France") == "France"  # inchangé si pas de divergence
