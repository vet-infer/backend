"""Demo script: runs two clinical evaluations (dog otitis, cat hyperthyroid) through
the real hybrid inference pipeline and prints the exact results, to hand the user
concrete numbers to compare against the running app."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import Species, Breed, Owner, Patient, Role, User
from app.services.bootstrap_service import bootstrap_reference_data
from app.services.inference_service import InferenceService
from app.repositories.rule_repository import RuleRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.result_repository import ResultRepository
from app.core.security import get_password_hash

engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)
db = Session()

db.add(Role(id=1, name="admin", description="Admin"))
db.add(Role(id=2, name="veterinario", description="Veterinario"))
db.add(User(id=1, full_name="Dr. Juan Perez", email="vet@example.com", password_hash=get_password_hash("x"), role_id=2))
db.commit()
bootstrap_reference_data(db)

service = InferenceService(RuleRepository(db), PatientRepository(db), EvaluationRepository(db), ResultRepository(db))
eval_repo = EvaluationRepository(db)


def run_case(species_name, breed_name, patient_name, facts, title):
    species = db.query(Species).filter(Species.name == species_name).first()
    breed = db.query(Breed).filter(Breed.name == breed_name, Breed.species_id == species.id).first()
    owner = Owner(first_name="Demo", last_name="Owner", email=f"{patient_name.lower()}@example.com")
    db.add(owner)
    db.commit()
    patient = Patient(owner_id=owner.id, name=patient_name, species_id=species.id, breed_id=breed.id, sex="Macho", weight=10.0, created_by=1)
    db.add(patient)
    db.commit()
    evaluation = eval_repo.create_with_facts(
        patient_id=patient.id, veterinarian_id=1, reason=title, observations="demo",
        facts=[{"fact_key": k, "value": v, "source_type": "clinical_input"} for k, v in facts.items()],
    )
    results = service.run_and_persist(evaluation.id)
    print(f"\n=== {title} ({species_name}) ===")
    for r in sorted(results, key=lambda x: x.probability, reverse=True)[:5]:
        rules = ", ".join(ar.rule_code for ar in r.activated_rules)
        print(f"  {r.disease.name:45s} prob={r.probability*100:6.2f}%  riesgo={r.risk_level:8s} reglas=[{rules}]")


run_case(
    "Perro", "Poodle", "Rocky",
    {
        "mal olor otico": True,
        "secrecion otica": True,
        "rascado de oidos": True,
        "sacudida de cabeza": True,
        "eritema del pabellon auricular": True,
        "citologia_otica": "positiva",
    },
    "Caso 1: Otitis externa (perro)",
)

run_case(
    "Gato", "Persian", "Michi",
    {
        "polifagia": True,
        "perdida de peso": True,
        "hiperactividad": True,
        "taquicardia": True,
        "t4_total": 5.5,
    },
    "Caso 2: Hipertiroidismo felino (gato)",
)

db.close()
