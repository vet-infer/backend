from dataclasses import dataclass


@dataclass
class DiseaseView:
    id: int
    name: str


@dataclass
class ConditionView:
    variable_key: str
    operator: str
    expected_value: object
    logical_group: int = 1


@dataclass
class RuleView:
    """Snapshot inmutable de una regla, desacoplado de la sesion de SQLAlchemy
    que la cargo. InferenceEngine.evaluate solo necesita estos campos; cachear
    este objeto en vez del modelo ORM evita depender de atributos cargados
    perezosamente sobre una sesion ya cerrada."""

    id: int
    code: str
    name: str
    disease: DiseaseView
    conditions: list[ConditionView]
    weight: float = 1.0
    priority: int = 1
    risk_level: str = "moderado"
    version: int | None = None

    @classmethod
    def from_orm_rule(cls, rule) -> "RuleView":
        return cls(
            id=rule.id,
            code=rule.code,
            name=rule.name,
            disease=DiseaseView(id=rule.disease.id, name=rule.disease.name),
            conditions=[
                ConditionView(
                    variable_key=condition.variable_key,
                    operator=condition.operator,
                    expected_value=condition.expected_value,
                    logical_group=condition.logical_group,
                )
                for condition in rule.conditions
            ],
            weight=rule.weight,
            priority=rule.priority,
            risk_level=rule.risk_level,
            version=getattr(rule, "version", None),
        )
