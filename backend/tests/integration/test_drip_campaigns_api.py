# =============================================================================
# Stratum AI - Drip Campaigns API Integration Tests
# =============================================================================
"""Integration tests for the drip-campaigns (email sequence) API.

Exercises the real ASGI app: sequence creation from a flow graph,
listing, detail (200/404), update, activate/pause lifecycle, archive
(soft delete), prebuilt templates, and auth enforcement.

Sequences are persisted to PostgreSQL, so list assertions use
tenant-scoped subset checks (each test runs under a fresh tenant_id).
The trigger -> execution-log -> analytics flow is covered separately in
``test_drip_persistence_api.py``.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


def _sequence(name="Welcome series", trigger_type="user_subscribed", **extra):
    body = {
        "name": name,
        "description": "Onboard new subscribers",
        "trigger_type": trigger_type,
        "trigger_config": {},
        "nodes": [
            {"id": "n1", "type": "trigger", "position": {"x": 0, "y": 0}, "data": {}},
            {"id": "n2", "type": "email", "position": {"x": 0, "y": 1}, "data": {}},
        ],
        "edges": [{"id": "e1", "source": "n1", "target": "n2"}],
        "status": "draft",
    }
    body.update(extra)
    return body


async def _create(client: AsyncClient, **extra) -> dict:
    resp = await client.post("/api/v1/drip-campaigns", json=_sequence(**extra))
    assert resp.status_code == 200, resp.text
    return resp.json()["data"]


# =============================================================================
# Create
# =============================================================================
class TestCreateSequence:
    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/drip-campaigns", json=_sequence())
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_create_success(self, authenticated_client: AsyncClient):
        data = await _create(authenticated_client, name="Cart recovery")
        assert data["name"] == "Cart recovery"
        assert data["status"] == "draft"
        assert len(data["nodes"]) == 2

    @pytest.mark.asyncio
    async def test_invalid_trigger_type_rejected(
        self, authenticated_client: AsyncClient
    ):
        resp = await authenticated_client.post(
            "/api/v1/drip-campaigns", json=_sequence(trigger_type="not_a_trigger")
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_name_rejected(self, authenticated_client: AsyncClient):
        body = _sequence()
        del body["name"]
        resp = await authenticated_client.post("/api/v1/drip-campaigns", json=body)
        assert resp.status_code == 422


# =============================================================================
# List + detail
# =============================================================================
class TestListAndDetail:
    @pytest.mark.asyncio
    async def test_list_returns_created(self, authenticated_client: AsyncClient):
        await _create(authenticated_client, name="Seq Alpha")
        await _create(authenticated_client, name="Seq Beta")
        resp = await authenticated_client.get("/api/v1/drip-campaigns")
        assert resp.status_code == 200
        names = {s["name"] for s in resp.json()["data"]}
        assert {"Seq Alpha", "Seq Beta"} <= names

    @pytest.mark.asyncio
    async def test_detail_roundtrip(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, name="Detail Seq")
        resp = await authenticated_client.get(f"/api/v1/drip-campaigns/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "Detail Seq"

    @pytest.mark.asyncio
    async def test_detail_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/drip-campaigns/nonexistent-id")
        assert resp.status_code == 404


# =============================================================================
# Update + lifecycle
# =============================================================================
class TestMutationsAndLifecycle:
    @pytest.mark.asyncio
    async def test_update_name(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, name="Before")
        resp = await authenticated_client.put(
            f"/api/v1/drip-campaigns/{created['id']}",
            json=_sequence(name="After"),
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "After"

    @pytest.mark.asyncio
    async def test_activate_then_pause(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, name="Toggle Seq")
        sid = created["id"]
        activated = await authenticated_client.post(
            f"/api/v1/drip-campaigns/{sid}/activate"
        )
        assert activated.status_code == 200
        assert activated.json()["data"]["status"] == "active"

        paused = await authenticated_client.post(f"/api/v1/drip-campaigns/{sid}/pause")
        assert paused.status_code == 200
        assert paused.json()["data"]["status"] == "paused"

    @pytest.mark.asyncio
    async def test_delete_archives(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, name="Doomed Seq")
        resp = await authenticated_client.delete(
            f"/api/v1/drip-campaigns/{created['id']}"
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["deleted"] is True

    @pytest.mark.asyncio
    async def test_activate_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post("/api/v1/drip-campaigns/nope/activate")
        assert resp.status_code == 404


# =============================================================================
# Prebuilt templates
# =============================================================================
class TestPrebuiltTemplates:
    @pytest.mark.asyncio
    async def test_prebuilt_templates(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(
            "/api/v1/drip-campaigns/templates/prebuilt"
        )
        assert resp.status_code == 200
        assert isinstance(resp.json()["data"], list)
