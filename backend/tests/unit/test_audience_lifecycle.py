# =============================================================================
# Stratum AI - Audience Lifecycle unit tests
# =============================================================================
"""Unit tests for app.analytics.logic.audience_lifecycle.

Pure CDP lifecycle aggregation + rule/health logic, no I/O. Covers stage
analysis, transition detection, health assessment across all four levels, and
the build_audience_lifecycle entry point.
"""

import pytest

from app.analytics.logic import audience_lifecycle as al
from app.analytics.logic.audience_lifecycle import (
    AudienceLifecycleResponse,
    AudienceRule,
    LifecycleStageMetric,
    LifecycleTransition,
    build_audience_lifecycle,
)

pytestmark = pytest.mark.unit


def _stage(stage, count, pct, avg_rev=0.0):
    return LifecycleStageMetric(
        stage=stage,
        count=count,
        pct_of_total=pct,
        change_7d=0,
        change_pct=0.0,
        avg_revenue=avg_rev,
        avg_events=0.0,
    )


def _rule(i):
    return AudienceRule(
        rule_id=f"r{i}",
        name="n",
        description="d",
        trigger_stage="known",
        trigger_condition="enters_stage",
        action="sync_to_platform",
    )


def _trans(frm, to, positive, trend, c7=5, c30=20):
    return LifecycleTransition(
        from_stage=frm,
        to_stage=to,
        count_7d=c7,
        count_30d=c30,
        trend=trend,
        is_positive=positive,
    )


# =============================================================================
# Stage analysis
# =============================================================================
class TestAnalyzeStages:
    def test_distribution_and_averages(self):
        profiles = [
            {
                "lifecycle_stage": "customer",
                "total_revenue": 100,
                "total_events": 10,
                "is_recent": True,
            },
            {"lifecycle_stage": "customer", "total_revenue": 300, "total_events": 30},
            {"lifecycle_stage": "anonymous"},
        ]
        by = {m.stage: m for m in al._analyze_stages(profiles)}
        assert by["customer"].count == 2
        assert by["customer"].avg_revenue == 200.0
        assert by["customer"].avg_events == 20.0
        assert by["customer"].change_7d == 1  # one is_recent
        assert by["customer"].pct_of_total == pytest.approx(66.7, abs=0.1)

    def test_all_stages_present_even_when_empty(self):
        metrics = al._analyze_stages([{"lifecycle_stage": "anonymous"}])
        stages = {m.stage for m in metrics}
        assert stages == {"anonymous", "known", "customer", "churned"}
        by = {m.stage: m for m in metrics}
        assert by["known"].count == 0
        assert by["known"].avg_revenue == 0


# =============================================================================
# Transition detection
# =============================================================================
class TestDetectTransitions:
    def test_explicit_positive_transition(self):
        profiles = [
            {
                "lifecycle_stage": "known",
                "previous_stage": "anonymous",
                "is_recent": True,
            },
            {"lifecycle_stage": "customer", "previous_stage": "known"},
        ]
        trans = al._detect_transitions(profiles)
        ak = next(
            t for t in trans if (t.from_stage, t.to_stage) == ("anonymous", "known")
        )
        assert ak.is_positive is True
        assert ak.count_7d >= 1

    def test_negative_transition_flagged(self):
        profiles = [{"lifecycle_stage": "churned", "previous_stage": "customer"}]
        trans = al._detect_transitions(profiles)
        cc = next(
            (t for t in trans if (t.from_stage, t.to_stage) == ("customer", "churned")),
            None,
        )
        assert cc is not None
        assert cc.is_positive is False

    def test_sorted_by_recent_count_desc(self):
        profiles = [
            {
                "lifecycle_stage": "known",
                "previous_stage": "anonymous",
                "is_recent": True,
            },
            {
                "lifecycle_stage": "customer",
                "previous_stage": "known",
                "is_recent": True,
            },
            {"lifecycle_stage": "anonymous"},
        ]
        trans = al._detect_transitions(profiles)
        counts = [t.count_7d for t in trans]
        assert counts == sorted(counts, reverse=True)


# =============================================================================
# Health assessment
# =============================================================================
class TestAssessHealth:
    def test_needs_attention_anon_heavy_no_rules(self):
        stages = [_stage("anonymous", 80, 80.0), _stage("customer", 0, 0.0)]
        assert al._assess_health(stages, [], []) == "needs_attention"

    def test_poor_with_rising_negative_transition(self):
        stages = [_stage("anonymous", 80, 80.0), _stage("customer", 0, 0.0)]
        transitions = [_trans("customer", "churned", False, "increasing")]
        assert al._assess_health(stages, transitions, []) == "poor"

    def test_good_with_healthy_customer_share(self):
        stages = [_stage("anonymous", 50, 50.0), _stage("customer", 50, 50.0)]
        assert al._assess_health(stages, [], []) == "good"

    def test_excellent_with_customers_and_active_rules(self):
        stages = [
            _stage("anonymous", 50, 50.0),
            _stage("customer", 25, 25.0),
            _stage("known", 25, 25.0),
        ]
        rules = [_rule(i) for i in range(5)]
        assert al._assess_health(stages, [], rules) == "excellent"


# =============================================================================
# build_audience_lifecycle
# =============================================================================
class TestBuildLifecycle:
    def _profiles(self):
        return [
            {"lifecycle_stage": "anonymous", "is_recent": True},
            {"lifecycle_stage": "anonymous"},
            {
                "lifecycle_stage": "known",
                "previous_stage": "anonymous",
                "is_recent": True,
            },
            {
                "lifecycle_stage": "customer",
                "previous_stage": "known",
                "total_revenue": 500,
                "total_events": 20,
                "is_recent": True,
            },
            {"lifecycle_stage": "churned", "previous_stage": "customer"},
        ]

    def test_empty_profiles(self):
        resp = build_audience_lifecycle([])
        assert isinstance(resp, AudienceLifecycleResponse)
        assert resp.total_profiles == 0
        assert resp.total_rules == 0
        assert "No CDP profiles" in resp.summary

    def test_full_build_structure(self):
        resp = build_audience_lifecycle(
            self._profiles(),
            connected_platforms=["meta", "google"],
            existing_audiences=[{"platform": "meta"}],
        )
        assert resp.total_profiles == 5
        assert len(resp.stages) == 4
        assert resp.transitions
        assert resp.rules  # anon->known transition seeds platform rules
        # is_active defaults True, so all generated rules are active
        assert resp.active_rules == resp.total_rules
        # health re-computation is consistent with the response
        assert resp.lifecycle_health in {"excellent", "good", "needs_attention", "poor"}
        assert (
            al._assess_health(resp.stages, resp.transitions, resp.rules)
            == resp.lifecycle_health
        )

    def test_sync_readiness_reflects_existing_audiences(self):
        resp = build_audience_lifecycle(
            self._profiles(),
            connected_platforms=["meta", "google"],
            existing_audiences=[{"platform": "meta"}],
        )
        readiness = {s.platform: s for s in resp.sync_readiness}
        assert set(readiness) == {"meta", "google"}
        assert readiness["meta"].audiences_count == 1
        assert readiness["meta"].auto_sync_enabled is True
        assert readiness["google"].audiences_count == 0
        assert readiness["google"].auto_sync_enabled is False

    def test_no_platforms_no_sync_readiness(self):
        resp = build_audience_lifecycle(self._profiles())
        assert resp.sync_readiness == []

    def test_summary_mentions_profile_count(self):
        resp = build_audience_lifecycle(self._profiles(), connected_platforms=["meta"])
        assert "5 profiles" in resp.summary
        assert "lifecycle stages" in resp.summary
