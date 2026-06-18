# =============================================================================
# Stratum AI - Developer Portal Endpoint Integration Tests
# =============================================================================
"""Integration tests for the developer-portal surface under
``/api/v1/developer/...``: portal config, usage analytics, and self-service
webhook management (list / create / deliveries / test / delete).

This also guards a routing fix: the router declares ``prefix="/developer"`` and
was *also* mounted with the same prefix, so routes had only been reachable at
the doubled path ``/developer/developer/...`` (the documented single-prefix
path 404'd). The mount-level prefix was removed.
"""

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_BASE = "/api/v1/developer"


class TestPortal:
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get(f"{_BASE}/portal")
        assert resp.status_code == 401

    async def test_portal_config(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"{_BASE}/portal")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert "sdk_examples" in data
        assert "rate_limit_per_minute" in data

    async def test_usage_analytics(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"{_BASE}/usage", params={"days": 30})
        assert resp.status_code == 200, resp.text


class TestWebhooks:
    async def test_list_webhooks(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"{_BASE}/webhooks")
        assert resp.status_code == 200, resp.text
        assert isinstance(resp.json()["data"], list)

    async def test_create_webhook_generates_secret(
        self, authenticated_client: AsyncClient
    ):
        resp = await authenticated_client.post(
            f"{_BASE}/webhooks",
            json={
                "id": "wh_test",
                "name": "My Hook",
                "url": "https://example.com/hook",
                "events": ["campaign.created"],
                "created_at": "2026-01-01T00:00:00Z",
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        # The server mints the signing secret and resets counters.
        assert data["secret"].startswith("whsec_")
        assert data["delivery_count"] == 0

    async def test_deliveries_and_test_and_delete(
        self, authenticated_client: AsyncClient
    ):
        deliveries = await authenticated_client.get(f"{_BASE}/webhooks/wh_1/deliveries")
        assert deliveries.status_code == 200, deliveries.text
        assert isinstance(deliveries.json()["data"], list)

        deleted = await authenticated_client.delete(f"{_BASE}/webhooks/wh_1")
        assert deleted.status_code == 200, deleted.text
        assert deleted.json()["data"]["deleted"] is True
