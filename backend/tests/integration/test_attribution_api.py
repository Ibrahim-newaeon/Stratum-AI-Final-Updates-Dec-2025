# =============================================================================
# Stratum AI - Attribution API Integration Tests
# =============================================================================
"""Integration tests for the attribution summary / model-comparison API.

Exercises the real ASGI app against Postgres + Redis: auth enforcement,
required-parameter validation, and the empty-data response envelopes for
a tenant with no attribution data yet.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

_RANGE = "start_date=2026-06-01T00:00:00&end_date=2026-06-30T23:59:59"


class TestAttributionSummary:
    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get(f"/api/v1/attribution/summary?{_RANGE}")
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_missing_dates_rejected(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/attribution/summary")
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_empty_summary_envelope(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"/api/v1/attribution/summary?{_RANGE}")
        assert resp.status_code == 200
        assert "data" in resp.json()


class TestModelComparison:
    @pytest.mark.asyncio
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get(f"/api/v1/attribution/models/compare?{_RANGE}")
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_compare_responds(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(
            f"/api/v1/attribution/models/compare?{_RANGE}"
        )
        assert resp.status_code == 200
