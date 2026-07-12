from datetime import timedelta

from fastapi.testclient import TestClient

from app.core.security import create_access_token

PASSWORD = "correcthorsebattery"


def _register(client: TestClient, email: str = "joueur@example.com", username: str = "joueur") -> dict:
    response = client.post(
        "/auth/register",
        json={"email": email, "username": username, "password": PASSWORD},
    )
    assert response.status_code == 201
    return response.json()


def _login(client: TestClient, email: str, password: str = PASSWORD):
    """/auth/login suit le flux OAuth2PasswordRequestForm : form-data, champ `username` = e-mail."""
    return client.post("/auth/login", data={"username": email, "password": password})


def test_register_login_me_flow(client: TestClient) -> None:
    """Parcours complet : inscription -> connexion -> accès au profil authentifié."""
    registered = _register(client)
    assert registered["email"] == "joueur@example.com"
    assert registered["username"] == "joueur"

    login_response = _login(client, "joueur@example.com")
    assert login_response.status_code == 200
    token_body = login_response.json()
    assert token_body["token_type"] == "bearer"
    assert token_body["access_token"]

    me_response = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {token_body['access_token']}"}
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "joueur@example.com"


def test_no_plaintext_password_in_any_response(client: TestClient) -> None:
    """Ni le mot de passe en clair ni son hash ne doivent jamais apparaître dans une réponse."""
    register_response = client.post(
        "/auth/register",
        json={"email": "secret@example.com", "username": "secretuser", "password": PASSWORD},
    )
    login_response = _login(client, "secret@example.com")
    token = login_response.json()["access_token"]
    me_response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    for response in (register_response, login_response, me_response):
        assert PASSWORD not in response.text
        body = response.json()
        assert "password" not in body
        assert "hashed_password" not in body


def test_register_duplicate_email_rejected(client: TestClient) -> None:
    """Un e-mail déjà utilisé est rejeté avec un 409."""
    _register(client, email="duplicate@example.com", username="premier")

    response = client.post(
        "/auth/register",
        json={"email": "duplicate@example.com", "username": "second", "password": PASSWORD},
    )
    assert response.status_code == 409


def test_me_rejects_invalid_token(client: TestClient) -> None:
    response = client.get("/auth/me", headers={"Authorization": "Bearer ceci-nest-pas-un-jwt"})
    assert response.status_code == 401


def test_me_rejects_missing_token(client: TestClient) -> None:
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_rejects_expired_token(client: TestClient) -> None:
    registered = _register(client, email="expire@example.com", username="expireuser")
    expired_token = create_access_token(subject=str(registered["id"]), expires_delta=timedelta(minutes=-1))

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
    assert response.status_code == 401
