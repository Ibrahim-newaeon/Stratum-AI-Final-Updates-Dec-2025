# =============================================================================
# Stratum AI - Superadmin Analytics Endpoint Integration Tests
# =============================================================================
"""Integration tests for the platform-wide superadmin analytics under
``/api/v1/superadmin/analytics/superadmin/...``: platform overview, tenant
profitability, signal-health trends, and actions analytics. Every route is
gated on ``request.state.is_superadmin``.
"""

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_BASE = "/api/v1/superadmin/analytics/superadmin"

_ENDPOINTS = [
    "/platform-overview",
    "/tenant-profitability",
    "/signal-health-trends",
    "/actions-analytics",
]


class TestSuperadminGate:
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get(f"{_BASE}/platform-overview")
        assert resp.status_code in {401, 403}

    async def test_non_superadmin_forbidden(self, authenticated_client: AsyncClient):
        # authenticated_client is a regular ADMIN -> is_superadmin is False.
        resp = await authenticated_client.get(f"{_BASE}/platform-overview")
        assert resp.status_code == 403


class TestSuperadminAnalytics:
    @pytest.mark.parametrize("path", _ENDPOINTS)
    async def test_superadmin_can_read(
        self, client: AsyncClient, superadmin_headers, path
    ):
        resp = await client.get(f"{_BASE}{path}", headers=superadmin_headers)
        assert resp.status_code == 200, f"{path}: {resp.text}"
        assert resp.json()["success"] is True
