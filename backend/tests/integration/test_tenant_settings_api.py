# =============================================================================
# Stratum AI - Tenant Settings Endpoint Integration Tests
# =============================================================================
"""Integration tests for the DB-backed tenant-settings GET/PUT under
``/tenant/{tenant_id}/settings`` (tenant_dashboard router). The PUT merges
into ``Tenant.settings`` (JSON) and is gated by require_tenant +
TENANT_SETTINGS permission (the ADMIN test user has it).
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


def _url(test_tenant) -> str:
    return f"/api/v1/tenant/{test_tenant['id']}/settings"


class TestAuth:
    async def test_get_requires_auth(self, client, test_tenant):
        resp = await client.get(_url(test_tenant))
        assert resp.status_code in (401, 403)

    async def test_wrong_tenant_forbidden(self, authenticated_client):
        resp = await authenticated_client.get("/api/v1/tenant/9999999/settings")
        assert resp.status_code == 403


class TestSettings:
    async def test_get_returns_defaults(self, authenticated_client, test_tenant):
        resp = await authenticated_client.get(_url(test_tenant))
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        # Unset tenant settings fall back to documented defaults.
        assert data["currency"] == "USD"
        assert data["timezone"] == "UTC"
        assert data["email_notifications"] is True

    async def test_put_updates_and_persists(self, authenticated_client, test_tenant):
        resp = await authenticated_client.put(
            _url(test_tenant),
            json={
                "currency": "EUR",
                "timezone": "Europe/Berlin",
                "slack_notifications": True,
                "alert_roas_drop_pct": 15.0,
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()["data"]
        assert body["currency"] == "EUR"
        assert body["timezone"] == "Europe/Berlin"
        assert body["slack_notifications"] is True
        assert body["alert_roas_drop_pct"] == 15.0

        # Re-read: the change persisted to Tenant.settings.
        got = await authenticated_client.get(_url(test_tenant))
        assert got.json()["data"]["currency"] == "EUR"

    async def test_put_partial_merges(self, authenticated_client, test_tenant):
        # Set currency first ...
        await authenticated_client.put(_url(test_tenant), json={"currency": "GBP"})
        # ... then update only timezone — currency must survive the merge.
        resp = await authenticated_client.put(
            _url(test_tenant), json={"timezone": "Asia/Dubai"}
        )
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["timezone"] == "Asia/Dubai"
        assert body["currency"] == "GBP"
