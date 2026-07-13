import httpx
import pytest

from app.services.api_football_client import (
    ApiFootballClient,
    ApiFootballNotConfigured,
    ApiFootballQuotaExceeded,
)


def test_missing_api_key_raises_clear_error() -> None:
    # "" plutôt que None : None retomberait sur la vraie clé de settings.football_api_key.
    client = ApiFootballClient(api_key="")
    with pytest.raises(ApiFootballNotConfigured):
        client.find_team_id("France")


def test_http_429_raises_quota_exceeded(monkeypatch: pytest.MonkeyPatch) -> None:
    request = httpx.Request("GET", "https://v3.football.api-sports.io/teams")
    response = httpx.Response(429, request=request)
    monkeypatch.setattr("app.services.api_football_client.httpx.get", lambda *a, **k: response)

    client = ApiFootballClient(api_key="fake-key")
    with pytest.raises(ApiFootballQuotaExceeded):
        client.find_team_id("France")


def test_quota_message_in_200_response_raises_quota_exceeded(monkeypatch: pytest.MonkeyPatch) -> None:
    """api-football renvoie parfois un dépassement de quota en HTTP 200 avec un champ
    "errors" plutôt qu'un vrai 429."""
    request = httpx.Request("GET", "https://v3.football.api-sports.io/teams")
    response = httpx.Response(
        200, request=request, json={"errors": {"requests": "Too many requests"}, "response": []}
    )
    monkeypatch.setattr("app.services.api_football_client.httpx.get", lambda *a, **k: response)

    client = ApiFootballClient(api_key="fake-key")
    with pytest.raises(ApiFootballQuotaExceeded):
        client.find_team_id("France")


def test_lineups_empty_response_returns_empty_list(monkeypatch: pytest.MonkeyPatch) -> None:
    """Cas normal : les compositions ne sont pas encore publiées."""
    request = httpx.Request("GET", "https://v3.football.api-sports.io/fixtures/lineups")
    response = httpx.Response(200, request=request, json={"errors": [], "response": []})
    monkeypatch.setattr("app.services.api_football_client.httpx.get", lambda *a, **k: response)

    client = ApiFootballClient(api_key="fake-key")
    assert client.get_lineups(12345) == []
