from app.core.exceptions import ConflictError, NotFoundError
from app.models.disease import Disease
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
        conditions = [condition.model_dump() for condition in payload.conditions]
        return self.repository.create_rule(data, conditions)

    def update_rule(self, rule_id: int, payload: RuleUpdate):
        rule = self.repository.get_with_conditions(rule_id)
        if rule is None:
            raise NotFoundError("Regla no encontrada")

        data = payload.model_dump(exclude_unset=True, exclude={"conditions"})
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
