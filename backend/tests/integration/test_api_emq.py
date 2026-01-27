# =============================================================================
# Stratum AI - EMQ API Integration Tests
# =============================================================================
"""
Integration tests for EMQ v2 API endpoints.

Tests cover:
- EMQ score retrieval
- Confidence band details
- Playbook management
- Incident timeline
- ROAS impact calculation
- Signal volatility
- Autopilot state management
"""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


class TestEmqScoreEndpoint:
    """Tests for GET /api/v1/tenants/{tenant_id}/emq/score"""

    @pytest.mark.asyncio
    async def test_get_emq_score_success(
        self, authenticated_client: AsyncClient, test_tenant: dict, test_signal_health: dict
    ):
        """Test successful EMQ score retrieval."""
        response = await authenticated_client.get(f"/api/v1/tenants/{test_tenant['id']}/emq/score")

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "data" in data
        assert "score" in data["data"]
        assert "previousScore" in data["data"]
        assert "confidenceBand" in data["data"]
        assert "drivers" in data["data"]
        assert "lastUpdated" in data["data"]

        # Score should be between 0 and 100
        assert 0 <= data["data"]["score"] <= 100

        # Confidence band should be one of the valid values
        assert data["data"]["confidenceBand"] in ["reliable", "directional", "unsafe"]

        # Should have 5 drivers
        assert len(data["data"]["drivers"]) == 5

    @pytest.mark.asyncio
    async def test_get_emq_score_with_date(
        self, authenticated_client: AsyncClient, test_tenant: dict
    ):
        """Test EMQ score retrieval with specific date."""
        target_date = (datetime.now(UTC).date() - timedelta(days=1)).isoformat()

        response = await authenticated_client.get(
            f"/api/v1/tenants/{test_tenant['id']}/emq/score",
            params={"date": target_date},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_get_emq_score_invalid_date(
        self, authenticated_client: AsyncClient, test_tenant: dict
    ):
        """Test EMQ score with invalid date format."""
        response = await authenticated_client.get(
            f"/api/v1/tenants/{test_tenant['id']}/emq/score",
            params={"date": "invalid-date"},
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_emq_score_unauthorized(self, client: AsyncClient, test_tenant: dict):
        """Test EMQ score without authentication."""
        response = await client.get(f"/api/v1/tenants/{test_tenant['id']}/emq/score")

        # Should return 401 or 403 depending on auth implementation
        assert response.status_code in [401, 403]


class TestConfidenceEndpoint:
    """Tests for GET /api/v1/tenants/{tenant_id}/emq/confidence"""

    @pytest.mark.asyncio
    async def test_get_confidence_success(
        self, authenticated_client: AsyncClient, test_tenant: dict
    ):
        """Test successful confidence band retrieval."""
        response = await authenticated_client.get(
            f"/api/v1/tenants/{test_tenant['id']}/emq/confidence"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "band" in data["data"]
        assert "score" in data["data"]
        assert "thresholds" in data["data"]
        assert "factors" in data["data"]

        # Verify thresholds structure
        assert "reliable" in data["data"]["thresholds"]
        assert "directional" in data["data"]["thresholds"]


class TestPlaybookEndpoint:
    """Tests for playbook management endpoints."""

    @pytest.mark.asyncio
    async def test_get_playbook_success(self, authenticated_client: AsyncClient, test_tenant: dict):
        """Test successful playbook retrieval."""
        response = await authenticated_client.get(
            f"/api/v1/tenants/{test_tenant['id']}/emq/playbook"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert isinstance(data["data"], list)

        if len(data["data"]) > 0:
            item = data["data"][0]
            assert "id" in item
            assert "title" in item
            assert "priority" in item
            assert item["priority"] in ["critical", "high", "medium", "low"]

    @pytest.mark.asyncio
    async def test_update_playbook_item(self, authenticated_client: AsyncClient, test_tenant: dict):
        """Test playbook item update."""
        # First get the playbook
        response = await authenticated_client.get(
            f"/api/v1/tenants/{test_tenant['id']}/emq/playbook"
        )
        playbook = response.json()["data"]

        if len(playbook) > 0:
            item_id = playbook[0]["id"]

            # Update the item
            response = await authenticated_client.patch(
                f"/api/v1/tenants/{test_tenant['id']}/emq/playbook/{item_id}",
                json={
                    "status": "in_progress",
                    "owner": "test@example.com",
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["data"]["status"] == "in_progress"


class TestIncidentsEndpoint:
    """Tests for GET /api/v1/tenants/{tenant_id}/emq/incidents"""

    @pytest.mark.asyncio
    async def test_get_incidents_success(
        self, authenticated_client: AsyncClient, test_tenant: dict
    ):
        """Test successful incidents retrieval."""
        start_date = (datetime.now(UTC).date() - timedelta(days=7)).isoformat()
        end_date = datetime.now(UTC).date().isoformat()

        response = await authenticated_client.get(
            f"/api/v1/tenants/{test_tenant['id']}/emq/incidents",
            params={"start_date": start_date, "end_date": end_date},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert isinstance(data["data"], list)

    @pytest.mark.asyncio
    async def test_get_incidents_missing_dates(
        self, authenticated_client: AsyncClient, test_tenant: dict
    ):
        """Test incidents without required date parameters."""
        response = await authenticated_client.get(
            f"/api/v1/tenants/{test_tenant['id']}/emq/incidents"
        )

        assert response.status_code == 422  # Validation error


class TestImpactEndpoint:
    """Tests for GET /api/v1/tenants/{tenant_id}/emq/impact"""

    @pytest.mark.asyncio
    async def test_get_impact_success(self, authenticated_client: AsyncClient, test_tenant: dict):
        """Test successful ROAS impact retrieval."""
        start_date = (datetime.now(UTC).date() - timedelta(days=30)).isoformat()
        end_date = datetime.now(UTC).date().isoformat()

        response = await authenticated_client.get(
            f"/api/v1/tenants/{test_tenant['id']}/emq/impact",
            params={"start_date": start_date, "end_date": end_date},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "totalImpact" in data["data"]
        assert "currency" in data["data"]
        assert "breakdown" in data["data"]


class TestVolatilityEndpoint:
    """Tests for GET /api/v1/tenants/{tenant_id}/emq/volatility"""

    @pytest.mark.asyncio
    async def test_get_volatility_success(
        self, authenticated_client: AsyncClient, test_tenant: dict
    ):
        """Test successful volatility retrieval."""
        response = await authenticated_client.get(
            f"/api/v1/tenants/{test_tenant['id']}/emq/volatility"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "svi" in data["data"]  # Signal Volatility Index
        assert "trend" in data["data"]
        assert "weeklyData" in data["data"]

        assert data["data"]["trend"] in ["increasing", "decreasing", "stable"]


class TestAutopilotStateEndpoint:
    """Tests for autopilot state endpoints."""

    @pytest.mark.asyncio
    async def test_get_autopilot_state_success(
        self, authenticated_client: AsyncClient, test_tenant: dict
    ):
        """Test successful autopilot state retrieval."""
        response = await authenticated_client.get(
            f"/api/v1/tenants/{test_tenant['id']}/emq/autopilot-state"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "mode" in data["data"]
        assert "allowedActions" in data["data"]
        assert "restrictedActions" in data["data"]

        assert data["data"]["mode"] in ["normal", "limited", "cuts_only", "frozen"]

    @pytest.mark.asyncio
    async def test_update_autopilot_mode(
        self, authenticated_client: AsyncClient, test_tenant: dict
    ):
        """Test autopilot mode update."""
        response = await authenticated_client.put(
            f"/api/v1/tenants/{test_tenant['id']}/emq/autopilot-mode",
            json={
                "mode": "limited",
                "reason": "Testing manual override",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["data"]["mode"] == "limited"
        assert "Testing manual override" in data["data"]["reason"]


class TestSuperAdminEndpoints:
    """Tests for super admin EMQ endpoints."""

    @pytest.mark.asyncio
    async def test_get_benchmarks(self, client: AsyncClient, superadmin_headers: dict):
        """Test EMQ benchmarks retrieval."""
        response = await client.get(
            "/api/v1/emq/benchmarks",
            headers=superadmin_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert isinstance(data["data"], list)

        if len(data["data"]) > 0:
            benchmark = data["data"][0]
            assert "platform" in benchmark
            assert "p25" in benchmark
            assert "p50" in benchmark
            assert "p75" in benchmark

    @pytest.mark.asyncio
    async def test_get_portfolio(self, client: AsyncClient, superadmin_headers: dict):
        """Test portfolio overview retrieval."""
        response = await client.get(
            "/api/v1/emq/portfolio",
            headers=superadmin_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "totalTenants" in data["data"]
        assert "byBand" in data["data"]
        assert "avgScore" in data["data"]
        assert "topIssues" in data["data"]
