from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.main import app

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(name="db")
def fixture_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@asynccontextmanager
async def _mock_lifespan(_app):
    yield


def test_health_check_returns_ok_when_database_is_available(db):
    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = _mock_lifespan

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}
    finally:
        app.dependency_overrides.clear()
        app.router.lifespan_context = original_lifespan


def test_health_check_returns_503_when_database_is_unavailable():
    class _BrokenSession:
        def execute(self, *_args, **_kwargs):
            raise RuntimeError("connection refused")

    original_lifespan = app.router.lifespan_context
    app.router.lifespan_context = _mock_lifespan

    def override_get_db():
        yield _BrokenSession()

    app.dependency_overrides[get_db] = override_get_db
    try:
        with TestClient(app) as client:
            response = client.get("/health")
        assert response.status_code == 503
        body = response.json()
        assert body["status"] == "error"
        assert "Traceback" not in response.text
    finally:
        app.dependency_overrides.clear()
        app.router.lifespan_context = original_lifespan
