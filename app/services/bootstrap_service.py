import json
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import settings
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
from app.repositories.risk_level_repository import RiskLevelRepository

DEFAULT_ALLOWED_VALUES = {
    "placa": ["ausente", "leve", "moderada", "severa"],
    "glucosuria": ["negativa", "positiva"],
    "felv_p27": ["negativo", "positivo"],
    "snap_felv": ["negativo", "positivo"],
}

KNOWLEDGE_SOURCE_SPECS = {
    "ERC": ("Kim y Yun (2026)", "Kim y Yun (2026)"),
    "DM": ("Winiarczyk et al. (2022)", "Winiarczyk et al. (2022)"),
    "CARD": ("Park, Choi y Hyun (2026)", "Park, Choi y Hyun (2026)"),
    "FELV": ("Beall et al. (2025)", "Beall et al. (2025)"),
    "PER": ("Wallis, Colyer y Holcombe (2025)", "Wallis, Colyer y Holcombe (2025)"),
}

LEGACY_RULE_CODES = ["MMVD-R01", "MMVD-R02", "PERIO-R01"]


def load_seed_data() -> dict[str, Any]:
    path = Path(settings.seed_data_path)
    if not path.is_absolute():
        path = Path.cwd() / path
    with path.open(encoding="utf-8-sig") as seed_file:
        return json.load(seed_file)


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


def _seed_roles(db: Session, seed_data: dict) -> None:
    for role in seed_data["roles"]:
        if db.query(Role).filter(Role.name == role["name"]).first() is None:
            db.add(Role(name=role["name"], description=role["description"]))
    db.commit()


def _seed_risk_levels(db: Session, seed_data: dict) -> None:
    for risk_level in seed_data["risk_levels"]:
        if db.query(RiskLevel).filter(RiskLevel.code == risk_level["code"]).first() is None:
            db.add(RiskLevel(**risk_level, is_active=True))
    db.commit()


def _seed_species(db: Session, seed_data: dict) -> None:
    for species_name in seed_data["species"]:
        if db.query(Species).filter(Species.name == species_name).first() is None:
            db.add(Species(name=species_name))
    db.commit()


def _seed_breeds(db: Session, seed_data: dict) -> None:
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


def _seed_admin_user(db: Session) -> None:
    admin_role = db.query(Role).filter(Role.name == "admin").first()
    if not (settings.bootstrap_admin_email and settings.bootstrap_admin_password and admin_role):
        return

    existing_admin = db.query(User).filter(User.email == settings.bootstrap_admin_email).first()
    # Solo se crea el admin la primera vez; nunca se sobrescribe una cuenta ya existente
    # (evita resetear silenciosamente la contrasena/rol del admin en cada reinicio).
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


def _seed_symptoms(db: Session, seed_data: dict) -> None:
    for symptom in seed_data["symptoms"]:
        species_id = _species_id(db, symptom["species"])
        existing = db.query(Symptom).filter(
            Symptom.name == symptom["name"],
            Symptom.species_id == species_id,
        ).first()
        if existing is None:
            db.add(Symptom(name=symptom["name"], species_id=species_id))
    db.commit()


def _seed_clinical_variables(db: Session, seed_data: dict) -> None:
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


def _seed_fact_definitions(db: Session, seed_data: dict) -> None:
    variable_allowed_values = {
        (variable["key"], _species_id(db, variable["species"])): variable.get(
            "allowed_values", DEFAULT_ALLOWED_VALUES.get(variable["key"])
        )
        for variable in seed_data["clinical_variables"]
    }

    # The dictionary is derived from existing active catalogues; it never creates clinical facts not available in OE3.
    for symptom in db.query(Symptom).filter(Symptom.is_active.is_(True)).all():
        exists = db.query(FactDefinition).filter(
            FactDefinition.fact_key == symptom.name, FactDefinition.species_id == symptom.species_id
        ).first()
        if exists is None:
            db.add(
                FactDefinition(
                    fact_key=symptom.name,
                    display_name=symptom.name,
                    source_type="symptom",
                    data_type="boolean",
                    species_id=symptom.species_id,
                    symptom_id=symptom.id,
                    is_active=True,
                )
            )

    for variable in db.query(ClinicalVariable).filter(ClinicalVariable.is_active.is_(True)).all():
        exists = db.query(FactDefinition).filter(
            FactDefinition.fact_key == variable.key, FactDefinition.species_id == variable.species_id
        ).first()
        if exists is None:
            exists = FactDefinition(
                fact_key=variable.key,
                display_name=variable.name,
                source_type="clinical_variable",
                data_type=variable.data_type,
                unit=variable.unit,
                species_id=variable.species_id,
                clinical_variable_id=variable.id,
                is_active=True,
            )
            db.add(exists)
        allowed_values = variable_allowed_values.get((variable.key, variable.species_id))
        if allowed_values is not None:
            exists.allowed_values = allowed_values
    db.commit()


def _seed_diseases(db: Session, seed_data: dict) -> None:
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


def _seed_rules(db: Session, seed_data: dict) -> None:
    risk_level_repository = RiskLevelRepository(db)
    for rule in seed_data["rules"]:
        disease = _disease(db, rule["disease"], rule["species"])
        risk_level = risk_level_repository.get_or_create(rule["risk_level"])
        db_rule = db.query(InferenceRule).filter(InferenceRule.code == rule["code"]).first()
        if db_rule is None:
            db_rule = InferenceRule(code=rule["code"], disease_id=disease.id, risk_level_id=risk_level.id)
            db.add(db_rule)
        db_rule.name = rule["name"]
        db_rule.disease_id = disease.id
        db_rule.risk_level_id = risk_level.id
        db_rule.weight = rule["weight"]
        db_rule.priority = rule["priority"]
        db_rule.is_active = True
        db.flush()
        db.query(RuleCondition).filter(RuleCondition.rule_id == db_rule.id).delete()

        for condition in rule["conditions"]:
            db.add(
                RuleCondition(
                    rule_id=db_rule.id,
                    variable_key=condition["variable_key"],
                    operator=condition["operator"],
                    expected_value=condition["expected_value"],
                    logical_group=condition.get("logical_group", 1),
                )
            )
        db.commit()


def _deactivate_legacy_rules(db: Session) -> None:
    # Reglas del catalogo inicial sustituidas por los codigos de la tabla 12.
    db.query(InferenceRule).filter(InferenceRule.code.in_(LEGACY_RULE_CODES)).update(
        {"is_active": False}, synchronize_session=False
    )
    db.commit()


def _backfill_categorical_allowed_values(db: Session) -> None:
    # Los valores categoricos publicados al frontend se derivan de condiciones
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
        if values and definition.allowed_values is None:
            definition.allowed_values = list(dict.fromkeys(values))
    db.commit()


def _seed_knowledge_references(db: Session) -> None:
    # References are limited to citations already present in the academic Markdown.
    for prefix, (title, citation) in KNOWLEDGE_SOURCE_SPECS.items():
        source = db.query(KnowledgeSource).filter(KnowledgeSource.citation == citation).first()
        if source is None:
            source = KnowledgeSource(title=title, citation=citation, is_active=True)
            db.add(source)
            db.flush()
        for rule in db.query(InferenceRule).filter(InferenceRule.code.like(f"{prefix}%")).all():
            if db.query(RuleReference).filter(
                RuleReference.rule_id == rule.id, RuleReference.source_id == source.id
            ).first() is None:
                db.add(
                    RuleReference(
                        rule_id=rule.id,
                        source_id=source.id,
                        rationale="Fuente clinica citada en Base de Conocimiento.md.",
                    )
                )
    db.commit()


def _seed_clinical_probabilities(db: Session, seed_data: dict) -> None:
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


def bootstrap_reference_data(db: Session) -> None:
    seed_data = load_seed_data()

    _seed_roles(db, seed_data)
    _seed_risk_levels(db, seed_data)
    _seed_species(db, seed_data)
    _seed_breeds(db, seed_data)
    _seed_admin_user(db)
    _seed_symptoms(db, seed_data)
    _seed_clinical_variables(db, seed_data)
    _seed_fact_definitions(db, seed_data)
    _seed_diseases(db, seed_data)
    _seed_rules(db, seed_data)
    _deactivate_legacy_rules(db)
    _backfill_categorical_allowed_values(db)
    _seed_knowledge_references(db)
    _seed_clinical_probabilities(db, seed_data)
