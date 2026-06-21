from app.inference.evaluator import ConditionEvaluator
from app.inference.facts import normalize_facts
from app.inference.risk import risk_from_score
from app.inference.trace import ConditionTrace


class InferenceEngine:
    def __init__(self, evaluator: ConditionEvaluator | None = None):
        self.evaluator = evaluator or ConditionEvaluator()

    def evaluate(self, facts: dict, rules: list) -> list[dict]:
        normalized_facts = normalize_facts(facts)
        grouped: dict[int, dict] = {}

        for rule in rules:
            traces: list[ConditionTrace] = []
            if not self._rule_matches(rule, normalized_facts, traces):
                continue

            disease = rule.disease
            grouped.setdefault(
                disease.id,
                {
                    "disease_id": disease.id,
                    "disease": disease.name,
                    "suggested_diagnosis": f"Diagnostico sugerido: posible riesgo asociado a {disease.name}",
                    "score": 0.0,
                    "activated_rules": [],
                },
            )
            grouped[disease.id]["score"] += float(rule.weight) * max(int(rule.priority), 1)
            grouped[disease.id]["activated_rules"].append(
                {
                    "rule_id": rule.id,
                    "rule_code": rule.code,
                    "rule_name": rule.name,
                    "rule_version": getattr(rule, "version", None),
                    "risk_level": rule.risk_level,
                    "fulfilled_conditions": [trace.as_text() for trace in traces],
                    "justification": (
                        f"La regla {rule.code} se activo porque todas sus condiciones "
                        "coincidieron con los datos de la evaluacion clinica."
                    ),
                }
            )

        output = []
        for item in grouped.values():
            item["risk_level"] = risk_from_score(item["score"])
            item["explanation"] = (
                "Resultado sugerido generado por reglas clinicas de soporte; "
                "no constituye diagnostico definitivo."
            )
            output.append(item)
        return sorted(output, key=lambda result: result["score"], reverse=True)

    def _rule_matches(self, rule, facts: dict, traces: list[ConditionTrace]) -> bool:
        # Cada grupo conserva AND; grupos distintos son alternativas OR.
        # Las nueve reglas seed siguen en el grupo 1, por lo que no cambia su comportamiento.
        groups: dict[int, list] = {}
        for condition in rule.conditions:
            groups.setdefault(getattr(condition, "logical_group", 1), []).append(condition)

        for conditions in groups.values():
            if not all(
                self.evaluator.matches(facts.get(condition.variable_key), condition.operator, condition.expected_value)
                for condition in conditions
            ):
                continue
            traces.extend(
                ConditionTrace(
                    variable_key=condition.variable_key,
                    operator=condition.operator,
                    expected_value=condition.expected_value,
                    observed_value=facts.get(condition.variable_key),
                )
                for condition in conditions
            )
            return True
        return False
