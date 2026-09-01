import logging
from collections.abc import Sequence
from typing import Any

logger = logging.getLogger(__name__)


class ConditionEvaluator:
    def matches(self, observed: Any, operator: str, expected: Any) -> bool:
        if observed is None:
            return False
        if operator == "eq":
            return observed == expected
        if operator == "neq":
            return observed != expected
        if operator == "gt":
            return self._compare_numeric(observed, expected, operator, lambda a, b: a > b)
        if operator == "gte":
            return self._compare_numeric(observed, expected, operator, lambda a, b: a >= b)
        if operator == "lt":
            return self._compare_numeric(observed, expected, operator, lambda a, b: a < b)
        if operator == "lte":
            return self._compare_numeric(observed, expected, operator, lambda a, b: a <= b)
        if operator == "between":
            # expected_value shape (min/max) es responsabilidad de la regla, no del fact
            # observado; un fallo aqui es una regla mal configurada, no se silencia (ver
            # app/core/exceptions.py, manejador generico de excepciones no controladas).
            low, high = self._range(expected)
            value = self._to_float_or_warn(observed, operator, expected)
            if value is None:
                return False
            return low <= value <= high
        if operator == "contains":
            return self._contains(observed, expected)
        if operator == "in":
            return self._in(observed, expected)
        return False

    def _compare_numeric(self, observed: Any, expected: Any, operator: str, compare) -> bool:
        observed_num = self._to_float_or_warn(observed, operator, expected)
        if observed_num is None:
            return False
        return compare(observed_num, self._to_float(expected))

    def _to_float_or_warn(self, observed: Any, operator: str, expected: Any) -> float | None:
        try:
            return self._to_float(observed)
        except (TypeError, ValueError) as exc:
            logger.warning(
                "No se pudo evaluar operator=%s: valor observado %r no es numerico (expected=%r): %s",
                operator, observed, expected, exc,
            )
            return None

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
