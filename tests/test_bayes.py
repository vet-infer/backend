import logging

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


def test_normalizar_probabilidades_uniform_split_when_total_likelihood_is_zero():
    service = BayesService(db=None)
    resultados = [
        {"disease_id": 1, "likelihood": 0.0},
        {"disease_id": 2, "likelihood": 0.0},
        {"disease_id": 3, "likelihood": 0.0},
    ]

    normalized = service.normalizar_probabilidades(resultados)

    assert all(r["probability"] == round(1.0 / 3, 4) for r in normalized)


def test_normalizar_probabilidades_uniform_split_when_total_likelihood_is_negative():
    service = BayesService(db=None)
    resultados = [
        {"disease_id": 1, "likelihood": -0.5},
        {"disease_id": 2, "likelihood": -0.5},
    ]

    normalized = service.normalizar_probabilidades(resultados)

    assert all(r["probability"] == 0.5 for r in normalized)


@pytest.mark.parametrize(
    ("probability", "expected_risk"),
    [(0.0, "Bajo"), (0.3999, "Bajo"), (0.40, "Moderado"), (0.6999, "Moderado"), (0.70, "Alto"), (1.0, "Alto")],
)
def test_risk_level_uses_documented_probability_ranges(probability, expected_risk):
    service = BayesService(db=None)

    assert service.determinar_nivel_riesgo(probability, [{"risk_level": "alto"}]) == expected_risk


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


def test_bayes_service_calculations(db, caplog):
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
    with caplog.at_level(logging.DEBUG, logger="app.services.bayes_service"):
        likelihood_dm = bayes_svc.calcular_probabilidad_bayes(dm, evidences, probs)
        likelihood_erc = bayes_svc.calcular_probabilidad_bayes(erc, evidences, probs)

    messages = "\n".join(record.getMessage() for record in caplog.records)
    assert f"disease_id={dm.id}" in messages
    # ERC no tiene ClinicalProbability para "glucosa" -> debe registrar warning de smoothing
    assert "Sin ClinicalProbability" in messages and "glucosa" in messages

    def _ratio(disease_id, symptom_name):
        prob = next(
            p for p in probs
            if p.disease_id == disease_id and p.symptom is not None and p.symptom.name == symptom_name
        )
        return prob.probability_given_disease / prob.general_probability

    # Expected DM = prior (0.18) * razon_verosimilitud(poliuria) * razon_verosimilitud(polidipsia)
    #             * razon_verosimilitud(glucosa > 200); "glucosa" es variable, no symptom.
    glucosa_dm = next(p for p in probs if p.disease_id == dm.id and p.variable is not None and p.variable.key == "glucosa")
    expected_likelihood_dm = (
        dm.base_probability
        * _ratio(dm.id, "poliuria")
        * _ratio(dm.id, "polidipsia")
        * (glucosa_dm.probability_given_disease / glucosa_dm.general_probability)
    )
    assert abs(likelihood_dm - expected_likelihood_dm) < 1e-6

    # Expected ERC = prior (0.20) * razon_verosimilitud(poliuria) * razon_verosimilitud(polidipsia)
    #              * glucosa (sin ClinicalProbability para ERC -> smoothing 0.5, sin cambios)
    expected_likelihood_erc = erc.base_probability * _ratio(erc.id, "poliuria") * _ratio(erc.id, "polidipsia") * 0.50
    assert abs(likelihood_erc - expected_likelihood_erc) < 1e-6

    # La razon de verosimilitud debe discriminar: Diabetes (evidencia especifica glucosa)
    # supera ampliamente a ERC (solo comparte sintomas generales) tras esta correccion.
    assert likelihood_dm > likelihood_erc * 3

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
        {"fact_key": "glucosuria", "value": "positiva", "source_type": "clinical_input"},
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
        {"fact_key": "glucosuria", "value": "positiva"},
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




def test_evaluation_fact_definition_endpoints_are_separated(client, db):
    dog = db.query(Species).filter(Species.name == "Perro").first()

    symptoms_response = client.get(f"/api/v1/evaluation-symptoms?species_id={dog.id}")
    variables_response = client.get(f"/api/v1/evaluation-clinical-variables?species_id={dog.id}")

    assert symptoms_response.status_code == 200
    assert variables_response.status_code == 200
    assert symptoms_response.json()
    assert variables_response.json()
    assert {item["source_type"] for item in symptoms_response.json()} == {"symptom"}
    assert {item["source_type"] for item in variables_response.json()} == {"clinical_variable"}


def test_evaluation_create_normalizes_legacy_clinical_input_source_type(client, db):
    dog = db.query(Species).filter(Species.name == "Perro").first()
    poodle = db.query(Breed).filter(Breed.name == "Poodle", Breed.species_id == dog.id).first()
    owner = Owner(first_name="Ana", last_name="Ruiz", email="ana.ruiz@example.com")
    db.add(owner)
    db.commit()

    patient = Patient(
        owner_id=owner.id,
        name="Luna",
        species_id=dog.id,
        breed_id=poodle.id,
        sex="Hembra",
        weight=10.0,
        created_by=1,
    )
    db.add(patient)
    db.commit()

    payload = {
        "patient_id": patient.id,
        "reason": "Poliuria y glucosa elevada",
        "facts": [
            {"fact_key": "poliuria", "value": True, "source_type": "clinical_input"},
            {"fact_key": "glucosa", "value": 240.0, "source_type": "clinical_input"},
        ],
    }

    response = client.post("/api/v1/evaluations", json=payload)

    assert response.status_code == 201
    evaluation_data = response.json()
    facts_by_key = {fact["fact_key"]: fact for fact in evaluation_data["facts"]}
    assert facts_by_key["poliuria"]["source_type"] == "symptom"
    assert facts_by_key["glucosa"]["source_type"] == "clinical_variable"
    assert facts_by_key["poliuria"]["patient_id"] == patient.id
    assert facts_by_key["poliuria"]["evaluation_id"] == evaluation_data["id"]
    assert facts_by_key["glucosa"]["patient_id"] == patient.id
    assert facts_by_key["glucosa"]["evaluation_id"] == evaluation_data["id"]

    history_response = client.get(f"/api/v1/patients/{patient.id}/history")
    assert history_response.status_code == 200
    evaluation_event = next(
        item for item in history_response.json() if item["evaluation_id"] == evaluation_data["id"]
    )
    history_facts_by_key = {fact["fact_key"]: fact for fact in evaluation_event["clinical_facts"]}
    assert history_facts_by_key["poliuria"]["source_type"] == "symptom"
    assert history_facts_by_key["glucosa"]["source_type"] == "clinical_variable"
    assert history_facts_by_key["poliuria"]["patient_id"] == patient.id
    assert history_facts_by_key["poliuria"]["evaluation_id"] == evaluation_data["id"]

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
