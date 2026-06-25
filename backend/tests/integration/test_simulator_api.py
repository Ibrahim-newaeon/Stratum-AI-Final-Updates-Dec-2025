# =============================================================================
# Stratum AI - What-If Simulator Endpoint Integration Tests
# =============================================================================
"""Integration tests for the ML simulator surface under ``/api/v1/simulate/...``:
budget-change simulation, ROAS forecasting, conversion prediction, and model
status.

These endpoints resolve the tenant from ``request.state.tenant_id`` (set by the
tenant middleware from the authenticated client) and depend on
``get_async_session`` (overridden by the harness). The ML layer
(``WhatIfSimulator``/``ROASForecaster``/``ConversionPredictor``) degrades to a
heuristic when no trained model artifact is present, so the portfolio happy path
runs without seeded campaigns.

NOTE: run with the session-scoped event loop CI uses
(``-o asyncio_default_test_loop_scope=session``).
"""

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_BASE = "/api/v1/simulate"


@pytest.fixture(autouse=True)
def _enterprise_tier(monkeypatch):
    """Elevate the test tenant to ENTERPRISE for the simulator router.

    The What-If Simulator is gated behind ``Feature.WHAT_IF_SIMULATOR`` (enterprise
    tier). The autouse ``_active_subscription`` fixture reports PROFESSIONAL, which
    the ``FeatureGate`` dependency rejects with 403. This fixture is requested
    after that autouse one, so its patch of ``get_subscription_info`` wins and the
    gate sees enterprise — letting requests reach the endpoint bodies under test.
    """
    from app.core import subscription as sub_mod
    from app.core.tiers import SubscriptionTier

    async def _enterprise(tenant_id: int) -> "sub_mod.SubscriptionInfo":
        return sub_mod.SubscriptionInfo(
            tenant_id=tenant_id,
            plan="enterprise",
            tier=SubscriptionTier.ENTERPRISE,
            status=sub_mod.SubscriptionStatus.ACTIVE,
            expires_at=None,
            days_until_expiry=None,
            days_in_grace=None,
            is_access_restricted=False,
            restriction_reason=None,
        )

    monkeypatch.setattr(sub_mod, "get_subscription_info", _enterprise)


class TestModelStatus:
    async def test_model_status_ok(self, authenticated_client: AsyncClient):
        # No auth dependency and no DB — pure ML registry read.
        resp = await authenticated_client.get(f"{_BASE}/models/status")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["success"] is True
        assert "ml_provider" in body["data"]


class TestSimulate:
    # NOTE: the portfolio/single-campaign happy path runs ``WhatIfSimulator``,
    # which calls ``ModelRegistry.predict``. The registry deliberately raises
    # ``ModelUnavailableError`` (rather than returning fabricated data) when no
    # trained model artifact is deployed — which is the case in CI — so the happy
    # path is not exercised here. The campaign-existence guard below runs *before*
    # any model inference, so it's harness-stable.

    async def test_unknown_campaign_404(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            _BASE,
            json={
                "campaign_id": 999999999,
                "budget_change_percent": 10.0,
                "days_ahead": 7,
            },
        )
        assert resp.status_code == 404, resp.text

    async def test_validation_error_missing_budget(
        self, authenticated_client: AsyncClient
    ):
        # budget_change_percent is required.
        resp = await authenticated_client.post(_BASE, json={"days_ahead": 7})
        assert resp.status_code == 422


class TestForecastRoas:
    async def test_no_campaigns_404(self, authenticated_client: AsyncClient):
        # With no campaigns seeded, the forecaster has nothing to project.
        resp = await authenticated_client.post(
            _BASE + "/forecast/roas",
            json={"days_ahead": 14, "granularity": "daily"},
        )
        assert resp.status_code == 404, resp.text


class TestPredictConversions:
    async def test_unknown_campaign_404(self, authenticated_client: AsyncClient):
        # Campaign-existence guard runs before the predictor.
        resp = await authenticated_client.post(
            _BASE + "/predict/conversions",
            json={"campaign_id": 999999999, "features": {}},
        )
        assert resp.status_code == 404, resp.text
