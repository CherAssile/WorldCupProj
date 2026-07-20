"""Réinitialisation de mot de passe : anti-énumération, usage unique, expiration.

Le jeton en clair n'existe que dans le lien e-mail (loggé en dev par LoggingEmailSender) :
les tests le récupèrent depuis les logs, exactement comme un utilisateur depuis sa boîte.
"""
import re
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.password_reset_token import PasswordResetToken

PASSWORD = "correcthorsebattery"
NEW_PASSWORD = "nouveaumotdepasse1"
FORGOT_MESSAGE = "Si un compte existe pour cet e-mail, un lien de réinitialisation a été envoyé."


def _register(client: TestClient, email: str) -> None:
    username = email.split("@")[0].replace("-", "_")
    client.post("/auth/register", json={"email": email, "username": username, "password": PASSWORD})


def _request_reset_token(client: TestClient, email: str, caplog: pytest.LogCaptureFixture) -> str:
    """Déclenche forgot-password et extrait le jeton en clair du lien loggé."""
    with caplog.at_level("INFO", logger="app.services.email"):
        response = client.post("/auth/forgot-password", json={"email": email})
    assert response.status_code == 200
    match = re.search(r"\?token=([A-Za-z0-9_\-]+)", caplog.text)
    assert match is not None, "le lien de réinitialisation doit apparaître dans les logs (mode dev)"
    return match.group(1)


def test_forgot_password_unknown_email_returns_same_200(client: TestClient) -> None:
    """Anti-énumération : e-mail inconnu → même 200 et même message qu'un e-mail connu."""
    response = client.post("/auth/forgot-password", json={"email": "inconnu@example.com"})
    assert response.status_code == 200
    assert response.json()["message"] == FORGOT_MESSAGE


def test_forgot_password_known_email_same_response_and_logs_link(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    _register(client, "reset-connu@example.com")
    with caplog.at_level("INFO", logger="app.services.email"):
        response = client.post("/auth/forgot-password", json={"email": "reset-connu@example.com"})
    assert response.status_code == 200
    assert response.json()["message"] == FORGOT_MESSAGE  # indiscernable du cas inconnu
    assert "reset-connu@example.com" in caplog.text
    assert "?token=" in caplog.text


def test_full_reset_flow_changes_password(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    """Jeton valide → mot de passe changé : l'ancien ne fonctionne plus, le nouveau oui."""
    _register(client, "reset-flow@example.com")
    token = _request_reset_token(client, "reset-flow@example.com", caplog)

    response = client.post("/auth/reset-password", json={"token": token, "new_password": NEW_PASSWORD})
    assert response.status_code == 200

    old_login = client.post("/auth/login", data={"username": "reset-flow@example.com", "password": PASSWORD})
    assert old_login.status_code == 401

    new_login = client.post("/auth/login", data={"username": "reset-flow@example.com", "password": NEW_PASSWORD})
    assert new_login.status_code == 200


def test_reused_token_rejected(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    """Un jeton est à usage unique : la seconde consommation échoue en 400."""
    _register(client, "reset-reuse@example.com")
    token = _request_reset_token(client, "reset-reuse@example.com", caplog)

    first = client.post("/auth/reset-password", json={"token": token, "new_password": NEW_PASSWORD})
    assert first.status_code == 200

    second = client.post("/auth/reset-password", json={"token": token, "new_password": "encoreunautre1"})
    assert second.status_code == 400


def test_expired_token_rejected(
    client: TestClient, db_session: Session, caplog: pytest.LogCaptureFixture
) -> None:
    _register(client, "reset-expire@example.com")
    token = _request_reset_token(client, "reset-expire@example.com", caplog)

    # order_by explicite : d'autres jetons peuvent déjà exister sur cette base (usage réel
    # de la fonctionnalité) -- sans tri, l'ordre de retour n'est pas garanti "insertion".
    reset_token = (
        db_session.execute(select(PasswordResetToken).order_by(PasswordResetToken.id.desc())).scalars().first()
    )
    reset_token.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
    db_session.commit()

    response = client.post("/auth/reset-password", json={"token": token, "new_password": NEW_PASSWORD})
    assert response.status_code == 400


def test_unknown_token_rejected(client: TestClient) -> None:
    response = client.post(
        "/auth/reset-password", json={"token": "jeton-completement-invente", "new_password": NEW_PASSWORD}
    )
    assert response.status_code == 400
