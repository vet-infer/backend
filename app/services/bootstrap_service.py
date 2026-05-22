from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_password_hash
from app.models.species import Species
from app.models.breed import Breed
from app.models.role import Role
from app.models.user import User
from app.models.disease import Disease
from app.models.symptom import Symptom
from app.models.clinical_variable import ClinicalVariable
from app.models.rule import InferenceRule, RuleCondition
from app.models.clinical_probability import ClinicalProbability
from app.models.risk_level import RiskLevel


RISK_LEVELS = [
    {
        "code": "bajo",
        "name": "Bajo",
        "description": "Riesgo clinico bajo o evidencia insuficiente para sospecha relevante.",
        "min_probability": 0.0,
        "max_probability": 0.3999,
        "sort_order": 1,
    },
    {
        "code": "moderado",
        "name": "Moderado",
        "description": "Riesgo clinico intermedio que requiere seguimiento o pruebas complementarias.",
        "min_probability": 0.40,
        "max_probability": 0.6999,
        "sort_order": 2,
    },
    {
        "code": "alto",
        "name": "Alto",
        "description": "Riesgo clinico alto compatible con alerta temprana prioritaria.",
        "min_probability": 0.70,
        "max_probability": 1.0,
        "sort_order": 3,
    },
]


def normalize_risk_level(value: str | None) -> str:
    normalized = (value or "moderado").strip().lower()
    aliases = {
        "low": "bajo",
        "medium": "moderado",
        "moderate": "moderado",
        "high": "alto",
    }
    return aliases.get(normalized, normalized)


def get_or_create_risk_level(db: Session, code: str) -> RiskLevel:
    normalized_code = normalize_risk_level(code)
    risk_level = db.query(RiskLevel).filter(RiskLevel.code == normalized_code).first()
    if risk_level is not None:
        return risk_level

    seed = next((item for item in RISK_LEVELS if item["code"] == normalized_code), None)
    if seed is None:
        seed = {
            "code": normalized_code,
            "name": normalized_code.capitalize(),
            "description": "Nivel de riesgo clinico definido por el sistema.",
            "min_probability": None,
            "max_probability": None,
            "sort_order": 99,
        }
    risk_level = RiskLevel(**seed, is_active=True)
    db.add(risk_level)
    db.commit()
    db.refresh(risk_level)
    return risk_level


def bootstrap_reference_data(db: Session) -> None:
    # 1. Roles
    roles = {
        "admin": "Administrador del sistema",
        "veterinario": "Medico veterinario",
        "evaluador": "Asesor o evaluador academico",
    }
    for name, description in roles.items():
        if db.query(Role).filter(Role.name == name).first() is None:
            db.add(Role(name=name, description=description))
    db.commit()

    # 1.b Risk levels
    for risk_level in RISK_LEVELS:
        existing = db.query(RiskLevel).filter(RiskLevel.code == risk_level["code"]).first()
        if existing is None:
            db.add(RiskLevel(**risk_level, is_active=True))
    db.commit()

    # 2. Species
    for species_name in ["Perro", "Gato"]:
        if db.query(Species).filter(Species.name == species_name).first() is None:
            db.add(Species(name=species_name))
    db.commit()

    perro = db.query(Species).filter(Species.name == "Perro").first()
    gato = db.query(Species).filter(Species.name == "Gato").first()

    # 3. Breeds
    for species_name, breed_names in [
        ("Perro", ["Mestizo", "Poodle", "Schnauzer", "Yorkshire Terrier", "Chihuahua"]),
        ("Gato", ["Mestizo", "Siamés", "Persa", "Maine Coon"])
    ]:
        species = db.query(Species).filter(Species.name == species_name).first()
        if species:
            for breed_name in breed_names:
                if db.query(Breed).filter(Breed.species_id == species.id, Breed.name == breed_name).first() is None:
                    db.add(Breed(species_id=species.id, name=breed_name))
    db.commit()

    # 4. Admin User
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if settings.bootstrap_admin_email and settings.bootstrap_admin_password and admin_role:
        existing_admin = db.query(User).filter(User.email == settings.bootstrap_admin_email).first()
        if existing_admin is None:
            db.add(
                User(
                    full_name="Administrador",
                    email=settings.bootstrap_admin_email,
                    password_hash=get_password_hash(settings.bootstrap_admin_password),
                    role_id=admin_role.id,
                )
            )
            db.commit()

    # 5. Symptoms
    symptoms_data = [
        {"name": "poliuria", "species_id": perro.id},
        {"name": "polidipsia", "species_id": perro.id},
        {"name": "perdida de peso", "species_id": perro.id},
        {"name": "polifagia", "species_id": perro.id},
        {"name": "soplo cardiaco", "species_id": perro.id},
        {"name": "tos", "species_id": perro.id},
        {"name": "intolerancia ejercicio", "species_id": perro.id},
        {"name": "halitosis", "species_id": perro.id},
        {"name": "gingivitis", "species_id": perro.id},
        {"name": "sangrado gingival", "species_id": perro.id},
        # Cat symptoms
        {"name": "poliuria", "species_id": gato.id},
        {"name": "polidipsia", "species_id": gato.id},
        {"name": "perdida de peso", "species_id": gato.id},
        {"name": "anemia", "species_id": gato.id},
        {"name": "infecciones recurrentes", "species_id": gato.id},
    ]

    for sym in symptoms_data:
        existing = db.query(Symptom).filter(Symptom.name == sym["name"], Symptom.species_id == sym["species_id"]).first()
        if not existing:
            db.add(Symptom(name=sym["name"], species_id=sym["species_id"]))
    db.commit()

    # 6. Clinical Variables
    variables_data = [
        # Dog variables
        {"key": "creatinina", "name": "Creatinina sérica", "data_type": "numeric", "unit": "mg/dL", "normal_min": 0.5, "normal_max": 1.6, "species_id": perro.id},
        {"key": "densidad_urinaria", "name": "Densidad urinaria", "data_type": "numeric", "unit": "", "normal_min": 1.015, "normal_max": 1.045, "species_id": perro.id},
        {"key": "glucosa", "name": "Glucosa sanguínea", "data_type": "numeric", "unit": "mg/dL", "normal_min": 70, "normal_max": 120, "species_id": perro.id},
        {"key": "glucosuria", "name": "Glucosa en orina", "data_type": "string", "unit": "", "normal_min": None, "normal_max": None, "species_id": perro.id},
        {"key": "la_ao", "name": "Relación LA:Ao", "data_type": "numeric", "unit": "ratio", "normal_min": 1.0, "normal_max": 1.6, "species_id": perro.id},
        {"key": "placa", "name": "Nivel de placa dental", "data_type": "string", "unit": "", "normal_min": None, "normal_max": None, "species_id": perro.id},
        # Cat variables
        {"key": "creatinina", "name": "Creatinina sérica", "data_type": "numeric", "unit": "mg/dL", "normal_min": 0.5, "normal_max": 1.6, "species_id": gato.id},
        {"key": "felv_p27", "name": "Antígeno p27 FeLV", "data_type": "string", "unit": "", "normal_min": None, "normal_max": None, "species_id": gato.id},
        {"key": "snap_felv", "name": "Resultado SNAP FeLV", "data_type": "string", "unit": "", "normal_min": None, "normal_max": None, "species_id": gato.id},
    ]

    for var in variables_data:
        existing = db.query(ClinicalVariable).filter(ClinicalVariable.key == var["key"], ClinicalVariable.species_id == var["species_id"]).first()
        if not existing:
            db.add(ClinicalVariable(
                key=var["key"],
                name=var["name"],
                data_type=var["data_type"],
                unit=var["unit"],
                normal_min=var["normal_min"],
                normal_max=var["normal_max"],
                species_id=var["species_id"]
            ))
    db.commit()

    # 7. Diseases
    diseases_data = [
        # Dogs
        {"name": "Enfermedad renal crónica", "species_id": perro.id, "base_probability": 0.20, "description": "Insuficiencia renal progresiva y degenerativa en caninos."},
        {"name": "Diabetes mellitus", "species_id": perro.id, "base_probability": 0.18, "description": "Trastorno metabolico de la glucosa en caninos."},
        {"name": "Enfermedad cardiaca degenerativa / MMVD", "species_id": perro.id, "base_probability": 0.15, "description": "Degeneracion mixomatosa de la valvula mitral."},
        {"name": "Enfermedad periodontal", "species_id": perro.id, "base_probability": 0.25, "description": "Enfermedad oral inflamatoria cronica canina."},
        # Cats
        {"name": "Leucemia viral felina", "species_id": gato.id, "base_probability": 0.12, "description": "Infeccion viral retrovirica felina."},
        {"name": "Enfermedad renal crónica", "species_id": gato.id, "base_probability": 0.20, "description": "Insuficiencia renal progresiva y degenerativa en felinos."},
        {"name": "Diabetes mellitus", "species_id": gato.id, "base_probability": 0.18, "description": "Trastorno metabolico de la glucosa en felinos."},
        {"name": "Enfermedad periodontal", "species_id": gato.id, "base_probability": 0.25, "description": "Enfermedad oral inflamatoria cronica felina."},
    ]

    for dis in diseases_data:
        existing = db.query(Disease).filter(Disease.name == dis["name"], Disease.species_id == dis["species_id"]).first()
        if not existing:
            db.add(Disease(
                name=dis["name"],
                species_id=dis["species_id"],
                base_probability=dis["base_probability"],
                description=dis["description"]
            ))
    db.commit()

    # Fetch diseases for references
    erc_dog = db.query(Disease).filter(Disease.name == "Enfermedad renal crónica", Disease.species_id == perro.id).first()
    dm_dog = db.query(Disease).filter(Disease.name == "Diabetes mellitus", Disease.species_id == perro.id).first()
    mmvd_dog = db.query(Disease).filter(Disease.name == "Enfermedad cardiaca degenerativa / MMVD", Disease.species_id == perro.id).first()
    perio_dog = db.query(Disease).filter(Disease.name == "Enfermedad periodontal", Disease.species_id == perro.id).first()
    felv_cat = db.query(Disease).filter(Disease.name == "Leucemia viral felina", Disease.species_id == gato.id).first()
    risk_levels_by_code = {
        risk.code: risk
        for risk in db.query(RiskLevel).filter(RiskLevel.code.in_(["bajo", "moderado", "alto"])).all()
    }

    # 8. Rules & Rule Conditions (Dummy / Clinical rules matching actual variables)
    rules_data = [
        # ERC Dog Rules
        # R01: Azotemia declarada (creatinina > 1.6 mg/dL) -> riesgo ALTO
        {"code": "ERC-R01", "name": "Azotemia severa en perro", "disease_id": erc_dog.id, "risk_level": "alto", "weight": 3.0, "priority": 2, "conditions": [
            {"variable_key": "creatinina", "operator": "gt", "expected_value": 1.6}
        ]},
        # R02: Creatinina borderline (> 1.2 mg/dL) -> sospecha MODERADA
        {"code": "ERC-R02", "name": "Creatinina borderline en perro", "disease_id": erc_dog.id, "risk_level": "moderado", "weight": 1.5, "priority": 1, "conditions": [
            {"variable_key": "creatinina", "operator": "gt", "expected_value": 1.2}
        ]},
        # DM Dog Rules
        {"code": "DM-R03", "name": "Hiperglucemia en perro", "disease_id": dm_dog.id, "risk_level": "alto", "weight": 3.0, "priority": 2, "conditions": [
            {"variable_key": "glucosa", "operator": "gt", "expected_value": 200.0}
        ]},
        {"code": "DM-R04", "name": "Glucosuria presente", "disease_id": dm_dog.id, "risk_level": "alto", "weight": 2.5, "priority": 1, "conditions": [
            {"variable_key": "glucosuria", "operator": "eq", "expected_value": "presente"}
        ]},
        # MMVD Dog Rules
        # R01: Dilatacion atrial severa (LA:Ao > 1.6) -> riesgo ALTO (estadio C/D)
        {"code": "MMVD-R01", "name": "Dilatacion atrial severa LA:Ao > 1.6", "disease_id": mmvd_dog.id, "risk_level": "alto", "weight": 3.5, "priority": 2, "conditions": [
            {"variable_key": "la_ao", "operator": "gt", "expected_value": 1.6}
        ]},
        # R02: Remodelado cardiaco inicial (LA:Ao > 1.35) -> sospecha MODERADA (estadio B1)
        {"code": "MMVD-R02", "name": "Remodelado cardiaco inicial LA:Ao > 1.35", "disease_id": mmvd_dog.id, "risk_level": "moderado", "weight": 2.0, "priority": 1, "conditions": [
            {"variable_key": "la_ao", "operator": "gt", "expected_value": 1.35}
        ]},
        # Periodontal Dog Rules
        # R01: Placa moderada/severa con inflamacion activa -> riesgo ALTO (periodontitis estadio III/IV)
        {"code": "PERIO-R01", "name": "Periodontitis activa placa severa", "disease_id": perio_dog.id, "risk_level": "alto", "weight": 2.5, "priority": 2, "conditions": [
            {"variable_key": "placa", "operator": "eq", "expected_value": "moderada/severa"}
        ]},
        # FeLV Cat Rules
        {"code": "FELV-R01", "name": "SNAP FeLV Positivo", "disease_id": felv_cat.id, "risk_level": "alto", "weight": 4.0, "priority": 2, "conditions": [
            {"variable_key": "snap_felv", "operator": "eq", "expected_value": "positivo"}
        ]},
        # FELV-R02: Antigeno p27 positivo confirma infeccion activa -> ALTO
        {"code": "FELV-R02", "name": "Antigeno p27 FeLV Positivo", "disease_id": felv_cat.id, "risk_level": "alto", "weight": 4.5, "priority": 3, "conditions": [
            {"variable_key": "felv_p27", "operator": "eq", "expected_value": "positivo"}
        ]},
    ]

    for rule in rules_data:
        existing = db.query(InferenceRule).filter(InferenceRule.code == rule["code"]).first()
        if not existing:
            risk_code = normalize_risk_level(rule["risk_level"])
            risk_level_ref = risk_levels_by_code.get(risk_code) or get_or_create_risk_level(db, risk_code)
            db_rule = InferenceRule(
                code=rule["code"],
                name=rule["name"],
                disease_id=rule["disease_id"],
                risk_level_id=risk_level_ref.id,
                risk_level=rule["risk_level"],
                weight=rule["weight"],
                priority=rule["priority"]
            )
            db.add(db_rule)
            db.commit()
            db.refresh(db_rule)

            for cond in rule["conditions"]:
                db.add(RuleCondition(
                    rule_id=db_rule.id,
                    variable_key=cond["variable_key"],
                    operator=cond["operator"],
                    expected_value=cond["expected_value"]
                ))
            db.commit()

    # 9. Clinical Probabilities (Teorema de Bayes Seeds)
    # Helper to fetch symptom_id or variable_id by name/key
    def sym_id(name: str, species_id: int) -> int:
        s = db.query(Symptom).filter(Symptom.name == name, Symptom.species_id == species_id).first()
        return s.id if s else None

    def var_id(key: str, species_id: int) -> int:
        v = db.query(ClinicalVariable).filter(ClinicalVariable.key == key, ClinicalVariable.species_id == species_id).first()
        return v.id if v else None

    prob_seeds = [
        # Enfermedad Renal Crónica (ERC) Canina (prior: 0.20)
        {"disease_id": erc_dog.id, "symptom_id": sym_id("poliuria", perro.id), "probability_given_disease": 0.70, "general_probability": 0.25},
        {"disease_id": erc_dog.id, "symptom_id": sym_id("polidipsia", perro.id), "probability_given_disease": 0.75, "general_probability": 0.28},
        {"disease_id": erc_dog.id, "symptom_id": sym_id("perdida de peso", perro.id), "probability_given_disease": 0.65, "general_probability": 0.22},
        {"disease_id": erc_dog.id, "variable_id": var_id("creatinina", perro.id), "expected_value": "> 1.6", "probability_given_disease": 0.85, "general_probability": 0.15},
        {"disease_id": erc_dog.id, "variable_id": var_id("densidad_urinaria", perro.id), "expected_value": "baja", "probability_given_disease": 0.80, "general_probability": 0.18},

        # Diabetes Mellitus (DM) Canina (prior: 0.18)
        {"disease_id": dm_dog.id, "symptom_id": sym_id("poliuria", perro.id), "probability_given_disease": 0.80, "general_probability": 0.25},
        {"disease_id": dm_dog.id, "symptom_id": sym_id("polidipsia", perro.id), "probability_given_disease": 0.85, "general_probability": 0.28},
        {"disease_id": dm_dog.id, "symptom_id": sym_id("polifagia", perro.id), "probability_given_disease": 0.70, "general_probability": 0.20},
        {"disease_id": dm_dog.id, "variable_id": var_id("glucosa", perro.id), "expected_value": "> 200", "probability_given_disease": 0.90, "general_probability": 0.10},
        {"disease_id": dm_dog.id, "variable_id": var_id("glucosuria", perro.id), "expected_value": "presente", "probability_given_disease": 0.88, "general_probability": 0.12},

        # MMVD Canina (prior: 0.15)
        {"disease_id": mmvd_dog.id, "symptom_id": sym_id("soplo cardiaco", perro.id), "probability_given_disease": 0.85, "general_probability": 0.18},
        {"disease_id": mmvd_dog.id, "symptom_id": sym_id("tos", perro.id), "probability_given_disease": 0.65, "general_probability": 0.24},
        {"disease_id": mmvd_dog.id, "symptom_id": sym_id("intolerancia ejercicio", perro.id), "probability_given_disease": 0.60, "general_probability": 0.22},
        {"disease_id": mmvd_dog.id, "variable_id": var_id("la_ao", perro.id), "expected_value": "> 1.6", "probability_given_disease": 0.80, "general_probability": 0.14},

        # Enfermedad Periodontal Canina (prior: 0.25)
        {"disease_id": perio_dog.id, "symptom_id": sym_id("halitosis", perro.id), "probability_given_disease": 0.75, "general_probability": 0.30},
        {"disease_id": perio_dog.id, "variable_id": var_id("placa", perro.id), "expected_value": "moderada/severa", "probability_given_disease": 0.85, "general_probability": 0.32},
        {"disease_id": perio_dog.id, "symptom_id": sym_id("gingivitis", perro.id), "probability_given_disease": 0.80, "general_probability": 0.35},
        {"disease_id": perio_dog.id, "symptom_id": sym_id("sangrado gingival", perro.id), "probability_given_disease": 0.65, "general_probability": 0.20},

        # Leucemia Viral Felina (FeLV) (prior: 0.12)
        {"disease_id": felv_cat.id, "variable_id": var_id("felv_p27", gato.id), "expected_value": "positivo", "probability_given_disease": 0.95, "general_probability": 0.05},
        {"disease_id": felv_cat.id, "variable_id": var_id("snap_felv", gato.id), "expected_value": "positivo", "probability_given_disease": 0.93, "general_probability": 0.06},
        {"disease_id": felv_cat.id, "symptom_id": sym_id("anemia", gato.id), "probability_given_disease": 0.65, "general_probability": 0.18},
        {"disease_id": felv_cat.id, "symptom_id": sym_id("infecciones recurrentes", gato.id), "probability_given_disease": 0.60, "general_probability": 0.20},
    ]

    for seed in prob_seeds:
        # Check if already seeded
        query = db.query(ClinicalProbability).filter(
            ClinicalProbability.disease_id == seed["disease_id"]
        )
        if seed.get("symptom_id") is not None:
            query = query.filter(ClinicalProbability.symptom_id == seed["symptom_id"])
        elif seed.get("variable_id") is not None:
            query = query.filter(ClinicalProbability.variable_id == seed["variable_id"])

        existing = query.first()
        if not existing:
            db.add(ClinicalProbability(
                disease_id=seed["disease_id"],
                symptom_id=seed.get("symptom_id"),
                variable_id=seed.get("variable_id"),
                expected_value=seed.get("expected_value"),
                probability_given_disease=seed["probability_given_disease"],
                general_probability=seed["general_probability"],
                is_active=True
            ))

    db.commit()
