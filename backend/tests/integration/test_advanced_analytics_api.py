# =============================================================================
# Stratum AI - Advanced Analytics Endpoint Integration Tests
# =============================================================================
"""Integration tests for the advanced-analytics surface under
``/api/v1/analytics/advanced/...``: funnel analysis, cohort analysis, and the
superadmin-gated SQL editor.

This also guards a routing fix: the router declares
``prefix="/analytics/advanced"`` and was *also* mounted with the same prefix,
so the routes had previously been reachable only at the doubled path
``/analytics/advanced/analytics/advanced/...`` (the documented single-prefix
path 404'd). The mount-level prefix was removed; these tests hit the correct
single-prefix path.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_BASE = "/api/v1/analytics/advanced"
_DATES = {"date_from": "2026-01-01", "date_to": "2026-06-01"}


# =============================================================================
# Funnel analysis
# =============================================================================
class TestFunnel:
    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post(
            f"{_BASE}/funnel",
            json={"name": "f", "steps": ["impression", "click"], **_DATES},
        )
        assert resp.status_code == 401

    async def test_empty_funnel(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            f"{_BASE}/funnel",
            json={
                "name": "Acquisition",
                "steps": ["impression", "click", "purchase"],
                **_DATES,
            },
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["total_entries"] == 0
        assert len(data["steps"]) == 3
        assert data["steps"][0]["step_name"] == "impression"


# =============================================================================
# Cohort analysis
# =============================================================================
class TestCohorts:
    async def test_empty_cohorts(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            f"{_BASE}/cohorts",
            json={"metric": "retention", "period": "weekly", **_DATES},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["rows"] == []
        assert data["metric"] == "retention"


# =============================================================================
# SQL editor (superadmin-gated)
# =============================================================================
class TestSqlEditor:
    """The SQL editor is superadmin-gated. Its *executing* path can't be
    exercised here: superadmin requests trigger ``_log_super_admin_bypass``,
    which opens its own session via ``get_async_session()`` directly (bypassing
    the test dependency override) and binds a connection to a different event
    loop. So this only asserts the authorization gate.
    """

    async def test_non_superadmin_forbidden(self, authenticated_client: AsyncClient):
        # authenticated_client is ADMIN, not superadmin.
        resp = await authenticated_client.post(
            f"{_BASE}/sql", json={"query": "SELECT platform FROM campaigns"}
        )
        assert resp.status_code == 403
