# =============================================================================
# Stratum AI - CDP Audience Sync API Integration Tests
# =============================================================================
"""Integration tests for the CDP audience-sync API.

Exercises the real ASGI app against Postgres + Redis: connected-platform
and audience listing, detail/history lookups, validation (invalid
platform / sync operation), 404 paths, and auth enforcement.

These cover the deterministic surface — routing, auth, tenant scoping,
validation, and not-found handling. The create/sync happy paths reach
out to external ad platforms (Meta/Google/...), so they are intentionally
left to service-level tests rather than exercised here.
"""

import uuid

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

_MISSING = "00000000-0000-0000-0000-000000000000"


def _audience(platform="meta", **extra):
    body = {
        "segment_id": str(uuid.uuid4()),
        "platform": platform,
        "ad_account_id": "act_123",
        "audience_name": "Lookalike seed",
    }
    body.update(extra)
    return body


# =============================================================================
# Read surfaces
# =============================================================================
class TestReadSurfaces:
    @pytest.mark.asyncio
    async def test_platforms_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/cdp/audience-sync/platforms")
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_list_platforms(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/cdp/audience-sync/platforms")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    @pytest.mark.asyncio
    async def test_list_audiences_envelope(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/cdp/audience-sync/audiences")
        assert resp.status_code == 200
        body = resp.json()
        assert "audiences" in body
        assert "total" in body

    @pytest.mark.asyncio
    async def test_audience_detail_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(
            f"/api/v1/cdp/audience-sync/audiences/{_MISSING}"
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_history_empty_for_unknown(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(
            f"/api/v1/cdp/audience-sync/audiences/{_MISSING}/history"
        )
        assert resp.status_code == 200
        assert resp.json()["jobs"] == []


# =============================================================================
# Validation + mutations
# =============================================================================
class TestValidationAndMutations:
    @pytest.mark.asyncio
    async def test_create_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            "/api/v1/cdp/audience-sync/audiences", json=_audience()
        )
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_create_invalid_platform_rejected(
        self, authenticated_client: AsyncClient
    ):
        resp = await authenticated_client.post(
            "/api/v1/cdp/audience-sync/audiences",
            json=_audience(platform="myspace"),
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_create_missing_field_rejected(
        self, authenticated_client: AsyncClient
    ):
        body = _audience()
        del body["ad_account_id"]
        resp = await authenticated_client.post(
            "/api/v1/cdp/audience-sync/audiences", json=body
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_trigger_sync_invalid_operation_rejected(
        self, authenticated_client: AsyncClient
    ):
        # The operation is validated before the audience is loaded, so a bad
        # operation is a deterministic 400 regardless of audience existence.
        resp = await authenticated_client.post(
            f"/api/v1/cdp/audience-sync/audiences/{_MISSING}/sync",
            json={"operation": "bogus"},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.delete(
            f"/api/v1/cdp/audience-sync/audiences/{_MISSING}"
        )
        assert resp.status_code == 404
