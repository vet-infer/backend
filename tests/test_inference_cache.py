import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.core.security import get_password_hash
from app.models import Breed, Disease, Owner, Patient, Role, RiskLevel, Species, User
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.result_repository import ResultRepository
from app.repositories.rule_repository import RuleRepository
from app.schemas.rule import RuleConditionCreate, RuleCreate, RuleStatusUpdate
from app.services.bootstrap_service import bootstrap_reference_data
from app.services.inference_service import InferenceService
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
        db.add(User(id=1, full_name="Admin", email="admin@example.com", password_hash=get_password_hash("x"), role_id=1))
        db.commit()
        bootstrap_reference_data(db)
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


def _make_patient(db):
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
    return patient


def _service(db):
    return InferenceService(RuleRepository(db), PatientRepository(db), EvaluationRepository(db), ResultRepository(db))


def test_activating_a_new_rule_is_used_by_the_next_inference_without_restart(db):
    patient = _make_patient(db)
    dm = db.query(Disease).filter(Disease.name == "Diabetes mellitus", Disease.species_id == patient.species_id).first()
    facts = {"lactato": 5.0}

    # Warm the cache with the current active rule set (lactato not covered by any seed rule)
    before = _service(db)._run_hybrid_inference(patient.species_id, facts)
    codes_before = {code for r in before for code in (a["rule_code"] for a in r["activated_rules"])}
    assert "LACT-NEW-01" not in codes_before

    risk_level = db.query(RiskLevel).filter(RiskLevel.code == "alto").first()
    rule_service = RuleService(RuleRepository(db))
    rule_service.create_rule(
        RuleCreate(
            code="LACT-NEW-01",
            name="Lactato elevado",
            disease_id=dm.id,
            risk_level_id=risk_level.id,
            weight=1.0,
            priority=1,
            conditions=[RuleConditionCreate(variable_key="lactato", operator="gt", expected_value=4)],
        )
    )

    after = _service(db)._run_hybrid_inference(patient.species_id, facts)
    codes_after = {code for r in after for code in (a["rule_code"] for a in r["activated_rules"])}
    assert "LACT-NEW-01" in codes_after


def test_deactivating_a_rule_stops_applying_on_the_next_inference_without_restart(db):
    patient = _make_patient(db)
    facts = {"glucosa": 260.0, "glucosuria": "positiva"}

    rule_repo = RuleRepository(db)
    dm_rule = rule_repo.get_by_code("DM-R03")
    assert dm_rule is not None

    before = _service(db)._run_hybrid_inference(patient.species_id, facts)
    codes_before = {code for r in before for code in (a["rule_code"] for a in r["activated_rules"])}
    assert "DM-R03" in codes_before

    RuleService(rule_repo).update_status(dm_rule.id, RuleStatusUpdate(is_active=False))

    after = _service(db)._run_hybrid_inference(patient.species_id, facts)
    codes_after = {code for r in after for code in (a["rule_code"] for a in r["activated_rules"])}
    assert "DM-R03" not in codes_after


def test_cache_does_not_change_inference_results_across_repeated_calls(db):
    patient = _make_patient(db)
    facts = {"poliuria": True, "polidipsia": True, "glucosa": 260.0, "glucosuria": "positiva"}
    service = _service(db)

    first = service._run_hybrid_inference(patient.species_id, facts)
    second = service._run_hybrid_inference(patient.species_id, facts)

    assert [(r["disease_id"], r["probability"], r["risk_level"]) for r in first] == [
        (r["disease_id"], r["probability"], r["risk_level"]) for r in second
    ]
