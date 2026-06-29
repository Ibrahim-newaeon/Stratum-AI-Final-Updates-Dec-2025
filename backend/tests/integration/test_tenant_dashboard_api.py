# =============================================================================
# Stratum AI - Tenant Dashboard Endpoint Integration Tests
# =============================================================================
"""Integration tests for the tenant-scoped dashboard surface under
``/api/v1/tenant/{tenant_id}/...``: overview KPIs, derived alerts, alert
ack/resolve, settings get/update, and the command center.

The alerts are *derived* from ``Campaign`` rows (ROAS/CTR thresholds) rather
than a persisted alert table, so the fixtures seed real campaigns and assert
the threshold logic. ``require_tenant`` is exercised for cross-tenant denial.
"""

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


def _base(tenant_id: int) -> str:
    return f"/api/v1/tenant/{tenant_id}"


async def _seed_campaign(
    db: AsyncSession,
    tenant_id: int,
    *,
    external_id: str,
    name: str,
    status: str = "active",
    roas: float | None = None,
    ctr: float | None = None,
    spend_cents: int = 0,
    revenue_cents: int = 0,
):
    """Insert a real Campaign row; the dashboard queries this table."""
    from app.models import Campaign

    campaign = Campaign(
        tenant_id=tenant_id,
        platform="meta",
        external_id=external_id,
        account_id="acct_test",
        name=name,
        status=status,
        roas=roas,
        ctr=ctr,
        total_spend_cents=spend_cents,
        revenue_cents=revenue_cents,
    )
    db.add(campaign)
    await db.flush()
    return campaign


# =============================================================================
# Overview
# =============================================================================
class TestOverview:
    async def test_requires_auth(self, client: AsyncClient, test_tenant):
        resp = await client.get(f"{_base(test_tenant['id'])}/dashboard/overview")
        assert resp.status_code in {401, 403}

    async def test_empty_overview(self, authenticated_client: AsyncClient, test_tenant):
        resp = await authenticated_client.get(
            f"{_base(test_tenant['id'])}/dashboard/overview"
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["total_campaigns"] == 0

    async def test_overview_aggregates_and_classifies(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_tenant,
    ):
        # Scaling candidate (roas >= 3.0), active.
        await _seed_campaign(
            db_session,
            test_tenant["id"],
            external_id="ov_1",
            name="Winner",
            status="active",
            roas=5.0,
            spend_cents=10000,  # $100
            revenue_cents=50000,  # $500
        )
        # Fix candidate (roas < 1.5), paused.
        await _seed_campaign(
            db_session,
            test_tenant["id"],
            external_id="ov_2",
            name="Loser",
            status="paused",
            roas=0.5,
            spend_cents=20000,  # $200
            revenue_cents=10000,  # $100
        )

        resp = await authenticated_client.get(
            f"{_base(test_tenant['id'])}/dashboard/overview"
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["total_campaigns"] == 2
        assert data["total_spend"] == 300.0
        assert data["total_revenue"] == 600.0
        assert data["portfolio_roas"] == 2.0
        assert data["active_campaigns"] == 1
        assert data["paused_campaigns"] == 1
        assert data["scaling_candidates"] == 1
        assert data["fix_candidates"] == 1
        assert data["watch_campaigns"] == 0

    async def test_cross_tenant_forbidden(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        # The authenticated user belongs to test_tenant; a different path
        # tenant_id must be rejected by require_tenant.
        resp = await authenticated_client.get(
            f"{_base(test_tenant['id'] + 99999)}/dashboard/overview"
        )
        assert resp.status_code == 403


# =============================================================================
# Derived alerts
# =============================================================================
class TestAlerts:
    async def test_low_roas_creates_budget_alert(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_tenant,
    ):
        await _seed_campaign(
            db_session,
            test_tenant["id"],
            external_id="al_roas",
            name="Bleeding Spend",
            roas=0.5,  # 0 < roas < 1.0 -> budget/high
            ctr=None,
        )
        resp = await authenticated_client.get(f"{_base(test_tenant['id'])}/alerts")
        assert resp.status_code == 200, resp.text
        alerts = resp.json()["data"]
        budget = [a for a in alerts if a["type"] == "budget"]
        assert len(budget) == 1
        assert budget[0]["severity"] == "high"
        assert budget[0]["entity_type"] == "campaign"

    async def test_low_ctr_creates_fatigue_alert(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_tenant,
    ):
        await _seed_campaign(
            db_session,
            test_tenant["id"],
            external_id="al_ctr",
            name="Stale Creative",
            roas=2.0,  # >= 1.0 so no budget alert
            ctr=0.3,  # 0 < ctr < 0.5 -> fatigue/medium
        )
        resp = await authenticated_client.get(f"{_base(test_tenant['id'])}/alerts")
        assert resp.status_code == 200, resp.text
        alerts = resp.json()["data"]
        types = {a["type"] for a in alerts}
        assert "fatigue" in types
        assert "budget" not in types

    async def test_severity_filter(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_tenant,
    ):
        # One campaign trips both a high (budget) and medium (fatigue) alert.
        await _seed_campaign(
            db_session,
            test_tenant["id"],
            external_id="al_both",
            name="Double Trouble",
            roas=0.5,
            ctr=0.3,
        )
        resp = await authenticated_client.get(
            f"{_base(test_tenant['id'])}/alerts", params={"severity": "high"}
        )
        assert resp.status_code == 200, resp.text
        alerts = resp.json()["data"]
        assert alerts  # at least one
        assert all(a["severity"] == "high" for a in alerts)


# =============================================================================
# Alert actions (ack not yet persisted -> 501; resolve is a no-op success)
# =============================================================================
class TestAlertActions:
    async def test_acknowledge_not_implemented(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        resp = await authenticated_client.post(
            f"{_base(test_tenant['id'])}/alerts/1/ack"
        )
        assert resp.status_code == 501

    async def test_resolve_returns_success(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        resp = await authenticated_client.post(
            f"{_base(test_tenant['id'])}/alerts/7/resolve",
            params={"resolution_notes": "handled"},
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["alert_id"] == 7
        assert body["data"]["resolution_notes"] == "handled"


# =============================================================================
# Settings
# =============================================================================
class TestSettings:
    async def test_get_returns_defaults(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        resp = await authenticated_client.get(f"{_base(test_tenant['id'])}/settings")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["currency"] == "USD"
        assert data["timezone"] == "UTC"

    async def test_update_persists(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        update = await authenticated_client.put(
            f"{_base(test_tenant['id'])}/settings",
            json={"currency": "EUR", "timezone": "Europe/Berlin"},
        )
        assert update.status_code == 200, update.text
        assert update.json()["data"]["currency"] == "EUR"

        # Re-read to confirm the JSON settings blob persisted.
        resp = await authenticated_client.get(f"{_base(test_tenant['id'])}/settings")
        data = resp.json()["data"]
        assert data["currency"] == "EUR"
        assert data["timezone"] == "Europe/Berlin"


# =============================================================================
# Command Center
# =============================================================================
class TestCommandCenter:
    async def test_command_center_ok(
        self,
        authenticated_client: AsyncClient,
        db_session: AsyncSession,
        test_tenant,
    ):
        await _seed_campaign(
            db_session,
            test_tenant["id"],
            external_id="cc_1",
            name="CC Campaign",
            roas=2.0,
            ctr=1.2,
            spend_cents=5000,
            revenue_cents=10000,
        )
        resp = await authenticated_client.get(
            f"{_base(test_tenant['id'])}/command-center"
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["success"] is True
