# =============================================================================
# Stratum AI - SuperAdmin Endpoint Integration Tests
# =============================================================================
"""Integration tests for the platform SuperAdmin API under
``/api/v1/superadmin/...``: revenue, tenant portfolio, system health, churn
risks, audit log, and billing reads. Every route is gated by an internal
``require_superadmin`` (reads ``request.state.role``).

NOTE: run with the session-scoped event loop CI uses
(``-o asyncio_default_test_loop_scope=session``).
"""

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_BASE = "/api/v1/superadmin"

_GETS = [
    "/revenue",
    "/revenue/breakdown",
    "/tenants/portfolio",
    "/system/health",
    "/churn/risks",
    "/audit",
    "/billing/plans",
    # NOTE: /billing/invoices reads the `invoices` table, which is created by a
    # migration (not Base.metadata) and isn't registered in the test harness, so
    # the endpoint correctly returns a graceful 503 there — excluded from the
    # 200-smoke set rather than asserted.
]


class TestGate:
    async def test_unauthenticated_denied(self, client: AsyncClient):
        resp = await client.get(f"{_BASE}/revenue")
        assert resp.status_code in {401, 403}

    async def test_non_superadmin_denied(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"{_BASE}/revenue")
        assert resp.status_code in {401, 403}


class TestSuperadminReads:
    @pytest.mark.parametrize("path", _GETS)
    async def test_get_returns_200(self, client: AsyncClient, superadmin_headers, path):
        resp = await client.get(f"{_BASE}{path}", headers=superadmin_headers)
        assert resp.status_code == 200, f"{path}: {resp.text}"
        assert resp.json()["success"] is True
