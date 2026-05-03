from collections.abc import Sequence
from typing import Any


class ConditionEvaluator:
    def matches(self, observed: Any, operator: str, expected: Any) -> bool:
        if observed is None:
            return False
        if operator == "eq":
            return observed == expected
        if operator == "neq":
            return observed != expected
        if operator == "gt":
            return self._to_float(observed) > self._to_float(expected)
        if operator == "gte":
            return self._to_float(observed) >= self._to_float(expected)
        if operator == "lt":
            return self._to_float(observed) < self._to_float(expected)
        if operator == "lte":
            return self._to_float(observed) <= self._to_float(expected)
        if operator == "between":
            low, high = self._range(expected)
            value = self._to_float(observed)
            return low <= value <= high
        if operator == "contains":
            return self._contains(observed, expected)
        if operator == "in":
            return self._in(observed, expected)
        return False

    def _to_float(self, value: Any) -> float:
        return float(value)

    def _range(self, expected: Any) -> tuple[float, float]:
        if isinstance(expected, dict):
            return self._to_float(expected["min"]), self._to_float(expected["max"])
        if isinstance(expected, Sequence) and not isinstance(expected, str) and len(expected) == 2:
            return self._to_float(expected[0]), self._to_float(expected[1])
        raise ValueError("El operador between requiere [min, max] o {'min': x, 'max': y}")

    def _contains(self, observed: Any, expected: Any) -> bool:
        if isinstance(observed, str):
            return str(expected).lower() in observed.lower()
        return expected in observed

    def _in(self, observed: Any, expected: Any) -> bool:
        if isinstance(expected, str):
            return str(observed) == expected
        return observed in expected
