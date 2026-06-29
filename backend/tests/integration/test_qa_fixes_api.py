# =============================================================================
# Stratum AI - QA Fixes Endpoint Integration Tests
# =============================================================================
"""Integration tests for the QA-fixes surface under ``/api/v1/qa-fixes/...``:
quality-issue detection, the prioritized fix playbook, and applied-fix
history. All tenant-scoped routes enforce a path-tenant / token match.
"""

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_BASE = "/api/v1/qa-fixes"


class TestHealth:
    async def test_health(self, authenticated_client: AsyncClient):
        # The handler takes no auth dependency, but the tenant middleware gates
        # the path, so an authenticated client is required to reach it.
        resp = await authenticated_client.get(f"{_BASE}/health")
        assert resp.status_code == 200


class TestIssues:
    async def test_requires_auth(self, client: AsyncClient, test_tenant):
        resp = await client.get(f"{_BASE}/{test_tenant['id']}/issues")
        assert resp.status_code in {401, 403}

    async def test_cross_tenant_forbidden(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        resp = await authenticated_client.get(
            f"{_BASE}/{test_tenant['id'] + 99999}/issues"
        )
        assert resp.status_code == 403

    async def test_no_connections_empty_issues(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        resp = await authenticated_client.get(f"{_BASE}/{test_tenant['id']}/issues")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["total"] == 0
        assert data["issues"] == []


class TestPlaybook:
    async def test_empty_playbook(self, authenticated_client: AsyncClient, test_tenant):
        resp = await authenticated_client.get(f"{_BASE}/{test_tenant['id']}/playbook")
        assert resp.status_code == 200, resp.text
        assert "data" in resp.json()

    async def test_cross_tenant_forbidden(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        resp = await authenticated_client.get(
            f"{_BASE}/{test_tenant['id'] + 99999}/playbook"
        )
        assert resp.status_code == 403


class TestHistory:
    async def test_empty_history(self, authenticated_client: AsyncClient, test_tenant):
        resp = await authenticated_client.get(f"{_BASE}/{test_tenant['id']}/history")
        assert resp.status_code == 200, resp.text
        assert "data" in resp.json()
