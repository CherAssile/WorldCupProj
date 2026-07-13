from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings
from app.database import engine
from app.redis_client import redis_client
from app.routers import auth, matches, players, predictions, teams

app = FastAPI(title="Mundial Pronos API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(teams.router)
app.include_router(matches.router)
app.include_router(players.router)
app.include_router(predictions.router)


@app.get("/health")
def health() -> dict[str, str]:
    """Vérifie que le service backend est opérationnel."""
    return {"status": "ok"}


@app.get("/health/deep")
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