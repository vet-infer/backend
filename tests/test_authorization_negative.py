from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import get_current_user, get_password_hash
from app.models import Role, Species, User
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
        db.add(Role(id=3, name="evaluador", description="Evaluador"))
        db.add(User(id=1, full_name="Admin", email="admin@example.com", password_hash=get_password_hash("x"), role_id=1))
        db.add(User(id=2, full_name="Vet", email="vet@example.com", password_hash=get_password_hash("x"), role_id=2))
        db.add(
            User(id=3, full_name="Evaluador", email="eval@example.com", password_hash=get_password_hash("x"), role_id=3)
        )
        db.commit()
        bootstrap_reference_data(db)
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def _client_as(db, user_id: int):
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
        return db.get(User, user_id)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    return TestClient(app)


@pytest.fixture(name="vet_client")
def fixture_vet_client(db):
    client = _client_as(db, 2)
    with client as c:
        yield c
    client.app.dependency_overrides.clear()


@pytest.fixture(name="evaluador_client")
def fixture_evaluador_client(db):
    client = _client_as(db, 3)
    with client as c:
        yield c
    client.app.dependency_overrides.clear()


# --- /rules requires ADMIN_ONLY; veterinario is WRITE but not ADMIN ---


def test_list_rules_forbidden_for_non_admin(vet_client):
    assert vet_client.get("/api/v1/rules").status_code == 403


def test_create_rule_forbidden_for_non_admin(vet_client, db):
    dog = db.query(Species).filter(Species.name == "Perro").first()
    response = vet_client.post(
        "/api/v1/rules",
        json={
            "code": "X-1",
            "name": "x",
            "disease_id": 1,
            "weight": 1.0,
            "priority": 1,
            "conditions": [{"variable_key": "glucosa", "operator": "gt", "expected_value": 1}],
        },
    )
    assert response.status_code == 403


def test_update_rule_forbidden_for_non_admin(vet_client):
    response = vet_client.put(
        "/api/v1/rules/1",
        json={"name": "Nombre nuevo"},
    )
    assert response.status_code == 403


def test_update_rule_status_forbidden_for_non_admin(vet_client):
    assert vet_client.patch("/api/v1/rules/1/status", json={"is_active": False}).status_code == 403


def test_simulate_rule_forbidden_for_non_admin(vet_client):
    assert (
        vet_client.post(
            "/api/v1/rules/simulate",
            json={"disease_id": 1, "conditions": [{"variable_key": "glucosa", "operator": "gt", "expected_value": 1}], "facts": {}},
        ).status_code
        == 403
    )


# --- /inference/run requires CLINICAL_WRITE; evaluador is READ-only ---


def test_run_inference_forbidden_for_read_only_role(evaluador_client):
    response = evaluador_client.post(
        "/api/v1/inference/run",
        json={"patient_id": 1, "facts": [{"key": "glucosa", "value": 200}]},
    )
    assert response.status_code == 403


def test_run_inference_for_evaluation_forbidden_for_read_only_role(evaluador_client):
    response = evaluador_client.post("/api/v1/inference/evaluations/1/run")
    assert response.status_code == 403


def test_procesar_evaluacion_forbidden_for_read_only_role(evaluador_client):
    response = evaluador_client.post("/api/v1/evaluaciones/1/procesar")
    assert response.status_code == 403
