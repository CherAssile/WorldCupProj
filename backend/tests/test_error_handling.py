import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app as fastapi_app
from app.models.user import User


def test_unknown_route_returns_french_404(client: TestClient) -> None:
    """Le message par défaut de Starlette ("Not Found") est traduit, pas exposé tel quel."""
    response = client.get("/route-qui-nexiste-pas")

    assert response.status_code == 404
    assert response.json() == {"detail": "Ressource introuvable."}


def test_method_not_allowed_returns_french_405(client: TestClient) -> None:
    response = client.delete("/teams")

    assert response.status_code == 405
    assert response.json() == {"detail": "Méthode non autorisée pour cette ressource."}


def test_validation_error_returns_clear_detail_and_field_errors(client: TestClient) -> None:
    """422 : un message clair en français dans `detail`, pas la liste brute de Pydantic."""
    response = client.post("/auth/register", json={})

    assert response.status_code == 422
    body = response.json()
    assert body["detail"] == "Requête invalide."
    fields = {error["champ"] for error in body["errors"]}
    assert fields == {"email", "username", "password"}


def test_business_http_exception_detail_passes_through_unchanged(client: TestClient) -> None:
    """Un detail métier explicite (raise HTTPException(..., detail="...")) n'est jamais
    réécrit par le handler générique."""
    response = client.get("/teams/999999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Équipe introuvable."}


def test_integrity_error_returns_409_conflict(
    client: TestClient, db_session: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Filet de sécurité : une contrainte d'unicité violée (ex. condition de course ayant
    échappé à la vérification préalable) devient une 409 propre, jamais une 500 brute."""
    existing = User(email="course@example.com", username="courseuser", hashed_password="x")
    db_session.add(existing)
    db_session.flush()

    # Simule une condition de course : la vérification préalable ("cet e-mail existe déjà
    # ?") ne voit rien, mais l'e-mail existe réellement -- l'INSERT viole la contrainte.
    monkeypatch.setattr("app.routers.auth.user_crud.get_by_email", lambda db, email: None)

    response = client.post(
        "/auth/register",
        json={"email": "course@example.com", "username": "courseuser2", "password": "secret123"},
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Cette opération entre en conflit avec une ressource existante."}


def test_unhandled_exception_returns_generic_500(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Un bug non prévu ne doit jamais fuiter de trace technique au client.

    Starlette re-lève volontairement l'exception d'origine après l'avoir déjà envoyée au
    client (pour que les tests puissent la capturer) : TestClient(raise_server_exceptions=
    False) est nécessaire ici pour observer la réponse HTTP réelle plutôt que l'exception
    Python. `client` (fixture partagée) reste utilisé pour que la dépendance get_db reste
    branchée sur la session de test.
    """

    def _boom(db: Session) -> None:
        raise RuntimeError("panne inattendue")

    monkeypatch.setattr("app.routers.teams.crud.team.list_all", _boom)

    non_raising_client = TestClient(fastapi_app, raise_server_exceptions=False)
    response = non_raising_client.get("/teams")

    assert response.status_code == 500
    assert response.json() == {"detail": "Une erreur interne est survenue. Réessayez plus tard."}


def test_openapi_tags_group_every_endpoint_by_domain(client: TestClient) -> None:
    """Chaque opération de l'API doit être rattachée à l'un des domaines documentés (pas
    d'opération orpheline dans le groupe "default" de /docs)."""
    schema = client.get("/openapi.json").json()

    declared_tags = {tag["name"] for tag in schema["tags"]}
    assert declared_tags == {
        "auth",
        "matchs",
        "pronostics",
        "récompenses",
        "classement",
        "entraînement",
        "simulation",
        "admin",
        "système",
    }

    for path, operations in schema["paths"].items():
        for method, operation in operations.items():
            assert operation.get("tags"), f"{method.upper()} {path} n'a aucun tag"
            assert set(operation["tags"]) <= declared_tags
