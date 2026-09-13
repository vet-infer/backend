"""
Verificacion manual de las 4 enfermedades nuevas (2 perros, 2 gatos):
- Otitis externa (Perro)
- Hipotiroidismo canino (Perro)
- Hipertiroidismo felino (Gato)
- Asma felina (Gato)

Para cada una se recalculan a mano los likelihoods bayesianos
(prior * producto de razones de verosimilitud) y se comparan contra
BayesService.calcular_probabilidad_bayes, y se corrobora el flujo
completo reglas + bayes vía InferenceService (activacion de reglas,
probabilidad normalizada y nivel de riesgo).
"""
import logging

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import (
    Species, Breed, Disease, Owner, Patient, Role, User, ClinicalProbability,
)
from app.services.bootstrap_service import bootstrap_reference_data
from app.services.bayes_service import BayesService
from app.services.inference_service import InferenceService
from app.repositories.rule_repository import RuleRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.result_repository import ResultRepository
from app.core.security import get_password_hash

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
        db.add(User(id=1, full_name="Dr. Juan Perez", email="vet@example.com",
                    password_hash=get_password_hash("password"), role_id=2))
        db.commit()
        bootstrap_reference_data(db)
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def _ratio(probs, disease_id, *, symptom_name=None, variable_key=None):
    if symptom_name is not None:
        p = next(p for p in probs if p.disease_id == disease_id and p.symptom is not None and p.symptom.name == symptom_name)
    else:
        p = next(p for p in probs if p.disease_id == disease_id and p.variable is not None and p.variable.key == variable_key)
    return p.probability_given_disease / p.general_probability


def test_otitis_externa_perro_bayes_manual(db, caplog):
    bayes_svc = BayesService(db)
    dog = db.query(Species).filter(Species.name == "Perro").first()
    oti = db.query(Disease).filter(Disease.name == "Otitis externa", Disease.species_id == dog.id).first()
    assert oti is not None
    assert oti.base_probability == 0.22

    facts = {
        "mal olor otico": True,
        "secrecion otica": True,
        "rascado de oidos": True,
        "citologia_otica": "positiva",
    }
    evidences = bayes_svc.obtener_evidencias_evaluacion(facts)
    assert len(evidences) == 4

    probs = db.query(ClinicalProbability).filter(ClinicalProbability.is_active == True).all()  # noqa: E712

    with caplog.at_level(logging.DEBUG, logger="app.services.bayes_service"):
        likelihood = bayes_svc.calcular_probabilidad_bayes(oti, evidences, probs)

    expected = (
        oti.base_probability
        * _ratio(probs, oti.id, symptom_name="mal olor otico")
        * _ratio(probs, oti.id, symptom_name="secrecion otica")
        * _ratio(probs, oti.id, symptom_name="rascado de oidos")
        * _ratio(probs, oti.id, variable_key="citologia_otica")
    )
    # 0.22 * (0.75/0.2) * (0.8/0.15) * (0.7/0.25) * (0.85/0.2) = 52.36
    assert abs(expected - 52.36) < 1e-6
    assert abs(likelihood - expected) < 1e-6


def test_hipotiroidismo_canino_bayes_manual(db):
    bayes_svc = BayesService(db)
    dog = db.query(Species).filter(Species.name == "Perro").first()
    hipo = db.query(Disease).filter(Disease.name == "Hipotiroidismo canino", Disease.species_id == dog.id).first()
    assert hipo is not None
    assert hipo.base_probability == 0.15

    facts = {
        "letargo": True,
        "aumento de peso": True,
        "intolerancia al frio": True,
        "alopecia simetrica": True,
        "t4_total": 0.6,
    }
    evidences = bayes_svc.obtener_evidencias_evaluacion(facts)
    probs = db.query(ClinicalProbability).filter(ClinicalProbability.is_active == True).all()  # noqa: E712

    likelihood = bayes_svc.calcular_probabilidad_bayes(hipo, evidences, probs)

    expected = (
        hipo.base_probability
        * _ratio(probs, hipo.id, symptom_name="letargo")
        * _ratio(probs, hipo.id, symptom_name="aumento de peso")
        * _ratio(probs, hipo.id, symptom_name="intolerancia al frio")
        * _ratio(probs, hipo.id, symptom_name="alopecia simetrica")
        * _ratio(probs, hipo.id, variable_key="t4_total")
    )
    # 0.15 * (0.6/0.3) * (0.65/0.15) * (0.55/0.1) * (0.6/0.12) * (0.85/0.1) = 303.875
    assert abs(expected - 303.875) < 1e-6
    assert abs(likelihood - expected) < 1e-6


def test_hipertiroidismo_felino_bayes_manual(db):
    bayes_svc = BayesService(db)
    cat = db.query(Species).filter(Species.name == "Gato").first()
    hipert = db.query(Disease).filter(Disease.name == "Hipertiroidismo felino", Disease.species_id == cat.id).first()
    assert hipert is not None
    assert hipert.base_probability == 0.15

    facts = {
        "polifagia": True,
        "perdida de peso": True,
        "hiperactividad": True,
        "taquicardia": True,
        "t4_total": 5.2,
    }
    evidences = bayes_svc.obtener_evidencias_evaluacion(facts)
    probs = db.query(ClinicalProbability).filter(ClinicalProbability.is_active == True).all()  # noqa: E712

    likelihood = bayes_svc.calcular_probabilidad_bayes(hipert, evidences, probs)

    expected = (
        hipert.base_probability
        * _ratio(probs, hipert.id, symptom_name="polifagia")
        * _ratio(probs, hipert.id, symptom_name="perdida de peso")
        * _ratio(probs, hipert.id, symptom_name="hiperactividad")
        * _ratio(probs, hipert.id, symptom_name="taquicardia")
        * _ratio(probs, hipert.id, variable_key="t4_total")
    )
    # 0.15 * (0.75/0.2) * (0.7/0.22) * (0.6/0.15) * (0.55/0.12) * (0.88/0.08)
    assert abs(likelihood - expected) < 1e-6
    assert expected > 10  # evidencia fuerte y consistente -> likelihood elevado


def test_asma_felina_bayes_manual(db):
    bayes_svc = BayesService(db)
    cat = db.query(Species).filter(Species.name == "Gato").first()
    asma = db.query(Disease).filter(Disease.name == "Asma felina", Disease.species_id == cat.id).first()
    assert asma is not None
    assert asma.base_probability == 0.15

    facts = {
        "tos": True,
        "disnea": True,
        "sibilancias": True,
        "hallazgos_radiograficos_toracicos": "patron bronquial",
    }
    evidences = bayes_svc.obtener_evidencias_evaluacion(facts)
    probs = db.query(ClinicalProbability).filter(ClinicalProbability.is_active == True).all()  # noqa: E712

    likelihood = bayes_svc.calcular_probabilidad_bayes(asma, evidences, probs)

    expected = (
        asma.base_probability
        * _ratio(probs, asma.id, symptom_name="tos")
        * _ratio(probs, asma.id, symptom_name="disnea")
        * _ratio(probs, asma.id, symptom_name="sibilancias")
        * _ratio(probs, asma.id, variable_key="hallazgos_radiograficos_toracicos")
    )
    assert abs(likelihood - expected) < 1e-6
    assert expected > 5


def test_otitis_externa_hybrid_inference_flow(db):
    """Corrobora el flujo completo (reglas IF-THEN + Bayes) end-to-end para Otitis externa."""
    dog = db.query(Species).filter(Species.name == "Perro").first()
    poodle = db.query(Breed).filter(Breed.name == "Poodle", Breed.species_id == dog.id).first()

    owner = Owner(first_name="Rosa", last_name="Diaz", email="rosa@example.com")
    db.add(owner)
    db.commit()

    patient = Patient(
        owner_id=owner.id, name="Rocky", species_id=dog.id, breed_id=poodle.id,
        sex="Macho", weight=9.0, created_by=1,
    )
    db.add(patient)
    db.commit()

    eval_repo = EvaluationRepository(db)
    facts = [
        {"fact_key": "mal olor otico", "value": True, "source_type": "clinical_input"},
        {"fact_key": "secrecion otica", "value": True, "source_type": "clinical_input"},
        {"fact_key": "rascado de oidos", "value": True, "source_type": "clinical_input"},
        {"fact_key": "sacudida de cabeza", "value": True, "source_type": "clinical_input"},
        {"fact_key": "eritema del pabellon auricular", "value": True, "source_type": "clinical_input"},
        {"fact_key": "citologia_otica", "value": "positiva", "source_type": "clinical_input"},
    ]
    evaluation = eval_repo.create_with_facts(
        patient_id=patient.id, veterinarian_id=1,
        reason="Sacudida de cabeza y mal olor en oidos", observations="Paciente alerta",
        facts=facts,
    )

    service = InferenceService(
        RuleRepository(db), PatientRepository(db), EvaluationRepository(db), ResultRepository(db),
    )
    persisted = service.run_and_persist(evaluation.id)
    assert len(persisted) > 0

    oti_res = next((r for r in persisted if r.disease.name == "Otitis externa"), None)
    assert oti_res is not None

    # Las 3 reglas OTI-R01, OTI-R02 y OTI-R03 deben activarse con estos hechos.
    assert len(oti_res.activated_rules) == 3
    assert oti_res.probability > 0.50
    assert oti_res.risk_level == "Alto"
    assert oti_res.inference_method == "reglas_bayes"


def test_hipertiroidismo_felino_hybrid_inference_flow(db):
    cat = db.query(Species).filter(Species.name == "Gato").first()
    persian = db.query(Breed).filter(Breed.name == "Persian", Breed.species_id == cat.id).first()

    owner = Owner(first_name="Lucia", last_name="Vera", email="lucia@example.com")
    db.add(owner)
    db.commit()

    patient = Patient(
        owner_id=owner.id, name="Michi", species_id=cat.id, breed_id=persian.id,
        sex="Hembra", weight=3.8, created_by=1,
    )
    db.add(patient)
    db.commit()

    eval_repo = EvaluationRepository(db)
    facts = [
        {"fact_key": "polifagia", "value": True, "source_type": "clinical_input"},
        {"fact_key": "perdida de peso", "value": True, "source_type": "clinical_input"},
        {"fact_key": "hiperactividad", "value": True, "source_type": "clinical_input"},
        {"fact_key": "taquicardia", "value": True, "source_type": "clinical_input"},
        {"fact_key": "t4_total", "value": 5.5, "source_type": "clinical_input"},
    ]
    evaluation = eval_repo.create_with_facts(
        patient_id=patient.id, veterinarian_id=1,
        reason="Perdida de peso pese a buen apetito", observations="Gato geriatrico",
        facts=facts,
    )

    service = InferenceService(
        RuleRepository(db), PatientRepository(db), EvaluationRepository(db), ResultRepository(db),
    )
    persisted = service.run_and_persist(evaluation.id)
    hipert_res = next((r for r in persisted if r.disease.name == "Hipertiroidismo felino"), None)
    assert hipert_res is not None

    assert len(hipert_res.activated_rules) == 4  # HIPERT-R01..R04
    assert hipert_res.probability > 0.50
    assert hipert_res.risk_level == "Alto"
