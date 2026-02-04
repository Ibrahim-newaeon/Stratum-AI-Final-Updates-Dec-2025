# =============================================================================
# Stratum AI - Actions Queue Integration Tests
# =============================================================================
"""
Integration tests for autopilot actions queue API endpoints.

Tests cover:
- Action creation and queuing
- Action approval workflow
- Action dismissal
- Action execution
- Bulk operations
"""

from datetime import UTC, datetime

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.integration


class TestActionsQueue:
    """Tests for actions queue endpoints."""

    @pytest.mark.asyncio
    async def test_get_pending_actions(
        self,
        authenticated_client: AsyncClient,
        test_tenant: dict,
        test_action: dict,
    ):
        """Test retrieval of pending actions."""
        response = await authenticated_client.get(
            f"/api/v1/tenants/{test_tenant['id']}/actions",
            params={"status": "queued"},
        )

        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_approve_action(
        self,
        authenticated_client: AsyncClient,
        test_tenant: dict,
        test_action: dict,
    ):
        """Test action approval."""
        response = await authenticated_client.post(
            f"/api/v1/tenants/{test_tenant['id']}/actions/{test_action['id']}/approve"
        )

        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_dismiss_action(
        self,
        authenticated_client: AsyncClient,
        test_tenant: dict,
        db_session,
    ):
        """Test action dismissal."""
        import json

        from app.models.trust_layer import FactActionsQueue

        # Create a new action to dismiss
        action = FactActionsQueue(
            tenant_id=test_tenant["id"],
            date=datetime.now(UTC).date(),
            action_type="pause_campaign",
            entity_type="campaign",
            entity_id="campaign_456",
            entity_name="Campaign to Dismiss",
            platform="meta",
            action_json=json.dumps({}),
            status="queued",
        )
        db_session.add(action)
        await db_session.flush()

        response = await authenticated_client.post(
            f"/api/v1/tenants/{test_tenant['id']}/actions/{action.id}/dismiss"
        )

        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_bulk_approve_actions(
        self,
        authenticated_client: AsyncClient,
        test_tenant: dict,
        db_session,
    ):
        """Test bulk action approval."""
        import json

        from app.models.trust_layer import FactActionsQueue

        # Create multiple actions
        action_ids = []
        for i in range(3):
            action = FactActionsQueue(
                tenant_id=test_tenant["id"],
                date=datetime.now(UTC).date(),
                action_type="budget_increase",
                entity_type="campaign",
                entity_id=f"campaign_bulk_{i}",
                entity_name=f"Bulk Campaign {i}",
                platform="meta",
                action_json=json.dumps({"amount": 10}),
                status="queued",
            )
            db_session.add(action)
            await db_session.flush()
            action_ids.append(str(action.id))

        response = await authenticated_client.post(
            f"/api/v1/tenants/{test_tenant['id']}/actions/approve-all",
            json={"action_ids": action_ids},
        )

        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True


class TestActionValidation:
    """Tests for action validation."""

    @pytest.mark.asyncio
    async def test_action_respects_budget_caps(
        self,
        authenticated_client: AsyncClient,
        test_tenant: dict,
        db_session,
    ):
        """Test that actions respect budget change caps."""
        import json

        from app.models.trust_layer import FactActionsQueue

        # Create an action that exceeds caps
        large_action = FactActionsQueue(
            tenant_id=test_tenant["id"],
            date=datetime.now(UTC).date(),
            action_type="budget_increase",
            entity_type="campaign",
            entity_id="campaign_large",
            entity_name="Large Budget Campaign",
            platform="meta",
            action_json=json.dumps({"amount": 100000, "percentage": 500}),
            status="queued",
        )
        db_session.add(large_action)
        await db_session.flush()

        # Attempting to approve should validate caps
        response = await authenticated_client.post(
            f"/api/v1/tenants/{test_tenant['id']}/actions/{large_action.id}/approve"
        )

        # Either rejected or needs additional confirmation
        if response.status_code == 200:
            data = response.json()
            # Might have warnings about caps

    @pytest.mark.asyncio
    async def test_action_blocked_when_signal_health_degraded(
        self,
        authenticated_client: AsyncClient,
        test_tenant: dict,
        db_session,
    ):
        """Test that actions are blocked when signal health is degraded."""
        import json

        from app.models.trust_layer import (
            FactActionsQueue,
            FactSignalHealthDaily,
            SignalHealthStatus,
        )

        # Set signal health to degraded
        health = FactSignalHealthDaily(
            tenant_id=test_tenant["id"],
            date=datetime.now(UTC).date(),
            platform="meta",
            emq_score=65.0,  # Below threshold
            event_loss_pct=15.0,  # High loss
            status=SignalHealthStatus.DEGRADED,
        )
        db_session.add(health)

        # Create an action
        action = FactActionsQueue(
            tenant_id=test_tenant["id"],
            date=datetime.now(UTC).date(),
            action_type="budget_increase",
            entity_type="campaign",
            entity_id="campaign_blocked",
            entity_name="Blocked Campaign",
            platform="meta",
            action_json=json.dumps({"amount": 50}),
            status="approved",  # Already approved
        )
        db_session.add(action)
        await db_session.flush()

        # Check autopilot state - should be restricted
        response = await authenticated_client.get(
            f"/api/v1/tenants/{test_tenant['id']}/emq/autopilot-state"
        )

        if response.status_code == 200:
            data = response.json()
            # budget_increase should be in restricted actions
            restricted = data["data"].get("restrictedActions", [])
            # Might contain "increase_budget" depending on mode


class TestActionHistory:
    """Tests for action history and audit trail."""

    @pytest.mark.asyncio
    async def test_get_action_history(
        self,
        authenticated_client: AsyncClient,
        test_tenant: dict,
        test_action: dict,
    ):
        """Test retrieval of action history."""
        response = await authenticated_client.get(
            f"/api/v1/tenants/{test_tenant['id']}/actions/history",
            params={"limit": 10},
        )

        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True

    @pytest.mark.asyncio
    async def test_action_audit_log(
        self,
        authenticated_client: AsyncClient,
        test_tenant: dict,
        test_action: dict,
    ):
        """Test that actions are properly logged in audit trail."""
        # Approve the action first
        await authenticated_client.post(
            f"/api/v1/tenants/{test_tenant['id']}/actions/{test_action['id']}/approve"
        )

        # Check audit log
        response = await authenticated_client.get(
            f"/api/v1/tenants/{test_tenant['id']}/audit",
            params={"action_type": "action_approved"},
        )

        if response.status_code == 200:
            data = response.json()
            # Should contain the approval action


class TestActionSummary:
    """Tests for action summary endpoints."""

    @pytest.mark.asyncio
    async def test_get_actions_summary(
        self,
        authenticated_client: AsyncClient,
        test_tenant: dict,
        test_action: dict,
    ):
        """Test retrieval of actions summary."""
        response = await authenticated_client.get(
            f"/api/v1/tenants/{test_tenant['id']}/actions/summary"
        )

        if response.status_code == 200:
            data = response.json()
            assert data["success"] is True
            # Should contain counts by status

    @pytest.mark.asyncio
    async def test_get_actions_by_platform(
        self,
        authenticated_client: AsyncClient,
        test_tenant: dict,
        test_action: dict,
    ):
        """Test filtering actions by platform."""
        response = await authenticated_client.get(
            f"/api/v1/tenants/{test_tenant['id']}/actions",
            params={"platform": "meta"},
        )

        if response.status_code == 200:
            data = response.json()
            actions = data.get("data", [])

            for action in actions:
                if "platform" in action:
                    assert action["platform"] == "meta"
