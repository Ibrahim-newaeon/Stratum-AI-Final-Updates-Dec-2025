# =============================================================================
# Stratum AI - Automation Rules API Integration Tests
# =============================================================================
"""Integration tests for the automation rules engine API.

Exercises the real ASGI app against Postgres + Redis: rule creation,
listing (paginated), detail (200/404), update, lifecycle transitions
(activate / pause / toggle), duplicate, soft-delete, and auth enforcement.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


def _rule(name="Pause on high CPA", **extra):
    body = {
        "name": name,
        "description": "Pause campaigns when CPA exceeds target",
        "condition_field": "cpa",
        "condition_operator": "greater_than",
        "condition_value": "50",
        "condition_duration_hours": 24,
        "action_type": "pause_campaign",
        "action_config": {},
        "cooldown_hours": 24,
    }
    body.update(extra)
    return body


async def _create(client: AsyncClient, **extra) -> dict:
    resp = await client.post("/api/v1/rules", json=_rule(**extra))
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


# =============================================================================
# Create
# =============================================================================
class TestCreateRule:
    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/rules", json=_rule())
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_create_success(self, authenticated_client: AsyncClient):
        data = await _create(authenticated_client, name="Budget guard")
        assert data["name"] == "Budget guard"
        assert data["status"] == "draft"
        assert data["action_type"] == "pause_campaign"

    @pytest.mark.asyncio
    async def test_invalid_operator_rejected(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            "/api/v1/rules", json=_rule(condition_operator="not_an_op")
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_name_rejected(self, authenticated_client: AsyncClient):
        body = _rule()
        del body["name"]
        resp = await authenticated_client.post("/api/v1/rules", json=body)
        assert resp.status_code == 422


# =============================================================================
# List + detail
# =============================================================================
class TestListAndDetail:
    @pytest.mark.asyncio
    async def test_list_paginated(self, authenticated_client: AsyncClient):
        await _create(authenticated_client, name="Rule A")
        await _create(authenticated_client, name="Rule B")
        resp = await authenticated_client.get("/api/v1/rules")
        assert resp.status_code == 200
        page = resp.json()["data"]
        names = {r["name"] for r in page["items"]}
        assert {"Rule A", "Rule B"} <= names
        assert page["total"] >= 2

    @pytest.mark.asyncio
    async def test_detail_roundtrip(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, name="Detail Rule")
        resp = await authenticated_client.get(f"/api/v1/rules/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "Detail Rule"

    @pytest.mark.asyncio
    async def test_detail_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/rules/99999999")
        assert resp.status_code == 404


# =============================================================================
# Update + lifecycle + delete
# =============================================================================
class TestMutationsAndLifecycle:
    @pytest.mark.asyncio
    async def test_update_fields(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, name="Original")
        resp = await authenticated_client.patch(
            f"/api/v1/rules/{created['id']}",
            json={"name": "Renamed", "cooldown_hours": 48},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "Renamed"

    @pytest.mark.asyncio
    async def test_activate_then_pause(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client)
        rid = created["id"]
        activated = await authenticated_client.post(f"/api/v1/rules/{rid}/activate")
        assert activated.status_code == 200
        assert activated.json()["data"]["status"] == "active"

        paused = await authenticated_client.post(f"/api/v1/rules/{rid}/pause")
        assert paused.status_code == 200
        assert paused.json()["data"]["status"] == "paused"

    @pytest.mark.asyncio
    async def test_toggle_flips_status(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client)
        rid = created["id"]
        # draft → active on first toggle
        first = await authenticated_client.post(f"/api/v1/rules/{rid}/toggle")
        assert first.json()["data"]["status"] == "active"
        # active → paused on second toggle
        second = await authenticated_client.post(f"/api/v1/rules/{rid}/toggle")
        assert second.json()["data"]["status"] == "paused"

    @pytest.mark.asyncio
    async def test_duplicate_creates_draft_copy(
        self, authenticated_client: AsyncClient
    ):
        created = await _create(authenticated_client, name="Source Rule")
        resp = await authenticated_client.post(
            f"/api/v1/rules/{created['id']}/duplicate"
        )
        assert resp.status_code == 201
        copy = resp.json()["data"]
        assert copy["name"] == "Source Rule (Copy)"
        assert copy["status"] == "draft"
        assert copy["id"] != created["id"]

    @pytest.mark.asyncio
    async def test_soft_delete(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, name="Doomed Rule")
        rid = created["id"]
        deleted = await authenticated_client.delete(f"/api/v1/rules/{rid}")
        assert deleted.status_code == 204
        # soft-deleted rules disappear from detail lookups
        gone = await authenticated_client.get(f"/api/v1/rules/{rid}")
        assert gone.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.delete("/api/v1/rules/99999999")
        assert resp.status_code == 404
