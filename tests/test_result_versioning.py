from contextlib import asynccontextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import get_current_user, get_password_hash
from app.models import Species, Breed, Owner, Patient, Role, User
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.result_repository import ResultRepository
from app.repositories.rule_repository import RuleRepository
from app.services.bootstrap_service import bootstrap_reference_data
from app.services.inference_service import InferenceService

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
    with TestClient(app) as c:
        yield c
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


def _service(db):
    return InferenceService(RuleRepository(db), PatientRepository(db), EvaluationRepository(db), ResultRepository(db))


def test_rerunning_inference_supersedes_previous_results_and_keeps_only_current_by_default(db):
    evaluation = _make_evaluation(db)
    service = _service(db)

    first_run = service.run_and_persist(evaluation.id)
    assert len(first_run) > 0
    assert all(r.is_current for r in first_run)
    first_run_ids = {r.id for r in first_run}

    second_run = service.run_and_persist(evaluation.id)
    assert len(second_run) > 0
    assert all(r.is_current for r in second_run)

    current_only = service.list_results(evaluation.id)
    current_ids = {r.id for r in current_only}
    assert current_ids == {r.id for r in second_run}
    assert current_ids.isdisjoint(first_run_ids)
    assert all(r.is_current for r in current_only)

    with_history = service.list_results(evaluation.id, include_history=True)
    history_ids = {r.id for r in with_history}
    assert history_ids == first_run_ids | {r.id for r in second_run}

    superseded = [r for r in with_history if r.id in first_run_ids]
    assert all(not r.is_current for r in superseded)
    assert all(r.superseded_at is not None for r in superseded)


def test_evaluation_results_endpoint_defaults_to_current_and_supports_history(client, db):
    evaluation = _make_evaluation(db)
    service = _service(db)

    first_run_ids = {r.id for r in service.run_and_persist(evaluation.id)}
    second_run_ids = {r.id for r in service.run_and_persist(evaluation.id)}

    default_response = client.get(f"/api/v1/evaluations/{evaluation.id}/results")
    assert default_response.status_code == 200
    default_ids = {item["id"] for item in default_response.json()}
    assert default_ids == second_run_ids

    history_response = client.get(f"/api/v1/evaluations/{evaluation.id}/results?include_history=true")
    assert history_response.status_code == 200
    history_ids = {item["id"] for item in history_response.json()}
    assert history_ids == first_run_ids | second_run_ids
