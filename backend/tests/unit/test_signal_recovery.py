# =============================================================================
# Stratum AI - Signal Recovery unit tests
# =============================================================================
"""Unit tests for app.analytics.logic.signal_recovery.

Core Trust Engine module — detects signal-health issues and builds recovery
plans. Pure logic, no I/O. Covers issue detection across all four types +
severity bands, recovery-action generation, timeline, status, progress,
summary, and the build_signal_recovery entry point.
"""

import pytest

from app.analytics.logic.signal_recovery import (
    RecoveryAction,
    SignalRecoveryResponse,
    build_signal_recovery,
    calculate_recovery_progress,
    detect_signal_issues,
    determine_recovery_status,
    generate_recovery_actions,
    generate_recovery_summary,
)

pytestmark = pytest.mark.unit


def _healthy_kwargs(**kw):
    base = dict(
        overall_score=85,
        emq_score=0.9,
        event_loss_pct=2.0,
        api_health=True,
        data_freshness_hours=5.0,
        connected_platforms=["meta", "google"],
    )
    base.update(kw)
    return base


def _action(status="pending", auto=False, priority="normal"):
    return RecoveryAction(
        id="a1",
        issue_id="i1",
        type="resync",
        title="t",
        description="d",
        status=status,
        priority=priority,
        auto_triggered=auto,
        estimated_minutes=10,
    )


# =============================================================================
# Issue detection
# =============================================================================
class TestDetectIssues:
    def test_no_issues_when_healthy(self):
        assert detect_signal_issues(**_healthy_kwargs()) == []

    def test_api_down_is_critical(self):
        issues = detect_signal_issues(**_healthy_kwargs(api_health=False))
        api = next(i for i in issues if i.type == "api_down")
        assert api.severity == "critical"
        assert api.affected_platforms == ["meta", "google"]

    @pytest.mark.parametrize(
        "emq,severity",
        [(0.5, "critical"), (0.7, "high")],
    )
    def test_emq_drop_severity(self, emq, severity):
        issues = detect_signal_issues(**_healthy_kwargs(emq_score=emq))
        emq_issue = next(i for i in issues if i.type == "emq_drop")
        assert emq_issue.severity == severity

    def test_emq_healthy_no_issue(self):
        issues = detect_signal_issues(**_healthy_kwargs(emq_score=0.85))
        assert not any(i.type == "emq_drop" for i in issues)

    def test_emq_accepts_percentage_form(self):
        # value > 1.0 is treated as already-a-percentage
        issues = detect_signal_issues(**_healthy_kwargs(emq_score=70.0))
        emq_issue = next(i for i in issues if i.type == "emq_drop")
        assert emq_issue.metric_value == 70.0
        assert emq_issue.severity == "high"

    @pytest.mark.parametrize(
        "loss,severity",
        [(20.0, "critical"), (12.0, "high"), (7.0, "medium")],
    )
    def test_event_loss_severity(self, loss, severity):
        issues = detect_signal_issues(**_healthy_kwargs(event_loss_pct=loss))
        ev = next(i for i in issues if i.type == "event_loss")
        assert ev.severity == severity

    def test_event_loss_below_threshold_no_issue(self):
        issues = detect_signal_issues(**_healthy_kwargs(event_loss_pct=3.0))
        assert not any(i.type == "event_loss" for i in issues)

    @pytest.mark.parametrize(
        "hours,severity",
        [(80.0, "critical"), (50.0, "high"), (30.0, "medium")],
    )
    def test_data_stale_severity(self, hours, severity):
        issues = detect_signal_issues(**_healthy_kwargs(data_freshness_hours=hours))
        stale = next(i for i in issues if i.type == "data_stale")
        assert stale.severity == severity

    def test_issues_sorted_by_severity(self):
        issues = detect_signal_issues(
            **_healthy_kwargs(
                api_health=False,  # critical
                event_loss_pct=7.0,  # medium
                data_freshness_hours=50.0,  # high
            )
        )
        order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        ranks = [order[i.severity] for i in issues]
        assert ranks == sorted(ranks)


# =============================================================================
# Recovery actions
# =============================================================================
class TestRecoveryActions:
    def test_no_issues_no_actions(self):
        assert generate_recovery_actions([]) == []

    def test_actions_generated_auto_first(self):
        issues = detect_signal_issues(**_healthy_kwargs(api_health=False))
        actions = generate_recovery_actions(issues)
        assert actions  # api_down has recovery actions
        # auto-triggered actions sort to the front
        autos = [a.auto_triggered for a in actions]
        assert autos == sorted(autos, reverse=True)


# =============================================================================
# Status / progress
# =============================================================================
class TestStatusProgress:
    def test_status_healthy_when_no_issues(self):
        assert determine_recovery_status([]) == "healthy"

    def test_status_critical(self):
        issues = detect_signal_issues(**_healthy_kwargs(api_health=False))
        assert determine_recovery_status(issues) == "critical"

    def test_status_degraded_high_only(self):
        issues = detect_signal_issues(**_healthy_kwargs(data_freshness_hours=50.0))
        assert determine_recovery_status(issues) == "degraded"

    def test_status_recovering_medium_only(self):
        issues = detect_signal_issues(**_healthy_kwargs(event_loss_pct=7.0))
        assert determine_recovery_status(issues) == "recovering"

    def test_progress_no_actions_is_complete(self):
        assert calculate_recovery_progress([]) == 100

    def test_progress_partial_credit(self):
        actions = [
            _action(status="completed"),
            _action(status="in_progress"),
            _action(status="pending"),
        ]
        # (1 + 0.5) / 3 * 100 = 50
        assert calculate_recovery_progress(actions) == 50


# =============================================================================
# Summary
# =============================================================================
class TestSummary:
    def test_healthy_summary(self):
        s = generate_recovery_summary("healthy", [], [])
        assert "All signals are healthy" in s

    def test_critical_summary(self):
        issues = detect_signal_issues(**_healthy_kwargs(api_health=False))
        actions = generate_recovery_actions(issues)
        s = generate_recovery_summary("critical", issues, actions)
        assert "Critical issue detected" in s


# =============================================================================
# build_signal_recovery (entry point)
# =============================================================================
class TestBuild:
    def test_healthy_path(self):
        resp = build_signal_recovery(**_healthy_kwargs())
        assert isinstance(resp, SignalRecoveryResponse)
        assert resp.status == "healthy"
        assert resp.has_active_recovery is False
        assert resp.recovery_progress_pct == 100
        assert resp.issues == []

    def test_degraded_path(self):
        resp = build_signal_recovery(
            **_healthy_kwargs(
                api_health=False,
                emq_score=0.5,
                event_loss_pct=20.0,
                data_freshness_hours=80.0,
            )
        )
        assert resp.status == "critical"
        assert resp.has_active_recovery is True
        assert resp.issues
        assert resp.recovery_actions
        assert resp.timeline
        assert resp.platforms_affected == ["google", "meta"]  # sorted
        assert resp.overall_health_score == 85
