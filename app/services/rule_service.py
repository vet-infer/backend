from app.core.exceptions import ConflictError, NotFoundError
from app.models.disease import Disease
from app.services.bootstrap_service import get_or_create_risk_level, normalize_risk_level
from app.repositories.rule_repository import RuleRepository
from app.schemas.rule import RuleCreate, RuleUpdate


class RuleService:
    def __init__(self, repository: RuleRepository):
        self.repository = repository

    def list_rules(self):
        return self.repository.list_with_conditions()

    def create_rule(self, payload: RuleCreate):
        if self.repository.get_by_code(payload.code):
            raise ConflictError("Ya existe una regla con ese codigo")
        if self.repository.db.get(Disease, payload.disease_id) is None:
            raise NotFoundError("Enfermedad no encontrada")

        data = payload.model_dump(exclude={"conditions"})
        risk_level_code = normalize_risk_level(data.get("risk_level"))
        if data.get("risk_level_id") is not None:
            risk_level = self.repository.get_risk_level(data["risk_level_id"])
            if risk_level is None:
                raise NotFoundError("Nivel de riesgo no encontrado")
            data["risk_level"] = risk_level.code
        else:
            risk_level = get_or_create_risk_level(self.repository.db, risk_level_code)
            data["risk_level_id"] = risk_level.id
            data["risk_level"] = risk_level.code
        conditions = [condition.model_dump() for condition in payload.conditions]
        return self.repository.create_rule(data, conditions)

    def update_rule(self, rule_id: int, payload: RuleUpdate):
        rule = self.repository.get_with_conditions(rule_id)
        if rule is None:
            raise NotFoundError("Regla no encontrada")

        data = payload.model_dump(exclude_unset=True, exclude={"conditions"})
        if "risk_level_id" in data and data["risk_level_id"] is not None:
            risk_level = self.repository.get_risk_level(data["risk_level_id"])
            if risk_level is None:
                raise NotFoundError("Nivel de riesgo no encontrado")
            data["risk_level"] = risk_level.code
        elif "risk_level" in data and data["risk_level"] is not None:
            risk_level = get_or_create_risk_level(
                self.repository.db,
                normalize_risk_level(data["risk_level"]),
            )
            data["risk_level_id"] = risk_level.id
            data["risk_level"] = risk_level.code
        for field, value in data.items():
            setattr(rule, field, value)

        if payload.conditions is not None:
            self.repository.replace_conditions(
                rule,
                [condition.model_dump() for condition in payload.conditions],
            )
        else:
            self.repository.db.commit()
            self.repository.db.refresh(rule)
        return rule
