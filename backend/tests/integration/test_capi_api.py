# =============================================================================
# Stratum AI - CAPI (Conversions API) Endpoint Integration Tests
# =============================================================================
"""Integration tests for the CAPI surface under ``/api/v1/...``: platform
connection status and per-platform setup requirements.

These endpoints authenticate via ``CurrentUserDep`` (``get_current_user``),
which caches an async resource on the request's event loop; the suite keeps the
number of authenticated requests small so the function-scoped test loop stays
consistent.
"""

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


class TestPlatformStatus:
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/capi/platforms/status")
        assert resp.status_code in {401, 403}

    async def test_status_no_connections(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/capi/platforms/status")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert "connected_platforms" in data
        assert "setup_status" in data
