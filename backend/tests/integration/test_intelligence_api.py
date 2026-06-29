# =============================================================================
# Stratum AI - AI Intelligence Endpoint Integration Tests
# =============================================================================
"""Integration tests for the AI-intelligence surface under
``/api/v1/intelligence/analytics/insights/...``: natural-language query (NLQ),
anomaly explanation, and campaign performance prediction.

These use rule-based engines (no external LLM), so they run deterministically
in the harness. NLQ generates + executes read-only SQL (with a graceful empty
fallback); predict needs a real campaign + metric history.
"""

import datetime as dt

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_BASE = "/api/v1/intelligence/analytics/insights"


async def _seed_campaign_with_metrics(db: AsyncSession, tenant_id: int):
    from app.models import Campaign, CampaignMetric

    campaign = Campaign(
        tenant_id=tenant_id,
        platform="meta",
        external_id="intel_ext",
        account_id="acct_intel",
        name="Intel Campaign",
        status="active",
        roas=2.5,
        total_spend_cents=50000,
    )
    db.add(campaign)
    await db.flush()

    today = dt.date.today()
    for i in range(5):
        db.add(
            CampaignMetric(
                tenant_id=tenant_id,
                campaign_id=campaign.id,
                date=today - dt.timedelta(days=i),
                spend_cents=10000,
                revenue_cents=25000,
                impressions=2000,
                clicks=100,
                conversions=10,
            )
        )
    await db.flush()
    return campaign


class TestNLQ:
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post(f"{_BASE}/nlq", json={"question": "How much spend?"})
        assert resp.status_code == 401

    async def test_nlq_executes(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            f"{_BASE}/nlq",
            json={"question": "What are my top campaigns by ROAS?"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["generated_sql"]
        assert isinstance(data["results"], list)
        assert data["result_count"] == len(data["results"])


class TestAnomalyExplain:
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            f"{_BASE}/anomalies/explain", json={"metric": "roas", "severity": "high"}
        )
        assert resp.status_code == 401

    async def test_explain_without_campaign(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            f"{_BASE}/anomalies/explain",
            json={"metric": "roas", "severity": "critical"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["metric"] == "roas"
        assert isinstance(data["recommended_actions"], list)
        assert isinstance(data["root_causes"], list)


class TestPredict:
    async def test_campaign_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            f"{_BASE}/predict", json={"campaign_id": 99999999, "days_ahead": 7}
        )
        assert resp.status_code == 404

    async def test_predict_with_history(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_tenant,
    ):
        campaign = await _seed_campaign_with_metrics(db_session, test_tenant["id"])
        resp = await authenticated_client.post(
            f"{_BASE}/predict",
            json={"campaign_id": campaign.id, "days_ahead": 7},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["success"] is True
