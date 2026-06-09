# =============================================================================
# Stratum AI - Churn Prevention unit tests
# =============================================================================
"""Unit tests for app.analytics.logic.churn_prevention.

Pure risk-scoring + intervention logic, no I/O. Covers the three risk scorers,
intervention generation, the build_churn_prevention entry point, and the
summary builder.
"""

import pytest

from app.analytics.logic import churn_prevention as cp
from app.analytics.logic.churn_prevention import (
    ChurnPreventionResponse,
    ChurnSignal,
    Intervention,
    build_churn_prevention,
)

pytestmark = pytest.mark.unit


def _campaign(**kw):
    base = {
        "id": 1,
        "name": "C",
        "platform": "Meta",
        "status": "active",
        "spend": 100,
        "revenue": 300,
        "conversions": 30,
        "has_recent_sync": True,
    }
    base.update(kw)
    return base


# =============================================================================
# Performance risk
# =============================================================================
class TestPerformanceRisk:
    def test_critical_roas_and_zero_conversions(self):
        risk, signals = cp._score_performance_risk(roas=0.3, conversions=0, spend=200)
        names = {s.signal for s in signals}
        assert "critical_roas" in names
        assert "zero_conversions" in names
        assert risk == 50  # 35 + 20 capped at 50

    def test_low_roas_band(self):
        risk, signals = cp._score_performance_risk(roas=0.8, conversions=10, spend=60)
        assert risk == 25
        assert {s.signal for s in signals} == {"low_roas"}

    def test_underperforming_and_low_conversions(self):
        risk, signals = cp._score_performance_risk(roas=1.5, conversions=3, spend=200)
        names = {s.signal for s in signals}
        assert "underperforming_roas" in names
        assert "low_conversions" in names
        assert risk == 20

    def test_healthy_no_signals(self):
        risk, signals = cp._score_performance_risk(roas=2.5, conversions=100, spend=200)
        assert risk == 0
        assert signals == []


# =============================================================================
# Spend risk
# =============================================================================
class TestSpendRisk:
    def test_spend_collapse(self):
        risk, signals = cp._score_spend_risk(spend=20, avg_spend=200)
        assert risk == 25
        assert {s.signal for s in signals} == {"spend_collapse"}

    def test_spend_declining(self):
        risk, signals = cp._score_spend_risk(spend=100, avg_spend=200)
        assert risk == 15
        assert {s.signal for s in signals} == {"spend_declining"}

    def test_collapse_plus_minimal_caps_at_30(self):
        risk, signals = cp._score_spend_risk(spend=5, avg_spend=200)
        names = {s.signal for s in signals}
        assert "spend_collapse" in names
        assert "minimal_spend" in names
        assert risk == 30  # 25 + 10 capped at 30

    def test_no_average_no_ratio_signal(self):
        risk, signals = cp._score_spend_risk(spend=200, avg_spend=0)
        assert risk == 0
        assert signals == []


# =============================================================================
# Engagement risk
# =============================================================================
class TestEngagementRisk:
    def test_paused(self):
        risk, signals = cp._score_engagement_risk("paused", has_recent_sync=True)
        assert risk == 15
        assert {s.signal for s in signals} == {"campaign_paused"}

    def test_archived_is_higher(self):
        risk, signals = cp._score_engagement_risk("archived", has_recent_sync=True)
        assert risk == 20
        assert {s.signal for s in signals} == {"campaign_inactive"}

    def test_stale_sync_adds_risk(self):
        risk, signals = cp._score_engagement_risk("active", has_recent_sync=False)
        assert risk == 10
        assert {s.signal for s in signals} == {"stale_data"}

    def test_paused_plus_stale_caps_at_25(self):
        risk, _ = cp._score_engagement_risk("paused", has_recent_sync=False)
        assert risk == 25  # 15 + 10 capped at 25


# =============================================================================
# Interventions
# =============================================================================
class TestInterventions:
    def test_high_risk_creates_urgent_review_and_creative(self):
        signals = [
            ChurnSignal(
                signal="critical_roas",
                description="x",
                severity="critical",
                weight=0.35,
            ),
        ]
        interv = cp._generate_interventions(
            risk_score=75,
            signals=signals,
            roas=0.3,
            conversions=0,
            spend=200,
            platform="Meta",
        )
        actions = {i.action for i in interv}
        assert "urgent_review" in actions
        assert "creative_refresh" in actions
        assert "targeting_audit" in actions
        assert len(interv) <= 5

    def test_conversion_signal_is_auto_eligible(self):
        signals = [
            ChurnSignal(
                signal="zero_conversions",
                description="x",
                severity="critical",
                weight=0.2,
            ),
        ]
        interv = cp._generate_interventions(
            risk_score=30,
            signals=signals,
            roas=1.5,
            conversions=0,
            spend=200,
            platform="Meta",
        )
        audit = next(i for i in interv if i.action == "conversion_audit")
        assert audit.auto_eligible is True

    def test_stale_data_triggers_resync_with_platform_name(self):
        signals = [
            ChurnSignal(
                signal="stale_data", description="x", severity="medium", weight=0.1
            ),
        ]
        interv = cp._generate_interventions(
            risk_score=30,
            signals=signals,
            roas=2.0,
            conversions=10,
            spend=200,
            platform="TikTok",
        )
        resync = next(i for i in interv if i.action == "resync_platform")
        assert "TikTok" in resync.title

    def test_mid_risk_adds_proactive_outreach(self):
        # risk in [40,70) with no outreach signal -> proactive_checkup added
        signals = [
            ChurnSignal(
                signal="spend_declining", description="x", severity="high", weight=0.15
            ),
        ]
        interv = cp._generate_interventions(
            risk_score=45,
            signals=signals,
            roas=2.0,
            conversions=10,
            spend=100,
            platform="Meta",
        )
        assert any(i.action == "proactive_checkup" for i in interv)


# =============================================================================
# build_churn_prevention
# =============================================================================
class TestBuildChurnPrevention:
    def test_empty_is_healthy(self):
        resp = build_churn_prevention([])
        assert isinstance(resp, ChurnPreventionResponse)
        assert resp.portfolio_risk_level == "healthy"
        assert resp.retention_rate_pct == 100
        assert resp.total_campaigns_analyzed == 0

    def test_critical_and_healthy_mix(self):
        campaigns = [
            _campaign(
                id=1,
                name="Failing",
                spend=200,
                revenue=20,
                conversions=0,
                status="paused",
                has_recent_sync=False,
            ),
            _campaign(
                id=2,
                name="Winner",
                spend=1000,
                revenue=5000,
                conversions=100,
                status="active",
                has_recent_sync=True,
            ),
        ]
        resp = build_churn_prevention(campaigns)
        assert resp.total_campaigns_analyzed == 2
        assert resp.critical_count == 1
        assert resp.healthy_count == 1
        assert resp.retention_rate_pct == 50.0
        # only the risky one is surfaced (low-risk filtered out)
        assert len(resp.at_risk_campaigns) == 1
        assert resp.at_risk_campaigns[0].campaign_name == "Failing"
        assert resp.top_interventions
        assert any(i.action == "urgent_review" for i in resp.top_interventions)

    def test_all_healthy_summary(self):
        resp = build_churn_prevention(
            [_campaign(id=1, name="Good", spend=1000, revenue=5000, conversions=100)]
        )
        assert resp.at_risk_count == 0
        assert "healthy" in resp.summary.lower()
        assert resp.at_risk_campaigns == []

    def test_risk_campaigns_sorted_descending(self):
        campaigns = [
            _campaign(id=1, name="Mild", spend=100, revenue=120, conversions=10),
            _campaign(
                id=2,
                name="Severe",
                spend=300,
                revenue=15,
                conversions=0,
                status="paused",
                has_recent_sync=False,
            ),
        ]
        resp = build_churn_prevention(campaigns)
        scores = [c.risk_score for c in resp.at_risk_campaigns]
        assert scores == sorted(scores, reverse=True)


# =============================================================================
# Summary builder
# =============================================================================
class TestSummary:
    def test_summary_assembles_all_parts(self):
        interv = [
            Intervention(
                action="conversion_audit",
                title="t",
                description="d",
                priority="immediate",
                category="technical",
            ),
        ]
        s = cp._build_summary(
            total=5,
            at_risk=2,
            critical=1,
            healthy=3,
            retention_rate=60.0,
            portfolio_level="warning",
            top_interventions=interv,
        )
        assert "1 campaign at critical risk" in s
        assert "2 of 5 campaigns" in s
        assert "retention rate: 60%" in s
        assert "Warning:" in s
        assert "1 immediate intervention" in s

    def test_summary_all_healthy(self):
        s = cp._build_summary(
            total=3,
            at_risk=0,
            critical=0,
            healthy=3,
            retention_rate=100.0,
            portfolio_level="healthy",
            top_interventions=[],
        )
        assert "All 3 campaigns are healthy" in s
