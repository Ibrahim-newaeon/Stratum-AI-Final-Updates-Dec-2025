# =============================================================================
# Stratum AI - Pacing Forecasting Helpers Unit Tests
# =============================================================================
"""Unit tests for the pure helpers of ``ForecastingService`` in
app.services.pacing.forecasting: EWMA and end-of-month math. The
DB-backed forecast pipeline is out of scope here."""

from datetime import date

import pytest

from app.services.pacing.forecasting import ForecastingService

pytestmark = pytest.mark.unit


@pytest.fixture
def service() -> ForecastingService:
    # Pure helpers don't touch the session; alpha=0.5 for predictable EWMA.
    return ForecastingService(db=None, tenant_id=1, ewma_alpha=0.5)


class TestEwma:
    def test_empty_is_zero(self, service):
        assert service._calculate_ewma([]) == 0.0

    def test_single_point(self, service):
        assert service._calculate_ewma([{"value": 42.0}]) == 42.0

    def test_two_points(self, service):
        # ewma = 10, then 0.5*20 + 0.5*10 = 15.
        assert service._calculate_ewma([{"value": 10.0}, {"value": 20.0}]) == 15.0

    def test_constant_series_converges_to_constant(self, service):
        hist = [{"value": 7.0} for _ in range(10)]
        assert service._calculate_ewma(hist) == pytest.approx(7.0)


class TestEndOfMonth:
    @pytest.mark.parametrize(
        "d,expected",
        [
            (date(2026, 2, 15), date(2026, 2, 28)),  # non-leap February
            (date(2024, 2, 10), date(2024, 2, 29)),  # leap February
            (date(2026, 12, 5), date(2026, 12, 31)),  # December rollover
            (date(2026, 4, 1), date(2026, 4, 30)),  # 30-day month
        ],
    )
    def test_end_of_month(self, service, d, expected):
        assert service._get_end_of_month(d) == expected
