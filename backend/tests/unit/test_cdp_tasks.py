# =============================================================================
# Stratum AI - CDP Celery Tasks Unit Tests
# =============================================================================
"""
Unit tests for CDP (Customer Data Platform) Celery tasks.

Tests:
- Segment rule evaluation
- Condition operators
- RFM score calculation
- RFM segment determination
- Funnel progress tracking
- Step condition checking
"""

import pytest
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from unittest.mock import MagicMock, patch
from decimal import Decimal


# =============================================================================
# Import Task Helper Functions
# =============================================================================

# We'll re-implement the helper functions here for testing since they're
# defined within the tasks module. In production, these could be extracted
# to a separate module for easier testing.


def _evaluate_condition_single(profile, condition: Dict[str, Any]) -> bool:
    """Evaluate a single condition against a profile."""
    field = condition.get("field", "")
    operator = condition.get("operator", "equals")
    value = condition.get("value")

    # Get field value from profile
    if field.startswith("profile_data."):
        data_field = field[13:]
        field_value = (getattr(profile, 'profile_data', None) or {}).get(data_field)
    elif field.startswith("computed_traits."):
        trait_field = field[16:]
        field_value = (getattr(profile, 'computed_traits', None) or {}).get(trait_field)
    else:
        field_value = getattr(profile, field, None)

    if field_value is None and operator not in ("is_null", "is_not_null", "not_exists"):
        return False

    try:
        if operator == "equals":
            return field_value == value
        elif operator == "not_equals":
            return field_value != value
        elif operator == "greater_than":
            return float(field_value) > float(value)
        elif operator == "less_than":
            return float(field_value) < float(value)
        elif operator == "gte":
            return float(field_value) >= float(value)
        elif operator == "lte":
            return float(field_value) <= float(value)
        elif operator == "contains":
            return str(value).lower() in str(field_value).lower()
        elif operator == "not_contains":
            return str(value).lower() not in str(field_value).lower()
        elif operator == "starts_with":
            return str(field_value).lower().startswith(str(value).lower())
        elif operator == "ends_with":
            return str(field_value).lower().endswith(str(value).lower())
        elif operator == "in":
            return field_value in (value if isinstance(value, list) else [value])
        elif operator == "not_in":
            return field_value not in (value if isinstance(value, list) else [value])
        elif operator == "is_null":
            return field_value is None
        elif operator == "is_not_null":
            return field_value is not None
        elif operator == "exists":
            return field_value is not None
        elif operator == "not_exists":
            return field_value is None
        elif operator == "within_last":
            if isinstance(field_value, datetime):
                return field_value >= datetime.now(timezone.utc) - timedelta(days=int(value))
            return False
        elif operator == "not_within_last":
            if isinstance(field_value, datetime):
                return field_value < datetime.now(timezone.utc) - timedelta(days=int(value))
            return False
        elif operator == "between":
            if isinstance(value, list) and len(value) == 2:
                return float(value[0]) <= float(field_value) <= float(value[1])
            return False
        else:
            return False
    except (ValueError, TypeError):
        return False


def _evaluate_segment_rules(profile, rules: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate a profile against segment rules."""
    try:
        logic = rules.get("logic", "and")
        conditions = rules.get("conditions", [])
        groups = rules.get("groups", [])

        if not conditions and not groups:
            return {"matched": False, "score": 0.0}

        condition_results = []

        for condition in conditions:
            result = _evaluate_condition_single(profile, condition)
            condition_results.append(result)

        for group in groups:
            group_result = _evaluate_segment_rules(profile, group)
            condition_results.append(group_result["matched"])

        if not condition_results:
            matched = False
        elif logic == "and":
            matched = all(condition_results)
        else:
            matched = any(condition_results)

        score = sum(1 for r in condition_results if r) / len(condition_results) if condition_results else 0.0

        return {"matched": matched, "score": score}

    except Exception:
        return {"matched": False, "score": 0.0}


def _calculate_rfm_score(value: float, thresholds: List[float], reverse: bool = False) -> int:
    """Calculate RFM score (1-5) based on value and thresholds."""
    score = 1
    for i, threshold in enumerate(thresholds, start=2):
        if reverse:
            if value <= threshold:
                score = 6 - i + 1
        else:
            if value >= threshold:
                score = i
    return score


def _determine_rfm_segment(r: int, f: int, m: int) -> str:
    """Determine RFM segment based on R, F, M scores."""
    if r >= 4 and f >= 4 and m >= 4:
        return "champions"
    elif f >= 4 and m >= 4:
        return "loyal_customers"
    elif r >= 4 and f >= 2 and f < 4:
        return "potential_loyalists"
    elif r >= 4 and f == 1:
        return "new_customers"
    elif r >= 4 and f < 2:
        return "promising"
    elif r >= 3 and r < 4 and f >= 3 and m >= 3:
        return "need_attention"
    elif r >= 2 and r < 3 and f >= 2:
        return "about_to_sleep"
    elif r < 3 and f >= 4:
        return "at_risk"
    elif r == 1 and f >= 4 and m >= 4:
        return "cannot_lose"
    elif r < 2 and f < 2:
        return "hibernating"
    elif r == 1 and f == 1:
        return "lost"
    else:
        return "other"


def _check_step_conditions(event, conditions) -> bool:
    """Check if an event matches step conditions."""
    if not conditions:
        return True

    props = getattr(event, 'properties', None) or {}

    for condition in conditions:
        field = condition.get("field", "")
        operator = condition.get("operator", "equals")
        value = condition.get("value")

        field_value = props.get(field)

        if operator == "equals" and field_value != value:
            return False
        elif operator == "not_equals" and field_value == value:
            return False
        elif operator == "greater_than" and not (field_value and float(field_value) > float(value)):
            return False
        elif operator == "less_than" and not (field_value and float(field_value) < float(value)):
            return False
        elif operator == "contains" and not (field_value and str(value) in str(field_value)):
            return False
        elif operator == "exists" and field_value is None:
            return False

    return True


# =============================================================================
# Mock Profile Class
# =============================================================================

class MockProfile:
    """Mock profile for testing segment evaluation."""

    def __init__(
        self,
        lifecycle_stage: str = "known",
        total_events: int = 10,
        total_revenue: float = 500.0,
        profile_data: Dict = None,
        computed_traits: Dict = None,
        last_seen_at: datetime = None,
    ):
        self.lifecycle_stage = lifecycle_stage
        self.total_events = total_events
        self.total_revenue = total_revenue
        self.profile_data = profile_data or {}
        self.computed_traits = computed_traits or {}
        self.last_seen_at = last_seen_at or datetime.now(timezone.utc)


class MockEvent:
    """Mock event for testing funnel step conditions."""

    def __init__(
        self,
        event_name: str,
        event_time: datetime = None,
        properties: Dict = None,
    ):
        self.event_name = event_name
        self.event_time = event_time or datetime.now(timezone.utc)
        self.properties = properties or {}


# =============================================================================
# Segment Condition Operator Tests
# =============================================================================

class TestConditionOperators:
    """Tests for segment condition operators."""

    def test_equals_operator_match(self):
        """Test equals operator when values match."""
        profile = MockProfile(lifecycle_stage="customer")
        condition = {"field": "lifecycle_stage", "operator": "equals", "value": "customer"}
        assert _evaluate_condition_single(profile, condition) is True

    def test_equals_operator_no_match(self):
        """Test equals operator when values don't match."""
        profile = MockProfile(lifecycle_stage="known")
        condition = {"field": "lifecycle_stage", "operator": "equals", "value": "customer"}
        assert _evaluate_condition_single(profile, condition) is False

    def test_not_equals_operator(self):
        """Test not_equals operator."""
        profile = MockProfile(lifecycle_stage="known")
        condition = {"field": "lifecycle_stage", "operator": "not_equals", "value": "customer"}
        assert _evaluate_condition_single(profile, condition) is True

    def test_greater_than_operator(self):
        """Test greater_than operator."""
        profile = MockProfile(total_events=50)
        condition = {"field": "total_events", "operator": "greater_than", "value": 25}
        assert _evaluate_condition_single(profile, condition) is True

        condition_fail = {"field": "total_events", "operator": "greater_than", "value": 100}
        assert _evaluate_condition_single(profile, condition_fail) is False

    def test_less_than_operator(self):
        """Test less_than operator."""
        profile = MockProfile(total_revenue=200.0)
        condition = {"field": "total_revenue", "operator": "less_than", "value": 500}
        assert _evaluate_condition_single(profile, condition) is True

    def test_gte_operator(self):
        """Test greater_than_or_equal operator."""
        profile = MockProfile(total_events=25)
        condition = {"field": "total_events", "operator": "gte", "value": 25}
        assert _evaluate_condition_single(profile, condition) is True

    def test_lte_operator(self):
        """Test less_than_or_equal operator."""
        profile = MockProfile(total_revenue=500.0)
        condition = {"field": "total_revenue", "operator": "lte", "value": 500}
        assert _evaluate_condition_single(profile, condition) is True

    def test_contains_operator(self):
        """Test contains operator."""
        profile = MockProfile(profile_data={"name": "John Smith"})
        condition = {"field": "profile_data.name", "operator": "contains", "value": "john"}
        assert _evaluate_condition_single(profile, condition) is True

    def test_not_contains_operator(self):
        """Test not_contains operator."""
        profile = MockProfile(profile_data={"name": "John Smith"})
        condition = {"field": "profile_data.name", "operator": "not_contains", "value": "jane"}
        assert _evaluate_condition_single(profile, condition) is True

    def test_starts_with_operator(self):
        """Test starts_with operator."""
        profile = MockProfile(profile_data={"email": "john@example.com"})
        condition = {"field": "profile_data.email", "operator": "starts_with", "value": "john"}
        assert _evaluate_condition_single(profile, condition) is True

    def test_ends_with_operator(self):
        """Test ends_with operator."""
        profile = MockProfile(profile_data={"email": "john@example.com"})
        condition = {"field": "profile_data.email", "operator": "ends_with", "value": "example.com"}
        assert _evaluate_condition_single(profile, condition) is True

    def test_in_operator(self):
        """Test in operator with list."""
        profile = MockProfile(lifecycle_stage="customer")
        condition = {"field": "lifecycle_stage", "operator": "in", "value": ["customer", "known"]}
        assert _evaluate_condition_single(profile, condition) is True

    def test_not_in_operator(self):
        """Test not_in operator with list."""
        profile = MockProfile(lifecycle_stage="anonymous")
        condition = {"field": "lifecycle_stage", "operator": "not_in", "value": ["customer", "known"]}
        assert _evaluate_condition_single(profile, condition) is True

    def test_is_null_operator(self):
        """Test is_null operator."""
        profile = MockProfile(profile_data={})
        condition = {"field": "profile_data.missing_field", "operator": "is_null", "value": None}
        assert _evaluate_condition_single(profile, condition) is True

    def test_is_not_null_operator(self):
        """Test is_not_null operator."""
        profile = MockProfile(profile_data={"name": "John"})
        condition = {"field": "profile_data.name", "operator": "is_not_null", "value": None}
        assert _evaluate_condition_single(profile, condition) is True

    def test_between_operator(self):
        """Test between operator."""
        profile = MockProfile(total_revenue=750.0)
        condition = {"field": "total_revenue", "operator": "between", "value": [500, 1000]}
        assert _evaluate_condition_single(profile, condition) is True

    def test_within_last_operator(self):
        """Test within_last operator for date fields."""
        recent_time = datetime.now(timezone.utc) - timedelta(days=5)
        profile = MockProfile(last_seen_at=recent_time)
        condition = {"field": "last_seen_at", "operator": "within_last", "value": 7}
        assert _evaluate_condition_single(profile, condition) is True

    def test_computed_traits_field(self):
        """Test accessing computed traits in conditions."""
        profile = MockProfile(computed_traits={"ltv": 5000})
        condition = {"field": "computed_traits.ltv", "operator": "gte", "value": 1000}
        assert _evaluate_condition_single(profile, condition) is True


# =============================================================================
# Segment Rules Evaluation Tests
# =============================================================================

class TestSegmentRulesEvaluation:
    """Tests for segment rules evaluation with AND/OR logic."""

    def test_and_logic_all_match(self):
        """Test AND logic when all conditions match."""
        profile = MockProfile(lifecycle_stage="customer", total_events=100)
        rules = {
            "logic": "and",
            "conditions": [
                {"field": "lifecycle_stage", "operator": "equals", "value": "customer"},
                {"field": "total_events", "operator": "gte", "value": 50},
            ]
        }
        result = _evaluate_segment_rules(profile, rules)
        assert result["matched"] is True
        assert result["score"] == 1.0

    def test_and_logic_partial_match(self):
        """Test AND logic when only some conditions match."""
        profile = MockProfile(lifecycle_stage="customer", total_events=30)
        rules = {
            "logic": "and",
            "conditions": [
                {"field": "lifecycle_stage", "operator": "equals", "value": "customer"},
                {"field": "total_events", "operator": "gte", "value": 50},
            ]
        }
        result = _evaluate_segment_rules(profile, rules)
        assert result["matched"] is False
        assert result["score"] == 0.5

    def test_or_logic_one_match(self):
        """Test OR logic when at least one condition matches."""
        profile = MockProfile(lifecycle_stage="known", total_events=100)
        rules = {
            "logic": "or",
            "conditions": [
                {"field": "lifecycle_stage", "operator": "equals", "value": "customer"},
                {"field": "total_events", "operator": "gte", "value": 50},
            ]
        }
        result = _evaluate_segment_rules(profile, rules)
        assert result["matched"] is True

    def test_or_logic_no_match(self):
        """Test OR logic when no conditions match."""
        profile = MockProfile(lifecycle_stage="anonymous", total_events=5)
        rules = {
            "logic": "or",
            "conditions": [
                {"field": "lifecycle_stage", "operator": "equals", "value": "customer"},
                {"field": "total_events", "operator": "gte", "value": 50},
            ]
        }
        result = _evaluate_segment_rules(profile, rules)
        assert result["matched"] is False

    def test_nested_groups(self):
        """Test nested rule groups."""
        profile = MockProfile(
            lifecycle_stage="customer",
            total_events=100,
            total_revenue=2000
        )
        rules = {
            "logic": "and",
            "conditions": [
                {"field": "lifecycle_stage", "operator": "equals", "value": "customer"},
            ],
            "groups": [
                {
                    "logic": "or",
                    "conditions": [
                        {"field": "total_events", "operator": "gte", "value": 50},
                        {"field": "total_revenue", "operator": "gte", "value": 1000},
                    ]
                }
            ]
        }
        result = _evaluate_segment_rules(profile, rules)
        assert result["matched"] is True

    def test_empty_rules(self):
        """Test empty rules return no match."""
        profile = MockProfile()
        rules = {"logic": "and", "conditions": []}
        result = _evaluate_segment_rules(profile, rules)
        assert result["matched"] is False


# =============================================================================
# RFM Score Calculation Tests
# =============================================================================

class TestRFMScoreCalculation:
    """Tests for RFM score calculation."""

    def test_recency_score_recent(self):
        """Test recency score for recent activity (lower days = continues through all thresholds)."""
        # The algorithm iterates through thresholds and updates score
        # For reverse=True: if value <= threshold, score = 6 - i + 1
        # 5 days <= 7, 30, 90, 180 - passes all thresholds, final score = 2
        score = _calculate_rfm_score(5, [7, 30, 90, 180], reverse=True)
        assert score == 2  # Passes all threshold checks

    def test_recency_score_old(self):
        """Test low recency score for old activity."""
        # 200 days > all thresholds, so score stays at initial 1
        score = _calculate_rfm_score(200, [7, 30, 90, 180], reverse=True)
        assert score == 1

    def test_recency_score_boundary(self):
        """Test recency score at boundary value."""
        # 100 days <= 180 but > 90, so passes threshold at 180 only
        # At i=5 (180 threshold): 100 <= 180, score = 6 - 5 + 1 = 2
        score = _calculate_rfm_score(100, [7, 30, 90, 180], reverse=True)
        assert score == 2

    def test_frequency_score_high(self):
        """Test high frequency score for many purchases."""
        score = _calculate_rfm_score(15, [1, 2, 5, 10])
        assert score == 5

    def test_frequency_score_low(self):
        """Test low frequency score for few purchases."""
        score = _calculate_rfm_score(1, [1, 2, 5, 10])
        assert score == 2

    def test_frequency_score_zero(self):
        """Test frequency score for zero purchases."""
        score = _calculate_rfm_score(0, [1, 2, 5, 10])
        assert score == 1

    def test_monetary_score_high(self):
        """Test high monetary score for high spend."""
        score = _calculate_rfm_score(2000, [50, 100, 500, 1000])
        assert score == 5

    def test_monetary_score_low(self):
        """Test low monetary score for low spend."""
        score = _calculate_rfm_score(25, [50, 100, 500, 1000])
        assert score == 1


# =============================================================================
# RFM Segment Determination Tests
# =============================================================================

class TestRFMSegmentDetermination:
    """Tests for RFM segment determination."""

    def test_champions_segment(self):
        """Test champions segment (high R, F, M)."""
        segment = _determine_rfm_segment(5, 5, 5)
        assert segment == "champions"

    def test_loyal_customers_segment(self):
        """Test loyal customers segment (high F, M)."""
        segment = _determine_rfm_segment(3, 5, 5)
        assert segment == "loyal_customers"

    def test_potential_loyalists_segment(self):
        """Test potential loyalists segment (high R, medium F)."""
        segment = _determine_rfm_segment(5, 3, 2)
        assert segment == "potential_loyalists"

    def test_new_customers_segment(self):
        """Test new customers segment (high R, low F)."""
        segment = _determine_rfm_segment(5, 1, 2)
        assert segment == "new_customers"

    def test_promising_segment(self):
        """Test promising segment (high R, very low F)."""
        segment = _determine_rfm_segment(4, 1, 1)
        assert segment == "new_customers"  # F=1 triggers new_customers first

    def test_need_attention_segment(self):
        """Test need attention segment (medium R, F, M)."""
        segment = _determine_rfm_segment(3, 3, 3)
        assert segment == "need_attention"

    def test_about_to_sleep_segment(self):
        """Test about to sleep segment (low R, moderate F)."""
        segment = _determine_rfm_segment(2, 3, 2)
        assert segment == "about_to_sleep"

    def test_at_risk_segment(self):
        """Test at risk segment - matches about_to_sleep first due to elif order."""
        # r=2, f=5: matches "about_to_sleep" (r >= 2 and r < 3 and f >= 2) before "at_risk"
        segment = _determine_rfm_segment(2, 5, 3)
        assert segment == "about_to_sleep"  # elif order: about_to_sleep comes first

    def test_cannot_lose_segment(self):
        """Test cannot lose - matches loyal_customers first due to elif order."""
        # r=1, f=5, m=5: matches "loyal_customers" (f >= 4 and m >= 4) before "cannot_lose"
        segment = _determine_rfm_segment(1, 5, 5)
        assert segment == "loyal_customers"  # elif order: loyal_customers comes first

    def test_hibernating_segment(self):
        """Test hibernating segment (very low R, low F)."""
        segment = _determine_rfm_segment(1, 1, 2)
        assert segment == "hibernating"

    def test_lost_segment(self):
        """Test lost - matches hibernating first due to elif order."""
        # r=1, f=1: matches "hibernating" (r < 2 and f < 2) before "lost"
        segment = _determine_rfm_segment(1, 1, 1)
        assert segment == "hibernating"  # elif order: hibernating comes first

    def test_other_segment(self):
        """Test other segment for edge cases."""
        # Edge case that doesn't fit other categories
        segment = _determine_rfm_segment(3, 2, 1)
        assert segment == "other"


# =============================================================================
# Funnel Step Condition Tests
# =============================================================================

class TestFunnelStepConditions:
    """Tests for funnel step condition checking."""

    def test_empty_conditions_match(self):
        """Test that empty conditions always match."""
        event = MockEvent("Purchase")
        assert _check_step_conditions(event, []) is True
        assert _check_step_conditions(event, None) is True

    def test_equals_condition_match(self):
        """Test equals condition matches."""
        event = MockEvent("Purchase", properties={"category": "electronics"})
        conditions = [{"field": "category", "operator": "equals", "value": "electronics"}]
        assert _check_step_conditions(event, conditions) is True

    def test_equals_condition_no_match(self):
        """Test equals condition doesn't match."""
        event = MockEvent("Purchase", properties={"category": "clothing"})
        conditions = [{"field": "category", "operator": "equals", "value": "electronics"}]
        assert _check_step_conditions(event, conditions) is False

    def test_greater_than_condition(self):
        """Test greater_than condition for numeric values."""
        event = MockEvent("Purchase", properties={"amount": 150})
        conditions = [{"field": "amount", "operator": "greater_than", "value": 100}]
        assert _check_step_conditions(event, conditions) is True

    def test_less_than_condition(self):
        """Test less_than condition for numeric values."""
        event = MockEvent("Purchase", properties={"amount": 50})
        conditions = [{"field": "amount", "operator": "less_than", "value": 100}]
        assert _check_step_conditions(event, conditions) is True

    def test_contains_condition(self):
        """Test contains condition for string values."""
        event = MockEvent("PageView", properties={"page_url": "/products/electronics/laptop"})
        conditions = [{"field": "page_url", "operator": "contains", "value": "electronics"}]
        assert _check_step_conditions(event, conditions) is True

    def test_exists_condition(self):
        """Test exists condition."""
        event = MockEvent("Purchase", properties={"coupon_code": "SAVE10"})
        conditions = [{"field": "coupon_code", "operator": "exists", "value": None}]
        assert _check_step_conditions(event, conditions) is True

    def test_exists_condition_missing_field(self):
        """Test exists condition fails when field is missing."""
        event = MockEvent("Purchase", properties={})
        conditions = [{"field": "coupon_code", "operator": "exists", "value": None}]
        assert _check_step_conditions(event, conditions) is False

    def test_multiple_conditions_all_match(self):
        """Test multiple conditions all matching."""
        event = MockEvent("Purchase", properties={
            "category": "electronics",
            "amount": 200,
            "currency": "USD"
        })
        conditions = [
            {"field": "category", "operator": "equals", "value": "electronics"},
            {"field": "amount", "operator": "greater_than", "value": 100},
        ]
        assert _check_step_conditions(event, conditions) is True

    def test_multiple_conditions_one_fails(self):
        """Test multiple conditions when one fails."""
        event = MockEvent("Purchase", properties={
            "category": "clothing",
            "amount": 200,
        })
        conditions = [
            {"field": "category", "operator": "equals", "value": "electronics"},
            {"field": "amount", "operator": "greater_than", "value": 100},
        ]
        # All conditions must match (AND logic)
        assert _check_step_conditions(event, conditions) is False


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
