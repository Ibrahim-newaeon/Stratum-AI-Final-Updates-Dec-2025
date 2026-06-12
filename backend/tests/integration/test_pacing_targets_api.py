# =============================================================================
# Stratum AI - Pacing Targets API Integration Tests
# =============================================================================
"""Integration tests for the pacing/targets API.

Exercises the real ASGI app against Postgres + Redis: target creation,
listing, detail (200/404), validation, and auth enforcement.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


def _target(name="Q3 Spend Target", metric_type="spend", value=10000.0, **extra):
    body = {
        "name": name,
        "metric_type": metric_type,
        "target_value": value,
        "period_type": "monthly",
        "period_start": "2026-07-01",
        "period_end": "2026-07-31",
    }
    body.update(extra)
    return body


# =============================================================================
# Create
# =============================================================================
class TestCreateTarget:
    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/pacing/targets", json=_target())
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_create_success(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            "/api/v1/pacing/targets",
            json=_target(name="Revenue Goal", metric_type="revenue"),
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert body["target"]["name"] == "Revenue Goal"
        assert body["target"]["metric_type"] == "revenue"

    @pytest.mark.asyncio
    async def test_invalid_metric_rejected(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            "/api/v1/pacing/targets", json=_target(metric_type="not_a_metric")
        )
        assert resp.status_code == 422


# =============================================================================
# List + detail
# =============================================================================
class TestListAndDetail:
    @pytest.mark.asyncio
    async def test_list_returns_created_targets(
        self, authenticated_client: AsyncClient
    ):
        await authenticated_client.post(
            "/api/v1/pacing/targets", json=_target(name="Target A")
        )
        await authenticated_client.post(
            "/api/v1/pacing/targets", json=_target(name="Target B", metric_type="roas")
        )
        resp = await authenticated_client.get("/api/v1/pacing/targets")
        assert resp.status_code == 200
        body = resp.json()
        # response wraps the list; find the target names anywhere in the payload
        names = {t["name"] for t in body.get("targets", body.get("data", []))}
        assert {"Target A", "Target B"} <= names

    @pytest.mark.asyncio
    async def test_detail_roundtrip(self, authenticated_client: AsyncClient):
        created = await authenticated_client.post(
            "/api/v1/pacing/targets", json=_target(name="Detail Target")
        )
        target_id = created.json()["target"]["id"]
        resp = await authenticated_client.get(f"/api/v1/pacing/targets/{target_id}")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_detail_not_found(self, authenticated_client: AsyncClient):
        # well-formed but nonexistent UUID
        resp = await authenticated_client.get(
            "/api/v1/pacing/targets/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404
