# =============================================================================
# Stratum AI - Insights API Integration Tests
# =============================================================================
"""Integration tests for the AI-insights API.

Exercises the real ASGI app against Postgres + Redis: daily insights,
recommendations, anomalies, and KPIs. These endpoints are feature-gated
(ai_recommendations / anomaly_alerts), so an ``insights_enabled`` fixture
turns those flags on for the test tenant. A fresh tenant has no analytics
data, so the reads return empty/default payloads.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient

pytestmark = pytest.mark.integration


@pytest_asyncio.fixture
async def insights_enabled(db_session, test_tenant):
    """Enable the AI-insight feature flags on the test tenant."""
    from sqlalchemy import update

    from app.base_models import Tenant

    await db_session.execute(
        update(Tenant)
        .where(Tenant.id == test_tenant["id"])
        .values(feature_flags={"ai_recommendations": True, "anomaly_alerts": True})
    )
    await db_session.flush()


def _url(path: str, tenant_id: int) -> str:
    return f"/api/v1/insights/tenant/{tenant_id}/{path}"


class TestAuth:
    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient, test_tenant: dict):
        resp = await client.get(_url("insights", test_tenant["id"]))
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_cross_tenant_forbidden(
        self, authenticated_client: AsyncClient, test_tenant: dict, insights_enabled
    ):
        other = test_tenant["id"] + 99999
        resp = await authenticated_client.get(_url("insights", other))
        assert resp.status_code == 403


class TestInsightReads:
    @pytest.mark.asyncio
    async def test_insights(
        self, authenticated_client: AsyncClient, test_tenant: dict, insights_enabled
    ):
        resp = await authenticated_client.get(_url("insights", test_tenant["id"]))
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    @pytest.mark.asyncio
    async def test_recommendations(
        self, authenticated_client: AsyncClient, test_tenant: dict, insights_enabled
    ):
        resp = await authenticated_client.get(
            _url("recommendations", test_tenant["id"])
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    @pytest.mark.asyncio
    async def test_anomalies(
        self, authenticated_client: AsyncClient, test_tenant: dict, insights_enabled
    ):
        resp = await authenticated_client.get(_url("anomalies", test_tenant["id"]))
        assert resp.status_code == 200
        assert resp.json()["success"] is True

    @pytest.mark.asyncio
    async def test_kpis(
        self, authenticated_client: AsyncClient, test_tenant: dict, insights_enabled
    ):
        resp = await authenticated_client.get(_url("kpis", test_tenant["id"]))
        assert resp.status_code == 200
        assert resp.json()["success"] is True


class TestKpiAggregation:
    """The KPI endpoint sums campaigns in SQL [API-002] — verify the aggregate
    values and per-platform breakdown match seeded data exactly."""

    @pytest.mark.asyncio
    async def test_kpis_aggregate_seeded_campaigns(
        self,
        authenticated_client: AsyncClient,
        test_tenant: dict,
        insights_enabled,
        db_session,
    ):
        from app.models import Campaign

        # meta: $500 + $300 spend, $1500 + $600 revenue; google: $200 / $800.
        seed = [
            ("meta", 50000, 150000, 10, 2000, 100),
            ("meta", 30000, 60000, 5, 1000, 50),
            ("google", 20000, 80000, 8, 500, 40),
        ]
        for i, (platform, spend_c, rev_c, conv, impr, clk) in enumerate(seed):
            db_session.add(
                Campaign(
                    tenant_id=test_tenant["id"],
                    platform=platform,
                    external_id=f"kpi_ext_{i}",
                    account_id="acct_kpi",
                    name=f"KPI Campaign {i}",
                    status="active",
                    total_spend_cents=spend_c,
                    revenue_cents=rev_c,
                    conversions=conv,
                    impressions=impr,
                    clicks=clk,
                )
            )
        await db_session.flush()

        resp = await authenticated_client.get(_url("kpis", test_tenant["id"]))
        assert resp.status_code == 200
        data = resp.json()["data"]

        m = data["metrics"]
        # Totals: spend $1000, revenue $2900, conversions 23, roas 2.9.
        assert m["spend"]["value"] == 1000.0
        assert m["revenue"]["value"] == 2900.0
        assert m["conversions"]["value"] == 23
        assert m["roas"]["value"] == 2.9

        by_platform = data["by_platform"]
        assert by_platform["meta"] == {
            "spend": 800.0,
            "revenue": 2100.0,
            "conversions": 15,
        }
        assert by_platform["google"] == {
            "spend": 200.0,
            "revenue": 800.0,
            "conversions": 8,
        }
