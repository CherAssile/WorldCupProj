"""Envoi d'e-mails, derrière une interface unique choisie par variable d'environnement.

Aucun SMTP configuré pour l'instant (décision projet) : le backend par défaut
(« logging ») écrit le lien de réinitialisation dans les logs du serveur — suffisant en
développement. Un vrai fournisseur (Resend, Mailgun…) se branchera au déploiement en
implémentant EmailSender et en le référençant dans EMAIL_BACKEND, sans toucher aux
routers.
"""
from __future__ import annotations

import logging
from typing import Protocol

from app.config import settings

logger = logging.getLogger(__name__)

# Le lien de réinitialisation DOIT être visible dans les logs du serveur en dev : uvicorn
# ne configure pas les loggers applicatifs, et le handler Python de dernier recours
# n'affiche que WARNING et plus — un simple logger.info() serait silencieusement perdu.
# Handler dédié à CE logger uniquement ; la propagation reste active pour que les tests
# (caplog) capturent toujours les enregistrements via le logger racine.
if not logger.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(levelname)s:     %(message)s"))
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)


class EmailSender(Protocol):
    """Interface d'envoi : chaque implémentation choisit son transport."""

    def send_password_reset(self, to_email: str, reset_url: str) -> None: ...


class LoggingEmailSender:
    """Mode développement : le lien part dans les logs du serveur, pas de vrai e-mail."""

    def send_password_reset(self, to_email: str, reset_url: str) -> None:
        logger.info("Réinitialisation de mot de passe pour %s : %s", to_email, reset_url)


class ResendEmailSender:
    """Fournisseur réel (Resend/Mailgun) : à brancher au déploiement.

    Squelette volontairement non implémenté — clé API et appel HTTP viendront avec la
    configuration de production (cf. décision « pas de SMTP pour l'instant »).
    """

    def send_password_reset(self, to_email: str, reset_url: str) -> None:
        raise NotImplementedError(
            "Le backend e-mail « resend » n'est pas encore branché : configurer le fournisseur "
            "au déploiement ou repasser EMAIL_BACKEND=logging."
        )


def get_email_sender() -> EmailSender:
    """Sélectionne l'implémentation depuis EMAIL_BACKEND (logging par défaut)."""
    if settings.email_backend == "logging":
        return LoggingEmailSender()
    if settings.email_backend == "resend":
        return ResendEmailSender()
    raise ValueError(f"EMAIL_BACKEND inconnu : {settings.email_backend!r} (attendu : logging ou resend)")
