# =============================================================================
# Stratum AI - Webhook Subscription (admin) Endpoint Integration Tests
# =============================================================================
"""Integration tests for the super-admin webhook-subscription management API
under ``/api/v1/webhooks``. Every route is gated by ``require_super_admin``;
the tenant-scoped reads also need an ``X-Tenant-ID``.
"""

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_BASE = "/api/v1/webhooks"


class TestGate:
    async def test_unauthenticated_forbidden(self, client: AsyncClient):
        resp = await client.get(_BASE)
        assert resp.status_code in {401, 403}

    async def test_non_superadmin_denied(self, authenticated_client: AsyncClient):
        # A regular ADMIN is not a super admin -> require_super_admin rejects it.
        resp = await authenticated_client.get(_BASE)
        assert resp.status_code in {401, 403}


class TestSuperadminReads:
    async def test_list_webhooks_empty(
        self, client: AsyncClient, superadmin_headers, test_tenant
    ):
        headers = {**superadmin_headers, "X-Tenant-ID": str(test_tenant["id"])}
        resp = await client.get(_BASE, headers=headers)
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"] == []
