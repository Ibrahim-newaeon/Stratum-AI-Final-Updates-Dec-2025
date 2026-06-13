# =============================================================================
# Stratum AI - Changelog API Integration Tests
# =============================================================================
"""Integration tests for the changelog API.

Exercises the real ASGI app against Postgres + Redis: admin-gated entry
creation, listing, detail (200/404), summary, per-entry and bulk
mark-read, update, delete (204/404), validation, and auth enforcement.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

_MISSING = 99999999


def _entry(version="1.0.0", title="New dashboard", **extra):
    body = {
        "version": version,
        "title": title,
        "description": "Ships the redesigned overview.",
        "type": "feature",
        "is_published": True,
    }
    body.update(extra)
    return body


async def _create(client: AsyncClient, **extra) -> dict:
    resp = await client.post("/api/v1/changelog", json=_entry(**extra))
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]


# =============================================================================
# Create
# =============================================================================
class TestCreateEntry:
    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/changelog", json=_entry())
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_create_success(self, authenticated_client: AsyncClient):
        data = await _create(authenticated_client, version="2.1.0", title="Autopilot")
        assert data["version"] == "2.1.0"
        assert data["title"] == "Autopilot"
        assert data["is_published"] is True

    @pytest.mark.asyncio
    async def test_unknown_type_coerced_to_feature(
        self, authenticated_client: AsyncClient
    ):
        data = await _create(authenticated_client, version="3.0.0", type="not_a_type")
        assert data["type"] == "feature"

    @pytest.mark.asyncio
    async def test_missing_title_rejected(self, authenticated_client: AsyncClient):
        body = _entry()
        del body["title"]
        resp = await authenticated_client.post("/api/v1/changelog", json=body)
        assert resp.status_code == 422


# =============================================================================
# List + detail + summary
# =============================================================================
class TestReadSurfaces:
    @pytest.mark.asyncio
    async def test_list_returns_published(self, authenticated_client: AsyncClient):
        await _create(authenticated_client, version="1.1.0", title="Entry One")
        await _create(authenticated_client, version="1.2.0", title="Entry Two")
        resp = await authenticated_client.get("/api/v1/changelog")
        assert resp.status_code == 200
        titles = {e["title"] for e in resp.json()["data"]}
        assert {"Entry One", "Entry Two"} <= titles

    @pytest.mark.asyncio
    async def test_detail_roundtrip(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, title="Detail Entry")
        resp = await authenticated_client.get(f"/api/v1/changelog/{created['id']}")
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "Detail Entry"

    @pytest.mark.asyncio
    async def test_detail_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"/api/v1/changelog/{_MISSING}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_summary(self, authenticated_client: AsyncClient):
        await _create(authenticated_client, version="9.9.9", title="Fresh")
        resp = await authenticated_client.get("/api/v1/changelog/summary")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "unread_count" in data
        assert "has_new_features" in data


# =============================================================================
# Read tracking + update + delete
# =============================================================================
class TestMutations:
    @pytest.mark.asyncio
    async def test_mark_read(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, title="To Read")
        resp = await authenticated_client.post(
            f"/api/v1/changelog/{created['id']}/mark-read"
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_mark_all_read(self, authenticated_client: AsyncClient):
        await _create(authenticated_client, version="4.0.0", title="Bulk")
        resp = await authenticated_client.post("/api/v1/changelog/mark-all-read")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_update_entry(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, title="Before")
        resp = await authenticated_client.patch(
            f"/api/v1/changelog/{created['id']}", json={"title": "After"}
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["title"] == "After"

    @pytest.mark.asyncio
    async def test_update_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.patch(
            f"/api/v1/changelog/{_MISSING}", json={"title": "Nope"}
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_roundtrip(self, authenticated_client: AsyncClient):
        created = await _create(authenticated_client, title="Doomed")
        eid = created["id"]
        deleted = await authenticated_client.delete(f"/api/v1/changelog/{eid}")
        assert deleted.status_code == 204
        gone = await authenticated_client.get(f"/api/v1/changelog/{eid}")
        assert gone.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.delete(f"/api/v1/changelog/{_MISSING}")
        assert resp.status_code == 404
