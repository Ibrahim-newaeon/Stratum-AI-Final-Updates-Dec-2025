# =============================================================================
# Stratum AI - ROAS Forecaster Pure-Helper Unit Tests
# =============================================================================
"""Unit tests for the pure helpers of ``app.ml.forecaster.ROASForecaster``:
baseline aggregation, linear ROAS trend, weekday/weekend seasonality, and
the no-history mock forecast. The DB-backed forecast pipeline and the
ModelRegistry-backed inference path are out of scope here.

``__init__`` constructs a ModelRegistry (inference strategy) that the pure
helpers never touch, so we instantiate via ``__new__`` to keep these tests
dependency-free.
"""

from datetime import date

import pytest

from app.ml.forecaster import ROASForecaster

pytestmark = pytest.mark.unit


@pytest.fixture
def forecaster() -> ROASForecaster:
    # Bypass __init__ (ModelRegistry) — pure helpers only call other helpers.
    return ROASForecaster.__new__(ROASForecaster)


def _day(d: date, spend: float, revenue: float) -> dict:
    """Build a daily aggregate row in the cents-based shape the helpers expect."""
    return {
        "date": d,
        "spend_cents": int(spend * 100),
        "revenue_cents": int(revenue * 100),
        "impressions": 0,
        "clicks": 0,
        "conversions": 0,
    }


# =============================================================================
# _calculate_baseline
# =============================================================================
class TestBaseline:
    def test_empty_returns_defaults(self, forecaster):
        baseline = forecaster._calculate_baseline([])
        assert baseline["avg_roas"] == 1.5
        assert baseline["seasonality_factor"] == 1.0

    def test_aggregates_spend_revenue_and_roas(self, forecaster):
        data = [
            _day(date(2026, 6, 1), spend=100.0, revenue=200.0),
            _day(date(2026, 6, 2), spend=100.0, revenue=400.0),
        ]
        baseline = forecaster._calculate_baseline(data)
        assert baseline["avg_daily_spend"] == pytest.approx(100.0)
        assert baseline["avg_daily_revenue"] == pytest.approx(300.0)
        # Total revenue 600 / total spend 200 = 3.0
        assert baseline["avg_roas"] == pytest.approx(3.0)

    def test_zero_spend_uses_default_roas(self, forecaster):
        data = [_day(date(2026, 6, 1), spend=0.0, revenue=0.0)]
        baseline = forecaster._calculate_baseline(data)
        assert baseline["avg_roas"] == 1.5


# =============================================================================
# _calculate_trend
# =============================================================================
class TestTrend:
    def test_too_few_points_is_zero(self, forecaster):
        assert forecaster._calculate_trend([_day(date(2026, 6, 1), 10.0, 20.0)]) == 0

    def test_rising_roas_has_positive_slope(self, forecaster):
        data = [
            _day(date(2026, 6, 1), spend=100.0, revenue=100.0),  # roas 1.0
            _day(date(2026, 6, 2), spend=100.0, revenue=200.0),  # roas 2.0
            _day(date(2026, 6, 3), spend=100.0, revenue=300.0),  # roas 3.0
        ]
        slope = forecaster._calculate_trend(data)
        assert slope == pytest.approx(1.0)

    def test_falling_roas_has_negative_slope(self, forecaster):
        data = [
            _day(date(2026, 6, 1), spend=100.0, revenue=300.0),  # roas 3.0
            _day(date(2026, 6, 2), spend=100.0, revenue=200.0),  # roas 2.0
            _day(date(2026, 6, 3), spend=100.0, revenue=100.0),  # roas 1.0
        ]
        assert forecaster._calculate_trend(data) < 0

    def test_skips_zero_spend_rows(self, forecaster):
        # Only one usable ROAS point -> trend is zero.
        data = [
            _day(date(2026, 6, 1), spend=0.0, revenue=0.0),
            _day(date(2026, 6, 2), spend=100.0, revenue=200.0),
        ]
        assert forecaster._calculate_trend(data) == 0


# =============================================================================
# _calculate_seasonality
# =============================================================================
class TestSeasonality:
    def test_equal_weekday_weekend_is_one(self, forecaster):
        data = [
            _day(date(2026, 6, 1), spend=100.0, revenue=200.0),  # Monday
            _day(date(2026, 6, 6), spend=100.0, revenue=200.0),  # Saturday
        ]
        assert forecaster._calculate_seasonality(data) == pytest.approx(1.0)

    def test_missing_one_bucket_defaults_to_one(self, forecaster):
        # Only weekday data present -> default 1.0.
        data = [_day(date(2026, 6, 1), spend=100.0, revenue=200.0)]  # Monday
        assert forecaster._calculate_seasonality(data) == 1.0

    def test_higher_weekday_roas_above_one(self, forecaster):
        data = [
            _day(date(2026, 6, 1), spend=100.0, revenue=400.0),  # Monday roas 4.0
            _day(date(2026, 6, 6), spend=100.0, revenue=200.0),  # Saturday roas 2.0
        ]
        assert forecaster._calculate_seasonality(data) == pytest.approx(2.0)


# =============================================================================
# _generate_mock_forecast
# =============================================================================
class TestMockForecast:
    def test_daily_shape_and_horizon(self, forecaster):
        out = forecaster._generate_mock_forecast(days_ahead=5, granularity="daily")
        assert out["forecast_horizon"] == 5
        assert out["model_version"] == "mock_forecast_v1.0.0"
        assert len(out["predictions"]) == 5
        first = out["predictions"][0]
        assert first["confidence_lower"] <= first["predicted_roas"]
        assert first["predicted_roas"] <= first["confidence_upper"]

    def test_non_daily_granularity_has_no_daily_predictions(self, forecaster):
        out = forecaster._generate_mock_forecast(days_ahead=30, granularity="weekly")
        # Mock path only fills predictions for daily granularity.
        assert out["predictions"] == []
        assert out["granularity"] == "weekly"
