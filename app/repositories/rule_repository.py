from sqlalchemy.orm import joinedload

from app.models.disease import Disease
from app.models.risk_level import RiskLevel
from app.models.rule import InferenceRule, RuleCondition
from app.repositories.base import BaseRepository


class RuleRepository(BaseRepository[InferenceRule]):
    model = InferenceRule

    def get_with_conditions(self, rule_id: int) -> InferenceRule | None:
        return (
            self.db.query(InferenceRule)
            .options(joinedload(InferenceRule.conditions), joinedload(InferenceRule.disease))
            .filter(InferenceRule.id == rule_id)
            .first()
        )

    def list_with_conditions(self, skip: int = 0, limit: int = 100) -> list[InferenceRule]:
        return (
            self.db.query(InferenceRule)
            .options(joinedload(InferenceRule.conditions))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_active_rules_by_species(self, species_id: int) -> list[InferenceRule]:
        return (
            self.db.query(InferenceRule)
            .join(InferenceRule.disease)
            .options(joinedload(InferenceRule.conditions), joinedload(InferenceRule.disease))
            .filter(InferenceRule.is_active.is_(True))
            .filter(Disease.is_active.is_(True))
            .filter(Disease.species_id == species_id)
            .order_by(InferenceRule.priority.desc())
            .all()
        )

    def get_by_code(self, code: str) -> InferenceRule | None:
        return self.db.query(InferenceRule).filter(InferenceRule.code == code).first()

    def get_risk_level(self, risk_level_id: int) -> RiskLevel | None:
        return self.db.get(RiskLevel, risk_level_id)

    def create_rule(self, data: dict, conditions: list[dict]) -> InferenceRule:
        rule = InferenceRule(**data)
        rule.conditions = [RuleCondition(**condition) for condition in conditions]
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def replace_conditions(self, rule: InferenceRule, conditions: list[dict]) -> InferenceRule:
        rule.conditions.clear()
        rule.conditions.extend(RuleCondition(**condition) for condition in conditions)
        self.db.commit()
        self.db.refresh(rule)
        return rule
