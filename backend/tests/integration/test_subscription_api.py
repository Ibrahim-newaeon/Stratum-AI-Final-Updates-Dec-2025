# =============================================================================
# Stratum AI - Subscription Config Endpoint Integration Tests
# =============================================================================
"""Integration test for ``GET /api/v1/subscription/config`` -- the static
subscription configuration (grace period, expiry warning, available plans).
The status/check/warnings/usage routes resolve subscription state via a service
that opens its own session outside the test override, so only the static config
endpoint is covered here.
"""

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_BASE = "/api/v1/subscription"


class TestConfig:
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.get(f"{_BASE}/config")
        assert resp.status_code in {401, 403}

    async def test_config_lists_plans(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"{_BASE}/config")
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert "grace_period_days" in body
        tiers = {p["tier"] for p in body["available_plans"]}
        assert {"starter", "professional", "enterprise"} <= tiers
