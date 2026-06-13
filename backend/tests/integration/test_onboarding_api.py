# =============================================================================
# Stratum AI - Onboarding API Integration Tests
# =============================================================================
"""Integration tests for the multi-step onboarding wizard API.

Exercises the real ASGI app against Postgres + Redis: status/check
bootstrapping, each step's save endpoint, validation, the full
five-step completion flow (status → completed), and skip/reset.
"""

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


_BUSINESS_PROFILE = {
    "industry": "ecommerce",
    "monthly_ad_spend": "10k_50k",
    "team_size": "2_5",
    "company_website": "https://example.com",
    "target_markets": ["US", "CA"],
}
_PLATFORM_SELECTION = {"platforms": ["meta", "google"]}
_GOALS_SETUP = {"primary_kpi": "roas", "target_roas": 3.0, "currency": "USD"}
_AUTOMATION_PREFS = {"automation_mode": "assisted", "auto_pause_enabled": True}
_TRUST_GATE = {"trust_threshold_autopilot": 70, "trust_threshold_alert": 40}


async def _complete_all_steps(client: AsyncClient):
    for path, body in [
        ("business-profile", _BUSINESS_PROFILE),
        ("platform-selection", _PLATFORM_SELECTION),
        ("goals-setup", _GOALS_SETUP),
        ("automation-preferences", _AUTOMATION_PREFS),
        ("trust-gate-config", _TRUST_GATE),
    ]:
        resp = await client.post(f"/api/v1/onboarding/{path}", json=body)
        assert resp.status_code == 200, f"{path}: {resp.text}"


# =============================================================================
# Status / check bootstrap
# =============================================================================
class TestStatusAndCheck:
    @pytest.mark.asyncio
    async def test_check_requires_auth(self, client: AsyncClient):
        resp = await client.get("/api/v1/onboarding/check")
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_check_required_initially(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/onboarding/check")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["required"] is True
        assert data["redirect_to"] == "/onboarding"

    @pytest.mark.asyncio
    async def test_status_starts_not_started(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/onboarding/status")
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["status"] == "not_started"
        assert data["progress_percentage"] == 0


# =============================================================================
# Individual steps + validation
# =============================================================================
class TestSteps:
    @pytest.mark.asyncio
    async def test_business_profile_advances(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            "/api/v1/onboarding/business-profile", json=_BUSINESS_PROFILE
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["completed"] is True
        assert data["step"] == "business_profile"
        assert data["progress_percentage"] > 0

    @pytest.mark.asyncio
    async def test_invalid_industry_rejected(self, authenticated_client: AsyncClient):
        body = {**_BUSINESS_PROFILE, "industry": "not_an_industry"}
        resp = await authenticated_client.post(
            "/api/v1/onboarding/business-profile", json=body
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_platform_rejected(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            "/api/v1/onboarding/platform-selection",
            json={"platforms": ["myspace"]},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_trust_gate_alert_above_autopilot_rejected(
        self, authenticated_client: AsyncClient
    ):
        # Alert threshold must be below the autopilot threshold.
        resp = await authenticated_client.post(
            "/api/v1/onboarding/trust-gate-config",
            json={"trust_threshold_autopilot": 60, "trust_threshold_alert": 65},
        )
        assert resp.status_code == 422


# =============================================================================
# Full flow + skip + reset
# =============================================================================
class TestFlowSkipReset:
    @pytest.mark.asyncio
    async def test_full_completion_flow(self, authenticated_client: AsyncClient):
        await _complete_all_steps(authenticated_client)

        status = await authenticated_client.get("/api/v1/onboarding/status")
        data = status.json()["data"]
        assert data["status"] == "completed"
        assert data["progress_percentage"] == 100
        assert data["business_profile"]["industry"] == "ecommerce"
        assert data["goals_setup"]["primary_kpi"] == "roas"

        # Once complete, onboarding is no longer required.
        check = await authenticated_client.get("/api/v1/onboarding/check")
        assert check.json()["data"]["required"] is False

    @pytest.mark.asyncio
    async def test_skip(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post("/api/v1/onboarding/skip")
        assert resp.status_code == 200
        status = await authenticated_client.get("/api/v1/onboarding/status")
        assert status.json()["data"]["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_reset_after_progress(self, authenticated_client: AsyncClient):
        await authenticated_client.post(
            "/api/v1/onboarding/business-profile", json=_BUSINESS_PROFILE
        )
        reset = await authenticated_client.post("/api/v1/onboarding/reset")
        assert reset.status_code == 200
        status = await authenticated_client.get("/api/v1/onboarding/status")
        assert status.json()["data"]["status"] == "not_started"
