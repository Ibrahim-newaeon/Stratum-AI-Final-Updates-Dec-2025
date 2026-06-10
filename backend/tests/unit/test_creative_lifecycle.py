# =============================================================================
# Stratum AI - Creative Lifecycle & Fatigue Prediction unit tests
# =============================================================================
"""Unit tests for app.ml.creative_lifecycle.

Pure numpy/scipy/sklearn logic, no I/O. Covers the fatigue predictor
(phase detection, fatigue scoring, heuristic + ML decay fitting,
projections, urgency, recommendations, confidence), rotation planning,
the convenience entrypoint, decay-pattern extraction + clustering, the
cross-creative transfer learner, and the A/B test suggester.
"""

from datetime import datetime, timezone

import pytest

from app.ml.creative_lifecycle import (
    CreativeClusterAnalyzer,
    CreativeLifecyclePredictor,
    CreativePerformanceHistory,
    CreativeTestSuggester,
    CrossCreativeLearner,
    LifecyclePhase,
    RefreshUrgency,
    predict_creative_fatigue,
)

pytestmark = pytest.mark.unit


def _history(
    ctr,
    *,
    creative_id="c1",
    name="Creative",
    platform="meta",
    creative_type="image",
    roas=None,
    cpa=None,
    cvr=None,
    frequency=None,
):
    n = len(ctr)
    return CreativePerformanceHistory(
        creative_id=creative_id,
        creative_name=name,
        platform=platform,
        creative_type=creative_type,
        dates=[datetime(2026, 5, 1, tzinfo=timezone.utc) for _ in range(n)],
        impressions=[10000] * n,
        clicks=[int(10000 * c / 100) for c in ctr],
        conversions=[50] * n,
        spend=[100.0] * n,
        ctr=list(ctr),
        cvr=list(cvr) if cvr is not None else [2.0] * n,
        cpa=list(cpa) if cpa is not None else [20.0] * n,
        roas=list(roas) if roas is not None else [3.0] * n,
        frequency=list(frequency) if frequency is not None else [1.5] * n,
        days_active=n,
    )


def _rise_then_decay(days=20, peak=3.0, peak_day=5, floor=0.8):
    """Build a CTR curve that rises to a peak then decays toward a floor."""
    ctr = []
    for d in range(1, days + 1):
        if d <= peak_day:
            ctr.append(round(peak * d / peak_day, 4))
        else:
            # exponential-ish decline
            decay = (peak - floor) * (0.82 ** (d - peak_day))
            ctr.append(round(floor + decay, 4))
    return ctr


# =============================================================================
# predict_fatigue
# =============================================================================
class TestPredictFatigue:
    def test_insufficient_data(self):
        predictor = CreativeLifecyclePredictor()
        prediction = predictor.predict_fatigue(_history([1.0, 0.9]))
        assert prediction.current_phase == LifecyclePhase.LEARNING
        assert prediction.confidence == 0.3
        assert prediction.days_until_fatigue == 14
        assert "Insufficient data" in prediction.recommendations[0]

    def test_healthy_growing_creative(self):
        # rising CTR over 6 days -> growth phase, low fatigue
        predictor = CreativeLifecyclePredictor()
        prediction = predictor.predict_fatigue(
            _history([1.0, 1.2, 1.5, 1.8, 2.1, 2.4]), use_ml=False
        )
        assert prediction.current_phase == LifecyclePhase.GROWTH
        assert prediction.current_fatigue_score < 0.45
        assert prediction.refresh_urgency in {
            RefreshUrgency.HEALTHY,
            RefreshUrgency.MONITOR,
            RefreshUrgency.PLANNED,
        }

    def test_fatigued_creative_is_immediate(self):
        # deep CTR/ROAS drop + CPA rise + high frequency -> high fatigue
        ctr = _rise_then_decay(days=20, peak=4.0, peak_day=4, floor=0.5)
        predictor = CreativeLifecyclePredictor()
        prediction = predictor.predict_fatigue(
            _history(
                ctr,
                roas=[5.0] * 7 + [0.8] * 13,
                cpa=[10.0] * 7 + [70.0] * 13,
                frequency=[2.0] * 17 + [6.0] * 3,
            ),
            use_ml=False,
        )
        assert prediction.current_fatigue_score > 0.6
        assert prediction.current_phase == LifecyclePhase.FATIGUE
        assert prediction.refresh_urgency == RefreshUrgency.IMMEDIATE
        assert prediction.days_until_fatigue == 0
        assert any("immediately" in r for r in prediction.recommendations)

    def test_ml_fit_populates_decay_params(self):
        ctr = _rise_then_decay(days=20)
        predictor = CreativeLifecyclePredictor()
        prediction = predictor.predict_fatigue(_history(ctr), use_ml=True)
        assert prediction.decay_rate is not None
        assert prediction.peak_ctr == pytest.approx(3.0, abs=0.01)
        assert prediction.peak_day == 5

    def test_projections_and_loss(self):
        ctr = _rise_then_decay(days=18)
        predictor = CreativeLifecyclePredictor()
        prediction = predictor.predict_fatigue(
            _history(ctr, roas=[4.0] * 18), use_ml=False
        )
        assert prediction.projected_ctr_7d >= 0
        assert prediction.estimated_performance_loss_if_not_refreshed >= 0


# =============================================================================
# Phase detection
# =============================================================================
class TestPhaseDetection:
    def test_learning_phase(self):
        predictor = CreativeLifecyclePredictor()
        assert (
            predictor._determine_phase(_history([1.0, 1.1, 1.2]))
            == LifecyclePhase.LEARNING
        )

    def test_growth_phase(self):
        predictor = CreativeLifecyclePredictor()
        # 6 days, recent > early -> growth
        phase = predictor._determine_phase(_history([1.0, 1.2, 1.4, 1.7, 2.0, 2.3]))
        assert phase == LifecyclePhase.GROWTH

    def test_decline_phase_within_two_weeks(self):
        predictor = CreativeLifecyclePredictor()
        # peak around day 5-6, then well below 85% of peak
        ctr = [1.0, 2.0, 3.0, 3.2, 3.3, 3.3, 3.2, 2.0, 1.5, 1.2]
        assert predictor._determine_phase(_history(ctr)) == LifecyclePhase.DECLINE


# =============================================================================
# Fatigue scoring + platform decay rate
# =============================================================================
class TestFatigueScoring:
    def test_no_drop_low_fatigue(self):
        predictor = CreativeLifecyclePredictor()
        flat = [2.0] * 10
        score = predictor._calculate_current_fatigue(
            _history(flat, roas=[3.0] * 10, cpa=[20.0] * 10, frequency=[1.0] * 10)
        )
        assert score < 0.1

    def test_severe_drop_high_fatigue(self):
        predictor = CreativeLifecyclePredictor()
        ctr = [3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 3.0, 0.5, 0.5, 0.5]
        score = predictor._calculate_current_fatigue(
            _history(
                ctr,
                roas=[5.0] * 7 + [1.0] * 3,
                cpa=[10.0] * 7 + [50.0] * 3,
                frequency=[5.0] * 10,
            )
        )
        assert score > 0.6

    def test_platform_type_decay_rate(self):
        import math

        predictor = CreativeLifecyclePredictor()
        # tiktok half-life 7 days, video factor 0.85 -> 5.95 days
        rate = predictor._get_platform_decay_rate("tiktok", "video")
        assert rate == pytest.approx(math.log(2) / (7 * 0.85), abs=1e-6)
        # unknown platform/type fall back to default 14 / factor 1.0
        default = predictor._get_platform_decay_rate("unknown", "unknown")
        assert default == pytest.approx(math.log(2) / 14, abs=1e-6)


# =============================================================================
# Recommendations + urgency
# =============================================================================
class TestRecommendationsAndUrgency:
    @pytest.mark.parametrize(
        "days,fatigue,phase,expected",
        [
            (0, 0.2, LifecyclePhase.MATURITY, RefreshUrgency.IMMEDIATE),
            (2, 0.3, LifecyclePhase.DECLINE, RefreshUrgency.SOON),
            (6, 0.5, LifecyclePhase.DECLINE, RefreshUrgency.PLANNED),
            (30, 0.2, LifecyclePhase.DECLINE, RefreshUrgency.MONITOR),
            (30, 0.1, LifecyclePhase.GROWTH, RefreshUrgency.HEALTHY),
        ],
    )
    def test_urgency_levels(self, days, fatigue, phase, expected):
        predictor = CreativeLifecyclePredictor()
        assert predictor._determine_urgency(days, fatigue, phase) == expected

    def test_platform_and_frequency_recommendations(self):
        predictor = CreativeLifecyclePredictor()
        recs = predictor._generate_recommendations(
            _history([2.0] * 8, platform="tiktok", frequency=[1.0] * 7 + [4.0]),
            LifecyclePhase.DECLINE,
            RefreshUrgency.SOON,
            days_to_fatigue=2,
            projections={"ctr": 1.0, "roas": 2.0, "cpa": 25.0},
        )
        joined = " ".join(recs)
        assert "TikTok tip" in joined
        assert "High frequency" in joined


# =============================================================================
# Rotation planning + convenience entrypoint
# =============================================================================
class TestRotationPlan:
    def test_rotation_splits_healthy_and_needs_refresh(self):
        predictor = CreativeLifecyclePredictor()
        healthy = _history(
            [1.0, 1.2, 1.5, 1.8, 2.1, 2.4], creative_id="healthy", roas=[4.0] * 6
        )
        tired_ctr = _rise_then_decay(days=20, peak=4.0, peak_day=4, floor=0.5)
        tired = _history(
            tired_ctr,
            creative_id="tired",
            roas=[5.0] * 4 + [1.0] * 16,
            cpa=[10.0] * 4 + [60.0] * 16,
        )
        plan = predictor.get_rotation_plan([healthy, tired], weekly_budget=1000.0)
        assert plan["total_creatives"] == 2
        refresh_ids = {r["creative_id"] for r in plan["needs_refresh"]}
        assert "tired" in refresh_ids
        assert "healthy" in plan["budget_allocation"]
        assert sum(plan["budget_allocation"].values()) == pytest.approx(1000.0, abs=1.0)

    def test_convenience_entrypoint(self):
        daily = [
            {"date": "2026-05-0%d" % d, "ctr": c, "roas": 3.0, "cpa": 20.0, "cvr": 2.0}
            for d, c in enumerate([1.0, 1.5, 2.0, 2.5, 2.2, 1.8, 1.4, 1.0], start=1)
        ]
        result = predict_creative_fatigue("c1", "Hero", "meta", "video", daily)
        assert result["creative_id"] == "c1"
        assert result["current_phase"] in {p.value for p in LifecyclePhase}
        assert set(result["projections"]) == {"ctr_7d", "roas_7d", "cpa_7d"}
        assert "recommendations" in result


# =============================================================================
# Decay pattern extraction + clustering
# =============================================================================
class TestClusterAnalyzer:
    def test_extract_pattern_requires_seven_days(self):
        analyzer = CreativeClusterAnalyzer()
        assert analyzer.extract_pattern(_history([1.0] * 5)) is None

    def test_extract_pattern_features(self):
        analyzer = CreativeClusterAnalyzer()
        ctr = _rise_then_decay(days=20, peak=4.0, peak_day=5, floor=0.5)
        pattern = analyzer.extract_pattern(_history(ctr))
        assert pattern is not None
        assert pattern.peak_day == 5
        assert pattern.peak_ctr == pytest.approx(4.0, abs=0.01)
        assert pattern.decay_rate > 0
        assert pattern.days_to_fatigue >= 0
        assert pattern.total_lifetime_ctr > 0

    def test_fit_and_cluster_profiles(self):
        analyzer = CreativeClusterAnalyzer(n_clusters=2)
        histories = []
        # fast burners
        for i in range(3):
            ctr = _rise_then_decay(days=16, peak=5.0, peak_day=2, floor=0.3)
            histories.append(_history(ctr, creative_id=f"fast{i}"))
        # evergreen
        for i in range(3):
            ctr = _rise_then_decay(days=16, peak=2.0, peak_day=8, floor=1.6)
            histories.append(_history(ctr, creative_id=f"slow{i}"))
        analyzer.fit(histories)
        profiles = analyzer.get_cluster_profiles()
        assert profiles
        assert all("cluster_type" in p for p in profiles)
        total = sum(p["creative_count"] for p in profiles)
        assert total == 6

    def test_predict_cluster_before_fit_is_none(self):
        analyzer = CreativeClusterAnalyzer()
        ctr = _rise_then_decay(days=16)
        assert analyzer.predict_cluster(_history(ctr)) is None

    def test_predict_cluster_after_fit(self):
        analyzer = CreativeClusterAnalyzer(n_clusters=2)
        histories = [
            _history(
                _rise_then_decay(days=16, peak=5.0, peak_day=2), creative_id=f"f{i}"
            )
            for i in range(3)
        ] + [
            _history(
                _rise_then_decay(days=16, peak=2.0, peak_day=8, floor=1.6),
                creative_id=f"s{i}",
            )
            for i in range(3)
        ]
        analyzer.fit(histories)
        result = analyzer.predict_cluster(
            _history(_rise_then_decay(days=16, peak=5.0, peak_day=2), creative_id="new")
        )
        assert result is not None
        assert "predicted_cluster" in result
        assert result["creative_id"] == "new"


# =============================================================================
# Cross-creative learner
# =============================================================================
class TestCrossCreativeLearner:
    def _learned(self):
        predictor = CreativeLifecyclePredictor()
        histories, predictions = [], []
        for i in range(4):
            h = _history(
                _rise_then_decay(days=16),
                creative_id=f"meta_img_{i}",
                platform="meta",
                creative_type="image",
            )
            histories.append(h)
            predictions.append(predictor.predict_fatigue(h, use_ml=False))
        learner = CrossCreativeLearner().learn(histories, predictions)
        return learner

    def test_learn_builds_benchmarks(self):
        learner = self._learned()
        assert "meta" in learner._platform_benchmarks
        assert "image" in learner._type_benchmarks
        assert learner._platform_benchmarks["meta"]["sample_count"] == 4

    def test_cold_start_with_benchmarks(self):
        learner = self._learned()
        result = learner.get_cold_start_prediction("meta", "image")
        assert result["confidence"] == 0.4
        assert result["predicted_days_to_fatigue"] >= 0
        assert "meta" in result["recommendation"]

    def test_cold_start_fallback_default(self):
        result = CrossCreativeLearner().get_cold_start_prediction("unknown", "unknown")
        assert result["predicted_days_to_fatigue"] == 14
        assert result["predicted_decay_rate"] == 0.05

    def test_find_similar_ranks_matches(self):
        learner = self._learned()
        query = _history(
            _rise_then_decay(days=16),
            creative_id="query",
            platform="meta",
            creative_type="image",
        )
        similar = learner.find_similar_creatives(query, top_n=3)
        assert len(similar) == 3
        # same platform + type -> high similarity (>= 0.6)
        assert similar[0]["similarity_score"] >= 0.6


# =============================================================================
# Test suggester
# =============================================================================
class TestTestSuggester:
    def _prediction(self, predictor, urgency_ctr, **kw):
        return predictor.predict_fatigue(_history(urgency_ctr, **kw), use_ml=False)

    def test_immediate_suggests_high_impact(self):
        predictor = CreativeLifecyclePredictor()
        ctr = _rise_then_decay(days=20, peak=4.0, peak_day=4, floor=0.5)
        hist = _history(
            ctr,
            roas=[5.0] * 7 + [0.8] * 13,
            cpa=[10.0] * 7 + [70.0] * 13,
            frequency=[2.0] * 17 + [6.0] * 3,
        )
        prediction = predictor.predict_fatigue(hist, use_ml=False)
        assert prediction.refresh_urgency == RefreshUrgency.IMMEDIATE
        suggestions = CreativeTestSuggester().suggest_tests(prediction, hist)
        strategies = {s["strategy"] for s in suggestions}
        assert "format_switch" in strategies or "hook_change" in strategies
        assert all("rationale" in s for s in suggestions)

    def test_healthy_suggests_incremental(self):
        predictor = CreativeLifecyclePredictor()
        hist = _history([1.0, 1.2, 1.5, 1.8, 2.1, 2.4], roas=[4.0] * 6)
        prediction = predictor.predict_fatigue(hist, use_ml=False)
        suggestions = CreativeTestSuggester().suggest_tests(
            prediction, hist, max_suggestions=2
        )
        assert len(suggestions) == 2
        assert all(s["effort_level"] in {"low", "medium", "high"} for s in suggestions)
