# =============================================================================
# Stratum AI - LTV Predictor unit tests
# =============================================================================
"""Unit tests for app.ml.ltv_predictor.

Pure numpy/statistics logic, no I/O (no model file -> heuristic path).
Covers the heuristic LTV predictor (timeframe scaling, component
decomposition, segmentation, confidence, CAC math, cohort analysis), the
convenience entrypoints, and the P2 enhancements (Pareto/NBD, survival
analyzer, uncertainty quantifier, cohort tracker).
"""

from datetime import datetime, timedelta, timezone

import pytest

from app.ml.ltv_predictor import (
    CohortLTVTracker,
    CustomerBehavior,
    CustomerSegment,
    LTVPredictor,
    LTVTimeframe,
    LTVUncertaintyQuantifier,
    ParetoNBDModel,
    SurvivalAnalyzer,
    get_ltv_based_max_cac,
    predict_customer_ltv,
)

pytestmark = pytest.mark.unit


def _behavior(**overrides):
    defaults = dict(
        customer_id="c1",
        acquisition_date=datetime(2026, 1, 15, tzinfo=timezone.utc),
        acquisition_channel="meta",
        first_order_value=100.0,
        days_to_first_purchase=10,  # avoid the quick-conversion engagement bonus
    )
    defaults.update(overrides)
    return CustomerBehavior(**defaults)


@pytest.fixture()
def predictor():
    # nonexistent models_path -> model stays None -> heuristic path
    return LTVPredictor(models_path="/tmp/nonexistent_ltv_models")


# =============================================================================
# Core prediction
# =============================================================================
class TestPredict:
    def test_timeframe_multipliers(self, predictor):
        # plain $100 first order, meta, no engagement -> base 100
        prediction = predictor.predict(_behavior())
        assert prediction.predicted_ltv_30d == 100.0
        assert prediction.predicted_ltv_90d == pytest.approx(220.0)
        assert prediction.predicted_ltv_180d == pytest.approx(350.0)
        assert prediction.predicted_ltv_365d == pytest.approx(500.0)
        # lifetime is churn-adjusted: churn 0.5 (no engagement) ->
        # 800 * (1 - 0.5*0.5) = 600
        assert prediction.predicted_ltv_lifetime == pytest.approx(600.0, abs=0.5)

    def test_engagement_lifts_ltv(self, predictor):
        engaged = predictor.predict(
            _behavior(
                first_order_value=300.0,
                sessions_first_week=5,
                email_opens_first_week=3,
                email_clicks_first_week=1,
                days_to_first_purchase=1,
            )
        )
        # engagement_score = 1 + .3 + .2 + .15 + .2 = 1.85 -> base 555
        assert engaged.predicted_ltv_30d == pytest.approx(555.0, abs=0.5)
        assert engaged.segment == CustomerSegment.VIP  # 365d = 2775

    def test_channel_quality_applied(self, predictor):
        referral = predictor.predict(_behavior(acquisition_channel="referral"))
        meta = predictor.predict(_behavior(acquisition_channel="meta"))
        assert referral.predicted_ltv_30d == pytest.approx(130.0)  # 100 * 1.3
        assert meta.predicted_ltv_30d == 100.0

    def test_unknown_channel_default_multiplier(self, predictor):
        pred = predictor.predict(_behavior(acquisition_channel="billboard"))
        assert pred.predicted_ltv_30d == 100.0  # default 1.0

    def test_repeat_customer_history_multiplier(self, predictor):
        pred = predictor.predict(_behavior(total_orders=3))
        # historical_multiplier = min(1 + 3*0.2, 3) = 1.6
        assert pred.predicted_ltv_30d == pytest.approx(160.0)

    def test_cac_is_third_of_365d(self, predictor):
        pred = predictor.predict(_behavior())
        assert pred.recommended_cac_max == pytest.approx(
            pred.predicted_ltv_365d / 3.0, abs=0.01
        )


# =============================================================================
# Components
# =============================================================================
class TestComponents:
    def test_predict_orders_capped(self, predictor):
        # huge engagement -> capped at 24
        orders = predictor._predict_orders(
            _behavior(
                total_orders=10,
                sessions_first_week=50,
                email_opens_first_week=50,
                email_clicks_first_week=50,
                days_to_first_purchase=1,
            )
        )
        assert orders == 24

    def test_predict_aov_uses_history_when_present(self, predictor):
        assert predictor._predict_aov(_behavior(avg_order_value=80.0)) == pytest.approx(
            84.0
        )  # 80 * 1.05
        # no history -> 95% of first order
        assert predictor._predict_aov(_behavior(first_order_value=100.0)) == 95.0

    @pytest.mark.parametrize(
        "days_since,expected_min",
        [(0, 0.3), (45, 0.35), (75, 0.45), (120, 0.6)],
    )
    def test_churn_recency(self, predictor, days_since, expected_min):
        churn = predictor._predict_churn(
            _behavior(
                days_since_last_order=days_since,
                sessions_first_week=5,
                email_opens_first_week=5,
            )
        )
        assert churn == pytest.approx(expected_min, abs=0.01)

    def test_churn_max_factors(self, predictor):
        # base .3 + recency .3 + low-opens .1 + low-sessions .1 = .8
        churn = predictor._predict_churn(
            _behavior(
                days_since_last_order=200,
                sessions_first_week=0,
                email_opens_first_week=0,
            )
        )
        assert churn == pytest.approx(0.8)

    def test_churn_lower_clamp(self, predictor):
        # heavy repeat buyer, fresh, engaged -> floored at 0.1
        churn = predictor._predict_churn(
            _behavior(
                days_since_last_order=0,
                total_orders=5,
                sessions_first_week=10,
                email_opens_first_week=10,
            )
        )
        assert churn == 0.15  # 0.3 - 0.15 (repeat) , no other adds

    @pytest.mark.parametrize(
        "ltv,segment",
        [
            (1200, CustomerSegment.VIP),
            (600, CustomerSegment.HIGH_VALUE),
            (300, CustomerSegment.MEDIUM_VALUE),
            (50, CustomerSegment.LOW_VALUE),
        ],
    )
    def test_segment_thresholds(self, predictor, ltv, segment):
        assert predictor._determine_segment(ltv) == segment

    def test_confidence_scales_with_data(self, predictor):
        low = predictor._calculate_confidence(_behavior(total_orders=1))
        high = predictor._calculate_confidence(
            _behavior(total_orders=3, sessions_first_week=5, email_opens_first_week=5)
        )
        assert low < high
        assert high <= 0.95


# =============================================================================
# Segmentation / CAC / cohorts
# =============================================================================
class TestAggregations:
    def test_segment_customers_distribution(self, predictor):
        customers = [
            _behavior(
                customer_id="vip",
                first_order_value=300.0,
                sessions_first_week=5,
                email_opens_first_week=3,
                email_clicks_first_week=1,
                days_to_first_purchase=1,
            ),
            _behavior(customer_id="low", first_order_value=20.0),
        ]
        result = predictor.segment_customers(customers)
        assert result["total_customers"] == 2
        assert "vip" in result["segments"]
        assert "low_value" in result["segments"]
        assert result["segments"]["vip"]["count"] == 1
        assert result["total_predicted_ltv"] > 0

    def test_calculate_max_cac(self, predictor):
        result = predictor.calculate_max_cac(
            900.0, target_ratio=3.0, margin_percent=30.0
        )
        assert result["max_cac_by_ratio"] == 300.0
        assert result["max_cac_profitable"] == 135.0  # 900*0.3*0.5
        assert result["recommended_max_cac"] == 135.0  # min of the two

    def test_analyze_cohort_groups_by_month(self, predictor):
        customers = [
            _behavior(
                customer_id="a",
                acquisition_date=datetime(2026, 1, 5, tzinfo=timezone.utc),
            ),
            _behavior(
                customer_id="b",
                acquisition_date=datetime(2026, 1, 20, tzinfo=timezone.utc),
            ),
            _behavior(
                customer_id="c",
                acquisition_date=datetime(2026, 2, 1, tzinfo=timezone.utc),
            ),
        ]
        analyses = predictor.analyze_cohort(customers)
        assert [a.cohort_month for a in analyses] == ["2026-01", "2026-02"]
        assert analyses[0].customers == 2
        assert analyses[0].avg_ltv > 0
        assert sum(analyses[0].segment_distribution.values()) == 2


# =============================================================================
# Convenience functions (module singleton, heuristic)
# =============================================================================
class TestConvenience:
    def test_predict_customer_ltv_shape(self):
        result = predict_customer_ltv(
            customer_id="ut_ltv_1",
            first_order_value=150.0,
            acquisition_channel="google",
        )
        assert result["customer_id"] == "ut_ltv_1"
        assert set(result["predictions"]) == {
            "ltv_30d",
            "ltv_90d",
            "ltv_180d",
            "ltv_365d",
            "ltv_lifetime",
        }
        assert result["segment"] in {s.value for s in CustomerSegment}

    def test_get_ltv_based_max_cac(self):
        assert get_ltv_based_max_cac(900.0, target_ratio=3.0) == 135.0


# =============================================================================
# Pareto/NBD model
# =============================================================================
class TestParetoNBD:
    def test_fit_adjusts_parameters(self):
        model = ParetoNBDModel()
        transactions = [
            {"customer_id": "a", "date": datetime(2026, 1, 1, tzinfo=timezone.utc)},
            {"customer_id": "a", "date": datetime(2026, 2, 1, tzinfo=timezone.utc)},
            {"customer_id": "b", "date": datetime(2026, 1, 15, tzinfo=timezone.utc)},
        ]
        model.fit(transactions)
        # avg_freq = 1.5 -> r = min(2, 0.3) = 0.3, alpha = max(5, 13.33)
        assert model.r == pytest.approx(0.3)
        assert model.alpha == pytest.approx(20 / 1.5)

    def test_fit_empty_is_noop(self):
        model = ParetoNBDModel()
        model.fit([])
        assert model.r == 0.5  # unchanged default

    def test_predict_transactions_no_tenure(self):
        model = ParetoNBDModel()
        # tenure 0 -> simple proration
        assert model.predict_transactions(4, 0, 0, future_days=365) == 4.0

    def test_probability_alive_bounds(self):
        model = ParetoNBDModel()
        assert model._probability_alive(0, 0, 0) == 0  # zero tenure
        # high recency, low frequency -> high churn (clamped 0.95)
        churned = model._probability_alive(0, 100, 100)
        assert 0.05 <= churned <= 0.95

    def test_predict_transactions_active_customer(self):
        model = ParetoNBDModel()
        # recent purchase, high frequency, long tenure -> positive estimate
        result = model.predict_transactions(
            frequency=12, recency_days=5, tenure_days=365, future_days=365
        )
        assert result > 0


# =============================================================================
# Survival analyzer
# =============================================================================
class TestSurvivalAnalyzer:
    def test_default_curve_without_data(self):
        analyzer = SurvivalAnalyzer()
        pred = analyzer.predict_survival("c1", "vip", current_tenure_days=0)
        assert pred.survival_probability_30d >= pred.survival_probability_365d
        assert "default model" in pred.factors[0]

    def test_build_and_predict_from_curve(self):
        analyzer = SurvivalAnalyzer()
        lifetimes = [30, 60, 90, 120, 200, 300, 400]
        churned = [True, True, True, False, True, False, True]
        analyzer.build_survival_curve("seg", lifetimes, churned)
        pred = analyzer.predict_survival("c1", "seg", current_tenure_days=0)
        assert 0 <= pred.survival_probability_365d <= 1
        assert pred.risk_level in {"low", "medium", "high"}

    def test_mismatched_inputs_ignored(self):
        analyzer = SurvivalAnalyzer()
        analyzer.build_survival_curve("seg", [30, 60], [True])  # length mismatch
        assert "seg" not in analyzer._survival_curves


# =============================================================================
# Uncertainty quantifier
# =============================================================================
class TestUncertaintyQuantifier:
    def test_default_uncertainty(self):
        q = LTVUncertaintyQuantifier()
        ci = q.quantify_uncertainty(point_estimate=100.0, data_points=5)
        assert ci.lower_bound_95 <= ci.lower_bound_90 <= ci.point_estimate
        assert ci.point_estimate <= ci.upper_bound_90 <= ci.upper_bound_95
        assert ci.lower_bound_95 >= 0  # floored at 0
        assert any("Limited historical data" in f for f in ci.uncertainty_factors)

    def test_recorded_errors_tighten_with_data(self):
        q = LTVUncertaintyQuantifier()
        for _ in range(50):
            q.record_prediction_error(predicted=100.0, actual=105.0)
        ci = q.quantify_uncertainty(point_estimate=100.0, data_points=100)
        # consistent small errors -> narrow interval
        assert ci.upper_bound_95 - ci.lower_bound_95 < 60
        assert ci.confidence_level > 0.5

    def test_error_history_capped(self):
        q = LTVUncertaintyQuantifier()
        for i in range(1100):
            q.record_prediction_error(100.0, 100.0 + i)
        assert len(q._prediction_errors) == 1000


# =============================================================================
# Cohort LTV tracker
# =============================================================================
class TestCohortLTVTracker:
    def test_empty_trajectory(self):
        tracker = CohortLTVTracker()
        traj = tracker.get_cohort_trajectory("ghost", "2026-01")
        assert traj.customer_count == 0
        assert traj.ltv_by_month == {}
        assert traj.projected_ltv == 0

    def test_trajectory_projects_forward(self):
        tracker = CohortLTVTracker()
        tracker.record_cohort_ltv("jan", 1, [100.0, 120.0])
        tracker.record_cohort_ltv("jan", 2, [150.0, 170.0])
        tracker.record_cohort_ltv("jan", 3, [200.0, 220.0])
        traj = tracker.get_cohort_trajectory("jan", "2026-01")
        assert traj.customer_count == 2
        assert traj.ltv_by_month[1] == 110.0
        assert traj.ltv_by_month[3] == 210.0
        assert traj.projected_ltv > traj.ltv_by_month[3]  # growth projected

    def test_compare_cohorts(self):
        tracker = CohortLTVTracker()
        tracker.record_cohort_ltv("good", 6, [500.0, 550.0])
        tracker.record_cohort_ltv("bad", 6, [100.0, 120.0])
        result = tracker.compare_cohorts(["good", "bad"], at_month=6)
        assert result["best_performer"] == "good"
        assert result["worst_performer"] == "bad"
        assert result["ltv_range"] == pytest.approx(525.0 - 110.0)

    def test_compare_cohorts_no_data(self):
        result = CohortLTVTracker().compare_cohorts(["x"], at_month=6)
        assert result["cohorts"] == {}
        assert "No data" in result["message"]
