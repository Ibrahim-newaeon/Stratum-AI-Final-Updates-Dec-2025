# =============================================================================
# Stratum AI - Live Predictions API Integration Tests
# =============================================================================
"""Integration tests for the live-predictions / ROAS-optimization API.

Exercises the real ASGI app against Postgres + Redis: live predictions,
prediction alerts, budget optimization, and per-campaign prediction /
scenarios, plus auth and not-found paths. A fresh tenant has no campaigns
or stored predictions, so the read endpoints return empty/default results.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

_MISSING_CAMPAIGN = 99999999


class TestPredictionReads:
    @pytest.mark.asyncio
    async def test_live_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/predictions/live")
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_live_empty(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/predictions/live")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    @pytest.mark.asyncio
    async def test_alerts(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/predictions/alerts")
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    @pytest.mark.asyncio
    async def test_budget_optimization(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/predictions/optimize/budget")
        assert resp.status_code == 200
        assert resp.json()["success"] is True


class TestPerCampaign:
    @pytest.mark.asyncio
    async def test_campaign_prediction_not_found(
        self, authenticated_client: AsyncClient
    ):
        resp = await authenticated_client.get(
            f"/api/v1/predictions/campaign/{_MISSING_CAMPAIGN}"
        )
        assert resp.status_code in {200, 404}

    @pytest.mark.asyncio
    async def test_scenarios_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(
            f"/api/v1/predictions/scenarios/{_MISSING_CAMPAIGN}"
        )
        assert resp.status_code in {200, 404}
