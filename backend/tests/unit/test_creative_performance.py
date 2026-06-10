# =============================================================================
# Stratum AI - Creative Performance Service unit tests
# =============================================================================
"""Unit tests for app.services.creative_performance_service.

Pure in-memory creative tracking + analytics, no I/O. Covers
CreativeMetrics derivation, the CreativePerformanceService lifecycle
(register/record/fatigue/compare/top/summary), the element analyzer,
lifecycle predictor, and the cross-platform analyzer — including
regression tests for the cvr / _creatives / daily_metrics attribute
fixes and the empty-ROAS StatisticsError guards.
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.services.creative_performance_service import (
    CreativeElement,
    CreativeElementAnalyzer,
    CreativeLifecyclePredictor,
    CreativeMetrics,
    CreativePerformanceService,
    CreativeStatus,
    CreativeType,
    CrossPlatformCreativeAnalyzer,
    FatigueLevel,
    creative_service,
    record_creative_metrics,
)

pytestmark = pytest.mark.unit


def _now():
    return datetime.now(timezone.utc)


def _metrics(
    impressions=1000, clicks=50, conversions=5, spend=100.0, revenue=500.0, **kwargs
):
    return CreativeMetrics(
        impressions=impressions,
        clicks=clicks,
        conversions=conversions,
        spend=spend,
        revenue=revenue,
        **kwargs,
    )


# =============================================================================
# CreativeMetrics.calculate_derived
# =============================================================================
class TestCalculateDerived:
    def test_full_derivation(self):
        m = _metrics(video_views=100, video_completions=25)
        m.calculate_derived()
        assert m.ctr == 5.0  # 50/1000 * 100
        assert m.cvr == 10.0  # 5/50 * 100
        assert m.roas == 5.0  # 500/100
        assert m.cpc == 2.0  # 100/50
        assert m.cpm == 100.0  # 100/1000 * 1000
        assert m.cpa == 20.0  # 100/5
        assert m.video_completion_rate == 25.0

    def test_zero_division_guards(self):
        m = CreativeMetrics()
        m.calculate_derived()
        assert m.ctr == m.cvr == m.roas == m.cpc == m.cpm == m.cpa == 0.0


# =============================================================================
# Service: register / record
# =============================================================================
class TestRegisterAndRecord:
    def test_register_indexes_creative(self):
        svc = CreativePerformanceService()
        svc.register_creative("c1", "t1", "meta", "camp1", name="Hero")
        assert svc.get_creative("c1").name == "Hero"
        assert [c.creative_id for c in svc.get_creatives_for_campaign("camp1")] == [
            "c1"
        ]

    def test_record_auto_registers(self):
        svc = CreativePerformanceService()
        svc.record_metrics("c1", "t1", "meta", "camp1", _metrics())
        creative = svc.get_creative("c1")
        assert creative is not None
        assert creative.lifetime_metrics.impressions == 1000

    def test_lifetime_accumulates(self):
        svc = CreativePerformanceService()
        svc.record_metrics("c1", "t1", "meta", "camp1", _metrics())
        svc.record_metrics("c1", "t1", "meta", "camp1", _metrics())
        lifetime = svc.get_creative("c1").lifetime_metrics
        assert lifetime.impressions == 2000
        assert lifetime.spend == 200.0
        assert lifetime.roas == 5.0  # 1000/200

    def test_days_active_from_first_impression(self):
        svc = CreativePerformanceService()
        first = _now() - timedelta(days=9)
        svc.record_metrics("c1", "t1", "meta", "camp1", _metrics(), date=first)
        svc.record_metrics("c1", "t1", "meta", "camp1", _metrics(), date=_now())
        creative = svc.get_creative("c1")
        assert creative.first_impression_at == first
        assert creative.days_active == 10

    def test_unknown_creative_lookups(self):
        svc = CreativePerformanceService()
        assert svc.get_creative("missing") is None
        assert svc.get_creatives_for_campaign("missing") == []


# =============================================================================
# Fatigue detection
# =============================================================================
def _record_decline(svc, creative_id, start, high_days=7, low_days=7):
    """Record a CTR/ROAS collapse: high first half, low second half."""
    day = start
    for _ in range(high_days):
        svc.record_metrics(
            creative_id,
            "t1",
            "meta",
            "camp1",
            _metrics(clicks=50, revenue=500.0),
            date=day,
        )
        day += timedelta(days=1)
    for _ in range(low_days):
        svc.record_metrics(
            creative_id,
            "t1",
            "meta",
            "camp1",
            _metrics(clicks=10, revenue=100.0),
            date=day,
        )
        day += timedelta(days=1)


class TestFatigue:
    def test_under_seven_days_no_fatigue(self):
        svc = CreativePerformanceService()
        for i in range(5):
            svc.record_metrics(
                "c1",
                "t1",
                "meta",
                "camp1",
                _metrics(),
                date=_now() - timedelta(days=5 - i),
            )
        creative = svc.get_creative("c1")
        assert creative.fatigue_level == FatigueLevel.NONE
        assert creative.fatigue_score == 0.0

    def test_stable_metrics_no_fatigue(self):
        svc = CreativePerformanceService()
        for i in range(14):
            svc.record_metrics(
                "c1",
                "t1",
                "meta",
                "camp1",
                _metrics(),
                date=_now() - timedelta(days=14 - i),
            )
        assert svc.get_creative("c1").fatigue_level == FatigueLevel.NONE

    def test_collapse_within_two_weeks_is_high(self):
        svc = CreativePerformanceService()
        # 80% CTR decline (+30 capped) + 80% ROAS decline (+40 capped) = 70 -> HIGH
        _record_decline(svc, "c1", _now() - timedelta(days=13))
        creative = svc.get_creative("c1")
        assert creative.fatigue_level == FatigueLevel.HIGH
        assert creative.fatigue_score == 70.0
        assert creative.status == CreativeStatus.ACTIVE

    def test_old_collapsing_creative_is_critical(self):
        svc = CreativePerformanceService()
        # same collapse but spread over ~70 days -> +20 age factor -> 90
        first = _now() - timedelta(days=69)
        for i in range(7):  # high weeks
            svc.record_metrics(
                "c1",
                "t1",
                "meta",
                "camp1",
                _metrics(clicks=50, revenue=500.0),
                date=first + timedelta(days=i * 9),
            )
        for i in range(7):  # recent low week
            svc.record_metrics(
                "c1",
                "t1",
                "meta",
                "camp1",
                _metrics(clicks=10, revenue=100.0),
                date=_now() - timedelta(days=6 - i),
            )
        creative = svc.get_creative("c1")
        assert creative.fatigue_level == FatigueLevel.CRITICAL
        assert creative.status == CreativeStatus.FATIGUED

    def test_analyze_fatigue_unknown_returns_none(self):
        assert CreativePerformanceService().analyze_fatigue("ghost") is None

    def test_analyze_fatigue_recommendations(self):
        svc = CreativePerformanceService()
        _record_decline(svc, "c1", _now() - timedelta(days=13))
        analysis = svc.analyze_fatigue("c1")
        assert analysis.fatigue_level == FatigueLevel.HIGH
        assert "refresh within 1 week" in analysis.recommendation
        assert set(analysis.trend_data) == {"ctr", "roas", "cpm"}
        assert len(analysis.trend_data["ctr"]) == 14

    def test_healthy_creative_no_action(self):
        svc = CreativePerformanceService()
        svc.record_metrics("c1", "t1", "meta", "camp1", _metrics())
        analysis = svc.analyze_fatigue("c1")
        assert analysis.recommendation == "No action needed"


# =============================================================================
# Comparison
# =============================================================================
class TestCompareCreatives:
    def _seed(self, svc, creative_id, base_roas):
        # 7 recent daily entries with slight variance (t-test needs variance)
        for i in range(7):
            revenue = 100.0 * (base_roas + (i - 3) * 0.05)
            svc.record_metrics(
                creative_id,
                "t1",
                "meta",
                "camp1",
                _metrics(spend=100.0, revenue=revenue),
                date=_now() - timedelta(days=6 - i),
            )

    def test_requires_two_known_creatives(self):
        svc = CreativePerformanceService()
        svc.record_metrics("c1", "t1", "meta", "camp1", _metrics())
        assert svc.compare_creatives(["c1"]) is None
        assert svc.compare_creatives(["c1", "ghost"]) is None

    def test_roas_winner_with_significance(self):
        svc = CreativePerformanceService()
        self._seed(svc, "winner", 5.0)
        self._seed(svc, "loser", 1.0)
        comparison = svc.compare_creatives(["winner", "loser"], metric="roas")
        assert comparison.winner_id == "winner"
        assert bool(comparison.statistical_significance) is True
        assert comparison.confidence_level > 95
        assert comparison.metrics_comparison["winner"]["roas"] == 5.0

    def test_cpa_lower_is_better(self):
        svc = CreativePerformanceService()
        # cheap: cpa 10; expensive: cpa 50
        svc.record_metrics(
            "cheap", "t1", "meta", "camp1", _metrics(conversions=10, spend=100.0)
        )
        svc.record_metrics(
            "expensive", "t1", "meta", "camp1", _metrics(conversions=2, spend=100.0)
        )
        comparison = svc.compare_creatives(["cheap", "expensive"], metric="cpa")
        assert comparison.winner_id == "cheap"


# =============================================================================
# Top creatives / type performance / summary
# =============================================================================
class TestAggregations:
    def _two_creatives(self, svc):
        svc.record_metrics(
            "hi", "t1", "meta", "camp1", _metrics(revenue=1000.0)
        )  # roas 10
        svc.record_metrics(
            "lo",
            "t1",
            "google",
            "camp2",
            _metrics(revenue=200.0),
            creative_type=CreativeType.VIDEO,
        )  # roas 2

    def test_top_creatives_sorted_and_limited(self):
        svc = CreativePerformanceService()
        self._two_creatives(svc)
        top = svc.get_top_creatives(metric="roas")
        assert [t["creative_id"] for t in top] == ["hi", "lo"]
        assert top[0]["metrics"]["roas"] == 10.0
        assert len(svc.get_top_creatives(limit=1)) == 1

    def test_top_creatives_filters(self):
        svc = CreativePerformanceService()
        self._two_creatives(svc)
        assert [t["creative_id"] for t in svc.get_top_creatives(platform="google")] == [
            "lo"
        ]
        assert svc.get_top_creatives(tenant_id="other") == []

    def test_type_performance_grouped(self):
        svc = CreativePerformanceService()
        self._two_creatives(svc)
        by_type = svc.get_creative_type_performance()
        assert set(by_type) == {"image", "video"}
        assert by_type["image"]["roas"] == 10.0
        assert by_type["video"]["creative_count"] == 1

    def test_summary_counts(self):
        svc = CreativePerformanceService()
        self._two_creatives(svc)
        summary = svc.get_summary()
        assert summary["total_creatives"] == 2
        assert summary["by_platform"] == {"meta": 1, "google": 1}
        assert summary["needs_attention"] == 0

    def test_fatigued_creatives_filter_and_sort(self):
        svc = CreativePerformanceService()
        _record_decline(svc, "tired", _now() - timedelta(days=13))  # HIGH
        svc.record_metrics("fresh", "t1", "meta", "camp1", _metrics())  # NONE
        fatigued = svc.get_fatigued_creatives(min_fatigue_level=FatigueLevel.MEDIUM)
        assert [f["creative_id"] for f in fatigued] == ["tired"]
        # NONE-level threshold includes everything, highest score first
        all_levels = svc.get_fatigued_creatives(min_fatigue_level=FatigueLevel.NONE)
        assert all_levels[0]["creative_id"] == "tired"


# =============================================================================
# Convenience singleton wrapper
# =============================================================================
class TestConvenience:
    def test_record_creative_metrics_singleton(self):
        record_creative_metrics(
            creative_id="ut_cp_conv_1",
            tenant_id="ut_cp_tenant",
            platform="meta",
            campaign_id="ut_cp_camp",
            impressions=1000,
            clicks=50,
            conversions=5,
            spend=100.0,
            revenue=300.0,
        )
        creative = creative_service.get_creative("ut_cp_conv_1")
        assert creative is not None
        assert creative.lifetime_metrics.roas == 3.0


# =============================================================================
# CreativeElementAnalyzer (regression: metrics.cvr, empty-ROAS guard)
# =============================================================================
class TestElementAnalyzer:
    def _record(self, analyzer, content, element_type="headline", **metric_kwargs):
        m = _metrics(**metric_kwargs)
        m.calculate_derived()
        analyzer.record_element_performance(
            "c1", CreativeElement(element_type=element_type, content=content), m
        )

    def test_record_uses_cvr_field(self):
        # Regression: used to read metrics.conversion_rate (AttributeError)
        analyzer = CreativeElementAnalyzer()
        self._record(analyzer, "Buy now?")
        stored = analyzer._element_performance["headline"]["headline:Buy now?"][0]
        assert stored["conversion_rate"] == 10.0  # cvr

    def test_empty_type_insufficient_data(self):
        analysis = CreativeElementAnalyzer().analyze_element_type("headline")
        assert analysis.top_performers == []
        assert analysis.recommendations == ["Insufficient data for analysis"]

    def test_min_impressions_filter(self):
        analyzer = CreativeElementAnalyzer()
        self._record(analyzer, "Tiny", impressions=10, clicks=1)
        analysis = analyzer.analyze_element_type("headline", min_impressions=1000)
        assert analysis.top_performers == []
        assert analysis.recommendations == [
            "Collect more data to analyze element performance"
        ]

    def test_headline_recommendations(self):
        analyzer = CreativeElementAnalyzer()
        self._record(analyzer, "Want a better ROAS today?", impressions=5000)
        analysis = analyzer.analyze_element_type("headline")
        assert len(analysis.top_performers) == 1
        assert any("headline length" in r for r in analysis.recommendations)
        assert any("Questions" in r for r in analysis.recommendations)

    def test_cta_recommendations(self):
        analyzer = CreativeElementAnalyzer()
        self._record(
            analyzer, "Shop Now - Free Shipping", element_type="cta", impressions=5000
        )
        analysis = analyzer.analyze_element_type("cta")
        recs = " ".join(analysis.recommendations)
        assert "Now" in recs
        assert "Free" in recs

    def test_zero_roas_does_not_crash(self):
        # Regression: all-zero ROAS used to raise StatisticsError
        analyzer = CreativeElementAnalyzer()
        self._record(analyzer, "No revenue yet", impressions=5000, revenue=0.0)
        analysis = analyzer.analyze_element_type("headline")
        assert analysis.top_performers[0]["avg_roas"] == 0.0


# =============================================================================
# CreativeLifecyclePredictor
# =============================================================================
class TestLifecyclePredictor:
    def test_no_history_unknown(self):
        prediction = CreativeLifecyclePredictor().predict("ghost")
        assert prediction.current_phase == "unknown"
        assert prediction.predicted_next_phase == "learning"
        assert prediction.confidence == 0.0

    def test_new_creative_learning_phase(self):
        predictor = CreativeLifecyclePredictor()
        m = _metrics()
        m.calculate_derived()
        predictor.record_metrics("c1", m)
        prediction = predictor.predict("c1")
        assert prediction.current_phase == "learning"
        assert prediction.predicted_next_phase == "growth"

    @pytest.mark.parametrize(
        "age,current_ctr,historical_ctr,expected",
        [
            (2, 5.0, 5.0, "learning"),
            (20, 1.0, 5.0, "fatigue"),  # -80%
            (20, 4.4, 5.0, "decline"),  # -12%
            (10, 5.5, 5.0, "growth"),  # +10%, age <= 14
            (20, 5.0, 5.0, "maturity"),  # stable
        ],
    )
    def test_phase_determination(self, age, current_ctr, historical_ctr, expected):
        predictor = CreativeLifecyclePredictor()
        phase, factors = predictor._determine_phase(
            age, current_ctr, historical_ctr, []
        )
        assert phase == expected
        assert factors

    def test_transition_map(self):
        predictor = CreativeLifecyclePredictor()
        assert predictor._predict_transition("learning", 1, 5.0, 5.0)[0] == "growth"
        next_phase, change_days, _conf = predictor._predict_transition(
            "fatigue", 50, 1.0, 5.0
        )
        assert next_phase == "fatigue"  # terminal
        assert change_days == 0

    def test_days_in_phase(self):
        predictor = CreativeLifecyclePredictor()
        history = [(_now() - timedelta(days=20), CreativeMetrics())]
        assert predictor._calculate_days_in_phase(history, "maturity") == 6  # 20 - 14
        assert predictor._calculate_days_in_phase([], "maturity") == 0


# =============================================================================
# CrossPlatformCreativeAnalyzer (regression: _creatives / daily_metrics)
# =============================================================================
class TestCrossPlatformAnalyzer:
    def _seed_platform(self, svc, creative_id, platform, roas, cvr_clicks=100):
        svc.record_metrics(
            creative_id,
            "t1",
            platform,
            "camp1",
            _metrics(
                clicks=cvr_clicks, conversions=10, spend=100.0, revenue=roas * 100.0
            ),
        )

    def test_single_platform_insufficient(self):
        svc = CreativePerformanceService()
        self._seed_platform(svc, "promo_meta", "meta", roas=5.0)
        analyzer = CrossPlatformCreativeAnalyzer(svc)
        insights = analyzer.analyze_creative_across_platforms("promo", "t1")
        assert insights[0].insight_type == "insufficient_data"

    def test_performance_gap_detected(self):
        # Regression: used to crash on service._creative_data / metrics_history
        svc = CreativePerformanceService()
        self._seed_platform(svc, "promo_meta", "meta", roas=10.0)
        self._seed_platform(svc, "promo_google", "google", roas=2.0)
        analyzer = CrossPlatformCreativeAnalyzer(svc)
        insights = analyzer.analyze_creative_across_platforms("promo", "t1")
        gap = next(i for i in insights if i.insight_type == "performance_gap")
        assert set(gap.platforms) == {"meta", "google"}
        assert "outperforms" in gap.description

    def test_universal_performer(self):
        svc = CreativePerformanceService()
        self._seed_platform(svc, "promo_meta", "meta", roas=5.0)
        self._seed_platform(svc, "promo_google", "google", roas=5.5)
        analyzer = CrossPlatformCreativeAnalyzer(svc)
        insights = analyzer.analyze_creative_across_platforms("promo", "t1")
        assert any(i.insight_type == "universal_performer" for i in insights)

    def test_tenant_isolation(self):
        svc = CreativePerformanceService()
        self._seed_platform(svc, "promo_meta", "meta", roas=5.0)
        analyzer = CrossPlatformCreativeAnalyzer(svc)
        insights = analyzer.analyze_creative_across_platforms("promo", "other_tenant")
        assert insights[0].insight_type == "insufficient_data"
        assert insights[0].platforms == []

    def test_platform_recommendations(self):
        # Regression: used to crash on _creative_data / metrics_history
        svc = CreativePerformanceService()
        # meta: ctr 0.5% (<1) and roas 1 (<2) -> both meta recommendations
        svc.record_metrics(
            "weak_meta",
            "t1",
            "meta",
            "camp1",
            _metrics(impressions=10000, clicks=50, spend=100.0, revenue=100.0),
        )
        analyzer = CrossPlatformCreativeAnalyzer(svc)
        recs = analyzer.get_platform_creative_recommendations("t1")
        assert len(recs["meta"]) == 2
        assert any("headlines" in r for r in recs["meta"])

    def test_strong_platform_keeps_strategy(self):
        svc = CreativePerformanceService()
        self._seed_platform(svc, "strong_meta", "meta", roas=5.0, cvr_clicks=200)
        analyzer = CrossPlatformCreativeAnalyzer(svc)
        recs = analyzer.get_platform_creative_recommendations("t1")
        assert recs["meta"] == ["Performance is strong - continue current strategy"]
