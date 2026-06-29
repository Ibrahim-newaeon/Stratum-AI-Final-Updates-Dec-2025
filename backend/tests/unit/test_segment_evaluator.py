# =============================================================================
# Stratum AI - CDP Segment Evaluator Unit Tests
# =============================================================================
"""Unit tests for the pure rule-evaluation logic in
``app.services.cdp.segment_service``:

- ``SegmentEvaluator._compare_values`` (the 17-operator comparison engine)
- ``SegmentEvaluator._get_profile_value`` / ``_get_trait_value`` /
  ``_get_profile_data_value`` / ``_parse_datetime`` field extraction
- ``SegmentService._generate_slug`` URL-slug normalization

These helpers never touch ``self.db``, so the services are instantiated
with ``db=None`` and fed lightweight duck-typed profile objects. The
DB-backed evaluation pipeline is out of scope here.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.cdp.segment_service import SegmentEvaluator, SegmentService

pytestmark = pytest.mark.unit


@pytest.fixture
def evaluator() -> SegmentEvaluator:
    return SegmentEvaluator(db=None, tenant_id=1)


@pytest.fixture
def service() -> SegmentService:
    return SegmentService(db=None, tenant_id=1)


# =============================================================================
# _compare_values - string operators
# =============================================================================
class TestStringOperators:
    @pytest.mark.parametrize(
        "actual,op,expected,result",
        [
            ("customer", "equals", "customer", True),
            ("customer", "equals", "lead", False),
            ("customer", "not_equals", "lead", True),
            ("HelloWorld", "contains", "world", True),
            ("HelloWorld", "not_contains", "xyz", True),
            ("premium_user", "starts_with", "PREMIUM", True),
            ("premium_user", "ends_with", "USER", True),
            ("abc", "starts_with", "z", False),
        ],
    )
    def test_string_ops(self, evaluator, actual, op, expected, result):
        assert evaluator._compare_values(actual, op, expected) == (
            result,
            1.0 if result else 0.0,
        )


# =============================================================================
# _compare_values - numeric operators
# =============================================================================
class TestNumericOperators:
    @pytest.mark.parametrize(
        "actual,op,expected,result",
        [
            (100, "greater_than", 50, True),
            (100, "less_than", 50, False),
            (50, "greater_or_equal", 50, True),
            (50, "less_or_equal", 50, True),
            (5, "between", [1, 10], True),
            (15, "between", [1, 10], False),
            (5, "between", [1], False),  # malformed bounds
        ],
    )
    def test_numeric_ops(self, evaluator, actual, op, expected, result):
        assert evaluator._compare_values(actual, op, expected)[0] is result


# =============================================================================
# _compare_values - membership + null operators
# =============================================================================
class TestMembershipAndNull:
    def test_in(self, evaluator):
        assert evaluator._compare_values("a", "in", ["a", "b"])[0] is True

    def test_in_non_list_is_false(self, evaluator):
        assert evaluator._compare_values("a", "in", "ab")[0] is False

    def test_not_in(self, evaluator):
        assert evaluator._compare_values("z", "not_in", ["a", "b"])[0] is True

    def test_is_null_on_none(self, evaluator):
        # None short-circuits for every operator except the null checks.
        assert evaluator._compare_values(None, "is_null", None)[0] is True

    def test_is_not_null_on_none(self, evaluator):
        assert evaluator._compare_values(None, "is_not_null", None)[0] is False

    def test_none_with_other_operator_is_false(self, evaluator):
        assert evaluator._compare_values(None, "equals", "x") == (False, None)

    def test_unknown_operator_is_false(self, evaluator):
        assert evaluator._compare_values("a", "no_such_op", "a")[0] is False


# =============================================================================
# _compare_values - datetime operators
# =============================================================================
class TestDatetimeOperators:
    def test_before(self, evaluator):
        assert (
            evaluator._compare_values(
                "2026-01-01T00:00:00", "before", "2026-06-01T00:00:00"
            )[0]
            is True
        )

    def test_after(self, evaluator):
        assert (
            evaluator._compare_values(
                "2026-06-01T00:00:00", "after", "2026-01-01T00:00:00"
            )[0]
            is True
        )

    def test_within_last_recent_true(self, evaluator):
        recent = (datetime.now(UTC) - timedelta(days=2)).isoformat()
        assert evaluator._compare_values(recent, "within_last", 7)[0] is True

    def test_within_last_old_false(self, evaluator):
        old = (datetime.now(UTC) - timedelta(days=30)).isoformat()
        assert evaluator._compare_values(old, "within_last", 7)[0] is False


# =============================================================================
# field extraction
# =============================================================================
class TestFieldExtraction:
    def test_profile_value_decimal_to_float(self, evaluator):
        profile = SimpleNamespace(total_revenue=Decimal("123.45"))
        assert evaluator._get_profile_value(profile, "total_revenue") == 123.45

    def test_profile_value_unknown_field_is_none(self, evaluator):
        profile = SimpleNamespace(secret="x")
        assert evaluator._get_profile_value(profile, "secret") is None

    def test_trait_value(self, evaluator):
        profile = SimpleNamespace(computed_traits={"ltv": 999})
        assert evaluator._get_trait_value(profile, "ltv") == 999

    def test_trait_value_missing_traits(self, evaluator):
        profile = SimpleNamespace(computed_traits=None)
        assert evaluator._get_trait_value(profile, "ltv") is None

    def test_profile_data_nested_path(self, evaluator):
        profile = SimpleNamespace(profile_data={"address": {"city": "NYC"}})
        assert evaluator._get_profile_data_value(profile, ["address", "city"]) == "NYC"

    def test_profile_data_path_breaks_on_non_dict(self, evaluator):
        profile = SimpleNamespace(profile_data={"address": "flat"})
        assert evaluator._get_profile_data_value(profile, ["address", "city"]) is None

    def test_parse_datetime_passthrough(self, evaluator):
        dt = datetime(2026, 6, 1, tzinfo=UTC)
        assert evaluator._parse_datetime(dt) is dt

    def test_parse_datetime_z_suffix(self, evaluator):
        parsed = evaluator._parse_datetime("2026-06-01T00:00:00Z")
        assert parsed.year == 2026 and parsed.tzinfo is not None

    def test_parse_datetime_invalid_is_none(self, evaluator):
        assert evaluator._parse_datetime("not-a-date") is None


# =============================================================================
# slug generation
# =============================================================================
class TestSlug:
    def test_basic(self, service):
        assert service._generate_slug("High Value Customers") == "high-value-customers"

    def test_strips_punctuation_and_collapses(self, service):
        assert service._generate_slug("VIP!! Buyers  (2026)") == "vip-buyers-2026"

    def test_trims_leading_trailing_dashes(self, service):
        assert service._generate_slug("  --Edge--  ") == "edge"

    def test_truncates_to_100_chars(self, service):
        assert len(service._generate_slug("a" * 200)) == 100
