import os
import sys
import json
from datetime import date
from sqlalchemy.orm import Session

# Add current directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.core.database import SessionLocal, Base, engine
from app.services.bootstrap_service import bootstrap_reference_data
from app.models import (
    Species,
    Breed,
    Owner,
    Patient,
    User,
    Role,
    Disease,
    EvaluationClinical,
    EvaluationClinicalFact,
    InferenceResult,
)
from app.services.inference_service import InferenceService
from app.repositories.rule_repository import RuleRepository
from app.repositories.patient_repository import PatientRepository
from app.repositories.evaluation_repository import EvaluationRepository
from app.repositories.result_repository import ResultRepository


def setup_validation_patients(db: Session):
    """
    Ensures roles, veterinarian, default owner, and testing patients (Dog & Cat)
    are registered in the database for the validation run.
    """
    # 1. Ensure bootstrap of clinical data is completed
    print("[*] Asegurando datos de referencia clínicos...")
    bootstrap_reference_data(db)

    # 2. Get Veterinarian User
    vet_role = db.query(Role).filter(Role.name == "veterinario").first()
    vet_user = db.query(User).filter(User.role_id == vet_role.id).first()
    if not vet_user:
        vet_user = User(
            full_name="Dr. Validador Clínico",
            email="validador@vet.com",
            password_hash="argon2_hashed_password",
            role_id=vet_role.id,
        )
        db.add(vet_user)
        db.commit()
        db.refresh(vet_user)

    # 3. Create Default Owner
    owner = db.query(Owner).filter(Owner.email == "silva.validador@example.com").first()
    if not owner:
        owner = Owner(
            first_name="Silva",
            last_name="Validador",
            phone="+51999000111",
            email="silva.validador@example.com",
            address="Laboratorio de Tesis OE3",
        )
        db.add(owner)
        db.commit()
        db.refresh(owner)

    # 4. Fetch Species
    perro = db.query(Species).filter(Species.name == "Perro").first()
    gato = db.query(Species).filter(Species.name == "Gato").first()

    # 5. Fetch or Create Breeds
    poodle = db.query(Breed).filter(Breed.name == "Poodle", Breed.species_id == perro.id).first()
    if not poodle:
        poodle = Breed(name="Poodle", species_id=perro.id)
        db.add(poodle)
        db.commit()
        db.refresh(poodle)

    mestizo_cat = db.query(Breed).filter(Breed.name == "Mestizo", Breed.species_id == gato.id).first()
    if not mestizo_cat:
        mestizo_cat = Breed(name="Mestizo", species_id=gato.id)
        db.add(mestizo_cat)
        db.commit()
        db.refresh(mestizo_cat)

    # 6. Create Patients
    dog_patient = db.query(Patient).filter(Patient.owner_id == owner.id, Patient.species_id == perro.id).first()
    if not dog_patient:
        dog_patient = Patient(
            owner_id=owner.id,
            species_id=perro.id,
            breed_id=poodle.id,
            name="Rocky",
            sex="Macho",
            birth_date=date(2018, 5, 20),
            weight=14.5,
            created_by=vet_user.id,
        )
        db.add(dog_patient)
        db.commit()
        db.refresh(dog_patient)

    cat_patient = db.query(Patient).filter(Patient.owner_id == owner.id, Patient.species_id == gato.id).first()
    if not cat_patient:
        cat_patient = Patient(
            owner_id=owner.id,
            species_id=gato.id,
            breed_id=mestizo_cat.id,
            name="Luna",
            sex="Hembra",
            birth_date=date(2021, 8, 10),
            weight=4.2,
            created_by=vet_user.id,
        )
        db.add(cat_patient)
        db.commit()
        db.refresh(cat_patient)

    return vet_user.id, dog_patient.id, cat_patient.id


def define_test_cases(dog_id: int, cat_id: int):
    """
    Defines the 15 clinical cases to evaluate.
    """
    return [
        # ========================================================
        # ENFERMEDAD 1: ENFERMEDAD RENAL CRÓNICA (CANINO)
        # ========================================================
        {
            "id": 1,
            "disease_name": "Enfermedad renal crónica",
            "patient_id": dog_id,
            "description": "ERC Caso 1: Riesgo Bajo (Compensado, creatinina normal)",
            "facts": {
                "creatinina": 1.0
            },
            "expected": {
                "risk_level": "Bajo",
                "rules": [],
                "prob_min": 0.10,
                "prob_max": 0.40
            }
        },
        {
            "id": 2,
            "disease_name": "Enfermedad renal crónica",
            "patient_id": dog_id,
            "description": "ERC Caso 2: Riesgo Moderado (Creatinina borderline + PU/PD)",
            # creatinina=1.4 -> ERC-R02 fires (moderado) -> hybrid escalation to Moderado
            "facts": {
                "poliuria": True,
                "polidipsia": True,
                "creatinina": 1.4
            },
            "expected": {
                "risk_level": "Moderado",
                "rules": ["ERC-R02"],
                "prob_min": 0.20,
                "prob_max": 0.55
            }
        },
        {
            "id": 3,
            "disease_name": "Enfermedad renal crónica",
            "patient_id": dog_id,
            "description": "ERC Caso 3: Riesgo Alto (Azotemia severa creatinina 2.4 mg/dL)",
            # creatinina=2.4 -> ERC-R01 fires (alto) -> hybrid escalation to Alto
            "facts": {
                "poliuria": True,
                "polidipsia": True,
                "perdida de peso": True,
                "creatinina": 2.4,
                "densidad_urinaria": "baja"
            },
            "expected": {
                "risk_level": "Alto",
                "rules": ["ERC-R01"],
                "prob_min": 0.40,
                "prob_max": 0.80
            }
        },
        # ========================================================
        # ENFERMEDAD 2: DIABETES MELLITUS (CANINO)
        # ========================================================
        {
            "id": 4,
            "disease_name": "Diabetes mellitus",
            "patient_id": dog_id,
            "description": "DM Caso 1: Riesgo Bajo (Glucosa normal, polifagia leve)",
            "facts": {
                "polifagia": True,
                "glucosa": 95.0
            },
            "expected": {
                "risk_level": "Bajo",
                "rules": [],
                "prob_min": 0.10,
                "prob_max": 0.45
            }
        },
        {
            "id": 5,
            "disease_name": "Diabetes mellitus",
            "patient_id": dog_id,
            "description": "DM Caso 2: Riesgo Moderado (PU/PD + polifagia + glucosa 145)",
            "facts": {
                "poliuria": True,
                "polidipsia": True,
                "polifagia": True,
                "glucosa": 145.0
            },
            "expected": {
                "risk_level": "Moderado",
                "rules": [],
                "prob_min": 0.35,
                "prob_max": 0.70
            }
        },
        {
            "id": 6,
            "disease_name": "Diabetes mellitus",
            "patient_id": dog_id,
            "description": "DM Caso 3: Riesgo Alto (Glucosa 280 + glucosuria - Diabetes declarada)",
            # glucosa=280 -> DM-R03 fires (alto); glucosuria=presente -> DM-R04 fires (alto)
            "facts": {
                "poliuria": True,
                "polidipsia": True,
                "glucosa": 280.0,
                "glucosuria": "presente"
            },
            "expected": {
                "risk_level": "Alto",
                "rules": ["DM-R03", "DM-R04"],
                "prob_min": 0.50,
                "prob_max": 0.85
            }
        },
        # ========================================================
        # ENFERMEDAD 3: ENFERMEDAD CARDÍACA / MMVD (CANINO)
        # ========================================================
        {
            "id": 7,
            "disease_name": "Enfermedad cardiaca degenerativa / MMVD",
            "patient_id": dog_id,
            "description": "MMVD Caso 1: Riesgo Bajo (LA:Ao 1.2 normal)",
            "facts": {
                "tos": True,
                "la_ao": 1.2
            },
            "expected": {
                "risk_level": "Bajo",
                "rules": [],
                "prob_min": 0.05,
                "prob_max": 0.40
            }
        },
        {
            "id": 8,
            "disease_name": "Enfermedad cardiaca degenerativa / MMVD",
            "patient_id": dog_id,
            "description": "MMVD Caso 2: Riesgo Moderado (LA:Ao 1.4, soplo + intolerancia - Estadio B1)",
            # la_ao=1.4 -> MMVD-R02 fires (moderado) -> hybrid escalation to Moderado
            "facts": {
                "soplo cardiaco": True,
                "intolerancia ejercicio": True,
                "la_ao": 1.4
            },
            "expected": {
                "risk_level": "Moderado",
                "rules": ["MMVD-R02"],
                "prob_min": 0.20,
                "prob_max": 0.55
            }
        },
        {
            "id": 9,
            "disease_name": "Enfermedad cardiaca degenerativa / MMVD",
            "patient_id": dog_id,
            "description": "MMVD Caso 3: Riesgo Alto (LA:Ao 1.9, soplo + tos - Estadio C falla congestiva)",
            # la_ao=1.9 -> MMVD-R01 fires (alto) -> hybrid escalation to Alto
            "facts": {
                "soplo cardiaco": True,
                "tos": True,
                "intolerancia ejercicio": True,
                "la_ao": 1.9
            },
            "expected": {
                "risk_level": "Alto",
                "rules": ["MMVD-R01"],
                "prob_min": 0.30,
                "prob_max": 0.70
            }
        },
        # ========================================================
        # ENFERMEDAD 4: LEUCEMIA VIRAL FELINA (FELINO)
        # ========================================================
        {
            "id": 10,
            "disease_name": "Leucemia viral felina",
            "patient_id": cat_id,
            "description": "FeLV Caso 1: Riesgo Bajo (SNAP negativo - sin evidencia)",
            "facts": {
                "snap_felv": "negativo"
            },
            "expected": {
                "risk_level": "Bajo",
                "rules": [],
                "prob_min": 0.05,
                "prob_max": 0.35
            }
        },
        {
            "id": 11,
            "disease_name": "Leucemia viral felina",
            "patient_id": cat_id,
            # Nota: Sin SNAP positivo, el motor bayesiano estima riesgo Bajo con evidencia parcial.
            # Clinicamente valido: se requiere prueba confirmatoria antes de asignar riesgo Moderado.
            "description": "FeLV Caso 2: Riesgo Bajo/Sospecha (Anemia + infecciones, SNAP negativo)",
            "facts": {
                "anemia": True,
                "infecciones recurrentes": True,
                "snap_felv": "negativo"
            },
            "expected": {
                "risk_level": "Bajo",
                "rules": [],
                "prob_min": 0.10,
                "prob_max": 0.45
            }
        },
        {
            "id": 12,
            "disease_name": "Leucemia viral felina",
            "patient_id": cat_id,
            "description": "FeLV Caso 3: Riesgo Alto (SNAP positivo + Ag p27 positivo - Infeccion confirmada)",
            # snap_felv=positivo -> FELV-R01 fires (alto); felv_p27=positivo -> FELV-R02 fires (alto)
            "facts": {
                "anemia": True,
                "infecciones recurrentes": True,
                "snap_felv": "positivo",
                "felv_p27": "positivo"
            },
            "expected": {
                "risk_level": "Alto",
                "rules": ["FELV-R01", "FELV-R02"],
                "prob_min": 0.35,
                "prob_max": 0.80
            }
        },
        # ========================================================
        # ENFERMEDAD 5: ENFERMEDAD PERIODONTAL (CANINO)
        # ========================================================
        {
            "id": 13,
            "disease_name": "Enfermedad periodontal",
            "patient_id": dog_id,
            "description": "PERIO Caso 1: Riesgo Bajo (Halitosis leve, placa leve - Estadio I)",
            "facts": {
                "halitosis": True,
                "placa": "leve"
            },
            "expected": {
                "risk_level": "Bajo",
                "rules": [],
                "prob_min": 0.25,
                "prob_max": 0.50
            }
        },
        {
            "id": 14,
            "disease_name": "Enfermedad periodontal",
            "patient_id": dog_id,
            "description": "PERIO Caso 2: Riesgo Moderado (Halitosis + gingivitis + sangrado - Estadio II)",
            "facts": {
                "halitosis": True,
                "gingivitis": True,
                "sangrado gingival": True,
                "placa": "leve"
            },
            "expected": {
                "risk_level": "Moderado",
                "rules": [],
                "prob_min": 0.40,
                "prob_max": 0.75
            }
        },
        {
            "id": 15,
            "disease_name": "Enfermedad periodontal",
            "patient_id": dog_id,
            "description": "PERIO Caso 3: Riesgo Alto (Placa moderada/severa + periodontitis activa - Estadio III/IV)",
            # placa=moderada/severa -> PERIO-R01 fires (alto) -> hybrid escalation to Alto
            "facts": {
                "halitosis": True,
                "gingivitis": True,
                "sangrado gingival": True,
                "placa": "moderada/severa"
            },
            "expected": {
                "risk_level": "Alto",
                "rules": ["PERIO-R01"],
                "prob_min": 0.50,
                "prob_max": 0.85
            }
        }
    ]


def run_clinical_validation():
    print("=" * 80)
    print("    EJECUCIÓN DE PRUEBAS DE VALIDACIÓN CLÍNICA MASIVA: REGLAS + BAYES    ")
    print("=" * 80)

    db = SessionLocal()
    try:
        # Initialize references and test patients
        vet_id, dog_id, cat_id = setup_validation_patients(db)

        # Initialize Inference Services
        eval_repo = EvaluationRepository(db)
        rule_repo = RuleRepository(db)
        patient_repo = PatientRepository(db)
        res_repo = ResultRepository(db)
        inference_service = InferenceService(rule_repo, patient_repo, eval_repo, res_repo)

        # Pre-fetch rule_id -> rule_code mapping for reliable code resolution
        from app.models.rule import InferenceRule
        rule_code_map = {r.id: r.code for r in db.query(InferenceRule).all()}

        # Define cases
        cases = define_test_cases(dog_id, cat_id)

        total_cases = len(cases)
        passed_cases = 0
        failed_cases = 0
        results_report = []

        print(f"\n[*] Iniciando validación masiva sobre {total_cases} casos clínicos...\n")

        for case in cases:
            case_id = case["id"]
            desc = case["description"]
            dis_name = case["disease_name"]
            pat_id = case["patient_id"]
            facts_input = case["facts"]
            expected = case["expected"]

            print(f"[Case {case_id}] Procesando: {desc}...")

            # 1. Create clinical evaluation with facts
            facts_list = [{"fact_key": k, "value": v, "source_type": "clinical_input"} for k, v in facts_input.items()]
            evaluation = eval_repo.create_with_facts(
                patient_id=pat_id,
                veterinarian_id=vet_id,
                reason=f"Validación Automatizada OE3 - Caso {case_id}",
                observations=desc,
                facts=facts_list,
            )

            # 2. Run hybrid inference
            persisted_results = inference_service.run_and_persist(evaluation.id)

            # 3. Extract evaluated disease result
            actual_result = next((r for r in persisted_results if r.disease.name == dis_name), None)

            # 4. Perform assertion validation
            status = "PASSED"
            failures = []

            if not actual_result:
                status = "FAILED"
                failures.append(f"La enfermedad '{dis_name}' no fue reportada en los resultados.")
            else:
                prob = actual_result.probability
                risk = actual_result.risk_level
                activated_codes = [
                    rule_code_map.get(ar.rule_id, f"UNKNOWN-{ar.rule_id}")
                    for ar in actual_result.activated_rules
                ]

                # Validate probability range
                if not (expected["prob_min"] <= prob <= expected["prob_max"]):
                    status = "FAILED"
                    failures.append(f"Probabilidad real {prob} fuera del rango esperado [{expected['prob_min']}, {expected['prob_max']}]")

                # Validate risk level
                if risk != expected["risk_level"]:
                    status = "FAILED"
                    failures.append(f"Nivel de riesgo real '{risk}' difiere del esperado '{expected['risk_level']}'")

                # Validate triggered rules
                for expected_rule in expected["rules"]:
                    if expected_rule not in activated_codes:
                        status = "FAILED"
                        failures.append(f"Regla esperada '{expected_rule}' no se activó (Reglas reales: {activated_codes})")

            # Update counters
            if status == "PASSED":
                passed_cases += 1
                print(f"   ↳ \033[92m[Aprobado]\033[0m Probabilidad: {prob * 100:.2f}%, Riesgo: {risk}, Reglas: {activated_codes}")
            else:
                failed_cases += 1
                print(f"   ↳ \033[91m[FALLIDO]\033[0m Fallas encontradas: {failures}")

            results_report.append({
                "caso_id": case_id,
                "descripcion": desc,
                "enfermedad": dis_name,
                "hechos_entrada": facts_input,
                "esperado": {
                    "nivel_riesgo": expected["risk_level"],
                    "rango_probabilidad": f"[{expected['prob_min']} - {expected['prob_max']}]",
                    "reglas": expected["rules"]
                },
                "real": {
                    "nivel_riesgo": actual_result.risk_level if actual_result else None,
                    "probabilidad": actual_result.probability if actual_result else None,
                    "reglas_activadas": [
                        rule_code_map.get(ar.rule_id, f"UNKNOWN-{ar.rule_id}")
                        for ar in actual_result.activated_rules
                    ] if actual_result else [],
                    "explicacion": actual_result.explanation if actual_result else None
                },
                "estado": status,
                "diferencias": failures
            })
            print("-" * 60)

        # Calculate final stats
        success_rate = (passed_cases / total_cases) * 100

        print("\n" + "=" * 80)
        print("    RESUMEN GLOBAL DE LA VALIDACIÓN VETERINARIA VET-INFERENCE    ")
        print("=" * 80)
        print(f" Total de Casos Evaluados : {total_cases}")
        print(f" Casos Aprobados (PASSED) : \033[92m{passed_cases}\033[0m")
        print(f" Casos Fallidos (FAILED)  : \033[91m{failed_cases}\033[0m")
        print(f" Porcentaje de Éxito      : {success_rate:.2f}%")
        print("=" * 80)

        # Export findings as JSON file for evidence
        report_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "clinical_validation_report.json"))
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump({
                "resumen": {
                    "total_casos": total_cases,
                    "aprobados": passed_cases,
                    "fallidos": failed_cases,
                    "tasa_exito_porcentaje": round(success_rate, 2)
                },
                "detalles": results_report
            }, f, indent=2, ensure_ascii=False)

        print(f"\n[+] Evidencia técnica exportada exitosamente en:\n    {report_path}\n")

    finally:
        db.close()


if __name__ == "__main__":
    run_clinical_validation()
