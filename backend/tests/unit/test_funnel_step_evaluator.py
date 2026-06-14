# =============================================================================
# Stratum AI - Funnel Step Evaluator Unit Tests
# =============================================================================
"""Unit tests for ``FunnelStepEvaluator`` in app.services.cdp.funnel_service.

Covers the pure, I/O-free funnel condition logic: per-operator
evaluation, event field extraction (properties./context./event_name),
and multi-condition matching. The DB-backed FunnelService is exercised
elsewhere.
"""

from types import SimpleNamespace

import pytest

from app.services.cdp.funnel_service import FunnelStepEvaluator

pytestmark = pytest.mark.unit


@pytest.fixture
def evaluator() -> FunnelStepEvaluator:
    return FunnelStepEvaluator()


def _event(event_name="purchase", properties=None, context=None):
    return SimpleNamespace(
        event_name=event_name,
        properties=properties or {},
        context=context or {},
    )


# =============================================================================
# _evaluate_condition — operator table
# =============================================================================
class TestEvaluateCondition:
    @pytest.mark.parametrize(
        "actual,operator,expected,result",
        [
            ("a", "equals", "a", True),
            ("a", "equals", "b", False),
            ("a", "not_equals", "b", True),
            ("hello world", "contains", "world", True),
            ("hello", "contains", "xyz", False),
            ("hello", "not_contains", "xyz", True),
            (5, "greater_than", 3, True),
            (3, "greater_than", 5, False),
            (3, "less_than", 5, True),
            (5, "greater_or_equal", 5, True),
            (5, "less_or_equal", 5, True),
            ("b", "in", ["a", "b", "c"], True),
            ("z", "in", ["a", "b"], False),
            ("z", "not_in", ["a", "b"], True),
            ("x", "is_not_null", None, True),
        ],
    )
    def test_operators(self, evaluator, actual, operator, expected, result):
        assert evaluator._evaluate_condition(actual, operator, expected) is result

    def test_none_actual_matches_is_null_and_not_equals(self, evaluator):
        assert evaluator._evaluate_condition(None, "is_null", None) is True
        assert evaluator._evaluate_condition(None, "not_equals", "x") is True
        # Any other operator against a None actual is False.
        assert evaluator._evaluate_condition(None, "equals", "x") is False
        assert evaluator._evaluate_condition(None, "greater_than", 1) is False

    def test_unknown_operator_defaults_to_equals(self, evaluator):
        assert evaluator._evaluate_condition("a", "bogus_op", "a") is True
        assert evaluator._evaluate_condition("a", "bogus_op", "b") is False

    def test_type_error_is_swallowed_to_false(self, evaluator):
        # float("abc") raises ValueError -> evaluator returns False, not raise.
        assert evaluator._evaluate_condition("abc", "greater_than", 3) is False


# =============================================================================
# _get_field_value
# =============================================================================
class TestGetFieldValue:
    def test_properties_field(self, evaluator):
        ev = _event(properties={"plan": "pro"})
        assert evaluator._get_field_value(ev, "properties.plan") == "pro"

    def test_context_field(self, evaluator):
        ev = _event(context={"country": "US"})
        assert evaluator._get_field_value(ev, "context.country") == "US"

    def test_event_name_field(self, evaluator):
        ev = _event(event_name="signup")
        assert evaluator._get_field_value(ev, "event_name") == "signup"

    def test_unknown_field_returns_none(self, evaluator):
        assert evaluator._get_field_value(_event(), "nope") is None


# =============================================================================
# _check_conditions
# =============================================================================
class TestCheckConditions:
    def test_no_conditions_always_matches(self, evaluator):
        assert evaluator._check_conditions(_event(), []) is True

    def test_all_conditions_must_match(self, evaluator):
        ev = _event(event_name="purchase", properties={"amount": 120})
        conditions = [
            {"field": "event_name", "operator": "equals", "value": "purchase"},
            {"field": "properties.amount", "operator": "greater_than", "value": 100},
        ]
        assert evaluator._check_conditions(ev, conditions) is True

    def test_one_failing_condition_fails(self, evaluator):
        ev = _event(event_name="purchase", properties={"amount": 50})
        conditions = [
            {"field": "event_name", "operator": "equals", "value": "purchase"},
            {"field": "properties.amount", "operator": "greater_than", "value": 100},
        ]
        assert evaluator._check_conditions(ev, conditions) is False
