# =============================================================================
# Stratum AI - CAPI (Conversions API) Endpoint Integration Tests
# =============================================================================
"""Integration tests for the CAPI surface under ``/api/v1/capi/...``: platform
connection status, per-platform setup requirements, data-quality reads, and
PII detection.

NOTE: run with the session-scoped event loop CI uses
(``-o asyncio_default_test_loop_scope=session``) — multiple ``get_current_user``
requests per module rely on a single consistent loop.
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


class TestDataQuality:
    async def test_quality_report(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"{_BASE}/quality/report")
        assert resp.status_code == 200, resp.text
        assert resp.json()["success"] is True

    async def test_quality_live(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"{_BASE}/quality/live")
        assert resp.status_code == 200, resp.text
        assert "data" in resp.json()


class TestPiiDetect:
    async def test_detects_pii_fields(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            f"{_BASE}/pii/detect",
            json={"email": "buyer@example.com", "phone": "+15551234567"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert "detections" in data
        assert "total_pii_fields" in data
