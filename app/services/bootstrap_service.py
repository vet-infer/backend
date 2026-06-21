import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.constants import DEFAULT_RISK_LEVEL
from app.core.security import get_password_hash
from app.models.breed import Breed
from app.models.clinical_probability import ClinicalProbability
from app.models.clinical_variable import ClinicalVariable
from app.models.disease import Disease
from app.models.risk_level import RiskLevel
from app.models.role import Role
from app.models.rule import InferenceRule, RuleCondition
from app.models.species import Species
from app.models.symptom import Symptom
from app.models.user import User
from app.models.knowledge import FactDefinition, KnowledgeSource, RuleReference


def load_seed_data() -> dict[str, Any]:
    path = Path(settings.seed_data_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    with path.open(encoding="utf-8-sig") as seed_file:
        return json.load(seed_file)


def normalize_risk_level(value: str | None) -> str:
    normalized = (value or DEFAULT_RISK_LEVEL).strip().lower()
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

    seed = next((item for item in load_seed_data()["risk_levels"] if item["code"] == normalized_code), None)
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


def _species_id(db: Session, name: str) -> int:
    species = db.query(Species).filter(Species.name == name).first()
    if species is None:
        raise ValueError(f"Especie semilla no encontrada: {name}")
    return species.id


def _disease(db: Session, name: str, species_name: str) -> Disease:
    species_id = _species_id(db, species_name)
    disease = db.query(Disease).filter(Disease.name == name, Disease.species_id == species_id).first()
    if disease is None:
        raise ValueError(f"Enfermedad semilla no encontrada: {name} ({species_name})")
    return disease


def _symptom_id(db: Session, name: str, species_name: str) -> int | None:
    species_id = _species_id(db, species_name)
    symptom = db.query(Symptom).filter(Symptom.name == name, Symptom.species_id == species_id).first()
    return symptom.id if symptom else None


def _variable_id(db: Session, key: str, species_name: str) -> int | None:
    species_id = _species_id(db, species_name)
    variable = db.query(ClinicalVariable).filter(
        ClinicalVariable.key == key,
        ClinicalVariable.species_id == species_id,
    ).first()
    return variable.id if variable else None


def bootstrap_reference_data(db: Session) -> None:
    seed_data = load_seed_data()

    for role in seed_data["roles"]:
        if db.query(Role).filter(Role.name == role["name"]).first() is None:
            db.add(Role(name=role["name"], description=role["description"]))
    db.commit()

    for risk_level in seed_data["risk_levels"]:
        if db.query(RiskLevel).filter(RiskLevel.code == risk_level["code"]).first() is None:
            db.add(RiskLevel(**risk_level, is_active=True))
    db.commit()

    for species_name in seed_data["species"]:
        if db.query(Species).filter(Species.name == species_name).first() is None:
            db.add(Species(name=species_name))
    db.commit()

    for species_name, breed_names in seed_data["breeds"].items():
        species_id = _species_id(db, species_name)
        for breed_name in breed_names:
            existing = db.query(Breed).filter(
                Breed.species_id == species_id,
                Breed.name == breed_name,
            ).first()
            if existing is None:
                db.add(Breed(species_id=species_id, name=breed_name))
    db.commit()

    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if settings.bootstrap_admin_email and settings.bootstrap_admin_password and admin_role:
        existing_admin = db.query(User).filter(User.email == settings.bootstrap_admin_email).first()
        password_hash = get_password_hash(settings.bootstrap_admin_password)
        if existing_admin is None:
            db.add(
                User(
                    full_name="Administrador",
                    email=settings.bootstrap_admin_email,
                    password_hash=password_hash,
                    role_id=admin_role.id,
                )
            )
        else:
            existing_admin.password_hash = password_hash
            existing_admin.role_id = admin_role.id
            existing_admin.is_active = True
        db.commit()

    for symptom in seed_data["symptoms"]:
        species_id = _species_id(db, symptom["species"])
        existing = db.query(Symptom).filter(
            Symptom.name == symptom["name"],
            Symptom.species_id == species_id,
        ).first()
        if existing is None:
            db.add(Symptom(name=symptom["name"], species_id=species_id))
    db.commit()

    for variable in seed_data["clinical_variables"]:
        species_id = _species_id(db, variable["species"])
        existing = db.query(ClinicalVariable).filter(
            ClinicalVariable.key == variable["key"],
            ClinicalVariable.species_id == species_id,
        ).first()
        if existing is None:
            db.add(
                ClinicalVariable(
                    key=variable["key"],
                    name=variable["name"],
                    data_type=variable["data_type"],
                    unit=variable["unit"],
                    normal_min=variable["normal_min"],
                    normal_max=variable["normal_max"],
                    species_id=species_id,
                )
            )
    db.commit()

    # The dictionary is derived from existing active catalogues; it never creates clinical facts not available in OE3.
    for symptom in db.query(Symptom).filter(Symptom.is_active.is_(True)).all():
        exists = db.query(FactDefinition).filter(FactDefinition.fact_key == symptom.name, FactDefinition.species_id == symptom.species_id).first()
        if exists is None:
            db.add(FactDefinition(fact_key=symptom.name, display_name=symptom.name, source_type="symptom", data_type="boolean", species_id=symptom.species_id, symptom_id=symptom.id, is_active=True))
    for variable in db.query(ClinicalVariable).filter(ClinicalVariable.is_active.is_(True)).all():
        exists = db.query(FactDefinition).filter(FactDefinition.fact_key == variable.key, FactDefinition.species_id == variable.species_id).first()
        if exists is None:
            db.add(FactDefinition(fact_key=variable.key, display_name=variable.name, source_type="clinical_variable", data_type=variable.data_type, unit=variable.unit, species_id=variable.species_id, clinical_variable_id=variable.id, is_active=True))
    db.commit()

    for disease in seed_data["diseases"]:
        species_id = _species_id(db, disease["species"])
        existing = db.query(Disease).filter(
            Disease.name == disease["name"],
            Disease.species_id == species_id,
        ).first()
        if existing is None:
            db.add(
                Disease(
                    name=disease["name"],
                    species_id=species_id,
                    base_probability=disease["base_probability"],
                    description=disease["description"],
                )
            )
    db.commit()

    for rule in seed_data["rules"]:
        if db.query(InferenceRule).filter(InferenceRule.code == rule["code"]).first() is not None:
            continue

        disease = _disease(db, rule["disease"], rule["species"])
        risk_level = get_or_create_risk_level(db, rule["risk_level"])
        db_rule = InferenceRule(
            code=rule["code"],
            name=rule["name"],
            disease_id=disease.id,
            risk_level_id=risk_level.id,
            risk_level=normalize_risk_level(rule["risk_level"]),
            weight=rule["weight"],
            priority=rule["priority"],
        )
        db.add(db_rule)
        db.commit()
        db.refresh(db_rule)

        for condition in rule["conditions"]:
            db.add(
                RuleCondition(
                    rule_id=db_rule.id,
                    variable_key=condition["variable_key"],
                    operator=condition["operator"],
                    expected_value=condition["expected_value"],
                )
            )
        db.commit()

    # Los valores categóricos publicados al frontend se derivan de condiciones
    # seed existentes; no se agregan facts ni reglas fuera del alcance OE3.
    for definition in db.query(FactDefinition).filter(
        FactDefinition.data_type.in_(["string", "categorical", "select"])
    ):
        values = [
            condition.expected_value
            for condition in (
                db.query(RuleCondition)
                .join(InferenceRule)
                .join(Disease)
                .filter(
                    RuleCondition.variable_key == definition.fact_key,
                    Disease.species_id == definition.species_id,
                    RuleCondition.operator == "eq",
                )
                .all()
            )
            if isinstance(condition.expected_value, (str, int, float, bool))
        ]
        if values:
            definition.allowed_values = list(dict.fromkeys(values))
    db.commit()

    # References are limited to citations already present in the academic Markdown.
    source_specs = {
        "ERC": ("Kim y Yun (2026)", "Kim y Yun (2026)"),
        "DM": ("Winiarczyk et al. (2022)", "Winiarczyk et al. (2022)"),
        "MMVD": ("Park, Choi y Hyun (2026)", "Park, Choi y Hyun (2026)"),
        "FELV": ("Beall et al. (2025)", "Beall et al. (2025)"),
        "PERIO": ("Wallis, Colyer y Holcombe (2025)", "Wallis, Colyer y Holcombe (2025)"),
    }
    for prefix, (title, citation) in source_specs.items():
        source = db.query(KnowledgeSource).filter(KnowledgeSource.citation == citation).first()
        if source is None:
            source = KnowledgeSource(title=title, citation=citation, is_active=True)
            db.add(source); db.flush()
        for rule in db.query(InferenceRule).filter(InferenceRule.code.like(f"{prefix}%")).all():
            if db.query(RuleReference).filter(RuleReference.rule_id == rule.id, RuleReference.source_id == source.id).first() is None:
                db.add(RuleReference(rule_id=rule.id, source_id=source.id, rationale="Fuente cl?nica citada en Base de Conocimiento.md."))
    db.commit()

    for probability in seed_data["clinical_probabilities"]:
        disease = _disease(db, probability["disease"], probability["species"])
        symptom_id = (
            _symptom_id(db, probability["symptom"], probability["species"])
            if probability.get("symptom")
            else None
        )
        variable_id = (
            _variable_id(db, probability["variable"], probability["species"])
            if probability.get("variable")
            else None
        )

        query = db.query(ClinicalProbability).filter(ClinicalProbability.disease_id == disease.id)
        if symptom_id is not None:
            query = query.filter(ClinicalProbability.symptom_id == symptom_id)
        elif variable_id is not None:
            query = query.filter(ClinicalProbability.variable_id == variable_id)

        if query.first() is None:
            db.add(
                ClinicalProbability(
                    disease_id=disease.id,
                    symptom_id=symptom_id,
                    variable_id=variable_id,
                    expected_value=probability.get("expected_value"),
                    probability_given_disease=probability["probability_given_disease"],
                    general_probability=probability["general_probability"],
                    is_active=True,
                )
            )
    db.commit()
