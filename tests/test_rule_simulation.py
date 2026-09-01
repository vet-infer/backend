from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import get_current_user, get_password_hash
from app.models import ClinicalHistory, Disease, InferenceResult, Role, Species, User
from app.repositories.rule_repository import RuleRepository
from app.schemas.rule import RuleConditionCreate, RuleSimulationRequest
from app.services.bootstrap_service import bootstrap_reference_data
from app.services.rule_service import RuleService

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
        db.add(User(id=1, full_name="Admin", email="admin@example.com", password_hash=get_password_hash("x"), role_id=1))
        db.add(User(id=2, full_name="Vet", email="vet@example.com", password_hash=get_password_hash("x"), role_id=2))
        db.commit()
        bootstrap_reference_data(db)
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def _dm_disease(db):
    dog = db.query(Species).filter(Species.name == "Perro").first()
    return db.query(Disease).filter(Disease.name == "Diabetes mellitus", Disease.species_id == dog.id).first()


def test_simulate_returns_activated_true_when_conditions_are_satisfied(db):
    disease = _dm_disease(db)
    service = RuleService(RuleRepository(db))
    payload = RuleSimulationRequest(
        disease_id=disease.id,
        conditions=[RuleConditionCreate(variable_key="glucosa", operator="gt", expected_value=200)],
        facts={"glucosa": 260.0},
    )

    result = service.simulate(payload)

    assert result["activated"] is True
    assert any("glucosa" in text for text in result["fulfilled_conditions"])


def test_simulate_returns_activated_false_when_conditions_are_not_satisfied(db):
    disease = _dm_disease(db)
    service = RuleService(RuleRepository(db))
    payload = RuleSimulationRequest(
        disease_id=disease.id,
        conditions=[RuleConditionCreate(variable_key="glucosa", operator="gt", expected_value=200)],
        facts={"glucosa": 100.0},
    )

    result = service.simulate(payload)

    assert result == {"activated": False, "fulfilled_conditions": []}


def test_simulate_does_not_persist_anything(db):
    disease = _dm_disease(db)
    service = RuleService(RuleRepository(db))
    payload = RuleSimulationRequest(
        disease_id=disease.id,
        conditions=[RuleConditionCreate(variable_key="glucosa", operator="gt", expected_value=200)],
        facts={"glucosa": 260.0},
    )

    service.simulate(payload)

    assert db.query(InferenceResult).count() == 0
    assert db.query(ClinicalHistory).count() == 0
    assert RuleRepository(db).get_by_code("SIMULACION") is None


@pytest.fixture(name="client")
def fixture_client(db):
    from app.main import app

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
        return db.get(User, 2)  # veterinario, no admin

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    app.router.lifespan_context = original_lifespan


def test_simulate_endpoint_requires_admin_role(client, db):
    disease = _dm_disease(db)
    response = client.post(
        "/api/v1/rules/simulate",
        json={
            "disease_id": disease.id,
            "conditions": [{"variable_key": "glucosa", "operator": "gt", "expected_value": 200}],
            "facts": {"glucosa": 260.0},
        },
    )
    assert response.status_code == 403
