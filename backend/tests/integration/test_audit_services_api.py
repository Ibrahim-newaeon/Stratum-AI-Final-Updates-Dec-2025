# =============================================================================
# Stratum AI - Audit Services Endpoint Integration Tests
# =============================================================================
"""Integration tests for the audit-services surface under
``/api/v1/audit/audit-services/...``. This is a large ML-service router; these
tests cover the stable read/info/admin endpoints (health, info, metrics, and
the admin config/status/rate-limit views) plus the auth + admin gates.
"""

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_BASE = "/api/v1/audit/audit-services"

# GET endpoints that don't require request bodies, ML execution, or seeded data.
_SMOKE_GETS = [
    "/health",
    "/info",
    "/metrics",
    "/admin/services/status",
    "/admin/config",
    "/admin/rate-limits",
]


class TestAuth:
    @pytest.mark.parametrize("path", ["/info", "/admin/config"])
    async def test_requires_auth(self, client: AsyncClient, path):
        resp = await client.get(f"{_BASE}{path}")
        assert resp.status_code in {401, 403}


class TestSmoke:
    @pytest.mark.parametrize("path", _SMOKE_GETS)
    async def test_get_returns_200(self, authenticated_client: AsyncClient, path):
        resp = await authenticated_client.get(f"{_BASE}{path}")
        assert resp.status_code == 200, f"{path}: {resp.text}"


class TestHealth:
    async def test_health_reports_services(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"{_BASE}/health")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["status"] in {"healthy", "degraded"}
        assert isinstance(body["services"], dict)
        assert body["services"]  # at least one service reported
