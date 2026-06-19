# =============================================================================
# Stratum AI - CAPI (Conversions API) Endpoint Integration Tests
# =============================================================================
"""Integration tests for the CAPI surface under ``/api/v1/capi/...``: platform
connection status and per-platform setup requirements.
"""

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_BASE = "/api/v1/capi"


class TestPlatformStatus:
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get(f"{_BASE}/platforms/status")
        assert resp.status_code in {401, 403}

    async def test_status_no_connections(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"{_BASE}/platforms/status")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert "connected_platforms" in data
        assert "setup_status" in data


class TestPlatformRequirements:
    async def test_requirements_for_platform(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"{_BASE}/platforms/meta/requirements")
        assert resp.status_code == 200, resp.text
        assert "data" in resp.json()
