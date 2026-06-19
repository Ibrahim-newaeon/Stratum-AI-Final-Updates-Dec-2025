# =============================================================================
# Stratum AI - Dashboard Endpoint Integration Tests
# =============================================================================
"""Integration tests for the main dashboard API under ``/api/v1/dashboard/...``:
overview KPIs, campaign performance, recommendations, activity feed,
quick-actions, and the signal-health summary. All routes authenticate via
``get_current_user``.

NOTE: run with the session-scoped event loop the CI uses, e.g.
``-o asyncio_default_test_loop_scope=session`` — multiple authenticated
requests per module rely on a single consistent loop.
"""

import pytest
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_BASE = "/api/v1/dashboard"

_GETS = [
    "/overview",
    "/campaigns",
    "/recommendations",
    "/activity",
    "/quick-actions",
    "/signal-health",
    # Intelligence / briefing surfaces (all DB-backed, no LLM/external calls).
    "/morning-briefing",
    "/signal-recovery",
    "/predictive-budget",
    "/ai-report",
    "/churn-prevention",
    "/settings/metric-visibility",
    "/anomaly-narratives",
    "/notifications-prioritized",
    "/cross-platform-optimizer",
    "/audience-lifecycle",
]


class TestAuth:
    @pytest.mark.parametrize("path", ["/overview", "/recommendations"])
    async def test_requires_auth(self, client: AsyncClient, path):
        resp = await client.get(f"{_BASE}{path}")
        assert resp.status_code in {401, 403}


class TestSmoke:
    @pytest.mark.parametrize("path", _GETS)
    async def test_get_returns_200(self, authenticated_client: AsyncClient, path):
        resp = await authenticated_client.get(f"{_BASE}{path}")
        assert resp.status_code == 200, f"{path}: {resp.text}"
        assert resp.json()["success"] is True


class TestOverview:
    async def test_overview_period_filter(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(
            f"{_BASE}/overview", params={"period": "30d"}
        )
        assert resp.status_code == 200, resp.text
        assert "data" in resp.json()
