# =============================================================================
# Stratum AI - Push Notifications API Integration Tests
# =============================================================================
"""Integration tests for the web-push notifications API.

Exercises the real ASGI app: VAPID key retrieval, device subscribe /
unsubscribe, subscriber listing, history, and analytics, plus auth.

Note: subscriptions live in an in-memory tenant-keyed store (the same
pattern drip campaigns used before being moved to PostgreSQL), so list
assertions are tenant-scoped subset checks — each test runs under a fresh
tenant_id. The /send path dispatches real web-push, so it is left to
service-level tests.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


def _subscription(endpoint="https://push.example.com/ep/abc", **extra):
    body = {
        "endpoint": endpoint,
        "keys": {"p256dh": "test-p256dh", "auth": "test-auth"},
        "user_agent": "pytest-agent",
        "platform": "web",
    }
    body.update(extra)
    return body


async def _subscribe(client: AsyncClient, **extra) -> dict:
    resp = await client.post(
        "/api/v1/push-notifications/subscribe", json=_subscription(**extra)
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


# =============================================================================
# VAPID key + subscribe
# =============================================================================
class TestSubscribe:
    @pytest.mark.asyncio
    async def test_subscribe_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/push-notifications/subscribe", json=_subscription()
        )
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_vapid_key(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/push-notifications/vapid-key")
        assert resp.status_code == 200
        assert resp.json()["data"]["public_key"]

    @pytest.mark.asyncio
    async def test_subscribe_success(self, authenticated_client: AsyncClient):
        data = await _subscribe(authenticated_client)
        assert data["status"] == "subscribed"
        assert data["subscription_id"]

    @pytest.mark.asyncio
    async def test_subscribe_missing_endpoint_rejected(
        self, authenticated_client: AsyncClient
    ):
        resp = await authenticated_client.post(
            "/api/v1/push-notifications/subscribe",
            json={"keys": {"p256dh": "x", "auth": "y"}},
        )
        assert resp.status_code == 422


# =============================================================================
# Subscribers + unsubscribe + reads
# =============================================================================
class TestSubscribersAndReads:
    @pytest.mark.asyncio
    async def test_subscriber_listed_after_subscribe(
        self, authenticated_client: AsyncClient
    ):
        created = await _subscribe(
            authenticated_client, endpoint="https://push.example.com/ep/listed"
        )
        resp = await authenticated_client.get("/api/v1/push-notifications/subscribers")
        assert resp.status_code == 200
        # The list omits the push endpoint (a secret URL); match on id instead.
        ids = {s["id"] for s in resp.json()["data"]}
        assert created["subscription_id"] in ids

    @pytest.mark.asyncio
    async def test_unsubscribe(self, authenticated_client: AsyncClient):
        endpoint = "https://push.example.com/ep/gone"
        await _subscribe(authenticated_client, endpoint=endpoint)
        resp = await authenticated_client.post(
            "/api/v1/push-notifications/unsubscribe", params={"endpoint": endpoint}
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["unsubscribed"] is True

    @pytest.mark.asyncio
    async def test_unsubscribe_unknown_endpoint(
        self, authenticated_client: AsyncClient
    ):
        resp = await authenticated_client.post(
            "/api/v1/push-notifications/unsubscribe",
            params={"endpoint": "https://push.example.com/ep/nope"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["unsubscribed"] is False

    @pytest.mark.asyncio
    async def test_history(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/push-notifications/history")
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"], list)

    @pytest.mark.asyncio
    async def test_analytics(self, authenticated_client: AsyncClient):
        await _subscribe(
            authenticated_client, endpoint="https://push.example.com/ep/analytics"
        )
        resp = await authenticated_client.get("/api/v1/push-notifications/analytics")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "total_subscribers" in data
        assert "platform_breakdown" in data
