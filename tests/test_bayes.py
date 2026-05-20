import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.models import (
    Species,
    Breed,
    Disease,
    Owner,
    Patient,
    Role,
    User,
    EvaluationClinical,
    EvaluationClinicalFact,
    ClinicalProbability,
    InferenceResult,
    ActivatedRule,
    InferenceRule,
    RuleCondition,
    Symptom,
    ClinicalVariable,
)
from app.services.bootstrap_service import bootstrap_reference_data
from app.services.inference_service import InferenceService
from app.repositories.rule_repository import RuleRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.result_repository import ResultRepository
from app.services.bayes_service import BayesService
from app.core.security import get_password_hash
from sqlalchemy.pool import StaticPool

# Setup test DB with StaticPool to share connection across threads
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
        # Create roles
        admin_role = Role(id=1, name="admin", description="Admin")
        db.add(admin_role)
        vet_role = Role(id=2, name="veterinario", description="Veterinario")
        db.add(vet_role)

        # Create user
        user = User(
            id=1,
            full_name="Dr. Juan Perez",
            email="vet@example.com",
            password_hash=get_password_hash("password"),
            role_id=2,
        )
        db.add(user)
        db.commit()

        # Run bootsrap to seed all reference clinical data (symptoms, diseases, variables, rules, probabilities)
        bootstrap_reference_data(db)

        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(name="client")
def fixture_client(db):
    from app.core.security import get_current_user
    from contextlib import asynccontextmanager
    
    @asynccontextmanager
    async def mock_lifespan(app):
        yield

    # Temporarily override lifespan to prevent connecting to PostgreSQL during test run
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


def test_bayes_service_calculations(db):
    """
    Directly tests Naive Bayes logic, smoothing, and normalization inside BayesService.
    """
    bayes_svc = BayesService(db)

    # Fetch dog species
    dog = db.query(Species).filter(Species.name == "Perro").first()
    assert dog is not None

    # Fetch diseases
    dm = db.query(Disease).filter(Disease.name == "Diabetes mellitus", Disease.species_id == dog.id).first()
    erc = db.query(Disease).filter(Disease.name == "Enfermedad renal crónica", Disease.species_id == dog.id).first()
    assert dm is not None
    assert erc is not None

    # Simulate facts: a dog presenting high glucose (> 200) and symptoms polyuria, polydipsia
    facts = {
        "poliuria": True,
        "polidipsia": True,
        "glucosa": 250.0,
    }

    # Extract evidences
    evidences = bayes_svc.obtener_evidencias_evaluacion(facts)
    assert len(evidences) == 3

    # Load active probabilities
    probs = db.query(ClinicalProbability).filter(ClinicalProbability.is_active == True).all()

    # Calculate posterior probabilities
    likelihood_dm = bayes_svc.calcular_probabilidad_bayes(dm, evidences, probs)
    likelihood_erc = bayes_svc.calcular_probabilidad_bayes(erc, evidences, probs)

    # Expected DM = prior (0.18) * poliuria (0.80) * polidipsia (0.85) * glucosa > 200 (0.90)
    expected_likelihood_dm = 0.18 * 0.80 * 0.85 * 0.90
    assert abs(likelihood_dm - expected_likelihood_dm) < 1e-6

    # Expected ERC = prior (0.20) * poliuria (0.70) * polidipsia (0.75) * glucosa (smoothing 0.5)
    expected_likelihood_erc = 0.20 * 0.70 * 0.75 * 0.50
    assert abs(likelihood_erc - expected_likelihood_erc) < 1e-6

    # Test normalization
    results = [
        {"disease_id": dm.id, "likelihood": likelihood_dm},
        {"disease_id": erc.id, "likelihood": likelihood_erc},
    ]
    normalized = bayes_svc.normalizar_probabilidades(results)

    total = likelihood_dm + likelihood_erc
    assert abs(normalized[0]["probability"] - round(likelihood_dm / total, 4)) < 1e-6
    assert abs(normalized[1]["probability"] - round(likelihood_erc / total, 4)) < 1e-6


def test_hybrid_inference_flow_and_risk_assignment(db):
    """
    Tests coordinate flow inside InferenceService (combining IF-THEN rules + Bayes).
    """
    dog = db.query(Species).filter(Species.name == "Perro").first()
    poodle = db.query(Breed).filter(Breed.name == "Poodle", Breed.species_id == dog.id).first()

    # Create Owner and Patient
    owner = Owner(first_name="Carlos", last_name="Mendoza", email="carlos@example.com")
    db.add(owner)
    db.commit()

    patient = Patient(
        owner_id=owner.id,
        name="Toby",
        species_id=dog.id,
        breed_id=poodle.id,
        sex="Macho",
        weight=12.5,
        created_by=1,
    )
    db.add(patient)
    db.commit()

    # Create Clinical Evaluation
    eval_repo = EvaluationRepository(db)
    facts = [
        {"fact_key": "poliuria", "value": True, "source_type": "clinical_input"},
        {"fact_key": "polidipsia", "value": True, "source_type": "clinical_input"},
        {"fact_key": "glucosa", "value": 260.0, "source_type": "clinical_input"},
        {"fact_key": "glucosuria", "value": "presente", "source_type": "clinical_input"},
    ]
    evaluation = eval_repo.create_with_facts(
        patient_id=patient.id,
        veterinarian_id=1,
        reason="Chequeo por poliuria y letargo",
        observations="Paciente alerta",
        facts=facts,
    )

    # Run Inference Service
    service = InferenceService(
        RuleRepository(db),
        PatientRepository(db),
        EvaluationRepository(db),
        ResultRepository(db),
    )

    persisted = service.run_and_persist(evaluation.id)
    assert len(persisted) > 0

    # Let's find Diabetes Mellitus in persisted results
    dm_res = next((r for r in persisted if r.disease.name == "Diabetes mellitus"), None)
    assert dm_res is not None

    # Glucosa > 200 triggers rules DM-R03 and glucosuria present triggers DM-R04 (both are High Risk rules)
    # Probability should be very high, and because of high rules and high probability, risk level must be "Alto"
    assert dm_res.probability > 0.50
    assert dm_res.risk_level == "Alto"
    assert len(dm_res.activated_rules) == 2
    assert dm_res.inference_method == "reglas_bayes"
    assert "glucosa (260" in dm_res.explanation.lower()
    assert "poliuria" in dm_res.explanation.lower()


def test_spanish_inference_endpoint(client, db):
    """
    Tests the POST /evaluaciones/{id}/procesar endpoint to ensure correct Spanish JSON contract.
    """
    dog = db.query(Species).filter(Species.name == "Perro").first()
    poodle = db.query(Breed).filter(Breed.name == "Poodle", Breed.species_id == dog.id).first()

    # Create Owner, Patient, and Evaluation
    owner = Owner(first_name="Maria", last_name="Gomez", email="maria@example.com")
    db.add(owner)
    db.commit()

    patient = Patient(
        owner_id=owner.id,
        name="Michi",
        species_id=dog.id,
        breed_id=poodle.id,
        sex="Hembra",
        weight=8.0,
        created_by=1,
    )
    db.add(patient)
    db.commit()

    eval_repo = EvaluationRepository(db)
    facts = [
        {"fact_key": "poliuria", "value": True},
        {"fact_key": "polidipsia", "value": True},
        {"fact_key": "glucosa", "value": 240.0},
    ]
    evaluation = eval_repo.create_with_facts(
        patient_id=patient.id,
        veterinarian_id=1,
        reason="Sospecha de diabetes",
        observations="...",
        facts=facts,
    )

    # Call Spanish endpoint
    response = client.post(f"/api/v1/evaluaciones/{evaluation.id}/procesar")
    assert response.status_code == 200

    data = response.json()
    assert data["evaluacion_id"] == evaluation.id
    assert data["metodo_inferencia"] == "reglas_bayes"
    assert len(data["resultados"]) > 0

    # Locate Diabetes Mellitus
    dm_res = next((r for r in data["resultados"] if r["enfermedad"] == "Diabetes mellitus"), None)
    assert dm_res is not None
    assert dm_res["probabilidad"] > 0.50
    assert dm_res["nivel_riesgo"] == "Alto"
    assert "DM-R03" in dm_res["reglas_activadas"]
    assert "glucosa" in dm_res["explicacion"].lower()


def test_clinical_probabilities_crud(client, db):
    """
    Tests GET, POST, PUT, DELETE endpoints for Clinical Probability management.
    """
    dog = db.query(Species).filter(Species.name == "Perro").first()
    dm = db.query(Disease).filter(Disease.name == "Diabetes mellitus", Disease.species_id == dog.id).first()

    # Create a new clinical probability
    payload = {
        "disease_id": dm.id,
        "symptom_id": None,
        "variable_id": None,
        "expected_value": "test_val",
        "probability_given_disease": 0.77,
        "general_probability": 0.33,
        "is_active": True
    }
    response = client.post("/api/v1/probabilidades-clinicas", json=payload)
    assert response.status_code == 201
    prob_id = response.json()["id"]
    assert response.json()["probability_given_disease"] == 0.77

    # Get details
    response = client.get(f"/api/v1/probabilidades-clinicas/{prob_id}")
    assert response.status_code == 200
    assert response.json()["expected_value"] == "test_val"

    # List filtered by disease
    response = client.get(f"/api/v1/probabilidades-clinicas?disease_id={dm.id}")
    assert response.status_code == 200
    assert any(p["id"] == prob_id for p in response.json())

    # Update
    update_payload = {
        "probability_given_disease": 0.88
    }
    response = client.put(f"/api/v1/probabilidades-clinicas/{prob_id}", json=update_payload)
    assert response.status_code == 200
    assert response.json()["probability_given_disease"] == 0.88

    # Delete (Deactivate)
    response = client.delete(f"/api/v1/probabilidades-clinicas/{prob_id}")
    assert response.status_code == 200
    assert response.json()["is_active"] is False
