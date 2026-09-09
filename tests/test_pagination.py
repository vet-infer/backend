from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import get_current_user, get_password_hash
from app.models import Owner, Patient, Role, Species, User
from app.services.bootstrap_service import bootstrap_reference_data

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
        db.add(Role(id=1, name="admin", description="Admin"))
        db.add(User(id=1, full_name="Admin", email="admin@example.com", password_hash=get_password_hash("x"), role_id=1))
        db.commit()
        bootstrap_reference_data(db)

        species = db.query(Species).first()
        for index in range(3):
            owner = Owner(first_name=f"Propietario {index}", last_name="Test", email=f"owner{index}@example.test")
            db.add(owner)
            db.flush()
            db.add(Patient(owner_id=owner.id, name=f"Paciente {index}", species_id=species.id, sex="M", created_by=1))
        db.commit()

        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(name="client")
def fixture_client(db):
    from app.main import app

    @asynccontextmanager
    async def mock_lifespan(_app):
        yield

    app.router.lifespan_context = mock_lifespan

    def override_get_db():
        try:
            yield db
        finally:
            pass

    def override_get_current_user():
        return db.get(User, 1)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_list_patients_respects_limit(client):
    response = client.get("/api/v1/patients", params={"skip": 0, "limit": 1})
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_list_patients_total_count_header_reflects_full_total(client):
    response = client.get("/api/v1/patients", params={"skip": 0, "limit": 1})
    assert response.headers["x-total-count"] == "3"
    assert len(response.json()) == 1


def test_list_owners_total_count_header_reflects_full_total(client):
    response = client.get("/api/v1/owners/", params={"skip": 0, "limit": 1})
    assert response.headers["x-total-count"] == "3"
    assert len(response.json()) == 1
