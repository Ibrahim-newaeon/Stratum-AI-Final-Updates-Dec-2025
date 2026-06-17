# =============================================================================
# Stratum AI - AI Analytics Endpoint Integration Tests
# =============================================================================
"""Integration tests for the AI-analytics surface under
``/api/v1/analytics/ai/...``: Trust-Engine scoring (scaling, creative fatigue),
anomaly detection, signal-health, and the DB-backed recommendations / KPIs.

The scoring/anomaly/health endpoints are pure-computation (no DB), driven by
request payloads; recommendations + kpis read tenant-scoped campaign data.
"""

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_BASE = "/api/v1/analytics/ai"

_SCALE_BODY = {
    "entity_id": "c1",
    "entity_name": "Campaign One",
    "platform": "meta",
    "spend": 100.0,
    "impressions": 10000,
    "clicks": 300,
    "conversions": 20,
    "revenue": 500.0,
    "baseline_spend": 90.0,
    "baseline_impressions": 9500,
    "baseline_clicks": 280,
    "baseline_conversions": 18,
    "baseline_revenue": 420.0,
}

_FATIGUE_BODY = {
    "creative_id": "cr1",
    "creative_name": "Hero Video",
    "ctr": 0.8,
    "roas": 1.5,
    "cpa": 30.0,
    "frequency": 4.5,
    "baseline_ctr": 1.6,
    "baseline_roas": 3.0,
    "baseline_cpa": 18.0,
}


class TestAuth:
    async def test_scoring_requires_auth(self, client: AsyncClient):
        resp = await client.post(f"{_BASE}/scoring/scale", json=_SCALE_BODY)
        assert resp.status_code in {401, 403}


class TestScoring:
    async def test_scaling_score(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            f"{_BASE}/scoring/scale", json=_SCALE_BODY
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert -1.0 <= data["score"] <= 1.0
        assert "action" in data

    async def test_fatigue_score(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            f"{_BASE}/scoring/fatigue", json=_FATIGUE_BODY
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert 0.0 <= data["fatigue_score"] <= 1.0


class TestAnomalies:
    async def test_detect_anomaly(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            f"{_BASE}/anomalies/detect",
            json={
                "metrics_history": {"roas": [2.0, 2.1, 1.9, 2.0, 2.2, 2.05, 1.95]},
                "current_values": {"roas": 0.4},
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert "anomaly_count" in data
        assert isinstance(data["anomalies"], list)


class TestSignalHealth:
    async def test_healthy_signal(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            f"{_BASE}/health/signal",
            json={"emq_score": 92, "event_loss_pct": 2, "api_health": True},
        )
        assert resp.status_code == 200, resp.text
        assert "health" in resp.json()["data"]

    async def test_degraded_signal(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            f"{_BASE}/health/signal",
            json={"emq_score": 25, "event_loss_pct": 60, "api_health": False},
        )
        assert resp.status_code == 200, resp.text
        assert "health" in resp.json()["data"]


class TestDbBacked:
    async def test_recommendations_empty(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"{_BASE}/recommendations")
        assert resp.status_code == 200, resp.text

    async def test_kpis_empty(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"{_BASE}/kpis")
        assert resp.status_code == 200, resp.text
