# =============================================================================
# Stratum AI - Notifications API Integration Tests
# =============================================================================
"""Integration tests for the in-app notifications API.

Exercises the real ASGI app against Postgres + Redis: create (admin-only),
list, unread count, mark-read, delete (204/404), and auth enforcement.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


def _notification(title="Trust gate held", message="Signal health degraded", **extra):
    body = {"title": title, "message": message}
    body.update(extra)
    return body


# =============================================================================
# Create
# =============================================================================
class TestCreateNotification:
    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/notifications", json=_notification())
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_create_success(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            "/api/v1/notifications",
            json=_notification(
                title="Pacing breach", category="campaign", type="warning"
            ),
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["success"] is True
        assert body["data"]["title"] == "Pacing breach"
        assert body["data"]["category"] == "campaign"
        assert body["data"]["type"] == "warning"

    @pytest.mark.asyncio
    async def test_invalid_type_falls_back_to_info(
        self, authenticated_client: AsyncClient
    ):
        # Unknown type/category are coerced to safe defaults, not rejected.
        resp = await authenticated_client.post(
            "/api/v1/notifications",
            json=_notification(type="not_a_type", category="not_a_cat"),
        )
        assert resp.status_code == 201
        data = resp.json()["data"]
        assert data["type"] == "info"
        assert data["category"] == "system"

    @pytest.mark.asyncio
    async def test_missing_title_rejected(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            "/api/v1/notifications", json={"message": "No title"}
        )
        assert resp.status_code == 422


# =============================================================================
# List + count + mark-read + delete
# =============================================================================
class TestListCountAndMutations:
    @pytest.mark.asyncio
    async def test_list_returns_created(self, authenticated_client: AsyncClient):
        await authenticated_client.post(
            "/api/v1/notifications", json=_notification(title="Notif One")
        )
        await authenticated_client.post(
            "/api/v1/notifications", json=_notification(title="Notif Two")
        )
        resp = await authenticated_client.get("/api/v1/notifications")
        assert resp.status_code == 200
        titles = {n["title"] for n in resp.json()["data"]}
        assert {"Notif One", "Notif Two"} <= titles

    @pytest.mark.asyncio
    async def test_count_reflects_unread(self, authenticated_client: AsyncClient):
        await authenticated_client.post(
            "/api/v1/notifications", json=_notification(title="Counted")
        )
        resp = await authenticated_client.get("/api/v1/notifications/count")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["unread_count"] >= 1
        assert data["total_count"] >= data["unread_count"]

    @pytest.mark.asyncio
    async def test_mark_read_clears_unread(self, authenticated_client: AsyncClient):
        await authenticated_client.post(
            "/api/v1/notifications", json=_notification(title="To Read")
        )
        marked = await authenticated_client.post(
            "/api/v1/notifications/mark-read", json={}
        )
        assert marked.status_code == 200
        assert marked.json()["data"]["marked_read"] >= 1

        # After marking all read, unread count should be zero.
        count = await authenticated_client.get("/api/v1/notifications/count")
        assert count.json()["data"]["unread_count"] == 0

    @pytest.mark.asyncio
    async def test_delete_roundtrip(self, authenticated_client: AsyncClient):
        created = await authenticated_client.post(
            "/api/v1/notifications", json=_notification(title="Doomed")
        )
        notif_id = created.json()["data"]["id"]
        deleted = await authenticated_client.delete(f"/api/v1/notifications/{notif_id}")
        assert deleted.status_code == 204

    @pytest.mark.asyncio
    async def test_delete_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.delete("/api/v1/notifications/99999999")
        assert resp.status_code == 404
