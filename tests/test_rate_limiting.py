from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.rate_limit import limiter
from app.core.security import get_current_user, get_password_hash
from app.models import Breed, Disease, Owner, Patient, Role, Species, User
from app.repositories.evaluation_repository import EvaluationRepository

engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(name="db")
def fixture_db():
    from app.services.bootstrap_service import bootstrap_reference_data

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        db.add(Role(id=1, name="admin", description="Admin"))
        db.add(Role(id=2, name="veterinario", description="Veterinario"))
        db.add(
            User(id=1, full_name="Admin", email="admin@example.com", password_hash=get_password_hash("Secreto123"), role_id=1)
        )
        db.add(User(id=2, full_name="Vet", email="vet@example.com", password_hash=get_password_hash("x"), role_id=2))
        db.commit()
        bootstrap_reference_data(db)
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

    limiter.enabled = True
    limiter.reset()
    try:
        with TestClient(app) as c:
            yield c
    finally:
        limiter.enabled = False
        limiter.reset()
        app.dependency_overrides.clear()
        app.router.lifespan_context = original_lifespan


def _make_evaluation(db):
    dog = db.query(Species).filter(Species.name == "Perro").first()
    poodle = db.query(Breed).filter(Breed.name == "Poodle", Breed.species_id == dog.id).first()
    owner = Owner(first_name="Carlos", last_name="Mendoza", email="carlos@example.com")
    db.add(owner)
    db.commit()
    patient = Patient(
        owner_id=owner.id, name="Toby", species_id=dog.id, breed_id=poodle.id, sex="Macho", weight=12.5, created_by=1
    )
    db.add(patient)
    db.commit()
    eval_repo = EvaluationRepository(db)
    facts = [
        {"fact_key": "poliuria", "value": True, "source_type": "clinical_input"},
        {"fact_key": "polidipsia", "value": True, "source_type": "clinical_input"},
        {"fact_key": "glucosa", "value": 260.0, "source_type": "clinical_input"},
        {"fact_key": "glucosuria", "value": "positiva", "source_type": "clinical_input"},
    ]
    return eval_repo.create_with_facts(
        patient_id=patient.id, veterinarian_id=1, reason="Chequeo", observations="", facts=facts
    )


def test_rate_limit_exceeded_response_shape(client):
    """Verifica el shape 429 consistente con el resto de la API (Fase 4, tasks 2.2)."""
    for _ in range(10):
        client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "wrong-password"},
        )
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "wrong-password"},
    )
    assert response.status_code == 429
    assert response.json() == {"detail": "Demasiadas solicitudes, intente nuevamente en unos momentos"}


def test_login_rate_limit_blocks_after_default_threshold_without_checking_password(client, monkeypatch):
    import app.services.auth_service as auth_service_module

    calls = {"count": 0}
    original_verify_password = auth_service_module.verify_password

    def spy_verify_password(*args, **kwargs):
        calls["count"] += 1
        return original_verify_password(*args, **kwargs)

    monkeypatch.setattr(auth_service_module, "verify_password", spy_verify_password)

    for _ in range(10):
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "admin@example.com", "password": "Secreto123"},
        )
        assert response.status_code in (200, 401)

    calls_before_block = calls["count"]

    blocked = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "Secreto123"},
    )
    assert blocked.status_code == 429
    assert calls["count"] == calls_before_block


def test_login_within_limit_is_not_blocked(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "Secreto123"},
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


def test_rule_simulate_rate_limit_blocks_after_default_threshold(client, db):
    dog = db.query(Species).filter(Species.name == "Perro").first()
    disease = db.query(Disease).filter_by(species_id=dog.id).first()
    payload = {
        "disease_id": disease.id,
        "conditions": [{"variable_key": "glucosa", "operator": "gt", "expected_value": 1}],
        "facts": {},
    }

    for _ in range(30):
        response = client.post("/api/v1/rules/simulate", json=payload)
        assert response.status_code == 200

    blocked = client.post("/api/v1/rules/simulate", json=payload)
    assert blocked.status_code == 429


def test_inference_run_rate_limit_blocks_after_default_threshold(client, db):
    evaluation = _make_evaluation(db)
    payload = {
        "patient_id": evaluation.patient_id,
        "facts": [{"key": "glucosa", "value": 260.0}],
    }

    for _ in range(30):
        response = client.post("/api/v1/inference/run", json=payload)
        assert response.status_code == 200

    blocked = client.post("/api/v1/inference/run", json=payload)
    assert blocked.status_code == 429


def test_procesar_evaluacion_rate_limit_blocks_after_default_threshold(client, db):
    evaluation = _make_evaluation(db)

    for _ in range(30):
        response = client.post(f"/api/v1/evaluaciones/{evaluation.id}/procesar")
        assert response.status_code == 200

    blocked = client.post(f"/api/v1/evaluaciones/{evaluation.id}/procesar")
    assert blocked.status_code == 429


def test_endpoints_without_rate_limiting_are_unaffected(client, db):
    """Regresion (Fase 4, task 3.3): rutas no cubiertas por esta fase no limitan tasa."""
    for _ in range(40):
        response = client.get("/api/v1/rules")
        assert response.status_code == 200
