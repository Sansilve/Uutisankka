"""
Shared pytest fixtures for UutisAnkka backend tests.

Strategy:
  - Patch app.database.DB_PATH to a temporary SQLite file before the
    lifespan starts, so tests never touch the production database.
  - Set INGEST_INTERVAL_SECONDS to a very high value so the background
    periodic ingest task never fires during the test session.
"""
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client(tmp_path_factory):
    """Session-scoped FastAPI TestClient backed by a temporary database."""
    # Point the app at a throwaway DB before startup runs.
    db_file = str(tmp_path_factory.mktemp("db") / "test.db")

    import app.database as _db

    _db.DB_PATH = db_file

    # Prevent the background ingest loop from firing during tests.
    os.environ.setdefault("INGEST_INTERVAL_SECONDS", str(10 * 365 * 24 * 3600))

    from app.main import app

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c
