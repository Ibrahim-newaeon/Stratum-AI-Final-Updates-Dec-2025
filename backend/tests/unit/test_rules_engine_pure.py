# =============================================================================
# Stratum AI - Rules Engine (pure logic) Unit Tests
# =============================================================================
"""Unit tests for the I/O-free logic of ``app.services.rules_engine``.

Covers the fluent ``RuleBuilder`` (build + validate) and the pure
``RulesEngine`` helpers: value parsing, operator comparison, and campaign
field extraction. The DB-backed evaluation/execution paths are out of
scope here.
"""

from types import SimpleNamespace

import pytest

from app.models import RuleAction, RuleOperator
from app.services.rules_engine import RuleBuilder, RulesEngine

pytestmark = pytest.mark.unit


@pytest.fixture
def engine() -> RulesEngine:
    # The pure helpers never touch the session, so a None db is fine.
    return RulesEngine(db=None, tenant_id=1)


# =============================================================================
# RuleBuilder
# =============================================================================
class TestRuleBuilder:
    def test_fluent_build(self):
        rule = (
            RuleBuilder(tenant_id=7)
            .name("Pause high CPA")
            .description("Pause when CPA too high")
            .when("cpa", RuleOperator.GREATER_THAN, 50, duration_hours=24)
            .then(RuleAction.PAUSE_CAMPAIGN, {"reason": "cpa"})
            .cooldown(48)
            .build()
        )
        assert rule.name == "Pause high CPA"
        assert rule.condition_field == "cpa"
        assert rule.condition_operator == RuleOperator.GREATER_THAN
        assert rule.condition_value == "50"  # stringified
        assert rule.action_type == RuleAction.PAUSE_CAMPAIGN
        assert rule.cooldown_hours == 48

    def test_validate_reports_missing_fields(self):
        errors = RuleBuilder(tenant_id=1).validate()
        # Empty builder is missing name, condition, and action.
        assert any("name" in e.lower() for e in errors)
        assert any("condition field" in e.lower() for e in errors)
        assert any("action type" in e.lower() for e in errors)

    def test_validate_passes_when_complete(self):
        errors = (
            RuleBuilder(tenant_id=1)
            .name("ok")
            .when("roas", RuleOperator.LESS_THAN, 1.0)
            .then(RuleAction.SEND_ALERT)
            .validate()
        )
        assert errors == []


# =============================================================================
# RulesEngine._parse_value
# =============================================================================
class TestParseValue:
    def test_float(self, engine):
        assert engine._parse_value("3.5", float) == 3.5

    def test_int_via_float(self, engine):
        assert engine._parse_value("42.0", int) == 42

    @pytest.mark.parametrize(
        "raw,expected", [("true", True), ("0", False), ("yes", True)]
    )
    def test_bool(self, engine, raw, expected):
        assert engine._parse_value(raw, bool) is expected

    def test_list_from_json(self, engine):
        assert engine._parse_value('["a", "b"]', list) == ["a", "b"]

    def test_list_from_scalar(self, engine):
        assert engine._parse_value("solo", list) == ["solo"]

    def test_str_passthrough(self, engine):
        assert engine._parse_value("hello", str) == "hello"


# =============================================================================
# RulesEngine._compare_values
# =============================================================================
class TestCompareValues:
    @pytest.mark.parametrize(
        "actual,op,expected,result",
        [
            (5, RuleOperator.EQUALS, 5, True),
            (5, RuleOperator.NOT_EQUALS, 6, True),
            (5, RuleOperator.GREATER_THAN, 3, True),
            (3, RuleOperator.LESS_THAN, 5, True),
            (5, RuleOperator.GREATER_THAN_OR_EQUAL, 5, True),
            (5, RuleOperator.LESS_THAN_OR_EQUAL, 5, True),
            ("hello world", RuleOperator.CONTAINS, "world", True),
            (2, RuleOperator.IN, [1, 2, 3], True),
            (9, RuleOperator.IN, [1, 2, 3], False),
        ],
    )
    def test_operators(self, engine, actual, op, expected, result):
        assert engine._compare_values(actual, op, expected) is result


# =============================================================================
# RulesEngine._get_field_value
# =============================================================================
class TestGetFieldValue:
    def test_direct_attribute(self, engine):
        campaign = SimpleNamespace(status="active")
        assert engine._get_field_value(campaign, "status") == "active"

    def test_unknown_field_returns_none(self, engine):
        campaign = SimpleNamespace(status="active")
        assert engine._get_field_value(campaign, "nonexistent_field") is None
