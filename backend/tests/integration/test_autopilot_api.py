# =============================================================================
# Stratum AI - Autopilot Endpoint Integration Tests
# =============================================================================
"""Integration tests for the tenant-scoped autopilot API under
``/api/v1/tenant/{tenant_id}/autopilot/...``: status, action queue
listing, and the action/outcome summaries. All routes enforce a path-tenant /
token match.
"""

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


def _base(tenant_id: int) -> str:
    return f"/api/v1/tenant/{tenant_id}/autopilot"


class TestStatus:
    async def test_requires_auth(self, client: AsyncClient, test_tenant):
        resp = await client.get(f"{_base(test_tenant['id'])}/status")
        assert resp.status_code in {401, 403}

    async def test_cross_tenant_forbidden(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        resp = await authenticated_client.get(
            f"{_base(test_tenant['id'] + 99999)}/status"
        )
        assert resp.status_code == 403

    async def test_status_defaults(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        resp = await authenticated_client.get(f"{_base(test_tenant['id'])}/status")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert "autopilot_level" in data
        assert "pending_actions" in data
        assert "caps" in data
        assert isinstance(data["enabled"], bool)


class TestActions:
    async def test_empty_actions(self, authenticated_client: AsyncClient, test_tenant):
        resp = await authenticated_client.get(f"{_base(test_tenant['id'])}/actions")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["count"] == 0
        assert data["actions"] == []

    async def test_actions_summary(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        resp = await authenticated_client.get(
            f"{_base(test_tenant['id'])}/actions/summary"
        )
        assert resp.status_code == 200, resp.text
        assert "data" in resp.json()

    async def test_outcomes_summary(
        self, authenticated_client: AsyncClient, test_tenant
    ):
        resp = await authenticated_client.get(
            f"{_base(test_tenant['id'])}/outcomes/summary"
        )
        assert resp.status_code == 200, resp.text
        assert "data" in resp.json()
