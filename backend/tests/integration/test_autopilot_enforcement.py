# =============================================================================
# Stratum AI - Autopilot Enforcement API Integration Tests
# =============================================================================
"""
Integration tests for Autopilot Enforcement API endpoints.

Tests cover:
- GET /settings - Get enforcement settings
- PUT /settings - Update enforcement settings
- POST /check - Check action enforcement
- POST /confirm - Confirm soft-blocked action
- POST /kill-switch - Toggle enforcement
- GET /audit-log - Get intervention audit log
- POST /rules - Add custom rule
- DELETE /rules/{rule_id} - Delete custom rule
"""

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.integration


class TestEnforcementSettingsEndpoints:
    """Tests for enforcement settings API endpoints."""

    @pytest.mark.asyncio
    async def test_get_settings(
        self,
        authenticated_client: AsyncClient,
        test_tenant: dict,
    ):
        """Test getting enforcement settings."""
        response = await authenticated_client.get(
            f"/api/v1/tenant/{test_tenant['id']}/autopilot/enforcement/settings"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "settings" in data["data"]
        assert "enforcement_enabled" in data["data"]["settings"]
        assert "default_mode" in data["data"]["settings"]
        assert "modes" in data["data"]

    @pytest.mark.asyncio
    async def test_update_settings(
        self,
        authenticated_client: AsyncClient,
        test_tenant: dict,
    ):
        """Test updating enforcement settings."""
        response = await authenticated_client.put(
            f"/api/v1/tenant/{test_tenant['id']}/autopilot/enforcement/settings",
            json={
                "max_campaign_budget": 5000.0,
                "min_roas_threshold": 1.5,
                "default_mode": "soft_block",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["data"]["settings"]["max_campaign_budget"] == 5000.0
        assert data["data"]["settings"]["min_roas_threshold"] == 1.5
        assert data["data"]["settings"]["default_mode"] == "soft_block"

    @pytest.mark.asyncio
    async def test_update_settings_invalid_mode(
        self,
        authenticated_client: AsyncClient,
        test_tenant: dict,
    ):
        """Test updating settings with invalid mode fails."""
        response = await authenticated_client.put(
            f"/api/v1/tenant/{test_tenant['id']}/autopilot/enforcement/settings",
            json={
                "default_mode": "invalid_mode",
            },
        )

        assert response.status_code == 400


class TestEnforcementCheckEndpoint:
    """Tests for enforcement check endpoint."""

    @pytest.mark.asyncio
    async def test_check_allowed_action(
        self,
        authenticated_client: AsyncClient,
        test_tenant: dict,
    ):
        """Test checking an allowed action."""
        response = await authenticated_client.post(
            f"/api/v1/tenant/{test_tenant['id']}/autopilot/enforcement/check",
            json={
                "action_type": "set_budget",
                "entity_type": "campaign",
                "entity_id": "camp_123",
                "proposed_value": {"budget": 1000.0},
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "allowed" in data["data"]
        assert "mode" in data["data"]

    @pytest.mark.asyncio
    async def test_check_with_metrics(
        self,
        authenticated_client: AsyncClient,
        test_tenant: dict,
    ):
        """Test checking action with performance metrics."""
        response = await authenticated_client.post(
            f"/api/v1/tenant/{test_tenant['id']}/autopilot/enforcement/check",
            json={
                "action_type": "budget_increase",
                "entity_type": "campaign",
                "entity_id": "camp_123",
                "proposed_value": {"budget": 2000.0},
                "current_value": {"budget": 1000.0},
                "metrics": {"roas": 2.5, "spend": 500.0},
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["data"]["allowed"] is True

    @pytest.mark.asyncio
    async def test_check_budget_violation(
        self,
        authenticated_client: AsyncClient,
        test_tenant: dict,
    ):
        """Test checking action that violates budget limit."""
        # First set up a strict limit
        await authenticated_client.put(
            f"/api/v1/tenant/{test_tenant['id']}/autopilot/enforcement/settings",
            json={
                "max_campaign_budget": 1000.0,
                "default_mode": "advisory",
            },
        )

        # Check action that exceeds limit
        response = await authenticated_client.post(
            f"/api/v1/tenant/{test_tenant['id']}/autopilot/enforcement/check",
            json={
                "action_type": "set_budget",
                "entity_type": "campaign",
                "entity_id": "camp_123",
                "proposed_value": {"budget": 5000.0},
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        # In advisory mode, still allowed but with violations
        assert data["data"]["allowed"] is True
        assert len(data["data"]["violations"]) > 0
        assert len(data["data"]["warnings"]) > 0


class TestSoftBlockConfirmationEndpoint:
    """Tests for soft-block confirmation endpoint."""

    @pytest.mark.asyncio
    async def test_soft_block_and_confirm(
        self,
        authenticated_client: AsyncClient,
        test_tenant: dict,
    ):
        """Test full soft-block and confirmation workflow."""
        # Set up soft_block mode
        await authenticated_client.put(
            f"/api/v1/tenant/{test_tenant['id']}/autopilot/enforcement/settings",
            json={
                "max_campaign_budget": 1000.0,
                "default_mode": "soft_block",
            },
        )

        # Check action that triggers soft block
        check_response = await authenticated_client.post(
            f"/api/v1/tenant/{test_tenant['id']}/autopilot/enforcement/check",
            json={
                "action_type": "set_budget",
                "entity_type": "campaign",
                "entity_id": "camp_123",
                "proposed_value": {"budget": 5000.0},
            },
        )

        assert check_response.status_code == 200
        check_data = check_response.json()

        assert check_data["data"]["allowed"] is False
        assert check_data["data"]["requires_confirmation"] is True
        token = check_data["data"]["confirmation_token"]
        assert token is not None

        # Confirm the action
        confirm_response = await authenticated_client.post(
            f"/api/v1/tenant/{test_tenant['id']}/autopilot/enforcement/confirm",
            json={
                "confirmation_token": token,
                "override_reason": "Approved for special campaign",
            },
        )

        assert confirm_response.status_code == 200
        confirm_data = confirm_response.json()

        assert confirm_data["success"] is True
        assert confirm_data["data"]["override_logged"] is True

    @pytest.mark.asyncio
    async def test_confirm_invalid_token(
        self,
        authenticated_client: AsyncClient,
        test_tenant: dict,
    ):
        """Test confirming with invalid token fails."""
        response = await authenticated_client.post(
            f"/api/v1/tenant/{test_tenant['id']}/autopilot/enforcement/confirm",
            json={
                "confirmation_token": "invalid-token-12345",
            },
        )

        assert response.status_code == 400


class TestKillSwitchEndpoint:
    """Tests for enforcement kill switch endpoint."""

    @pytest.mark.asyncio
    async def test_disable_enforcement(
        self,
        authenticated_client: AsyncClient,
        test_tenant: dict,
    ):
        """Test disabling enforcement via kill switch."""
        response = await authenticated_client.post(
            f"/api/v1/tenant/{test_tenant['id']}/autopilot/enforcement/kill-switch",
            json={
                "enabled": False,
                "reason": "Emergency override for testing",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["data"]["enforcement_enabled"] is False

    @pytest.mark.asyncio
    async def test_enable_enforcement(
        self,
        authenticated_client: AsyncClient,
        test_tenant: dict,
    ):
        """Test enabling enforcement via kill switch."""
        # First disable
        await authenticated_client.post(
            f"/api/v1/tenant/{test_tenant['id']}/autopilot/enforcement/kill-switch",
            json={"enabled": False},
        )

        # Then enable
        response = await authenticated_client.post(
            f"/api/v1/tenant/{test_tenant['id']}/autopilot/enforcement/kill-switch",
            json={
                "enabled": True,
                "reason": "Resuming normal operations",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["data"]["enforcement_enabled"] is True


class TestAuditLogEndpoint:
    """Tests for intervention audit log endpoint."""

    @pytest.mark.asyncio
    async def test_get_audit_log(
        self,
        authenticated_client: AsyncClient,
        test_tenant: dict,
    ):
        """Test getting audit log."""
        response = await authenticated_client.get(
            f"/api/v1/tenant/{test_tenant['id']}/autopilot/enforcement/audit-log",
            params={"days": 30, "limit": 50},
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "logs" in data["data"]
        assert "count" in data["data"]
        assert "filters" in data["data"]


class TestCustomRulesEndpoints:
    """Tests for custom rules management endpoints."""

    @pytest.mark.asyncio
    async def test_add_custom_rule(
        self,
        authenticated_client: AsyncClient,
        test_tenant: dict,
    ):
        """Test adding a custom enforcement rule."""
        response = await authenticated_client.post(
            f"/api/v1/tenant/{test_tenant['id']}/autopilot/enforcement/rules",
            json={
                "rule_id": "premium_budget_limit",
                "rule_type": "budget_exceeded",
                "threshold_value": 2000.0,
                "enforcement_mode": "soft_block",
                "enabled": True,
                "description": "Budget limit for premium tier",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["data"]["rule"]["rule_id"] == "premium_budget_limit"
        assert data["data"]["rule"]["threshold_value"] == 2000.0

    @pytest.mark.asyncio
    async def test_add_rule_invalid_type(
        self,
        authenticated_client: AsyncClient,
        test_tenant: dict,
    ):
        """Test adding rule with invalid type fails."""
        response = await authenticated_client.post(
            f"/api/v1/tenant/{test_tenant['id']}/autopilot/enforcement/rules",
            json={
                "rule_id": "invalid_rule",
                "rule_type": "invalid_type",
                "threshold_value": 1000.0,
            },
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_delete_custom_rule(
        self,
        authenticated_client: AsyncClient,
        test_tenant: dict,
    ):
        """Test deleting a custom rule."""
        # First add a rule
        await authenticated_client.post(
            f"/api/v1/tenant/{test_tenant['id']}/autopilot/enforcement/rules",
            json={
                "rule_id": "rule_to_delete",
                "rule_type": "budget_exceeded",
                "threshold_value": 1000.0,
            },
        )

        # Delete the rule
        response = await authenticated_client.delete(
            f"/api/v1/tenant/{test_tenant['id']}/autopilot/enforcement/rules/rule_to_delete"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_delete_nonexistent_rule(
        self,
        authenticated_client: AsyncClient,
        test_tenant: dict,
    ):
        """Test deleting nonexistent rule returns 404."""
        response = await authenticated_client.delete(
            f"/api/v1/tenant/{test_tenant['id']}/autopilot/enforcement/rules/nonexistent_rule"
        )

        assert response.status_code == 404


class TestEnforcementAccessControl:
    """Tests for enforcement endpoint access control."""

    @pytest.mark.asyncio
    async def test_wrong_tenant_access_denied(
        self,
        authenticated_client: AsyncClient,
        test_tenant: dict,
    ):
        """Test accessing wrong tenant's settings is denied."""
        wrong_tenant_id = test_tenant["id"] + 999

        response = await authenticated_client.get(
            f"/api/v1/tenant/{wrong_tenant_id}/autopilot/enforcement/settings"
        )

        assert response.status_code == 403
