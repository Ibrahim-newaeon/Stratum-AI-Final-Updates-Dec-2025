# =============================================================================
# Stratum AI - Unified Notifications unit tests
# =============================================================================
"""Unit tests for app.analytics.logic.unified_notifications.

Pure notification scoring + aggregation, no I/O. Covers urgency/impact/
actionability scorers, the composite priority + label, and the
build_unified_notifications entry point (sources, re-scoring, grouping, ranking).
"""

from datetime import datetime, timezone

import pytest

from app.analytics.logic import unified_notifications as un
from app.analytics.logic.unified_notifications import (
    UnifiedNotificationsResponse,
    build_unified_notifications,
)

pytestmark = pytest.mark.unit


def _campaign(cid, name, platform, spend, revenue, conversions):
    return {
        "id": cid,
        "name": name,
        "platform": platform,
        "spend": spend,
        "revenue": revenue,
        "conversions": conversions,
    }


# =============================================================================
# Urgency
# =============================================================================
class TestUrgency:
    def test_critical_recent_clamps_to_100(self):
        assert un._score_urgency("critical", hours_ago=0.5) == 100

    def test_old_info_decays(self):
        assert un._score_urgency("info", hours_ago=48) == 10  # 20 - 10 recency

    def test_time_sensitive_boost(self):
        assert un._score_urgency("warning", hours_ago=3, is_time_sensitive=True) == 70

    def test_unknown_severity_default_base(self):
        # base 30, 24h window -> +0
        assert un._score_urgency("mystery", hours_ago=10) == 30


# =============================================================================
# Impact
# =============================================================================
class TestImpact:
    def test_max_impact_clamped(self):
        assert (
            un._score_impact(
                spend_at_risk=10000, deviation_pct=50, campaigns_affected=5
            )
            == 90
        )

    def test_small_impact(self):
        assert (
            un._score_impact(spend_at_risk=500, deviation_pct=5, campaigns_affected=0)
            == 10
        )

    def test_no_impact(self):
        assert un._score_impact() == 0


# =============================================================================
# Actionability
# =============================================================================
class TestActionability:
    def test_auto_resolve_highest(self):
        assert (
            un._score_actionability(has_suggested_action=True, can_auto_resolve=True)
            == 90
        )

    def test_suggested_not_manual(self):
        assert un._score_actionability(True, requires_manual=False) == 70

    def test_suggested_but_manual(self):
        assert un._score_actionability(True, requires_manual=True) == 50

    def test_manual_only(self):
        assert un._score_actionability(False, requires_manual=True) == 30

    def test_none(self):
        assert un._score_actionability(False) == 20


# =============================================================================
# Priority composite + label
# =============================================================================
class TestPriority:
    def test_composite_weights(self):
        assert un._compute_priority(90, 50, 70) == pytest.approx(74.0, abs=0.1)

    @pytest.mark.parametrize(
        "score,label",
        [(80, "critical"), (60, "high"), (40, "medium"), (20, "low")],
    )
    def test_label_thresholds(self, score, label):
        assert un._priority_label(score) == label


# =============================================================================
# build_unified_notifications
# =============================================================================
class TestBuild:
    def test_returns_sorted_feed(self):
        resp = build_unified_notifications([], signal_health_score=80)
        assert isinstance(resp, UnifiedNotificationsResponse)
        scores = [n.priority_score for n in resp.notifications]
        assert scores == sorted(scores, reverse=True)
        for n in resp.notifications:
            assert n.priority_label in {"critical", "high", "medium", "low"}

    def test_low_signal_health_generates_notification(self):
        resp = build_unified_notifications([], signal_health_score=30)
        # a degraded/blocked signal should surface something
        assert resp.total_count >= 1

    def test_campaign_notifications_included(self):
        campaigns = [_campaign(1, "Bad", "meta", 1000, 100, 1)]  # 0.1x ROAS
        resp = build_unified_notifications(campaigns, signal_health_score=80)
        assert resp.total_count >= 1
        assert resp.groups  # grouped by category

    def test_existing_notifications_rescored_and_included(self):
        now_iso = datetime.now(timezone.utc).isoformat()
        existing = [
            {
                "id": 7,
                "type": "error",  # valid stored notification_type, high urgency
                "title": "Budget exceeded",
                "message": "over budget",
                "created_at": now_iso,
                "action_url": "/campaigns/7",
                "action_label": "Review",
                "is_read": False,
            }
        ]
        resp = build_unified_notifications(
            [], signal_health_score=80, existing_notifications=existing
        )
        budget = next(
            (n for n in resp.notifications if n.title == "Budget exceeded"), None
        )
        assert budget is not None  # existing notification re-scored + included
        # its action_url was carried into a suggested action
        assert budget.suggested_action is not None
        assert budget.suggested_action.url == "/campaigns/7"

    def test_counts_are_consistent(self):
        campaigns = [
            _campaign(1, "Bad", "meta", 5000, 200, 1),
            _campaign(2, "Good", "google", 1000, 5000, 100),
        ]
        resp = build_unified_notifications(campaigns, signal_health_score=35)
        assert resp.unread_count <= resp.total_count
        assert resp.critical_count >= 0
        # at most 20 surfaced
        assert len(resp.notifications) <= 20

    def test_empty_everything_summary(self):
        # no campaigns AND a healthy signal that emits nothing actionable still
        # returns a valid response object
        resp = build_unified_notifications([], signal_health_score=95)
        assert isinstance(resp, UnifiedNotificationsResponse)
        assert resp.total_count == len(
            [n for g in resp.groups for n in g.notifications]
        ) or resp.total_count >= len(resp.notifications)
