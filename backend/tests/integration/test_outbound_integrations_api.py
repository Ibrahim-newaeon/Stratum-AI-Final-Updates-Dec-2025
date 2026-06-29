# =============================================================================
# Stratum AI - Outbound Integrations Endpoint Integration Tests
# =============================================================================
"""Integration tests for the outbound-integrations surface under
``/api/v1/integrations/outbound/...``: Zapier, data-warehouse, and Teams
outgoing-webhook configuration listings.

This also guards a routing fix: the router declares
``prefix="/integrations/outbound"`` and was *also* mounted with the same
prefix, so the routes had only been reachable at the doubled path
``/integrations/outbound/integrations/outbound/...`` (the documented
single-prefix path 404'd). The mount-level prefix was removed; these tests hit
the correct single-prefix path.
"""

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_BASE = "/api/v1/integrations/outbound"

_LIST_GETS = ["/zapier", "/warehouse", "/teams"]


class TestAuth:
    @pytest.mark.parametrize("path", _LIST_GETS)
    async def test_requires_auth(self, client: AsyncClient, path):
        resp = await client.get(f"{_BASE}{path}")
        assert resp.status_code == 401


class TestListings:
    @pytest.mark.parametrize("path", _LIST_GETS)
    async def test_list_returns_200(self, authenticated_client: AsyncClient, path):
        resp = await authenticated_client.get(f"{_BASE}{path}")
        assert resp.status_code == 200, f"{path}: {resp.text}"
        body = resp.json()
        assert body["success"] is True
        assert isinstance(body["data"], list)


class TestCreateZapier:
    async def test_create_webhook_echoes_config(
        self, authenticated_client: AsyncClient
    ):
        resp = await authenticated_client.post(
            f"{_BASE}/zapier",
            json={
                "id": "zap_test",
                "name": "Test Hook",
                "webhook_url": "https://example.com/hook",
                "event_types": ["roas_alert"],
                "is_active": True,
                "created_at": "2026-01-01T00:00:00Z",
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["id"] == "zap_test"
        # Server resets the trigger count on registration.
        assert data["trigger_count"] == 0
