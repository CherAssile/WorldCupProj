import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.core.errors import install_exception_handlers
from app.database import engine
from app.redis_client import redis_client
from app.routers import (
    admin,
    ai_predictions,
    auth,
    award_predictions,
    awards,
    leaderboard,
    matches,
    me,
    players,
    predictions,
    simulations,
    teams,
    training,
)
from app.services.scheduler import start_scheduler

# Sans ceci, les logs INFO du scheduler de synchro (résumé de chaque exécution -- cf.
# app.services.scheduler) restent invisibles sous uvicorn (root logger à WARNING par
# défaut), ce qui viderait de son sens l'exigence de pouvoir diagnostiquer sans fouiller.
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

# Regroupement du /docs par domaine métier plutôt que par router technique : plusieurs
# routers peuvent partager un même tag (ex. teams/matches/players -> "matchs").
OPENAPI_TAGS = [
    {"name": "auth", "description": "Inscription, connexion et profil de l'utilisateur."},
    {"name": "matchs", "description": "Calendrier du tournoi, équipes, effectifs et compositions."},
    {
        "name": "pronostics",
        "description": "Pronostics compétitifs sur les matchs à venir (Joueur contre Joueur, classement global).",
    },
    {
        "name": "récompenses",
        "description": "Récompenses individuelles (meilleur buteur, passeur, joueur) et pronostics associés.",
    },
    {"name": "classement", "description": "Classement global du concours compétitif."},
    {
        "name": "duel",
        "description": "Duel joueur contre IA en mode compétitif : lecture agrégée des pronostics et de "
        "l'IA sur les mêmes matchs, sans toucher au classement général.",
    },
    {
        "name": "entraînement",
        "description": "Joueur contre la Machine, sur des matchs déjà joués (Mondial en cours ou éditions "
        "passées) : hors classement compétitif.",
    },
    {
        "name": "simulation",
        "description": "Bac à sable admin : simulation complète du tournoi, réservée aux administrateurs.",
    },
    {
        "name": "admin",
        "description": "Actions d'administration transverses aux autres domaines (recalculs, régénérations).",
    },
    {"name": "système", "description": "Supervision technique de l'API (santé du service et de ses dépendances)."},
]

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    scheduler = start_scheduler()
    yield
    if scheduler is not None:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Mundial Pronos API", openapi_tags=OPENAPI_TAGS, lifespan=lifespan)

install_exception_handlers(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(admin.router)
app.include_router(auth.router)
app.include_router(teams.router)
app.include_router(matches.router)
app.include_router(players.router)
app.include_router(predictions.router)
app.include_router(awards.router)
app.include_router(award_predictions.router)
app.include_router(leaderboard.router)
app.include_router(me.router)
app.include_router(ai_predictions.router)
app.include_router(training.router)
app.include_router(training.tournaments_router)
app.include_router(simulations.router)


@app.get("/health", tags=["système"])
def health() -> dict[str, str]:
    """Vérifie que le service backend est opérationnel."""
    return {"status": "ok"}


@app.get("/health/deep", tags=["système"])
def health_deep(response: Response) -> dict[str, str]:
    """Vérifie l'API ainsi que les dépendances Postgres et Redis."""
    checks = {"api": "ok"}

    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        checks["postgres"] = "ok"
    except SQLAlchemyError:
        checks["postgres"] = "error"

    try:
        redis_client.ping()
        checks["redis"] = "ok"
    except RedisError:
        checks["redis"] = "error"

    if "error" in checks.values():
        response.status_code = 503

    return checks