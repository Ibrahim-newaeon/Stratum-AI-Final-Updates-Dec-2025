# =============================================================================
# Stratum AI - Goal Tracking unit tests
# =============================================================================
"""Unit tests for app.analytics.logic.goal_tracking.

Pure pacing / goal-projection logic, no I/O. Covers the pacing-status bands
(incl. inverted metrics), metric formatting, trend detection, goal building
with run-rate projection, and the build_goal_tracking entry point.
"""

from datetime import date, timedelta

import pytest

from app.analytics.logic import goal_tracking as gt
from app.analytics.logic.goal_tracking import GoalTrackingResponse, build_goal_tracking

pytestmark = pytest.mark.unit


# =============================================================================
# Pacing status
# =============================================================================
class TestPacingStatus:
    @pytest.mark.parametrize(
        "pct,status",
        [
            (120.0, "ahead"),
            (100.0, "on_track"),
            (80.0, "behind"),
            (60.0, "at_risk"),
            (40.0, "critical"),
        ],
    )
    def test_standard_bands(self, pct, status):
        assert gt._get_pacing_status(pct) == status

    def test_inverted_flips_ratio(self):
        # inverted: ratio = 2.0 - ratio, so a high raw pacing reads worse
        assert gt._get_pacing_status(120.0, is_inverted=True) == "behind"
        assert gt._get_pacing_status(80.0, is_inverted=True) == "ahead"


# =============================================================================
# Formatting + trend
# =============================================================================
class TestFormatting:
    @pytest.mark.parametrize(
        "value,metric,expected",
        [
            (500.0, "spend", "$500"),
            (1500.0, "revenue", "$1.5K"),
            (2_000_000.0, "spend", "$2.0M"),
            (3.5, "roas", "3.50x"),
            (1500.0, "conversions", "1.5K"),
            (500.0, "conversions", "500"),
            (42.0, "other", "42"),
        ],
    )
    def test_format_metric(self, value, metric, expected):
        assert gt._format_metric(value, metric) == expected

    @pytest.mark.parametrize(
        "pace,trend",
        [(1.1, "improving"), (0.8, "declining"), (1.0, "stable")],
    )
    def test_detect_trend(self, pace, trend):
        assert gt._detect_trend(pace, days_elapsed=10) == trend


# =============================================================================
# Goal building (deterministic with fixed dates)
# =============================================================================
class TestBuildGoals:
    def test_revenue_goal_pacing_and_projection(self):
        start = date(2026, 6, 1)
        today = date(2026, 6, 16)  # 15 days elapsed, 29 total
        end = date(2026, 6, 30)
        campaigns = [{"spend": 5000, "revenue": 15000, "conversions": 300}]
        goals = gt._build_goals(campaigns, {"revenue": 30000}, today, start, end)
        g = goals[0]
        assert g.metric == "revenue"
        assert g.progress_pct == 50.0  # 15000 / 30000
        assert g.pacing_status == "on_track"
        assert g.projected_value == 29000.0  # run-rate: 1000/day * 29 days
        assert g.gap == 15000.0
        assert g.days_remaining == 14

    def test_zero_target_skipped(self):
        start, today, end = date(2026, 6, 1), date(2026, 6, 16), date(2026, 6, 30)
        goals = gt._build_goals(
            [{"spend": 100, "revenue": 500, "conversions": 5}],
            {"revenue": 0, "spend": 1000},
            today,
            start,
            end,
        )
        metrics = {g.metric for g in goals}
        assert "revenue" not in metrics  # target 0 skipped
        assert "spend" in metrics

    def test_cpa_is_inverted(self):
        start, today, end = date(2026, 6, 1), date(2026, 6, 16), date(2026, 6, 30)
        goals = gt._build_goals(
            [{"spend": 1000, "revenue": 5000, "conversions": 100}],
            {"cpa": 15.0},
            today,
            start,
            end,
        )
        cpa = next(g for g in goals if g.metric == "cpa")
        assert cpa.is_inverted is True


# =============================================================================
# build_goal_tracking (entry point)
# =============================================================================
class TestBuild:
    def _period(self):
        today = date.today()
        return today - timedelta(days=15), today + timedelta(days=15)

    def test_empty_campaigns(self):
        resp = build_goal_tracking([])
        assert isinstance(resp, GoalTrackingResponse)
        assert "No campaign data" in resp.summary

    def test_full_with_explicit_targets(self):
        start, end = self._period()
        campaigns = [
            {"spend": 5000, "revenue": 15000, "conversions": 300},
            {"spend": 3000, "revenue": 9000, "conversions": 150},
        ]
        resp = build_goal_tracking(
            campaigns,
            targets={"revenue": 50000, "roas": 3.0},
            period_start=start,
            period_end=end,
        )
        assert resp.goals
        metrics = {g.metric for g in resp.goals}
        assert "revenue" in metrics
        assert resp.overall_pacing in {
            "ahead",
            "on_track",
            "behind",
            "at_risk",
            "critical",
        }
        # milestones built off the revenue goal
        assert len(resp.milestones) == 4
        assert resp.goals_on_track + resp.goals_at_risk + resp.goals_behind <= len(
            resp.goals
        )

    def test_default_targets_when_none(self):
        start, end = self._period()
        resp = build_goal_tracking(
            [{"spend": 5000, "revenue": 15000, "conversions": 300}],
            period_start=start,
            period_end=end,
        )
        # default targets are derived from run-rate -> goals exist
        assert resp.goals
        assert resp.period_label
