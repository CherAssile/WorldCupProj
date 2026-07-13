"""Gestion uniforme des erreurs de l'API : toute réponse d'erreur, quelle que soit sa
cause (métier, validation, conflit d'intégrité base de données, bug non prévu, route ou
méthode inconnue), renvoie la même enveloppe JSON `{"detail": "<message clair>"}`, en
français, avec le code HTTP approprié -- jamais de trace technique ni de message par
défaut de Starlette/Pydantic exposé tel quel au client.
"""
from __future__ import annotations

import logging
from http import HTTPStatus

from fastapi import FastAPI, Request, status
from fastapi.exception_handlers import http_exception_handler as default_http_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Messages par défaut de Starlette (routage), jamais définis par notre propre code : les
# remplacer par leur équivalent français plutôt que de les laisser fuiter tels quels.
_DEFAULT_REASON_PHRASES: dict[int, str] = {
    status.HTTP_404_NOT_FOUND: "Ressource introuvable.",
    status.HTTP_405_METHOD_NOT_ALLOWED: "Méthode non autorisée pour cette ressource.",
}


async def _http_exception_handler(request: Request, exc: StarletteHTTPException) -> Response:
    """Un `detail` déjà défini par notre code (ex. "Équipe introuvable.") passe tel quel ;
    seul le message par défaut généré par le routage de Starlette (ex. la phrase "Not
    Found" d'une route inexistante) est traduit."""
    try:
        is_default_phrase = exc.detail == HTTPStatus(exc.status_code).phrase
    except ValueError:
        is_default_phrase = False

    if is_default_phrase and exc.status_code in _DEFAULT_REASON_PHRASES:
        exc.detail = _DEFAULT_REASON_PHRASES[exc.status_code]

    return await default_http_exception_handler(request, exc)


async def _validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """422 : un seul message clair dans `detail` (cohérent avec le reste de l'API, où
    `detail` est toujours une chaîne) plutôt que la liste brute d'erreurs Pydantic en
    anglais. Le détail champ par champ reste disponible dans `errors`, pour un client qui
    en a besoin."""
    errors = [
        {"champ": ".".join(str(part) for part in error["loc"] if part != "body"), "message": error["msg"]}
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Requête invalide.", "errors": errors},
    )


async def _integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    """Filet de sécurité pour une contrainte base de données violée (ex. condition de
    course sur une contrainte d'unicité) qui aurait échappé à la vérification métier :
    409 plutôt qu'une 500 qui exposerait un détail technique de la base."""
    logger.warning("Conflit d'intégrité base de données sur %s %s : %s", request.method, request.url.path, exc)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": "Cette opération entre en conflit avec une ressource existante."},
    )


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Dernier filet : toute exception non prévue devient une 500 propre, sans jamais
    exposer de trace technique au client. L'exception complète est journalisée côté
    serveur pour le diagnostic."""
    logger.exception("Erreur non gérée sur %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Une erreur interne est survenue. Réessayez plus tard."},
    )


def install_exception_handlers(app: FastAPI) -> None:
    """Enregistre les handlers d'erreur uniformes. À appeler une fois, à la création de
    l'application (cf. main.py)."""
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    app.add_exception_handler(IntegrityError, _integrity_error_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)
