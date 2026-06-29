# =============================================================================
# Stratum AI - Pacing Alert Helper Unit Tests
# =============================================================================
"""Unit tests for the pure mapping helpers of
``app.services.pacing.alert_service.PacingAlertService``:

- ``_get_miss_alert_type`` metric -> alert-type mapping
- ``_get_metric_value`` DailyKPI -> metric value extraction (cents->dollars)

These helpers never touch ``self.db``, so the service is instantiated with
``db=None`` and fed a duck-typed DailyKPI. The DB-backed alert pipeline is
out of scope here.
"""

from types import SimpleNamespace

import pytest

from app.models.pacing import AlertType, TargetMetric
from app.services.pacing.alert_service import PacingAlertService

pytestmark = pytest.mark.unit


@pytest.fixture
def service() -> PacingAlertService:
    return PacingAlertService(db=None, tenant_id=1)


# =============================================================================
# _get_miss_alert_type
# =============================================================================
class TestMissAlertType:
    @pytest.mark.parametrize(
        "metric,alert",
        [
            ("roas", AlertType.ROAS_BELOW_TARGET),
            ("conversions", AlertType.CONVERSIONS_BELOW_TARGET),
            ("revenue", AlertType.REVENUE_BELOW_TARGET),
            ("pipeline_value", AlertType.PIPELINE_BELOW_TARGET),
        ],
    )
    def test_known_metrics(self, service, metric, alert):
        assert service._get_miss_alert_type(metric) == alert

    def test_unknown_metric_defaults_to_underpacing(self, service):
        assert service._get_miss_alert_type("???") == AlertType.UNDERPACING_SPEND


# =============================================================================
# _get_metric_value
# =============================================================================
class TestMetricValue:
    def _kpi(self, **overrides) -> SimpleNamespace:
        base = dict(
            spend_cents=12345,
            revenue_cents=50000,
            roas=2.5,
            conversions=42,
            leads=3,
            crm_leads=4,
            crm_pipeline_cents=900000,
            crm_won_revenue_cents=250000,
        )
        base.update(overrides)
        return SimpleNamespace(**base)

    def test_spend_cents_to_dollars(self, service):
        assert service._get_metric_value(self._kpi(), TargetMetric.SPEND) == 123.45

    def test_revenue_cents_to_dollars(self, service):
        assert service._get_metric_value(self._kpi(), TargetMetric.REVENUE) == 500.0

    def test_roas_passthrough(self, service):
        assert service._get_metric_value(self._kpi(), TargetMetric.ROAS) == 2.5

    def test_conversions_passthrough(self, service):
        assert service._get_metric_value(self._kpi(), TargetMetric.CONVERSIONS) == 42

    def test_leads_sums_native_and_crm(self, service):
        assert service._get_metric_value(self._kpi(), TargetMetric.LEADS) == 7

    def test_pipeline_value_cents_to_dollars(self, service):
        assert (
            service._get_metric_value(self._kpi(), TargetMetric.PIPELINE_VALUE)
            == 9000.0
        )

    def test_won_revenue_cents_to_dollars(self, service):
        assert (
            service._get_metric_value(self._kpi(), TargetMetric.WON_REVENUE) == 2500.0
        )

    def test_null_cents_default_to_zero(self, service):
        kpi = self._kpi(spend_cents=None)
        assert service._get_metric_value(kpi, TargetMetric.SPEND) == 0.0
