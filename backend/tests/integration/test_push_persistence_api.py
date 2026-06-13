# =============================================================================
# Stratum AI - Push Notifications Persistence Integration Tests
# =============================================================================
"""Integration tests for the DB-backed push-notification behavior.

Exercises the persistence layer added when push subscriptions and sent
records moved off the per-process in-memory store onto PostgreSQL: the
send -> history -> analytics flow, targeted vs broadcast sends, and the
empty-target guard. Complements ``test_push_notifications_api.py``.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


def _subscription(endpoint="https://push.example.com/ep/persist", **extra):
    body = {
        "endpoint": endpoint,
        "keys": {"p256dh": "p", "auth": "a"},
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


class TestSendFlow:
    @pytest.mark.asyncio
    async def test_send_to_all_records_history(self, authenticated_client: AsyncClient):
        await _subscribe(authenticated_client, endpoint="https://push.example.com/a")
        await _subscribe(authenticated_client, endpoint="https://push.example.com/b")

        sent = await authenticated_client.post(
            "/api/v1/push-notifications/send",
            json={"title": "Hello", "body": "World", "send_to_all": True},
        )
        assert sent.status_code == 200
        data = sent.json()["data"]
        assert data["sent_count"] == 2
        assert data["title"] == "Hello"

        # The send is persisted to history.
        history = await authenticated_client.get("/api/v1/push-notifications/history")
        assert history.status_code == 200
        titles = {n["title"] for n in history.json()["data"]}
        assert "Hello" in titles

        # Analytics reflects subscribers + the sent notification.
        analytics = await authenticated_client.get(
            "/api/v1/push-notifications/analytics"
        )
        adata = analytics.json()["data"]
        assert adata["total_subscribers"] == 2
        assert adata["notifications_sent_30d"] >= 1

    @pytest.mark.asyncio
    async def test_send_to_specific_subscription(
        self, authenticated_client: AsyncClient
    ):
        created = await _subscribe(
            authenticated_client, endpoint="https://push.example.com/target"
        )
        resp = await authenticated_client.post(
            "/api/v1/push-notifications/send",
            json={
                "title": "Targeted",
                "body": "Just you",
                "subscription_ids": [created["subscription_id"]],
            },
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["sent_count"] == 1

    @pytest.mark.asyncio
    async def test_send_with_no_targets_rejected(
        self, authenticated_client: AsyncClient
    ):
        # No subscribers and not broadcasting → 400.
        resp = await authenticated_client.post(
            "/api/v1/push-notifications/send",
            json={"title": "Nobody", "body": "home", "send_to_all": True},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_unsubscribe_excludes_from_send(
        self, authenticated_client: AsyncClient
    ):
        endpoint = "https://push.example.com/leaving"
        await _subscribe(authenticated_client, endpoint=endpoint)
        await authenticated_client.post(
            "/api/v1/push-notifications/unsubscribe", params={"endpoint": endpoint}
        )
        # Now inactive → broadcast finds no active targets → 400.
        resp = await authenticated_client.post(
            "/api/v1/push-notifications/send",
            json={"title": "Hi", "body": "there", "send_to_all": True},
        )
        assert resp.status_code == 400
