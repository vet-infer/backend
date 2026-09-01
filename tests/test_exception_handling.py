from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.exceptions import NotFoundError, register_exception_handlers
from app.core.security import get_current_user, get_password_hash
from app.models import Species, Disease, Owner, Patient, Role, User
from app.models.rule import InferenceRule, RuleCondition
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
    # raise_server_exceptions=False para que el TestClient reciba la respuesta
    # del handler generico en vez de re-lanzar la excepcion en el proceso de test.
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()
    app.router.lifespan_context = original_lifespan


def test_unhandled_exception_returns_sanitized_500(client, db):
    """
    Simula una regla que bypasea la validacion de Pydantic (creada directo en la
    DB, como podria ocurrir con datos legados) para forzar un error no controlado
    dentro del motor de reglas durante una ejecucion de inferencia real.
    """
    dog = db.query(Species).filter(Species.name == "Perro").first()
    disease = db.query(Disease).filter(Disease.name == "Diabetes mellitus", Disease.species_id == dog.id).first()

    from app.models.risk_level import RiskLevel

    risk_level = db.query(RiskLevel).filter(RiskLevel.code == "alto").first()
    broken_rule = InferenceRule(
        code="BROKEN-BETWEEN",
        name="Regla con between malformado",
        disease_id=disease.id,
        risk_level_id=risk_level.id,
        risk_level="alto",
        weight=1.0,
        priority=1,
        is_active=True,
    )
    broken_rule.conditions = [
        RuleCondition(variable_key="glucosa", operator="between", expected_value=42, logical_group=1)
    ]
    db.add(broken_rule)
    db.commit()

    owner = Owner(first_name="Ana", last_name="Ruiz", email="ana@example.com")
    db.add(owner)
    db.commit()
    breed = None
    patient = Patient(
        owner_id=owner.id, name="Firulais", species_id=dog.id, breed_id=breed, sex="Macho", weight=10.0, created_by=1
    )
    db.add(patient)
    db.commit()

    response = client.post(
        "/api/v1/inference/run",
        json={"patient_id": patient.id, "facts": [{"key": "glucosa", "value": 250.0}]},
    )

    assert response.status_code == 500
    body = response.json()
    assert body == {"detail": "Error interno del servidor"}
    # No debe filtrarse informacion interna (traza de Python, rutas de archivo)
    assert "Traceback" not in response.text
    assert "app/inference" not in response.text and "app\\inference" not in response.text


def test_request_validation_error_is_not_intercepted_by_generic_handler(client):
    # facts vacio viola `min_length=1` -> 422 de FastAPI, no debe convertirse en 500
    response = client.post("/api/v1/inference/run", json={"patient_id": 1, "facts": []})
    assert response.status_code == 422
    assert response.json()["detail"] != "Error interno del servidor"


def test_not_found_error_from_service_layer_returns_404_not_500(client):
    response = client.post(
        "/api/v1/inference/run",
        json={"patient_id": 999999, "facts": [{"key": "glucosa", "value": 200}]},
    )
    assert response.status_code == 404
    assert response.json()["detail"] != "Error interno del servidor"
