from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import get_current_user, get_password_hash
from app.main import app
from app.models import Species, Breed, Owner, Patient, Role, User
from app.repositories.evaluation_repository import EvaluationRepository
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
        db.add(Role(id=2, name="veterinario", description="Veterinario"))
        db.add(User(id=1, full_name="Dr. Test", email="vet@example.com", password_hash=get_password_hash("x"), role_id=2))
        db.commit()
        bootstrap_reference_data(db)
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(name="client")
def fixture_client(db):
    @asynccontextmanager
    async def mock_lifespan(_app):
        yield

    original_lifespan = app.router.lifespan_context
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
    app.router.lifespan_context = original_lifespan


def test_openapi_marks_english_run_endpoint_as_deprecated(client):
    schema = client.get("/openapi.json").json()
    path = schema["paths"]["/api/v1/inference/evaluations/{evaluation_id}/run"]["post"]
    assert path["deprecated"] is True
    assert "procesar" in path["description"]

    canonical = schema["paths"]["/api/v1/evaluaciones/{evaluation_id}/procesar"]["post"]
    assert canonical.get("deprecated") is not True


def test_deprecated_endpoint_still_persists_and_responds_like_before(client, db):
    dog = db.query(Species).filter(Species.name == "Perro").first()
    poodle = db.query(Breed).filter(Breed.name == "Poodle", Breed.species_id == dog.id).first()
    owner = Owner(first_name="Ana", last_name="Ruiz", email="ana@example.com")
    db.add(owner)
    db.commit()
    patient = Patient(
        owner_id=owner.id, name="Firulais", species_id=dog.id, breed_id=poodle.id, sex="Macho", weight=10.0, created_by=1
    )
    db.add(patient)
    db.commit()

    eval_repo = EvaluationRepository(db)
    facts = [
        {"fact_key": "poliuria", "value": True},
        {"fact_key": "polidipsia", "value": True},
        {"fact_key": "glucosa", "value": 260.0},
        {"fact_key": "glucosuria", "value": "positiva"},
    ]
    evaluation = eval_repo.create_with_facts(
        patient_id=patient.id, veterinarian_id=1, reason="x", observations="", facts=facts
    )

    response = client.post(f"/api/v1/inference/evaluations/{evaluation.id}/run")
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    dm_res = next((r for r in data if r["disease_id"] and r.get("probability") is not None), data[0])
    assert "id" in dm_res and "risk_level" in dm_res and "probability" in dm_res
    assert dm_res["evaluation_id"] == evaluation.id
