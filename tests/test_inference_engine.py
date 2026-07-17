from dataclasses import dataclass

from app.inference.engine import InferenceEngine


@dataclass
class FakeDisease:
    id: int
    name: str


@dataclass
class FakeCondition:
    variable_key: str
    operator: str
    expected_value: object
    logical_group: int = 1


@dataclass
class FakeRule:
    id: int
    code: str
    name: str
    disease: FakeDisease
    weight: float
    priority: int
    conditions: list[FakeCondition]
    risk_level: str = "moderado"


def test_engine_activates_rule_and_returns_trace():
    disease = FakeDisease(id=1, name="Osteoartritis")
    rule = FakeRule(
        id=10,
        code="OA-001",
        name="Dolor articular y edad avanzada",
        disease=disease,
        weight=2.0,
        priority=2,
        conditions=[
            FakeCondition("edad_anios", "gte", 7),
            FakeCondition("sintomas", "contains", "cojera"),
        ],
    )

    result = InferenceEngine().evaluate(
        facts={"edad_anios": 9, "sintomas": ["cojera", "rigidez"]},
        rules=[rule],
    )

    assert len(result) == 1
    assert result[0]["disease"] == "Osteoartritis"
    assert result[0]["risk_level"] == "moderado"
    assert result[0]["activated_rules"][0]["rule_code"] == "OA-001"
    assert "edad_anios" in result[0]["activated_rules"][0]["fulfilled_conditions"][0]


def test_engine_ignores_unfulfilled_rule():
    disease = FakeDisease(id=2, name="Enfermedad renal cronica")
    rule = FakeRule(
        id=20,
        code="ERC-001",
        name="Creatinina elevada",
        disease=disease,
        weight=5.0,
        priority=1,
        conditions=[FakeCondition("creatinina", "gt", 2.0)],
    )

    result = InferenceEngine().evaluate(facts={"creatinina": 1.1}, rules=[rule])

    assert result == []


def test_engine_supports_or_between_logical_groups():
    disease = FakeDisease(id=3, name="Prueba")
    rule = FakeRule(
        id=30,
        code="TEST-OR-01",
        name="Alternativas",
        disease=disease,
        weight=1.0,
        priority=1,
        conditions=[
            FakeCondition("a", "eq", True, logical_group=1),
            FakeCondition("b", "eq", True, logical_group=2),
        ],
    )

    result = InferenceEngine().evaluate(facts={"b": True}, rules=[rule])

    assert len(result) == 1
    assert "b" in result[0]["activated_rules"][0]["fulfilled_conditions"][0]
