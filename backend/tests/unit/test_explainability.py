# =============================================================================
# Stratum AI - ML Explainability unit tests
# =============================================================================
"""Unit tests for app.ml.explainability.

Pure numpy/statistics logic, no I/O (no model file -> fallback paths).
Covers the ModelExplainer fallback contribution/explanation helpers, the
convenience entrypoints, and the P2 enhancements (counterfactual
explainer, model-drift detector, feature-interaction analyzer) — with
regression coverage for the previously-missing statistics / timedelta
imports.
"""

import pytest

from app.ml.explainability import (
    CounterfactualExplainer,
    FeatureInteractionAnalyzer,
    ModelDriftDetector,
    ModelExplainer,
    explain_roas_prediction,
    get_model_feature_importance,
)

pytestmark = pytest.mark.unit


@pytest.fixture()
def explainer():
    # nonexistent path -> no model -> fallback paths
    exp = ModelExplainer("roas_predictor", models_path="/tmp/nonexistent_models")
    exp.feature_names = ["ctr", "cvr", "spend", "roas_7d_avg"]
    return exp


# =============================================================================
# Fallback contributions + explanation helpers
# =============================================================================
class TestFallbackContributions:
    def test_no_model_distributes_importance(self, explainer):
        contribs = explainer._fallback_contributions(
            {"ctr": 2.0, "cvr": 3.0, "spend": 500.0, "roas_7d_avg": 4.0}
        )
        assert len(contribs) == 4
        # roas feature -> positive; spend>100 -> negative
        by_name = {c.feature_name: c for c in contribs}
        assert by_name["roas_7d_avg"].direction == "positive"
        assert by_name["spend"].direction == "negative"

    def test_explain_prediction_envelope(self, explainer):
        explanation = explainer.explain_prediction(
            features={"ctr": 2.0, "cvr": 3.0, "spend": 50.0, "roas_7d_avg": 4.0},
            prediction=3.2,
        )
        assert explanation.predicted_value == 3.2
        assert explanation.model_name == "roas_predictor"
        assert "Predicted ROAS: 3.20" in explanation.explanation_summary
        assert explanation.detailed_explanation.startswith("The model predicts")
        # sorted by abs contribution
        abs_contribs = [abs(c.contribution) for c in explanation.all_contributions]
        assert abs_contribs == sorted(abs_contribs, reverse=True)

    def test_explain_feature_known_and_default(self, explainer):
        ctr_text = explainer._explain_feature("ctr", 2.5, 0.2)
        assert "Click-through rate" in ctr_text
        assert "significantly increases" in ctr_text
        default = explainer._explain_feature("mystery_metric", 5, -0.05)
        assert "decreases" in default and "slightly" in default

    def test_friendly_name(self, explainer):
        assert explainer._friendly_name("ctr") == "click-through rate"
        assert explainer._friendly_name("platform_meta") == "Meta platform"
        assert explainer._friendly_name("custom_feature") == "custom feature"

    def test_confidence_coverage_and_extremes(self, explainer):
        full = explainer._calculate_confidence(
            {"ctr": 2.0, "cvr": 3.0, "spend": 50.0, "roas_7d_avg": 4.0}
        )
        assert full == 1.0
        partial = explainer._calculate_confidence({"ctr": 2.0})
        assert partial == 0.25
        # extreme values penalize
        extreme = explainer._calculate_confidence(
            {"ctr": 2.0, "cvr": 3.0, "spend": 50.0, "roas_7d_avg": 5000.0}
        )
        assert extreme < full

    def test_fallback_importance_equal_without_model(self, explainer):
        importance = explainer._fallback_importance()
        assert set(importance) == set(explainer.feature_names)
        assert all(v == pytest.approx(0.25) for v in importance.values())

    def test_estimate_interactions(self, explainer):
        importance = {"a": 0.4, "b": 0.3, "c": 0.2, "d": 0.1}
        interactions = explainer._estimate_interactions(importance)
        assert interactions
        assert all(len(i) == 3 for i in interactions)
        # sorted by strength desc
        strengths = [i[2] for i in interactions]
        assert strengths == sorted(strengths, reverse=True)

    def test_global_summary(self, explainer):
        summary = explainer._generate_global_summary([("ctr", 0.5), ("cvr", 0.3)], 100)
        assert "100 predictions" in summary
        assert "click-through rate" in summary
        assert explainer._generate_global_summary([], 0) == (
            "No feature importance data available."
        )


# =============================================================================
# Convenience functions
# =============================================================================
class TestConvenience:
    def test_explain_roas_prediction(self):
        result = explain_roas_prediction(
            features={"ctr": 2.0, "roas_7d_avg": 4.0, "spend": 50.0},
            prediction=3.5,
            models_path="/tmp/nonexistent_models",
        )
        assert result["prediction"] == 3.5
        assert "summary" in result
        assert isinstance(result["top_positive_factors"], list)

    def test_get_model_feature_importance_empty_without_model(self):
        # no model, no feature_names -> empty importance dict
        importance = get_model_feature_importance(
            "roas_predictor", models_path="/tmp/nonexistent_models"
        )
        assert importance == {}


# =============================================================================
# CounterfactualExplainer (regression: statistics import)
# =============================================================================
class TestCounterfactualExplainer:
    def test_increase_target_proposes_increases(self):
        explainer = CounterfactualExplainer()
        cf = explainer.generate_counterfactual(
            original_features={"spend": 1000.0, "ctr": 2.0},
            original_prediction=2.0,
            target_prediction=3.0,
        )
        # moving up -> features increased toward 20%
        for old, new in cf.changed_features.values():
            assert new >= old
        assert cf.impact >= 0
        assert "increase" in cf.recommendation

    def test_decrease_target_proposes_decreases(self):
        explainer = CounterfactualExplainer()
        cf = explainer.generate_counterfactual(
            original_features={"spend": 1000.0, "ctr": 2.0},
            original_prediction=3.0,
            target_prediction=2.0,
        )
        for old, new in cf.changed_features.values():
            assert new <= old

    def test_feasibility_respects_constraints(self):
        # Regression: _calculate_feasibility used statistics.mean (was NameError)
        explainer = CounterfactualExplainer()
        explainer.set_feature_constraints("spend", 0, 1100)  # caps the 20% rise
        cf = explainer.generate_counterfactual(
            original_features={"spend": 1000.0},
            original_prediction=2.0,
            target_prediction=3.0,
        )
        assert 0.0 <= cf.feasibility_score <= 1.0

    def test_no_matching_features(self):
        explainer = CounterfactualExplainer()
        cf = explainer.generate_counterfactual(
            original_features={"unknown_feature": 5.0},
            original_prediction=2.0,
            target_prediction=3.0,
        )
        assert cf.changed_features == {}
        assert cf.feasibility_score == 1.0
        assert "No feasible changes" in cf.recommendation


# =============================================================================
# ModelDriftDetector (regression: statistics + timedelta imports)
# =============================================================================
class TestModelDriftDetector:
    def test_no_baseline_no_alerts(self):
        detector = ModelDriftDetector()
        assert detector.detect_drift("m1", {"ctr": [1.0, 2.0]}) == []

    def test_data_drift_detected(self):
        # Regression: detect_drift used statistics.mean/stdev (was NameError)
        detector = ModelDriftDetector()
        detector.set_baseline("m1", {"ctr": {"mean": 2.0, "std": 0.5}})
        # current mean ~5 -> z = (5-2)/0.5 = 6 > 2 -> drift
        alerts = detector.detect_drift("m1", {"ctr": [4.5, 5.0, 5.5]})
        assert len(alerts) == 1
        assert alerts[0].drift_type == "data_drift"
        assert "ctr" in alerts[0].affected_features

    def test_no_drift_when_stable(self):
        detector = ModelDriftDetector()
        detector.set_baseline("m1", {"ctr": {"mean": 2.0, "std": 0.5}})
        assert detector.detect_drift("m1", {"ctr": [2.0, 2.1, 1.9]}) == []

    def test_performance_drift(self):
        detector = ModelDriftDetector()
        detector.set_baseline("m1", {"ctr": {"mean": 2.0, "std": 0.5}})
        for _ in range(10):
            detector.record_performance(0.9)
        # current 0.6 -> drop 0.3 > 0.2 -> critical
        alerts = detector.detect_drift("m1", {}, current_performance=0.6)
        perf = [a for a in alerts if a.drift_type == "performance_drift"]
        assert perf and perf[0].severity == "critical"

    def test_drift_summary_uses_timedelta(self):
        # Regression: get_drift_summary used timedelta (was NameError)
        detector = ModelDriftDetector()
        detector.set_baseline("m1", {"ctr": {"mean": 2.0, "std": 0.5}})
        detector.detect_drift("m1", {"ctr": [5.0, 5.5, 6.0]})
        summary = detector.get_drift_summary("m1", days=7)
        assert summary["model_name"] == "m1"
        assert summary["total_alerts"] >= 1
        assert summary["status"] == "needs_attention"
        assert "ctr" in summary["most_affected_features"]

    def test_drift_summary_healthy_when_empty(self):
        summary = ModelDriftDetector().get_drift_summary("m1")
        assert summary["status"] == "healthy"
        assert summary["total_alerts"] == 0


# =============================================================================
# FeatureInteractionAnalyzer
# =============================================================================
class TestFeatureInteractionAnalyzer:
    def _data(self, pairs):
        return [{"a": a, "b": b, "roas": a + b} for a, b in pairs]

    def test_insufficient_data(self):
        analyzer = FeatureInteractionAnalyzer()
        result = analyzer.analyze_interaction("a", "b", self._data([(1, 2)] * 5))
        assert result.interaction_type == "unknown"
        assert "Insufficient data" in result.example_explanation

    def test_synergistic_interaction(self):
        analyzer = FeatureInteractionAnalyzer()
        # a and b perfectly correlated -> synergistic
        data = [{"a": i, "b": i * 2, "roas": i} for i in range(1, 15)]
        result = analyzer.analyze_interaction("a", "b", data)
        assert result.interaction_type == "synergistic"
        assert result.interaction_strength == pytest.approx(1.0, abs=0.01)
        assert "increase" in result.example_explanation

    def test_antagonistic_interaction(self):
        analyzer = FeatureInteractionAnalyzer()
        data = [{"a": i, "b": -i, "roas": 0} for i in range(1, 15)]
        result = analyzer.analyze_interaction("a", "b", data)
        assert result.interaction_type == "antagonistic"
        assert "opposite directions" in result.example_explanation

    def test_independent_interaction_and_cache(self):
        analyzer = FeatureInteractionAnalyzer()
        data = [{"a": 1, "b": i % 3, "roas": i} for i in range(1, 15)]
        result = analyzer.analyze_interaction("a", "b", data)
        assert result.interaction_type == "independent"
        # cached on second call
        assert analyzer.analyze_interaction("a", "b", []) is result

    def test_pearson_correlation(self):
        analyzer = FeatureInteractionAnalyzer()
        assert analyzer._calculate_correlation([1, 2, 3], [2, 4, 6]) == pytest.approx(
            1.0
        )
        assert analyzer._calculate_correlation([1], [2]) == 0.0
        assert analyzer._calculate_correlation([5, 5, 5], [1, 2, 3]) == 0.0

    def test_get_top_interactions_sorted(self):
        analyzer = FeatureInteractionAnalyzer()
        data = [{"a": i, "b": i * 2, "c": i % 2, "roas": i} for i in range(1, 15)]
        interactions = analyzer.get_top_interactions(["a", "b", "c"], data, top_n=2)
        assert len(interactions) == 2
        strengths = [i.interaction_strength for i in interactions]
        assert strengths == sorted(strengths, reverse=True)
