import os

# Force a local, disposable sqlite DB for the test run, and a fixed secret,
# BEFORE importing anything from `app` (settings are read at import time).
os.environ["DATABASE_URL"] = "sqlite:///./test_acmeflow.db"
os.environ["SECRET_KEY"] = "test-secret-key-not-for-lab-use"

import pytest
from fastapi.testclient import TestClient

from app import seed
from app.database import Base, SessionLocal, engine
from app.main import app

TEST_DB_PATH = "test_acmeflow.db"

CREDENTIALS = {
    "admin": "Admin#2024",
    "bob": "Bob#2024",
    "erin": "Erin#2024",
    "david": "David#2024",
    "alice": "Alice#2024",
    "carol": "Carol#2024",
    "frank": "Frank#2024",
}

# Fixed IDs produced by app/seed.py -- see comments there.
USER_IDS = {
    "admin": 1, "bob": 2, "erin": 3, "david": 4, "alice": 5, "carol": 6, "frank": 7,
}


@pytest.fixture(scope="session", autouse=True)
def _create_schema():
    Base.metadata.create_all(bind=engine)
    yield
    engine.dispose()
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)


@pytest.fixture(autouse=True)
def _reset_db():
    """Reseed deterministic data before every single test for reproducibility."""
    db = SessionLocal()
    try:
        seed.seed_all(db, reset=True)
    finally:
        db.close()
    yield


@pytest.fixture
def client():
    return TestClient(app)


def login(client, username: str) -> str:
    resp = client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": CREDENTIALS[username]},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_headers(client, username: str) -> dict:
    token = login(client, username)
    return {"Authorization": f"Bearer {token}"}
