# =============================================================================
# Stratum AI - Audience Insights Service unit tests
# =============================================================================
"""Unit tests for app.services.audience_insights_service.

Pure in-memory predictive audience analytics, no I/O. Covers metric
derivation, quality scoring, expansion-potential analysis, ROAS
prediction, insights/recommendations generation, performance prediction,
overlap estimation, and the P2 enhancement predictors (LTV, decay,
clustering).
"""

import pytest

from app.services.audience_insights_service import (
    AudienceClusterAnalyzer,
    AudienceDecayPredictor,
    AudienceInsightsService,
    AudienceLTVPredictor,
    AudienceMetrics,
    AudienceQuality,
    AudienceType,
    ExpansionPotential,
    predict_audience_performance,
)

pytestmark = pytest.mark.unit


def _excellent_metrics(**overrides):
    """roas 3 (40) + cvr 5 (25) + ctr 2 (20) + cpa 50 (15) = quality 100."""
    values = dict(
        reach=5000,
        impressions=10000,
        clicks=200,
        conversions=10,
        spend=500.0,
        revenue=1500.0,
    )
    values.update(overrides)
    return AudienceMetrics(**values)


def _register(svc, audience_id="a1", tenant_id="t1", **kwargs):
    defaults = dict(
        platform="meta",
        name="Test Audience",
        audience_type=AudienceType.CUSTOM,
        size=100000,
    )
    defaults.update(kwargs)
    return svc.register_audience(audience_id, tenant_id, **defaults)


# =============================================================================
# AudienceMetrics.calculate_derived
# =============================================================================
class TestMetricsDerivation:
    def test_full_derivation(self):
        m = _excellent_metrics()
        m.calculate_derived()
        assert m.ctr == 2.0
        assert m.cvr == 5.0
        assert m.roas == 3.0
        assert m.cpm == 50.0
        assert m.cpa == 50.0
        assert m.frequency == 2.0  # 10000/5000
        assert m.unique_reach_percent == 50.0

    def test_zero_division_guards(self):
        m = AudienceMetrics()
        m.calculate_derived()
        assert m.ctr == m.cvr == m.roas == m.cpm == m.cpa == m.frequency == 0.0


# =============================================================================
# Register / update / quality scoring
# =============================================================================
class TestQualityScoring:
    def test_register_and_lookup(self):
        svc = AudienceInsightsService()
        _register(svc)
        assert svc.get_audience("a1").name == "Test Audience"
        assert svc.get_audience("missing") is None

    def test_update_unknown_is_noop(self):
        svc = AudienceInsightsService()
        svc.update_metrics("ghost", AudienceMetrics())  # must not raise

    def test_perfect_metrics_excellent(self):
        svc = AudienceInsightsService()
        _register(svc)
        svc.update_metrics("a1", _excellent_metrics())
        audience = svc.get_audience("a1")
        assert audience.quality_score == 100.0
        assert audience.quality == AudienceQuality.EXCELLENT

    def test_weak_metrics_poor(self):
        svc = AudienceInsightsService()
        _register(svc)
        svc.update_metrics(
            "a1",
            AudienceMetrics(impressions=1000, clicks=1, spend=100.0),
        )
        audience = svc.get_audience("a1")
        assert audience.quality == AudienceQuality.POOR
        assert audience.quality_score < 40

    @pytest.mark.parametrize(
        "conversions,spend,expected",
        [
            (100, 1000.0, 1.0),
            (30, 500.0, 0.82),
            (10, 100.0, 0.64),
            (0, 0.0, 0.38),
        ],
    )
    def test_confidence_tiers(self, conversions, spend, expected):
        svc = AudienceInsightsService()
        audience = _register(svc)
        audience.metrics = AudienceMetrics(conversions=conversions, spend=spend)
        assert svc._calculate_confidence(audience) == expected


# =============================================================================
# Expansion potential
# =============================================================================
class TestExpansionPotential:
    def _analyzed(self, svc, metrics=None, **register_kwargs):
        audience = _register(svc, **register_kwargs)
        if metrics is not None:
            audience.metrics = metrics
        return svc._analyze_expansion_potential(audience)

    def test_high_frequency_saturated(self):
        svc = AudienceInsightsService()
        m = AudienceMetrics(reach=100, impressions=1100)
        m.calculate_derived()  # frequency 11
        assert self._analyzed(svc, m) == ExpansionPotential.SATURATED

    def test_moderate_frequency_low(self):
        svc = AudienceInsightsService()
        m = AudienceMetrics(reach=100, impressions=600)
        m.calculate_derived()  # frequency 6
        assert self._analyzed(svc, m) == ExpansionPotential.LOW

    @pytest.mark.parametrize(
        "reach,expected",
        [
            (60000, ExpansionPotential.LOW),  # penetration 0.6
            (30000, ExpansionPotential.MEDIUM),  # 0.3
            (10000, ExpansionPotential.HIGH),  # 0.1
        ],
    )
    def test_penetration_tiers(self, reach, expected):
        svc = AudienceInsightsService()
        m = AudienceMetrics(reach=reach, impressions=reach * 2)  # frequency 2
        m.calculate_derived()
        assert self._analyzed(svc, m, size=100000) == expected

    @pytest.mark.parametrize(
        "audience_type,kwargs,expected",
        [
            (AudienceType.RETARGETING, {}, ExpansionPotential.LOW),
            (
                AudienceType.LOOKALIKE,
                {"lookalike_percent": 2.0},
                ExpansionPotential.HIGH,
            ),
            (
                AudienceType.LOOKALIKE,
                {"lookalike_percent": 7.0},
                ExpansionPotential.MEDIUM,
            ),
            (AudienceType.BROAD, {}, ExpansionPotential.HIGH),
            (AudienceType.INTEREST, {}, ExpansionPotential.MEDIUM),
        ],
    )
    def test_type_defaults_without_reach(self, audience_type, kwargs, expected):
        svc = AudienceInsightsService()
        assert self._analyzed(svc, audience_type=audience_type, **kwargs) == expected


# =============================================================================
# ROAS prediction
# =============================================================================
class TestPredictRoas:
    def test_retargeting_multiplier_on_default_roas(self):
        svc = AudienceInsightsService()
        audience = _register(svc, audience_type=AudienceType.RETARGETING)
        audience.expansion_potential = ExpansionPotential.MEDIUM
        assert svc._predict_audience_roas(audience) == 1.3

    def test_wide_lookalike_penalty(self):
        svc = AudienceInsightsService()
        audience = _register(
            svc, audience_type=AudienceType.LOOKALIKE, lookalike_percent=8.0
        )
        audience.expansion_potential = ExpansionPotential.MEDIUM
        assert svc._predict_audience_roas(audience) == 0.99  # 1.1 * 0.9

    def test_saturation_discount_applied(self):
        svc = AudienceInsightsService()
        audience = _register(svc, audience_type=AudienceType.RETARGETING)
        audience.metrics = AudienceMetrics(spend=100.0, revenue=200.0)
        audience.metrics.calculate_derived()  # roas 2
        audience.expansion_potential = ExpansionPotential.SATURATED
        assert svc._predict_audience_roas(audience) == 2.21  # 2 * 1.3 * 0.85


# =============================================================================
# Insights
# =============================================================================
class TestInsights:
    def test_unknown_audience_empty(self):
        assert AudienceInsightsService().get_insights("ghost") == []

    def test_critical_saturation_insight(self):
        svc = AudienceInsightsService()
        _register(svc)
        svc.update_metrics("a1", _excellent_metrics(reach=1000, impressions=9000))
        insights = svc.get_insights("a1")
        saturation = next(i for i in insights if i.insight_type == "saturation")
        assert saturation.severity == "critical"
        assert "fatigue" in saturation.description

    def test_warning_saturation_insight(self):
        svc = AudienceInsightsService()
        _register(svc)
        svc.update_metrics("a1", _excellent_metrics(reach=1500, impressions=9000))
        saturation = next(
            i for i in svc.get_insights("a1") if i.insight_type == "saturation"
        )
        assert saturation.severity == "warning"

    def test_excellent_performance_insight(self):
        svc = AudienceInsightsService()
        _register(svc)
        svc.update_metrics("a1", _excellent_metrics())
        performance = next(
            i for i in svc.get_insights("a1") if i.insight_type == "performance"
        )
        assert performance.severity == "info"
        assert "Top Performing" in performance.title

    def test_poor_performance_insight(self):
        svc = AudienceInsightsService()
        _register(svc)
        svc.update_metrics(
            "a1", AudienceMetrics(impressions=1000, clicks=1, spend=100.0)
        )
        performance = next(
            i for i in svc.get_insights("a1") if i.insight_type == "performance"
        )
        assert performance.severity == "critical"

    def test_wide_lookalike_targeting_insight(self):
        svc = AudienceInsightsService()
        _register(svc, audience_type=AudienceType.LOOKALIKE, lookalike_percent=8.0)
        targeting = next(
            i for i in svc.get_insights("a1") if i.insight_type == "targeting"
        )
        assert "8.0% lookalike" in targeting.description

    def test_high_expansion_insight(self):
        svc = AudienceInsightsService()
        _register(svc, audience_type=AudienceType.BROAD)
        svc.update_metrics("a1", AudienceMetrics(spend=10.0, revenue=20.0))
        expansion = next(
            i for i in svc.get_insights("a1") if i.insight_type == "expansion"
        )
        assert "budget" in expansion.description


# =============================================================================
# Recommendations
# =============================================================================
class TestRecommendations:
    def test_lookalike_from_top_custom_audience(self):
        svc = AudienceInsightsService()
        _register(svc, "top", audience_type=AudienceType.CUSTOM)
        svc.update_metrics("top", _excellent_metrics())
        recs = svc.get_recommendations("t1")
        lookalike = next(r for r in recs if r.action == "create_lookalike")
        assert lookalike.audience_id == "top"
        assert lookalike.priority == "high"
        assert lookalike.expected_impact["reach_multiplier"] == 10

    def test_pause_poor_performer(self):
        svc = AudienceInsightsService()
        _register(svc, "weak")
        svc.update_metrics(
            "weak", AudienceMetrics(impressions=1000, clicks=1, spend=100.0)
        )
        recs = svc.get_recommendations("t1")
        pause = next(r for r in recs if r.action == "pause")
        assert pause.audience_id == "weak"
        assert pause.expected_impact["budget_saved"] == 50.0

    def test_expand_high_potential_performer(self):
        svc = AudienceInsightsService()
        _register(svc, "grow", audience_type=AudienceType.INTEREST)
        svc.update_metrics("grow", _excellent_metrics())  # penetration 0.05 -> HIGH
        recs = svc.get_recommendations("t1")
        expand = next(r for r in recs if r.action == "expand")
        assert expand.audience_id == "grow"
        assert expand.priority == "medium"

    def test_empty_tenant_gets_test_fallback(self):
        recs = AudienceInsightsService().get_recommendations("nobody")
        assert len(recs) == 1
        assert recs[0].action == "test"
        assert recs[0].audience_id is None

    def test_limit_respected(self):
        svc = AudienceInsightsService()
        for i in range(5):
            _register(svc, f"a{i}")
            svc.update_metrics(f"a{i}", _excellent_metrics())
        assert len(svc.get_recommendations("t1", limit=2)) == 2


# =============================================================================
# Performance prediction
# =============================================================================
class TestPredictPerformance:
    def test_meta_retargeting_math(self):
        svc = AudienceInsightsService()
        result = svc.predict_performance(
            audience_type=AudienceType.RETARGETING,
            size=1_000_000,
            platform="meta",
            budget=100.0,
        )
        p = result["predictions"]
        assert p["impressions"] == 8333  # 100/12 * 1000
        assert p["clicks"] == 250  # 8333.33 * 3%
        assert p["conversions"] == 12  # 250 * 5%
        assert p["roas"] == 10.0  # 12.5 * $80 / $100
        assert p["reach"] == 2083  # impressions / 4
        assert result["confidence"] == 0.7  # size > 100k

    def test_reach_capped_by_size(self):
        svc = AudienceInsightsService()
        result = svc.predict_performance(
            audience_type=AudienceType.BROAD,
            size=500,
            platform="meta",
            budget=100.0,
        )
        assert result["predictions"]["reach"] == 500
        assert result["confidence"] == 0.5

    def test_tight_lookalike_boost(self):
        svc = AudienceInsightsService()
        result = svc.predict_performance(
            audience_type=AudienceType.LOOKALIKE,
            size=1_000_000,
            platform="meta",
            budget=100.0,
            lookalike_percent=1.0,
        )
        p = result["predictions"]
        assert p["ctr"] == 2.4  # 2.0 * 1.2
        assert p["cvr"] == 3.9  # 3.0 * 1.3

    def test_unknown_platform_uses_default_cpm(self):
        svc = AudienceInsightsService()
        result = svc.predict_performance(
            audience_type=AudienceType.INTEREST,
            size=1_000_000,
            platform="pinterest",
            budget=120.0,
        )
        assert result["predictions"]["impressions"] == 10000  # 120/12 * 1000

    def test_convenience_wrapper_invalid_type_falls_back(self):
        result = predict_audience_performance(
            audience_type="not_a_type",
            size=1_000_000,
            platform="meta",
            budget=100.0,
        )
        assert result["audience_type"] == "interest"


# =============================================================================
# Overlap detection
# =============================================================================
class TestOverlap:
    def _pair(self, svc, type1, type2, **kwargs1):
        _register(svc, "x", audience_type=type1, **kwargs1)
        _register(svc, "y", audience_type=type2)
        return svc.detect_overlap(["x", "y"])[0]

    def test_missing_audiences_skipped(self):
        svc = AudienceInsightsService()
        _register(svc, "x")
        assert svc.detect_overlap(["x", "ghost"]) == []

    def test_same_retargeting_very_high(self):
        svc = AudienceInsightsService()
        overlap = self._pair(svc, AudienceType.RETARGETING, AudienceType.RETARGETING)
        assert overlap.overlap_percent == 60.0
        assert "combining" in overlap.recommendation

    def test_lookalikes_same_source(self):
        svc = AudienceInsightsService()
        _register(
            svc, "x", audience_type=AudienceType.LOOKALIKE, source_audience_id="seed"
        )
        _register(
            svc, "y", audience_type=AudienceType.LOOKALIKE, source_audience_id="seed"
        )
        assert svc.detect_overlap(["x", "y"])[0].overlap_percent == 50.0

    def test_similar_pair_interest_behavioral(self):
        svc = AudienceInsightsService()
        overlap = self._pair(svc, AudienceType.INTEREST, AudienceType.BEHAVIORAL)
        assert overlap.overlap_percent == 25.0

    def test_retargeting_vs_other(self):
        svc = AudienceInsightsService()
        overlap = self._pair(svc, AudienceType.RETARGETING, AudienceType.CUSTOM)
        assert overlap.overlap_percent == 15.0
        assert "Monitor" in overlap.recommendation

    def test_default_low_overlap(self):
        svc = AudienceInsightsService()
        overlap = self._pair(svc, AudienceType.INTEREST, AudienceType.BROAD)
        assert overlap.overlap_percent == 10.0
        assert "safe to run" in overlap.recommendation

    def test_overlap_size_from_smaller_audience(self):
        svc = AudienceInsightsService()
        _register(svc, "x", audience_type=AudienceType.RETARGETING, size=1000)
        _register(svc, "y", audience_type=AudienceType.RETARGETING, size=50000)
        assert svc.detect_overlap(["x", "y"])[0].overlap_size == 600  # 1000 * 60%


# =============================================================================
# Summary
# =============================================================================
class TestSummary:
    def test_summary_aggregates(self):
        svc = AudienceInsightsService()
        _register(svc, "a1", audience_type=AudienceType.CUSTOM)
        svc.update_metrics("a1", _excellent_metrics())
        _register(svc, "a2", audience_type=AudienceType.BROAD)
        svc.update_metrics("a2", AudienceMetrics(spend=500.0, revenue=500.0))
        summary = svc.get_summary("t1")
        assert summary["total_audiences"] == 2
        assert summary["by_type"] == {"custom": 1, "broad": 1}
        assert summary["total_spend"] == 1000.0
        assert summary["overall_roas"] == 2.0  # 2000/1000

    def test_empty_tenant(self):
        summary = AudienceInsightsService().get_summary("nobody")
        assert summary["total_audiences"] == 0
        assert summary["overall_roas"] == 0


# =============================================================================
# LTV predictor
# =============================================================================
class TestLTVPredictor:
    def test_retargeting_premium_tier(self):
        prediction = AudienceLTVPredictor().predict(
            "a1", AudienceType.RETARGETING, "unknown_tenant"
        )
        assert prediction.predicted_avg_ltv == 180.0  # 100 baseline * 1.8
        assert prediction.value_tier == "premium"
        assert prediction.recommended_cac_limit == 60.0
        assert prediction.confidence == 0.5
        assert prediction.ltv_range_low == 144.0  # 20% variance
        assert prediction.ltv_range_high == 216.0

    def test_historical_performance_adjustment(self):
        predictor = AudienceLTVPredictor()
        prediction = predictor.predict(
            "a1",
            AudienceType.LOOKALIKE,
            "t1",
            historical_performance={"roas": 5.0, "conversion_rate": 0.1},
        )
        # perf multiplier maxed: 0.8 + 0.3 + 0.2 = 1.3
        assert prediction.predicted_avg_ltv == 130.0
        assert prediction.value_tier == "high"
        assert prediction.confidence == 0.7
        # lookalike variance is 30%
        assert prediction.ltv_range_low == 91.0

    def test_tenant_baseline_override(self):
        predictor = AudienceLTVPredictor()
        predictor.set_baseline_ltv("rich_tenant", 1000.0)
        prediction = predictor.predict("a1", AudienceType.CUSTOM, "rich_tenant")
        assert prediction.predicted_avg_ltv == 1200.0


# =============================================================================
# Decay predictor
# =============================================================================
class TestDecayPredictor:
    def test_base_decay_without_history(self):
        prediction = AudienceDecayPredictor().predict(
            "a1", AudienceType.FIRST_PARTY, current_score=100.0, audience_age_days=0
        )
        assert prediction.decay_rate == 2.0
        assert prediction.predicted_score_30d == 98.0
        assert prediction.predicted_score_90d == 94.0
        assert prediction.time_to_refresh_days == 750
        assert prediction.factors == ["Normal decay pattern"]

    def test_observed_decay_blended(self):
        predictor = AudienceDecayPredictor()
        for score in [100.0, 90.0, 80.0]:
            predictor.record_performance("a1", score)
        prediction = predictor.predict(
            "a1", AudienceType.CUSTOM, current_score=80.0, audience_age_days=0
        )
        # (0.04 base + (100-80)/100/3 observed) / 2 = 0.0533
        assert prediction.decay_rate == pytest.approx(5.33, abs=0.01)

    def test_old_retargeting_high_decay_factors(self):
        prediction = AudienceDecayPredictor().predict(
            "a1", AudienceType.RETARGETING, current_score=100.0, audience_age_days=100
        )
        assert prediction.decay_rate > 8
        assert len(prediction.factors) == 3  # retargeting + age + high decay

    def test_scores_floor_at_zero(self):
        predictor = AudienceDecayPredictor()
        prediction = predictor.predict(
            "a1", AudienceType.RETARGETING, current_score=10.0, audience_age_days=3650
        )
        assert prediction.predicted_score_90d >= 0


# =============================================================================
# Cluster analyzer
# =============================================================================
class TestClusterAnalyzer:
    def _seeded(self):
        analyzer = AudienceClusterAnalyzer()
        for aid, roas in [("a", 1.0), ("b", 2.0), ("c", 3.5), ("d", 4.0)]:
            analyzer.record_audience_features(aid, {"roas": roas, "ctr": 0.4})
        return analyzer

    def test_too_few_audiences(self):
        analyzer = self._seeded()
        assert analyzer.cluster_audiences(["a"]) == []

    def test_missing_features_filtered(self):
        analyzer = AudienceClusterAnalyzer()
        analyzer.record_audience_features("a", {"roas": 1.0})
        assert analyzer.cluster_audiences(["a", "no_features"], n_clusters=2) == []

    def test_two_clusters_sorted_by_roas(self):
        analyzer = self._seeded()
        clusters = analyzer.cluster_audiences(["a", "b", "c", "d"], n_clusters=2)
        assert len(clusters) == 2
        low, high = clusters
        assert set(low.audiences) == {"a", "b"}
        assert set(high.audiences) == {"c", "d"}
        assert low.cluster_name == "Low Performers"
        assert "pause low performers" in low.recommendation
        assert "Scale budget" in high.recommendation
        assert high.avg_performance["roas"] == 3.75

    def test_traits_identified(self):
        analyzer = self._seeded()
        clusters = analyzer.cluster_audiences(["a", "b", "c", "d"], n_clusters=2)
        low, high = clusters
        assert "High ROAS performers" in high.common_traits
        assert "Low engagement" in low.common_traits  # ctr 0.4 < 0.5

    def test_find_similar_orders_by_similarity(self):
        analyzer = AudienceClusterAnalyzer()
        analyzer.record_audience_features("target", {"roas": 2.0, "ctr": 1.0})
        analyzer.record_audience_features("twin", {"roas": 2.0, "ctr": 1.0})
        analyzer.record_audience_features("cousin", {"roas": 4.0, "ctr": 1.0})
        similar = analyzer.find_similar_audiences(
            "target", ["twin", "cousin", "target"]
        )
        assert [s["audience_id"] for s in similar] == ["twin", "cousin"]
        assert similar[0]["similarity_score"] == 1.0

    def test_find_similar_no_target_features(self):
        assert AudienceClusterAnalyzer().find_similar_audiences("ghost", ["a"]) == []

    def test_similarity_no_common_keys_zero(self):
        analyzer = AudienceClusterAnalyzer()
        assert analyzer._calculate_similarity({"a": 1.0}, {"b": 1.0}) == 0
