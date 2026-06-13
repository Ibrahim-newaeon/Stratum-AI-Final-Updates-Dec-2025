# =============================================================================
# Stratum AI - Tenants API Integration Tests
# =============================================================================
"""Integration tests for the tenant-management API.

Exercises the real ASGI app against Postgres + Redis: current-tenant
read, tenant detail with cross-tenant isolation (403), tenant update,
tenant user listing, and tenant listing, plus auth.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


class TestCurrentAndDetail:
    @pytest.mark.asyncio
    async def test_current_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/tenants/current")
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_current(self, authenticated_client: AsyncClient, test_tenant: dict):
        resp = await authenticated_client.get("/api/v1/tenants/current")
        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == test_tenant["id"]

    @pytest.mark.asyncio
    async def test_detail_own_tenant(
        self, authenticated_client: AsyncClient, test_tenant: dict
    ):
        resp = await authenticated_client.get(f"/api/v1/tenants/{test_tenant['id']}")
        assert resp.status_code == 200
        assert resp.json()["data"]["id"] == test_tenant["id"]

    @pytest.mark.asyncio
    async def test_detail_other_tenant_forbidden(
        self, authenticated_client: AsyncClient, test_tenant: dict
    ):
        # A non-superadmin cannot read a different tenant.
        other = test_tenant["id"] + 99999
        resp = await authenticated_client.get(f"/api/v1/tenants/{other}")
        assert resp.status_code == 403


class TestMutationsAndLists:
    @pytest.mark.asyncio
    async def test_update_own_tenant(
        self, authenticated_client: AsyncClient, test_tenant: dict
    ):
        resp = await authenticated_client.patch(
            f"/api/v1/tenants/{test_tenant['id']}",
            json={"name": "Renamed Tenant"},
        )
        assert resp.status_code == 200
        assert resp.json()["data"]["name"] == "Renamed Tenant"

    @pytest.mark.asyncio
    async def test_tenant_users(
        self, authenticated_client: AsyncClient, test_tenant: dict, test_user: dict
    ):
        resp = await authenticated_client.get(
            f"/api/v1/tenants/{test_tenant['id']}/users"
        )
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_list_tenants(self, authenticated_client: AsyncClient):
        # test_user is an ADMIN, so listing is permitted.
        resp = await authenticated_client.get("/api/v1/tenants")
        assert resp.status_code == 200
