# =============================================================================
# Stratum AI - CDP Segments API Integration Tests
# =============================================================================
"""Integration tests for the CDP segments API.

Exercises the real ASGI app against Postgres + Redis: segment creation,
listing, detail (200/404), update, membership compute, preview, and
delete (204/404), plus auth enforcement and type validation.

Complements ``test_cdp.py`` (events / profiles / sources) by covering
the segment lifecycle, which it does not touch.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


_RULES = {
    "logic": "and",
    "conditions": [
        {"field": "profile.lifecycle_stage", "operator": "equals", "value": "customer"}
    ],
}


def _segment(name="High-value customers", segment_type="dynamic", **extra):
    body = {"name": name, "segment_type": segment_type, "rules": _RULES}
    body.update(extra)
    return body


async def _create(client: AsyncClient, **extra) -> dict:
    resp = await client.post("/api/v1/cdp/segments", json=_segment(**extra))
    assert resp.status_code == 201, resp.text
    return resp.json()


# =============================================================================
# Create
# =============================================================================
class TestCreateSegment:
    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/cdp/segments", json=_segment())
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_create_success(self, authenticated_client: AsyncClient):
        data = await _create(authenticated_client, name="VIPs")
        assert data["name"] == "VIPs"
        assert data["segment_type"] == "dynamic"
        assert "id" in data

    @pytest.mark.asyncio
    async def test_invalid_type_rejected(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            "/api/v1/cdp/segments", json=_segment(segment_type="not_a_type")
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_missing_name_rejected(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            "/api/v1/cdp/segments", json={"segment_type": "dynamic", "rules": _RULES}
        )
        assert resp.status_code == 422


# =============================================================================
# List + detail
# =============================================================================
class TestListAndDetail:
    @pytest.mark.asyncio
    async def test_list_returns_created(self, authenticated_client: AsyncClient):
        await _create(authenticated_client, name="Seg A")
        await _create(authenticated_client, name="Seg B")
        resp = await authenticated_client.get("/api/v1/cdp/segments")
        assert resp.status_code == 200
        body = resp.json()
        names = {s["name"] for s in body["segments"]}
        assert {"Seg A", "Seg B"} <= names
        assert body["total"] >= 2

    @pytest.mark.asyncio
    async def test_detail_roundtrip(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, name="Detail Seg")
        resp = await authenticated_client.get(f"/api/v1/cdp/segments/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Detail Seg"

    @pytest.mark.asyncio
    async def test_detail_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(
            "/api/v1/cdp/segments/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404


# =============================================================================
# Update + compute + delete
# =============================================================================
class TestMutationsAndCompute:
    @pytest.mark.asyncio
    async def test_update_name(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, name="Before")
        resp = await authenticated_client.patch(
            f"/api/v1/cdp/segments/{created['id']}", json={"name": "After"}
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "After"

    @pytest.mark.asyncio
    async def test_compute_membership(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, name="Computable")
        resp = await authenticated_client.post(
            f"/api/v1/cdp/segments/{created['id']}/compute"
        )
        # Recompute succeeds even with zero matching profiles.
        assert resp.status_code == 200
        assert "profile_count" in resp.json()

    @pytest.mark.asyncio
    async def test_preview(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            "/api/v1/cdp/segments/preview", json={"rules": _RULES, "limit": 50}
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_delete_roundtrip(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, name="Doomed Seg")
        sid = created["id"]
        deleted = await authenticated_client.delete(f"/api/v1/cdp/segments/{sid}")
        assert deleted.status_code == 204
        gone = await authenticated_client.get(f"/api/v1/cdp/segments/{sid}")
        assert gone.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.delete(
            "/api/v1/cdp/segments/00000000-0000-0000-0000-000000000000"
        )
        assert resp.status_code == 404
