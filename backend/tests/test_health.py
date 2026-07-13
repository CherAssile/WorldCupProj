from fastapi.testclient import TestClient


def test_health_deep_ok(client: TestClient) -> None:
    """L'API, Postgres et Redis doivent tous les trois répondre ok."""
    response = client.get("/health/deep")

    assert response.status_code == 200
    assert response.json() == {"api": "ok", "postgres": "ok", "redis": "ok"}
