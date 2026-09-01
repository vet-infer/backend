import pytest

from app.inference.evaluator import ConditionEvaluator


@pytest.fixture(name="evaluator")
def fixture_evaluator():
    return ConditionEvaluator()


# --- between ---


def test_between_within_range(evaluator):
    assert evaluator.matches(5, "between", [1, 10]) is True


def test_between_at_exact_min_boundary(evaluator):
    assert evaluator.matches(1, "between", [1, 10]) is True


def test_between_at_exact_max_boundary(evaluator):
    assert evaluator.matches(10, "between", [1, 10]) is True


def test_between_below_range(evaluator):
    assert evaluator.matches(0.99, "between", [1, 10]) is False


def test_between_above_range(evaluator):
    assert evaluator.matches(10.01, "between", [1, 10]) is False


def test_between_with_dict_shape(evaluator):
    assert evaluator.matches(5, "between", {"min": 1, "max": 10}) is True


# --- in ---


def test_in_with_list_match(evaluator):
    assert evaluator.matches("rojo", "in", ["rojo", "verde", "azul"]) is True


def test_in_with_list_no_match(evaluator):
    assert evaluator.matches("amarillo", "in", ["rojo", "verde", "azul"]) is False


def test_in_with_string_expected_exact_match(evaluator):
    assert evaluator.matches("positiva", "in", "positiva") is True


def test_in_with_string_expected_no_match(evaluator):
    assert evaluator.matches("negativa", "in", "positiva") is False


# --- contains ---


def test_contains_with_string_observed(evaluator):
    assert evaluator.matches("dolor articular severo", "contains", "articular") is True


def test_contains_with_string_observed_case_insensitive(evaluator):
    assert evaluator.matches("Dolor Articular", "contains", "articular") is True


def test_contains_with_list_observed(evaluator):
    assert evaluator.matches(["cojera", "rigidez"], "contains", "cojera") is True


def test_contains_with_list_observed_no_match(evaluator):
    assert evaluator.matches(["cojera", "rigidez"], "contains", "letargo") is False


# --- neq ---


def test_neq_different_values(evaluator):
    assert evaluator.matches("alto", "neq", "bajo") is True


def test_neq_equal_values(evaluator):
    assert evaluator.matches("alto", "neq", "alto") is False


# --- gt/gte/lt/lte at exact boundary ---


@pytest.mark.parametrize(
    ("operator", "observed", "expected", "result"),
    [
        ("gt", 5, 5, False),
        ("gt", 5.01, 5, True),
        ("gte", 5, 5, True),
        ("gte", 4.99, 5, False),
        ("lt", 5, 5, False),
        ("lt", 4.99, 5, True),
        ("lte", 5, 5, True),
        ("lte", 5.01, 5, False),
    ],
)
def test_numeric_operators_at_exact_boundary(evaluator, operator, observed, expected, result):
    assert evaluator.matches(observed, operator, expected) is result


# --- observed value None always fails, regardless of operator ---


@pytest.mark.parametrize("operator", ["eq", "neq", "gt", "gte", "lt", "lte", "between", "contains", "in"])
def test_none_observed_never_matches(evaluator, operator):
    expected = [1, 10] if operator == "between" else 1
    assert evaluator.matches(None, operator, expected) is False
