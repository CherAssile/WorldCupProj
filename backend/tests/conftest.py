import os
from collections.abc import Generator

# Doit être posé avant l'import de app.main (donc de app.config) : le scheduler de synchro
# (app.services.scheduler) lirait sinon settings.sync_scheduler_enabled=True et tournerait
# en tâche de fond pendant la suite pytest, la rendant non déterministe.
os.environ.setdefault("SYNC_SCHEDULER_ENABLED", "false")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine, get_db
from app.main import app


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    """Session de test isolée : tout est annulé par rollback en fin de test.

    Utilise une transaction externe + des savepoints imbriqués pour que même
    un `session.commit()` dans le code testé n'écrive jamais réellement en base.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)

    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(session: Session, transaction: object) -> None:
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Client de test FastAPI, avec la dépendance get_db branchée sur la session de test."""

    def _override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
