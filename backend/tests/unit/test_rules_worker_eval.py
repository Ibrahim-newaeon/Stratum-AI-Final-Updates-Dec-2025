# =============================================================================
# Stratum AI - Rules Beat-Worker Evaluation Tests
# =============================================================================
"""
Tests for the Celery rules evaluator after the schema reconciliation (Tier 3).

The beat task (``evaluate_all_rules`` -> ``evaluate_rules``) previously read
``rule.conditions`` (a list that doesn't exist) and constructed
``RuleExecution`` with the wrong kwargs, so it died with AttributeError /
TypeError on every 15-minute tick. It now reads the flat
``condition_field/operator/value`` schema and logs executions with the real
columns, mirroring the canonical async ``RulesEngine``.
"""

from types import SimpleNamespace

import pytest

from app.models import RuleExecution, RuleOperator
from app.workers.tasks.rules import (
    _compare_values,
    _evaluate_condition,
    _get_field_value,
    _parse_value,
)


def _campaign(**kw):
    base = dict(
        id=1,
        name="Camp",
        total_spend_cents=20000,  # 200.00
        revenue_cents=100000,
        clicks=100,
        impressions=10000,
        conversions=2,  # cpa = 200.00 / 2 = 100.0
    )
    base.update(kw)
    return SimpleNamespace(**base)


def _rule(field, operator, value):
    return SimpleNamespace(
        condition_field=field,
        condition_operator=operator,
        condition_value=value,
    )


# --- _compare_values covers every operator ---
@pytest.mark.parametrize(
    "actual,operator,expected,result",
    [
        (10, RuleOperator.GREATER_THAN, 5, True),
        (3, RuleOperator.GREATER_THAN, 5, False),
        (5, RuleOperator.LESS_THAN, 10, True),
        (5, RuleOperator.EQUALS, 5, True),
        (5, RuleOperator.NOT_EQUALS, 6, True),
        (5, RuleOperator.GREATER_THAN_OR_EQUAL, 5, True),
        (5, RuleOperator.LESS_THAN_OR_EQUAL, 5, True),
        ("abc", RuleOperator.CONTAINS, "b", True),
        (2, RuleOperator.IN, [1, 2, 3], True),
    ],
)
def test_compare_values(actual, operator, expected, result):
    assert _compare_values(actual, operator, expected) is result


# --- computed metric resolution ---
def test_get_field_value_computed_cpa():
    # 200.00 spend / 2 conversions = 100.0
    assert _get_field_value(_campaign(), "cpa") == 100.0


def test_get_field_value_direct_attr():
    assert _get_field_value(_campaign(clicks=42), "clicks") == 42


def test_parse_value_int_from_float_string():
    assert _parse_value("50.0", int) == 50


# --- end-to-end condition evaluation on the flat schema ---
def test_evaluate_condition_matched():
    rule = _rule("cpa", RuleOperator.GREATER_THAN, "50")  # cpa 100 > 50
    out = _evaluate_condition(rule, _campaign())
    assert out["matched"] is True
    assert out["values"]["actual"] == 100.0


def test_evaluate_condition_not_matched():
    rule = _rule("cpa", RuleOperator.LESS_THAN, "50")  # cpa 100 < 50 is False
    assert _evaluate_condition(rule, _campaign())["matched"] is False


def test_evaluate_condition_unknown_field():
    rule = _rule("nonexistent_metric", RuleOperator.GREATER_THAN, "1")
    out = _evaluate_condition(rule, _campaign())
    assert out["matched"] is False
    assert "not found" in out["values"]["reason"]


# --- RuleExecution is built with the real columns ---
def test_rule_execution_accepts_new_columns():
    ex = RuleExecution(
        tenant_id=1,
        rule_id=1,
        campaign_id=1,
        triggered=True,
        condition_result={"field": "cpa"},
        action_result={"action": "pause_campaign"},
    )
    assert ex.triggered is True
    assert ex.condition_result["field"] == "cpa"


def test_rule_execution_rejects_old_columns():
    # The pre-fix kwargs must no longer be accepted (guards against regressions).
    with pytest.raises(TypeError):
        RuleExecution(
            tenant_id=1,
            rule_id=1,
            triggered_at="now",
            condition_values={},
            action_taken="x",
        )
