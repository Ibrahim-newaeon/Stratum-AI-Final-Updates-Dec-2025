# =============================================================================
# Stratum AI - Creative Assets Endpoint Integration Tests
# =============================================================================
"""Integration tests for the DB-backed ``/assets`` CRUD surface (the JSON
create/list/get/update/soft-delete paths). The multipart ``/upload`` route
writes to the filesystem and is out of scope here.
"""

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_BASE = "/api/v1/assets"


def _payload(**overrides) -> dict:
    body = {
        "name": "Hero Banner",
        "asset_type": "image",
        "tags": ["spring", "sale"],
        "folder": "campaigns",
        "file_url": "https://cdn.example.com/hero.png",
    }
    body.update(overrides)
    return body


class TestAuth:
    async def test_list_requires_tenant(self, client):
        # No auth -> middleware leaves tenant_id unset -> empty/!=200-with-data.
        resp = await client.get(_BASE)
        # Unauthenticated callers must not receive another tenant's assets.
        assert resp.status_code in (200, 401)
        if resp.status_code == 200:
            assert resp.json()["data"]["total"] == 0


class TestCrud:
    async def test_create_then_get(self, authenticated_client):
        created = await authenticated_client.post(_BASE, json=_payload())
        assert created.status_code == 201, created.text
        data = created.json()["data"]
        assert data["name"] == "Hero Banner"
        assert data["asset_type"] == "image"
        assert data["tags"] == ["spring", "sale"]
        asset_id = data["id"]

        got = await authenticated_client.get(f"{_BASE}/{asset_id}")
        assert got.status_code == 200
        assert got.json()["data"]["id"] == asset_id

    async def test_list_includes_created(self, authenticated_client):
        created = await authenticated_client.post(
            _BASE, json=_payload(name="Listed Asset")
        )
        asset_id = created.json()["data"]["id"]

        listed = await authenticated_client.get(_BASE)
        assert listed.status_code == 200
        page = listed.json()["data"]
        assert page["total"] >= 1
        assert any(a["id"] == asset_id for a in page["items"])

    async def test_list_filter_by_asset_type(self, authenticated_client):
        await authenticated_client.post(_BASE, json=_payload(asset_type="video"))
        resp = await authenticated_client.get(_BASE, params={"asset_type": "video"})
        assert resp.status_code == 200
        assert all(a["asset_type"] == "video" for a in resp.json()["data"]["items"])

    async def test_update(self, authenticated_client):
        created = await authenticated_client.post(_BASE, json=_payload())
        asset_id = created.json()["data"]["id"]

        resp = await authenticated_client.patch(
            f"{_BASE}/{asset_id}", json={"name": "Renamed", "folder": "archive"}
        )
        assert resp.status_code == 200
        body = resp.json()["data"]
        assert body["name"] == "Renamed"
        assert body["folder"] == "archive"

    async def test_soft_delete_then_404(self, authenticated_client):
        created = await authenticated_client.post(_BASE, json=_payload())
        asset_id = created.json()["data"]["id"]

        deleted = await authenticated_client.delete(f"{_BASE}/{asset_id}")
        assert deleted.status_code == 204

        # Soft-deleted assets are no longer retrievable.
        gone = await authenticated_client.get(f"{_BASE}/{asset_id}")
        assert gone.status_code == 404

    async def test_get_missing_404(self, authenticated_client):
        resp = await authenticated_client.get(f"{_BASE}/99999999")
        assert resp.status_code == 404


class TestValidation:
    async def test_invalid_asset_type_422(self, authenticated_client):
        resp = await authenticated_client.post(
            _BASE, json=_payload(asset_type="hologram")
        )
        assert resp.status_code == 422

    async def test_missing_file_url_422(self, authenticated_client):
        body = _payload()
        del body["file_url"]
        resp = await authenticated_client.post(_BASE, json=body)
        assert resp.status_code == 422
