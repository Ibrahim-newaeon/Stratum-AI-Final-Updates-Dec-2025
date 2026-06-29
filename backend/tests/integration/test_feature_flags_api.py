# =============================================================================
# Stratum AI - Feature Flags API Integration Tests
# =============================================================================
"""Integration tests for the tenant + superadmin feature-flags API.

Exercises the real ASGI app against Postgres + Redis: tenant feature
retrieval/update with tenant-context enforcement, and the superadmin
cross-tenant routes (which gate on the ``superadmin`` role).

The superadmin route tests also guard the role-attribute fix: these
handlers previously read ``request.state.user_role`` (never set by the
tenant middleware, which populates ``request.state.role``), so every
superadmin feature-flag route returned 403 regardless of caller.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


# =============================================================================
# Tenant routes
# =============================================================================
class TestTenantFeatures:
    @pytest.mark.asyncio
    async def test_get_requires_auth(self, client: AsyncClient, test_tenant: dict):
        resp = await client.get(f"/api/v1/tenant/{test_tenant['id']}/features")
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_get_features(
        self, authenticated_client: AsyncClient, test_tenant: dict
    ):
        resp = await authenticated_client.get(
            f"/api/v1/tenant/{test_tenant['id']}/features"
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "features" in data
        assert "categories" in data
        assert "descriptions" in data

    @pytest.mark.asyncio
    async def test_get_other_tenant_forbidden(
        self, authenticated_client: AsyncClient, test_tenant: dict
    ):
        other = test_tenant["id"] + 99999
        resp = await authenticated_client.get(f"/api/v1/tenant/{other}/features")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_update_features_persists(
        self, authenticated_client: AsyncClient, test_tenant: dict
    ):
        tid = test_tenant["id"]
        updated = await authenticated_client.put(
            f"/api/v1/tenant/{tid}/features",
            json={"campaign_builder": True, "autopilot_level": 2},
        )
        assert updated.status_code == 200
        feats = updated.json()["data"]["features"]
        assert feats["campaign_builder"] is True
        assert feats["autopilot_level"] == 2

        # Override is persisted and visible on a subsequent GET.
        fetched = await authenticated_client.get(f"/api/v1/tenant/{tid}/features")
        assert fetched.json()["data"]["features"]["campaign_builder"] is True

    @pytest.mark.asyncio
    async def test_update_rejects_out_of_range(
        self, authenticated_client: AsyncClient, test_tenant: dict
    ):
        resp = await authenticated_client.put(
            f"/api/v1/tenant/{test_tenant['id']}/features",
            json={"autopilot_level": 9},  # bounded 0..2
        )
        assert resp.status_code == 422


# =============================================================================
# Superadmin routes (role-gated)
# =============================================================================
class TestSuperadminFeatures:
    @pytest.mark.asyncio
    async def test_non_superadmin_forbidden(
        self, authenticated_client: AsyncClient, test_tenant: dict
    ):
        # authenticated_client is an ADMIN, not a superadmin → 403.
        resp = await authenticated_client.get(
            f"/api/v1/superadmin/tenants/{test_tenant['id']}/features"
        )
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_superadmin_get_features(
        self, client: AsyncClient, superadmin_headers: dict, test_tenant: dict
    ):
        resp = await client.get(
            f"/api/v1/superadmin/tenants/{test_tenant['id']}/features",
            headers=superadmin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["tenant_id"] == test_tenant["id"]
        assert "features" in data

    @pytest.mark.asyncio
    async def test_superadmin_update_features(
        self, client: AsyncClient, superadmin_headers: dict, test_tenant: dict
    ):
        resp = await client.put(
            f"/api/v1/superadmin/tenants/{test_tenant['id']}/features",
            headers=superadmin_headers,
            json={"signal_health": True},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["features"]["signal_health"] is True

    @pytest.mark.asyncio
    async def test_superadmin_reset_features(
        self, client: AsyncClient, superadmin_headers: dict, test_tenant: dict
    ):
        resp = await client.post(
            f"/api/v1/superadmin/tenants/{test_tenant['id']}/features/reset",
            headers=superadmin_headers,
        )
        assert resp.status_code == 200
        assert "features" in resp.json()["data"]

    @pytest.mark.asyncio
    async def test_feature_metadata(
        self, client: AsyncClient, superadmin_headers: dict
    ):
        resp = await client.get(
            "/api/v1/superadmin/feature-metadata", headers=superadmin_headers
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert "categories" in data
        assert "descriptions" in data
