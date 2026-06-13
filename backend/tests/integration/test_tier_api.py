# =============================================================================
# Stratum AI - Tier / Subscription API Integration Tests
# =============================================================================
"""Integration tests for the subscription-tier API.

Exercises the real ASGI app: current-tier info, feature lists, per-feature
access checks, limits, tier comparison, and auth. Assertions check the
response contract (a valid tier string + the right shape) rather than a
specific tier, since tier resolution depends on the harness.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration

_TIERS = {"free", "starter", "professional", "enterprise", "custom"}


class TestTierInfo:
    @pytest.mark.asyncio
    async def test_current_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/tier/current")
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_current_tier(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/tier/current")
        assert resp.status_code == 200
        assert "tier" in resp.json() or "name" in resp.json()

    @pytest.mark.asyncio
    async def test_features_list(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/tier/features")
        assert resp.status_code == 200
        body = resp.json()
        assert body["tier"] in _TIERS
        assert isinstance(body["features"], list)

    @pytest.mark.asyncio
    async def test_limits(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/tier/limits")
        assert resp.status_code == 200
        body = resp.json()
        assert body["tier"] in _TIERS
        assert "limits" in body

    @pytest.mark.asyncio
    async def test_specific_limit(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/tier/limits/max_users")
        assert resp.status_code == 200
        body = resp.json()
        assert body["limit"] == "max_users"
        assert "value" in body


class TestFeatureChecks:
    @pytest.mark.asyncio
    async def test_known_feature(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(
            "/api/v1/tier/features/signal_health_monitoring"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["feature"] == "signal_health_monitoring"
        assert isinstance(body["available"], bool)
        assert body["tier"] in _TIERS

    @pytest.mark.asyncio
    async def test_unknown_feature(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(
            "/api/v1/tier/features/not_a_real_feature"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["available"] is False
        assert body.get("error") == "Unknown feature"


class TestTierCatalog:
    @pytest.mark.asyncio
    async def test_all_tiers(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/tier/all")
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_compare(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/tier/compare")
        assert resp.status_code == 200
