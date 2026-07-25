from app.core.exceptions import ConflictError, NotFoundError
from app.models.disease import Disease
from app.models.knowledge import FactDefinition
from app.repositories.rule_repository import RuleRepository
from app.schemas.rule import RuleCreate, RuleStatusUpdate, RuleUpdate
from app.services.bootstrap_service import get_or_create_risk_level, normalize_risk_level


class RuleService:
    def __init__(self, repository: RuleRepository):
        self.repository = repository

    def list_rules(self):
        return self.repository.list_with_conditions()

    def get_rule(self, rule_id: int):
        rule = self.repository.get_with_conditions(rule_id)
        if rule is None:
            raise NotFoundError("Regla no encontrada")
        return rule

    def create_rule(self, payload: RuleCreate):
        if self.repository.get_by_code(payload.code):
            raise ConflictError("Ya existe una regla con ese codigo")
        self._get_disease_or_raise(payload.disease_id)

        data = payload.model_dump(exclude={"conditions"})
        self._resolve_risk_level(data)
        conditions = [condition.model_dump() for condition in payload.conditions]
        self._validate_conditions(payload.disease_id, conditions)
        return self.repository.create_rule(data, conditions)

    def update_rule(self, rule_id: int, payload: RuleUpdate):
        rule = self.repository.get_with_conditions(rule_id)
        if rule is None:
            raise NotFoundError("Regla no encontrada")

        data = payload.model_dump(exclude_unset=True, exclude={"conditions"})
        target_disease_id = data.get("disease_id", rule.disease_id)
        self._get_disease_or_raise(target_disease_id)
        self._resolve_risk_level(data)

        if payload.conditions is not None:
            conditions = [condition.model_dump() for condition in payload.conditions]
            self._validate_conditions(target_disease_id, conditions)
        elif "disease_id" in data:
            existing_conditions = [
                {
                    "variable_key": condition.variable_key,
                    "operator": condition.operator,
                    "expected_value": condition.expected_value,
                    "logical_group": condition.logical_group,
                }
                for condition in rule.conditions
            ]
            self._validate_conditions(target_disease_id, existing_conditions)
            conditions = None
        else:
            conditions = None

        for field, value in data.items():
            setattr(rule, field, value)

        if conditions is not None:
            return self.repository.replace_conditions(rule, conditions)

        self.repository.db.commit()
        self.repository.db.refresh(rule)
        return rule

    def update_status(self, rule_id: int, payload: RuleStatusUpdate):
        rule = self.repository.get_with_conditions(rule_id)
        if rule is None:
            raise NotFoundError("Regla no encontrada")
        rule.is_active = payload.is_active
        self.repository.db.commit()
        self.repository.db.refresh(rule)
        return rule

    def _get_disease_or_raise(self, disease_id: int) -> Disease:
        disease = self.repository.db.get(Disease, disease_id)
        if disease is None:
            raise NotFoundError("Enfermedad no encontrada")
        return disease

    def _resolve_risk_level(self, data: dict) -> None:
        if "risk_level_id" in data and data["risk_level_id"] is not None:
            risk_level = self.repository.get_risk_level(data["risk_level_id"])
            if risk_level is None:
                raise NotFoundError("Nivel de riesgo no encontrado")
            data.pop("risk_level", None)
            return

        risk_level_name = data.pop("risk_level", None)
        if risk_level_name is not None:
            risk_level = get_or_create_risk_level(self.repository.db, normalize_risk_level(risk_level_name))
            data["risk_level_id"] = risk_level.id

    def _validate_conditions(self, disease_id: int, conditions: list[dict]) -> None:
        disease = self._get_disease_or_raise(disease_id)
        for condition in conditions:
            fact = (
                self.repository.db.query(FactDefinition)
                .filter(
                    FactDefinition.fact_key == condition["variable_key"],
                    FactDefinition.species_id == disease.species_id,
                    FactDefinition.is_active.is_(True),
                )
                .first()
            )
            if fact is None:
                raise NotFoundError(
                    "Fact activo no encontrado o incompatible con la especie: "
                    f"{condition['variable_key']}"
                )
