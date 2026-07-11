# =============================================================================
# Stratum AI - Autopilot Enforcer Unit Tests
# =============================================================================
"""
Comprehensive unit tests for the Autopilot Enforcer service.

Tests cover:
- Enforcement modes (advisory, soft_block, hard_block)
- Budget threshold enforcement
- ROAS threshold enforcement
- Custom rule evaluation
- Soft-block confirmation workflow
- Kill switch functionality
- Intervention logging
"""

import smtplib
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any, List, Optional
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.autopilot.enforcer import (
    AutopilotEnforcer,
    EnforcementMode,
    EnforcementResult,
    EnforcementRule,
    EnforcementSettings,
    InterventionAction,
    InterventionLog,
    ViolationType,
    send_enforcement_notification,
)
from app.models.autopilot import EnforcementAuditLog as EnforcementAuditLogDB
from app.models.autopilot import EnforcementMode as DBEnforcementMode
from app.models.autopilot import InterventionAction as DBInterventionAction
from app.models.autopilot import PendingConfirmationToken as PendingConfirmationTokenDB
from app.models.autopilot import TenantEnforcementRule as TenantEnforcementRuleDB
from app.models.autopilot import (
    TenantEnforcementSettings as TenantEnforcementSettingsDB,
)
from app.models.autopilot import ViolationType as DBViolationType

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def enforcer():
    """Create an AutopilotEnforcer instance without database."""
    # Create a fresh enforcer instance for each test to ensure clean state
    instance = AutopilotEnforcer(db=None)
    instance._settings_cache.clear()
    instance._pending_confirmations.clear()
    return instance


@pytest.fixture(autouse=True)
def _no_db_subscription(monkeypatch):
    """check_action() calls get_subscription_info(), which opens its own DB
    session. These enforcer tests run without a database (db=None), so stub it
    to a non-restricted subscription — the subscription gate becomes a no-op
    and no real connection is attempted."""
    from types import SimpleNamespace

    info = SimpleNamespace(is_access_restricted=False)
    monkeypatch.setattr(
        "app.core.subscription.get_subscription_info",
        AsyncMock(return_value=info),
    )


@pytest.fixture
def default_settings():
    """Create default enforcement settings."""
    return EnforcementSettings(
        tenant_id=1,
        enforcement_enabled=True,
        default_mode=EnforcementMode.ADVISORY,
        max_campaign_budget=10000.0,
        budget_increase_limit_pct=30.0,
        min_roas_threshold=1.0,
    )


@pytest.fixture
def strict_settings():
    """Create strict enforcement settings with hard_block mode."""
    return EnforcementSettings(
        tenant_id=1,
        enforcement_enabled=True,
        default_mode=EnforcementMode.HARD_BLOCK,
        max_campaign_budget=5000.0,
        budget_increase_limit_pct=20.0,
        min_roas_threshold=2.0,
    )


# =============================================================================
# Test Enforcement Settings
# =============================================================================


class TestEnforcementSettings:
    """Tests for enforcement settings management."""

    @pytest.mark.asyncio
    async def test_get_default_settings(self, enforcer):
        """Test getting default settings for a new tenant."""
        settings = await enforcer.get_settings(tenant_id=1)

        assert settings.tenant_id == 1
        assert settings.enforcement_enabled is True
        # TRUST-003: an unconfigured tenant fails safe to SOFT_BLOCK.
        assert settings.default_mode == EnforcementMode.SOFT_BLOCK
        assert settings.budget_increase_limit_pct == 30.0
        assert settings.min_roas_threshold == 1.0

    @pytest.mark.asyncio
    async def test_update_settings(self, enforcer):
        """Test updating enforcement settings."""
        settings = await enforcer.update_settings(
            tenant_id=1,
            updates={
                "max_campaign_budget": 5000.0,
                "default_mode": EnforcementMode.SOFT_BLOCK,
            },
        )

        assert settings.max_campaign_budget == 5000.0
        assert settings.default_mode == EnforcementMode.SOFT_BLOCK

    @pytest.mark.asyncio
    async def test_settings_caching(self, enforcer):
        """Test that settings are cached."""
        # First call creates settings
        settings1 = await enforcer.get_settings(tenant_id=1)

        # Update settings
        await enforcer.update_settings(
            tenant_id=1, updates={"max_campaign_budget": 7500.0}
        )

        # Second call should return cached (updated) settings
        settings2 = await enforcer.get_settings(tenant_id=1)

        assert settings2.max_campaign_budget == 7500.0


# =============================================================================
# Test Budget Enforcement
# =============================================================================


class TestBudgetEnforcement:
    """Tests for budget threshold enforcement."""

    @pytest.mark.asyncio
    async def test_budget_under_limit_allowed(self, enforcer):
        """Test that budget under limit is allowed."""
        await enforcer.update_settings(
            tenant_id=1,
            updates={"max_campaign_budget": 10000.0},
        )

        result = await enforcer.check_action(
            tenant_id=1,
            action_type="set_budget",
            entity_type="campaign",
            entity_id="camp_123",
            proposed_value={"budget": 5000.0},
        )

        assert result.allowed is True
        assert len(result.violations) == 0

    @pytest.mark.asyncio
    async def test_budget_over_limit_violations(self, enforcer):
        """Test that budget over limit creates violation."""
        await enforcer.update_settings(
            tenant_id=1,
            updates={
                "max_campaign_budget": 5000.0,
                "default_mode": EnforcementMode.ADVISORY,
            },
        )

        result = await enforcer.check_action(
            tenant_id=1,
            action_type="set_budget",
            entity_type="campaign",
            entity_id="camp_123",
            proposed_value={"budget": 7500.0},
        )

        # Advisory mode still allows, but with violation
        assert result.allowed is True
        assert len(result.violations) == 1
        assert result.violations[0]["type"] == ViolationType.BUDGET_EXCEEDED.value

    @pytest.mark.asyncio
    async def test_budget_increase_percentage_check(self, enforcer):
        """Test budget increase percentage limit."""
        await enforcer.update_settings(
            tenant_id=1,
            updates={
                "budget_increase_limit_pct": 30.0,
                "default_mode": EnforcementMode.ADVISORY,
            },
        )

        # 50% increase should violate 30% limit
        result = await enforcer.check_action(
            tenant_id=1,
            action_type="budget_increase",
            entity_type="campaign",
            entity_id="camp_123",
            proposed_value={"budget": 1500.0},
            current_value={"budget": 1000.0},
        )

        assert len(result.violations) == 1
        assert "50.0%" in result.violations[0]["message"]

    @pytest.mark.asyncio
    async def test_budget_increase_within_limit(self, enforcer):
        """Test budget increase within percentage limit."""
        await enforcer.update_settings(
            tenant_id=1,
            updates={"budget_increase_limit_pct": 30.0},
        )

        # 20% increase should be allowed
        result = await enforcer.check_action(
            tenant_id=1,
            action_type="budget_increase",
            entity_type="campaign",
            entity_id="camp_123",
            proposed_value={"budget": 1200.0},
            current_value={"budget": 1000.0},
        )

        assert result.allowed is True
        assert len(result.violations) == 0


# =============================================================================
# Test ROAS Enforcement
# =============================================================================


class TestROASEnforcement:
    """Tests for ROAS threshold enforcement."""

    @pytest.mark.asyncio
    async def test_roas_above_threshold_allowed(self, enforcer):
        """Test that ROAS above threshold is allowed."""
        await enforcer.update_settings(
            tenant_id=1,
            updates={"min_roas_threshold": 1.5},
        )

        result = await enforcer.check_action(
            tenant_id=1,
            action_type="budget_increase",
            entity_type="campaign",
            entity_id="camp_123",
            proposed_value={"budget": 1000.0},
            metrics={"roas": 2.5},
        )

        # No ROAS violation
        roas_violations = [
            v
            for v in result.violations
            if v["type"] == ViolationType.ROAS_BELOW_THRESHOLD.value
        ]
        assert len(roas_violations) == 0

    @pytest.mark.asyncio
    async def test_roas_below_threshold_violation(self, enforcer):
        """Test that ROAS below threshold creates violation."""
        await enforcer.update_settings(
            tenant_id=1,
            updates={
                "min_roas_threshold": 2.0,
                "default_mode": EnforcementMode.ADVISORY,
            },
        )

        result = await enforcer.check_action(
            tenant_id=1,
            action_type="budget_increase",
            entity_type="campaign",
            entity_id="camp_123",
            proposed_value={"budget": 1000.0},
            metrics={"roas": 1.5},
        )

        roas_violations = [
            v
            for v in result.violations
            if v["type"] == ViolationType.ROAS_BELOW_THRESHOLD.value
        ]
        assert len(roas_violations) == 1
        assert "1.50" in roas_violations[0]["message"]


# =============================================================================
# Test Enforcement Modes
# =============================================================================


class TestEnforcementModes:
    """Tests for different enforcement modes."""

    @pytest.mark.asyncio
    async def test_advisory_mode_allows_with_warnings(self, enforcer):
        """Test advisory mode allows action but returns warnings."""
        await enforcer.update_settings(
            tenant_id=1,
            updates={
                "default_mode": EnforcementMode.ADVISORY,
                "max_campaign_budget": 1000.0,
            },
        )

        result = await enforcer.check_action(
            tenant_id=1,
            action_type="set_budget",
            entity_type="campaign",
            entity_id="camp_123",
            proposed_value={"budget": 5000.0},
        )

        assert result.allowed is True
        assert result.mode == EnforcementMode.ADVISORY
        assert len(result.warnings) > 0

    @pytest.mark.asyncio
    async def test_soft_block_requires_confirmation(self, enforcer):
        """Test soft_block mode requires confirmation."""
        await enforcer.update_settings(
            tenant_id=1,
            updates={
                "default_mode": EnforcementMode.SOFT_BLOCK,
                "max_campaign_budget": 1000.0,
            },
        )

        result = await enforcer.check_action(
            tenant_id=1,
            action_type="set_budget",
            entity_type="campaign",
            entity_id="camp_123",
            proposed_value={"budget": 5000.0},
        )

        assert result.allowed is False
        assert result.mode == EnforcementMode.SOFT_BLOCK
        assert result.requires_confirmation is True
        assert result.confirmation_token is not None

    @pytest.mark.asyncio
    async def test_hard_block_prevents_action(self, enforcer):
        """Test hard_block mode prevents action completely."""
        await enforcer.update_settings(
            tenant_id=1,
            updates={
                "default_mode": EnforcementMode.HARD_BLOCK,
                "max_campaign_budget": 1000.0,
            },
        )

        result = await enforcer.check_action(
            tenant_id=1,
            action_type="set_budget",
            entity_type="campaign",
            entity_id="camp_123",
            proposed_value={"budget": 5000.0},
        )

        assert result.allowed is False
        assert result.mode == EnforcementMode.HARD_BLOCK
        assert result.requires_confirmation is False

    @pytest.mark.asyncio
    async def test_no_violations_always_allowed(self, enforcer):
        """Test that no violations means action is always allowed."""
        await enforcer.update_settings(
            tenant_id=1,
            updates={
                "default_mode": EnforcementMode.HARD_BLOCK,
                "max_campaign_budget": 10000.0,
            },
        )

        result = await enforcer.check_action(
            tenant_id=1,
            action_type="set_budget",
            entity_type="campaign",
            entity_id="camp_123",
            proposed_value={"budget": 5000.0},
        )

        assert result.allowed is True
        assert len(result.violations) == 0


# =============================================================================
# Test Soft-Block Confirmation
# =============================================================================


class TestSoftBlockConfirmation:
    """Tests for soft-block confirmation workflow."""

    @pytest.mark.asyncio
    async def test_confirm_valid_token(self, enforcer):
        """Test confirming a valid soft-block token."""
        await enforcer.update_settings(
            tenant_id=1,
            updates={
                "default_mode": EnforcementMode.SOFT_BLOCK,
                "max_campaign_budget": 1000.0,
            },
        )

        # Create a soft-blocked action
        result = await enforcer.check_action(
            tenant_id=1,
            action_type="set_budget",
            entity_type="campaign",
            entity_id="camp_123",
            proposed_value={"budget": 5000.0},
        )

        token = result.confirmation_token
        assert token is not None

        # Confirm the action
        success, error = await enforcer.confirm_action(
            tenant_id=1,
            confirmation_token=token,
            user_id=42,
            override_reason="Approved by manager",
        )

        assert success is True
        assert error is None

    @pytest.mark.asyncio
    async def test_confirm_invalid_token(self, enforcer):
        """Test confirming an invalid token fails."""
        success, error = await enforcer.confirm_action(
            tenant_id=1,
            confirmation_token="invalid-token",
            user_id=42,
        )

        assert success is False
        assert "Invalid" in error or "expired" in error

    @pytest.mark.asyncio
    async def test_confirm_wrong_tenant(self, enforcer):
        """Test confirming token with wrong tenant fails."""
        await enforcer.update_settings(
            tenant_id=1,
            updates={
                "default_mode": EnforcementMode.SOFT_BLOCK,
                "max_campaign_budget": 1000.0,
            },
        )

        result = await enforcer.check_action(
            tenant_id=1,
            action_type="set_budget",
            entity_type="campaign",
            entity_id="camp_123",
            proposed_value={"budget": 5000.0},
        )

        # Try to confirm with different tenant
        success, error = await enforcer.confirm_action(
            tenant_id=999,  # Wrong tenant
            confirmation_token=result.confirmation_token,
            user_id=42,
        )

        assert success is False
        assert "tenant" in error.lower()

    @pytest.mark.asyncio
    async def test_token_can_only_be_used_once(self, enforcer):
        """Test that confirmation token can only be used once."""
        await enforcer.update_settings(
            tenant_id=1,
            updates={
                "default_mode": EnforcementMode.SOFT_BLOCK,
                "max_campaign_budget": 1000.0,
            },
        )

        result = await enforcer.check_action(
            tenant_id=1,
            action_type="set_budget",
            entity_type="campaign",
            entity_id="camp_123",
            proposed_value={"budget": 5000.0},
        )

        token = result.confirmation_token

        # First confirmation succeeds
        success1, _ = await enforcer.confirm_action(
            tenant_id=1,
            confirmation_token=token,
            user_id=42,
        )
        assert success1 is True

        # Second confirmation fails
        success2, _error2 = await enforcer.confirm_action(
            tenant_id=1,
            confirmation_token=token,
            user_id=42,
        )
        assert success2 is False


# =============================================================================
# Test Kill Switch
# =============================================================================


class TestKillSwitch:
    """Tests for enforcement kill switch."""

    @pytest.mark.asyncio
    async def test_kill_switch_disables_enforcement(self, enforcer):
        """Test that kill switch disables all enforcement."""
        await enforcer.update_settings(
            tenant_id=1,
            updates={
                "enforcement_enabled": False,
                "default_mode": EnforcementMode.HARD_BLOCK,
                "max_campaign_budget": 100.0,
            },
        )

        # Even with hard_block and low budget limit, action should be allowed
        result = await enforcer.check_action(
            tenant_id=1,
            action_type="set_budget",
            entity_type="campaign",
            entity_id="camp_123",
            proposed_value={"budget": 10000.0},
        )

        assert result.allowed is True
        assert "disabled" in result.warnings[0].lower()

    @pytest.mark.asyncio
    async def test_set_kill_switch(self, enforcer):
        """Test setting kill switch via method."""
        settings = await enforcer.set_kill_switch(
            tenant_id=1,
            enabled=False,
            user_id=42,
            reason="Emergency override",
        )

        assert settings.enforcement_enabled is False

        # Re-enable
        settings = await enforcer.set_kill_switch(
            tenant_id=1,
            enabled=True,
            user_id=42,
            reason="Issue resolved",
        )

        assert settings.enforcement_enabled is True


class TestEmergencyStop:
    """Tests for the autopilot emergency stop (freeze)."""

    @pytest.mark.asyncio
    async def test_default_not_frozen(self, enforcer):
        """A new tenant is not frozen by default."""
        settings = await enforcer.get_settings(tenant_id=1)
        assert settings.autopilot_frozen is False
        assert await enforcer.is_frozen(tenant_id=1) is False

    @pytest.mark.asyncio
    async def test_set_freeze_halts(self, enforcer):
        """Freezing sets the flag and is_frozen reports True."""
        settings = await enforcer.set_freeze(
            tenant_id=1,
            frozen=True,
            user_id=42,
            reason="Meta reporting outage",
        )
        assert settings.autopilot_frozen is True
        assert await enforcer.is_frozen(tenant_id=1) is True

    @pytest.mark.asyncio
    async def test_set_freeze_resume(self, enforcer):
        """Resuming clears the freeze."""
        await enforcer.set_freeze(tenant_id=1, frozen=True, user_id=42)
        settings = await enforcer.set_freeze(
            tenant_id=1,
            frozen=False,
            user_id=42,
            reason="Incident resolved",
        )
        assert settings.autopilot_frozen is False
        assert await enforcer.is_frozen(tenant_id=1) is False

    @pytest.mark.asyncio
    async def test_freeze_independent_of_enforcement_toggle(self, enforcer):
        """Freeze and enforcement_enabled are orthogonal switches.

        Freezing must not silently flip the guardrails toggle, and toggling
        the kill switch must not freeze — they are distinct controls.
        """
        await enforcer.set_freeze(tenant_id=1, frozen=True, user_id=1)
        settings = await enforcer.get_settings(tenant_id=1)
        assert settings.autopilot_frozen is True
        assert settings.enforcement_enabled is True

        await enforcer.set_kill_switch(tenant_id=1, enabled=False, user_id=1)
        settings = await enforcer.get_settings(tenant_id=1)
        assert settings.enforcement_enabled is False
        # Freeze survives an enforcement-toggle change.
        assert settings.autopilot_frozen is True

    @pytest.mark.asyncio
    async def test_is_frozen_defaults_false_for_unknown_tenant(self, enforcer):
        """is_frozen returns False (not an error) for a tenant with no row."""
        assert await enforcer.is_frozen(tenant_id=9999) is False


# =============================================================================
# Test Custom Rules
# =============================================================================


class TestCustomRules:
    """Tests for custom enforcement rules."""

    @pytest.mark.asyncio
    async def test_custom_budget_rule(self, enforcer):
        """Test custom budget rule evaluation."""
        custom_rule = EnforcementRule(
            rule_id="premium_budget_limit",
            rule_type=ViolationType.BUDGET_EXCEEDED,
            threshold_value=2000.0,
            enforcement_mode=EnforcementMode.SOFT_BLOCK,
            enabled=True,
            description="Premium tier budget limit",
        )

        await enforcer.update_settings(
            tenant_id=1,
            updates={
                "rules": [custom_rule],
                "default_mode": EnforcementMode.ADVISORY,
            },
        )

        result = await enforcer.check_action(
            tenant_id=1,
            action_type="set_budget",
            entity_type="campaign",
            entity_id="camp_123",
            proposed_value={"budget": 3000.0},
        )

        # Custom rule should trigger soft_block
        assert result.allowed is False
        assert result.mode == EnforcementMode.SOFT_BLOCK
        assert any(
            v.get("rule_id") == "premium_budget_limit" for v in result.violations
        )

    @pytest.mark.asyncio
    async def test_custom_roas_rule(self, enforcer):
        """Test custom ROAS rule evaluation."""
        custom_rule = EnforcementRule(
            rule_id="high_roas_requirement",
            rule_type=ViolationType.ROAS_BELOW_THRESHOLD,
            threshold_value=3.0,
            enforcement_mode=EnforcementMode.HARD_BLOCK,
            enabled=True,
            description="High ROAS requirement for premium campaigns",
        )

        await enforcer.update_settings(
            tenant_id=1,
            updates={
                "rules": [custom_rule],
                "default_mode": EnforcementMode.ADVISORY,
            },
        )

        result = await enforcer.check_action(
            tenant_id=1,
            action_type="budget_increase",
            entity_type="campaign",
            entity_id="camp_123",
            proposed_value={"budget": 1000.0},
            metrics={"roas": 2.5},
        )

        # Custom rule should trigger hard_block
        assert result.allowed is False
        assert result.mode == EnforcementMode.HARD_BLOCK

    @pytest.mark.asyncio
    async def test_disabled_rule_ignored(self, enforcer):
        """Test that disabled rules are ignored."""
        custom_rule = EnforcementRule(
            rule_id="disabled_rule",
            rule_type=ViolationType.BUDGET_EXCEEDED,
            threshold_value=100.0,  # Very low threshold
            enforcement_mode=EnforcementMode.HARD_BLOCK,
            enabled=False,  # Disabled
        )

        await enforcer.update_settings(
            tenant_id=1,
            updates={"rules": [custom_rule]},
        )

        result = await enforcer.check_action(
            tenant_id=1,
            action_type="set_budget",
            entity_type="campaign",
            entity_id="camp_123",
            proposed_value={"budget": 5000.0},
        )

        # Disabled rule should not trigger
        assert result.allowed is True


# =============================================================================
# Test Auto-Pause
# =============================================================================


class TestAutoPause:
    """Tests for auto-pause functionality."""

    @pytest.mark.asyncio
    async def test_auto_pause_in_hard_block_mode(self, enforcer):
        """Test auto-pause works in hard_block mode."""
        await enforcer.update_settings(
            tenant_id=1,
            updates={
                "default_mode": EnforcementMode.HARD_BLOCK,
                "enforcement_enabled": True,
            },
        )

        # Mock the platform executor so we don't need real API credentials
        mock_executor = AsyncMock()
        mock_executor.execute_action = AsyncMock(return_value={"success": True})

        with patch(
            "app.autopilot.enforcer.PLATFORM_EXECUTORS",
            {"meta": mock_executor},
            create=True,
        ):
            with patch(
                "app.tasks.apply_actions_queue.PLATFORM_EXECUTORS",
                {"meta": mock_executor},
            ):
                paused = await enforcer.auto_pause_campaign(
                    tenant_id=1,
                    campaign_id="camp_123",
                    reason="ROAS below threshold",
                    metrics={"roas": 0.5, "spend": 1000.0},
                )

        assert paused is True

    @pytest.mark.asyncio
    async def test_auto_pause_disabled_in_advisory_mode(self, enforcer):
        """Test auto-pause is disabled in advisory mode."""
        await enforcer.update_settings(
            tenant_id=1,
            updates={
                "default_mode": EnforcementMode.ADVISORY,
                "enforcement_enabled": True,
            },
        )

        paused = await enforcer.auto_pause_campaign(
            tenant_id=1,
            campaign_id="camp_123",
            reason="ROAS below threshold",
            metrics={"roas": 0.5},
        )

        assert paused is False

    @pytest.mark.asyncio
    async def test_auto_pause_disabled_when_kill_switch_off(self, enforcer):
        """Test auto-pause is disabled when enforcement is off."""
        await enforcer.update_settings(
            tenant_id=1,
            updates={
                "default_mode": EnforcementMode.HARD_BLOCK,
                "enforcement_enabled": False,
            },
        )

        paused = await enforcer.auto_pause_campaign(
            tenant_id=1,
            campaign_id="camp_123",
            reason="ROAS below threshold",
            metrics={"roas": 0.5},
        )

        assert paused is False


# =============================================================================
# Test Result Serialization
# =============================================================================


class TestResultSerialization:
    """Tests for result serialization."""

    def test_enforcement_result_to_dict(self):
        """Test EnforcementResult serialization."""
        result = EnforcementResult(
            allowed=False,
            mode=EnforcementMode.SOFT_BLOCK,
            violations=[{"type": "budget_exceeded", "message": "Over limit"}],
            warnings=["Budget exceeds limit"],
            requires_confirmation=True,
            confirmation_token="token-123",
        )

        data = result.to_dict()

        assert data["allowed"] is False
        assert data["mode"] == "soft_block"
        assert len(data["violations"]) == 1
        assert data["requires_confirmation"] is True
        assert data["confirmation_token"] == "token-123"


# =============================================================================
# Test Notification Service
# =============================================================================


class TestNotificationService:
    """Tests for enforcement notification service."""

    @pytest.mark.asyncio
    @patch("app.autopilot.enforcer.SlackNotificationService")
    async def test_send_notification(self, mock_slack_cls):
        """Test sending enforcement notification."""
        # Configure mock Slack service to succeed
        mock_slack_instance = AsyncMock()
        mock_slack_instance.send_message = AsyncMock(return_value=True)
        mock_slack_instance.close = AsyncMock()
        mock_slack_cls.return_value = mock_slack_instance

        intervention = InterventionLog(
            tenant_id=1,
            timestamp=datetime.now(UTC),
            action_type="set_budget",
            entity_type="campaign",
            entity_id="camp_123",
            violation_type=ViolationType.BUDGET_EXCEEDED,
            intervention_action=InterventionAction.BLOCKED,
            enforcement_mode=EnforcementMode.HARD_BLOCK,
            details={"reason": "Over budget"},
        )

        result = await send_enforcement_notification(
            tenant_id=1,
            intervention=intervention,
            notification_channels=["email", "slack"],
        )

        assert result is True


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_zero_budget_handling(self, enforcer):
        """Test handling of zero budget values."""
        await enforcer.update_settings(
            tenant_id=1,
            updates={"budget_increase_limit_pct": 30.0},
        )

        # Increasing from zero should not cause division error
        result = await enforcer.check_action(
            tenant_id=1,
            action_type="budget_increase",
            entity_type="campaign",
            entity_id="camp_123",
            proposed_value={"budget": 1000.0},
            current_value={"budget": 0},
        )

        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_missing_metrics(self, enforcer):
        """Test handling of missing metrics."""
        result = await enforcer.check_action(
            tenant_id=1,
            action_type="budget_increase",
            entity_type="campaign",
            entity_id="camp_123",
            proposed_value={"budget": 1000.0},
            metrics=None,  # No metrics provided
        )

        # Should not crash, no ROAS violation
        assert result is not None
        roas_violations = [
            v
            for v in result.violations
            if v["type"] == ViolationType.ROAS_BELOW_THRESHOLD.value
        ]
        assert len(roas_violations) == 0

    @pytest.mark.asyncio
    async def test_multiple_violations_strictest_mode(self, enforcer):
        """Test that multiple violations use strictest mode."""
        # Create rules with different modes
        advisory_rule = EnforcementRule(
            rule_id="advisory_rule",
            rule_type=ViolationType.BUDGET_EXCEEDED,
            threshold_value=1000.0,
            enforcement_mode=EnforcementMode.ADVISORY,
            enabled=True,
        )
        hard_block_rule = EnforcementRule(
            rule_id="hard_block_rule",
            rule_type=ViolationType.BUDGET_EXCEEDED,
            threshold_value=500.0,
            enforcement_mode=EnforcementMode.HARD_BLOCK,
            enabled=True,
        )

        await enforcer.update_settings(
            tenant_id=1,
            updates={
                "rules": [advisory_rule, hard_block_rule],
                "default_mode": EnforcementMode.ADVISORY,
            },
        )

        result = await enforcer.check_action(
            tenant_id=1,
            action_type="set_budget",
            entity_type="campaign",
            entity_id="camp_123",
            proposed_value={"budget": 2000.0},
        )

        # Should use hard_block (strictest) mode
        assert result.mode == EnforcementMode.HARD_BLOCK
        assert result.allowed is False


# =============================================================================
# Database-Path Tests
# =============================================================================
#
# Everything below exercises the `if self.db is not None:` branches with a
# mocked AsyncSession. No real database connection is made: `db.execute` is
# stubbed to return crafted result objects, and persistence is asserted via
# `db.add` / `db.flush` / `db.commit` / `db.delete` call records.


def _make_db(execute_results: Optional[List[Any]] = None) -> MagicMock:
    """Build a mock AsyncSession.

    ``add`` is synchronous on AsyncSession, so it is a plain MagicMock;
    ``execute``/``flush``/``commit``/``delete``/``refresh`` are AsyncMocks.
    """
    db = MagicMock()
    db.add = MagicMock()
    db.delete = AsyncMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.refresh = AsyncMock()
    if execute_results is None:
        db.execute = AsyncMock(return_value=MagicMock())
    else:
        db.execute = AsyncMock(side_effect=list(execute_results))
    return db


def _scalars_first(value: Any) -> MagicMock:
    """Result stub for ``result.scalars().first()``."""
    result = MagicMock()
    result.scalars.return_value.first.return_value = value
    return result


def _scalars_all(values: List[Any]) -> MagicMock:
    """Result stub for ``result.scalars().all()``."""
    result = MagicMock()
    result.scalars.return_value.all.return_value = values
    return result


def _scalar_one(value: Any) -> MagicMock:
    """Result stub for ``result.scalar_one()``."""
    result = MagicMock()
    result.scalar_one.return_value = value
    return result


def _scalar_one_or_none(value: Any) -> MagicMock:
    """Result stub for ``result.scalar_one_or_none()``."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _rows_all(rows: List[Any]) -> MagicMock:
    """Result stub for ``result.all()``."""
    result = MagicMock()
    result.all.return_value = rows
    return result


def _added_of_type(db: MagicMock, model_cls: type) -> List[Any]:
    """Return all objects passed to ``db.add`` that are instances of model_cls."""
    return [
        call.args[0]
        for call in db.add.call_args_list
        if isinstance(call.args[0], model_cls)
    ]


def _db_settings_row(**overrides: Any) -> TenantEnforcementSettingsDB:
    """Construct an in-memory TenantEnforcementSettings row (no DB needed)."""
    row = TenantEnforcementSettingsDB(
        tenant_id=1,
        enforcement_enabled=True,
        autopilot_frozen=False,
        default_mode=DBEnforcementMode.SOFT_BLOCK,
        max_daily_budget=250.0,
        max_campaign_budget=5000.0,
        budget_increase_limit_pct=25.0,
        min_roas_threshold=1.5,
        roas_lookback_days=14,
        max_budget_changes_per_day=3,
        min_hours_between_changes=6,
    )
    row.id = uuid4()
    for key, value in overrides.items():
        setattr(row, key, value)
    return row


class TestGetSettingsDbPaths:
    """Tests for get_settings() database load/persist branches."""

    @pytest.mark.asyncio
    async def test_loads_existing_row_with_rules(self):
        """An existing DB row (with custom rules) maps to the Pydantic model."""
        rule_row = TenantEnforcementRuleDB(
            tenant_id=1,
            rule_id="min_roas_rule",
            rule_type=DBViolationType.ROAS_BELOW_THRESHOLD,
            threshold_value=2.0,
            enforcement_mode=DBEnforcementMode.HARD_BLOCK,
            enabled=True,
            description="Minimum ROAS",
        )
        row = _db_settings_row(rules=[rule_row])
        db = _make_db([_scalars_first(row)])
        enforcer = AutopilotEnforcer(db=db)

        settings = await enforcer.get_settings(tenant_id=1)

        assert settings.tenant_id == 1
        assert settings.default_mode == EnforcementMode.SOFT_BLOCK
        assert settings.max_daily_budget == 250.0
        assert settings.max_campaign_budget == 5000.0
        assert settings.budget_increase_limit_pct == 25.0
        assert settings.min_roas_threshold == 1.5
        assert settings.roas_lookback_days == 14
        assert settings.max_budget_changes_per_day == 3
        assert settings.min_hours_between_changes == 6
        assert len(settings.rules) == 1
        mapped = settings.rules[0]
        assert mapped.rule_id == "min_roas_rule"
        assert mapped.rule_type == ViolationType.ROAS_BELOW_THRESHOLD
        assert mapped.enforcement_mode == EnforcementMode.HARD_BLOCK
        assert mapped.threshold_value == 2.0
        assert mapped.description == "Minimum ROAS"

        # Nothing was created; result is cached (no second query)
        db.add.assert_not_called()
        await enforcer.get_settings(tenant_id=1)
        assert db.execute.await_count == 1

    @pytest.mark.asyncio
    async def test_creates_default_row_when_missing(self):
        """A cache+DB miss persists a defaults row and returns defaults."""
        db = _make_db([_scalars_first(None)])
        enforcer = AutopilotEnforcer(db=db)

        settings = await enforcer.get_settings(tenant_id=7)

        created = _added_of_type(db, TenantEnforcementSettingsDB)
        assert len(created) == 1
        assert created[0].tenant_id == 7
        assert created[0].enforcement_enabled is True
        # TRUST-003: the persisted first-use default fails safe to SOFT_BLOCK.
        assert created[0].default_mode == DBEnforcementMode.SOFT_BLOCK
        db.flush.assert_awaited_once()

        assert settings.tenant_id == 7
        assert settings.default_mode == EnforcementMode.SOFT_BLOCK
        # Cached for subsequent calls
        assert enforcer._settings_cache[7] is settings


class TestUpdateSettingsDbPaths:
    """Tests for update_settings() database persist branches."""

    @pytest.mark.asyncio
    async def test_scalar_updates_persist_to_row_and_commit(self):
        """Scalar field updates land on the DB row and are explicitly committed."""
        row = _db_settings_row(rules=[])
        db = _make_db([_scalars_first(row)])
        enforcer = AutopilotEnforcer(db=db)
        # Pre-seed the cache so get_settings() does not consume db.execute
        enforcer._settings_cache[1] = EnforcementSettings(tenant_id=1)

        settings = await enforcer.update_settings(
            tenant_id=1,
            updates={
                "default_mode": "hard_block",
                "max_campaign_budget": 9000.0,
                "not_a_real_field": "ignored",
            },
        )

        assert settings.default_mode == EnforcementMode.HARD_BLOCK
        assert settings.max_campaign_budget == 9000.0
        # DB row received mapped values (string mode -> DB enum)
        assert row.default_mode == DBEnforcementMode.HARD_BLOCK
        assert row.max_campaign_budget == 9000.0
        db.flush.assert_awaited()
        # Explicit commit is load-bearing: get_async_session never commits
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_creates_row_when_missing_then_commits(self):
        """If no settings row exists yet, update_settings creates one."""
        db = _make_db([_scalars_first(None)])
        enforcer = AutopilotEnforcer(db=db)
        enforcer._settings_cache[1] = EnforcementSettings(tenant_id=1)

        await enforcer.update_settings(
            tenant_id=1,
            updates={"max_daily_budget": 100.0},
        )

        created = _added_of_type(db, TenantEnforcementSettingsDB)
        assert len(created) == 1
        assert created[0].tenant_id == 1
        assert created[0].max_daily_budget == 100.0
        db.commit.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_rules_update_replaces_db_rules(self):
        """A rules update deletes existing DB rules and inserts the new set."""
        existing_rule = TenantEnforcementRuleDB(
            tenant_id=1,
            rule_id="old_rule",
            rule_type=DBViolationType.BUDGET_EXCEEDED,
            threshold_value=100.0,
            enforcement_mode=DBEnforcementMode.ADVISORY,
            enabled=True,
        )
        row = _db_settings_row(rules=[existing_rule])
        db = _make_db([_scalars_first(row)])
        enforcer = AutopilotEnforcer(db=db)
        enforcer._settings_cache[1] = EnforcementSettings(tenant_id=1)

        new_rule = EnforcementRule(
            rule_id="new_rule",
            rule_type=ViolationType.BUDGET_EXCEEDED,
            threshold_value=2500.0,
            enforcement_mode=EnforcementMode.SOFT_BLOCK,
            enabled=True,
            description="New budget cap",
        )
        await enforcer.update_settings(tenant_id=1, updates={"rules": [new_rule]})

        db.delete.assert_awaited_once_with(existing_rule)
        inserted = _added_of_type(db, TenantEnforcementRuleDB)
        assert len(inserted) == 1
        assert inserted[0].rule_id == "new_rule"
        assert inserted[0].rule_type == DBViolationType.BUDGET_EXCEEDED
        assert inserted[0].enforcement_mode == DBEnforcementMode.SOFT_BLOCK
        assert inserted[0].threshold_value == 2500.0
        assert inserted[0].tenant_id == 1
        db.commit.assert_awaited_once()


class TestSubscriptionGate:
    """Tests for the subscription gate in check_action()."""

    @pytest.mark.asyncio
    async def test_restricted_subscription_forces_advisory(self, monkeypatch):
        """A lapsed subscription blocks execution with an advisory violation."""
        info = SimpleNamespace(
            is_access_restricted=True,
            restriction_reason="Trial expired",
            plan="starter",
            status=SimpleNamespace(value="expired"),
            days_in_grace=3,
        )
        monkeypatch.setattr(
            "app.core.subscription.get_subscription_info",
            AsyncMock(return_value=info),
        )
        enforcer = AutopilotEnforcer(db=None)

        result = await enforcer.check_action(
            tenant_id=1,
            action_type="set_budget",
            entity_type="campaign",
            entity_id="camp_123",
            proposed_value={"budget": 100.0},
        )

        assert result.allowed is False
        assert result.mode == EnforcementMode.ADVISORY
        assert len(result.violations) == 1
        violation = result.violations[0]
        assert violation["type"] == ViolationType.SUBSCRIPTION_EXPIRED.value
        assert violation["message"] == "Trial expired"
        assert violation["plan"] == "starter"
        assert violation["status"] == "expired"
        assert violation["days_in_grace"] == 3
        assert result.warnings


class TestCheckActionDbPaths:
    """Tests for check_action() persistence branches."""

    @pytest.mark.asyncio
    async def test_soft_block_persists_confirmation_token(self):
        """A soft-blocked action persists its confirmation token to the DB."""
        # Two DB round-trips come from _check_frequency_rules
        db = _make_db([_scalar_one(0), _scalars_first(None)])
        enforcer = AutopilotEnforcer(db=db)
        enforcer._settings_cache[1] = EnforcementSettings(
            tenant_id=1,
            default_mode=EnforcementMode.SOFT_BLOCK,
            max_campaign_budget=1000.0,
        )

        result = await enforcer.check_action(
            tenant_id=1,
            action_type="set_budget",
            entity_type="campaign",
            entity_id="camp_123",
            proposed_value={"budget": 5000.0},
        )

        assert result.allowed is False
        assert result.requires_confirmation is True
        tokens = _added_of_type(db, PendingConfirmationTokenDB)
        assert len(tokens) == 1
        assert tokens[0].token == result.confirmation_token
        assert tokens[0].tenant_id == 1
        assert tokens[0].action_type == "set_budget"
        assert tokens[0].entity_id == "camp_123"
        assert tokens[0].expires_at > tokens[0].created_at
        db.flush.assert_awaited()

    @pytest.mark.asyncio
    async def test_hard_block_logs_audit_row_and_notifies(self):
        """A hard-blocked action writes an audit row and sends a notification."""
        db = _make_db([_scalar_one(0), _scalars_first(None)])
        enforcer = AutopilotEnforcer(db=db)
        enforcer._settings_cache[1] = EnforcementSettings(
            tenant_id=1,
            default_mode=EnforcementMode.HARD_BLOCK,
            max_campaign_budget=1000.0,
        )

        notify = AsyncMock(return_value=True)
        with patch("app.autopilot.enforcer.send_enforcement_notification", notify):
            result = await enforcer.check_action(
                tenant_id=1,
                action_type="set_budget",
                entity_type="campaign",
                entity_id="camp_123",
                proposed_value={"budget": 5000.0},
            )

        assert result.allowed is False
        audit_rows = _added_of_type(db, EnforcementAuditLogDB)
        assert len(audit_rows) == 1
        assert audit_rows[0].intervention_action == DBInterventionAction.BLOCKED
        assert audit_rows[0].enforcement_mode == DBEnforcementMode.HARD_BLOCK
        assert audit_rows[0].violation_type == DBViolationType.BUDGET_EXCEEDED
        notify.assert_awaited_once()


class TestFrequencyRulesDbPaths:
    """Tests for _check_frequency_rules() DB-backed checks."""

    @pytest.mark.asyncio
    async def test_daily_cap_and_min_gap_violations(self):
        """Hitting the daily cap and a too-recent change yields two violations."""
        last_change = datetime.now(UTC) - timedelta(hours=1)
        db = _make_db([_scalar_one(5), _scalars_first(last_change)])
        enforcer = AutopilotEnforcer(db=db)
        settings = EnforcementSettings(tenant_id=1)  # 5/day cap, 4h min gap

        violations = await enforcer._check_frequency_rules(settings, 1, "camp_123")

        assert len(violations) == 2
        assert all(
            v["type"] == ViolationType.FREQUENCY_CAP_EXCEEDED.value for v in violations
        )
        assert violations[0]["actual"] == 5
        assert violations[0]["threshold"] == 5
        assert violations[1]["actual"] == pytest.approx(1.0, abs=0.1)
        assert violations[1]["threshold"] == 4

    @pytest.mark.asyncio
    async def test_quiet_history_yields_no_violations(self):
        """No recent budget changes means no frequency violations."""
        db = _make_db([_scalar_one(0), _scalars_first(None)])
        enforcer = AutopilotEnforcer(db=db)
        settings = EnforcementSettings(tenant_id=1)

        violations = await enforcer._check_frequency_rules(settings, 1, "camp_123")

        assert violations == []


class TestConfirmActionDbPaths:
    """Tests for confirm_action() DB token fallback."""

    def _token_row(self, tenant_id: int = 1) -> PendingConfirmationTokenDB:
        """Construct an in-memory pending confirmation token row."""
        now = datetime.now(UTC)
        return PendingConfirmationTokenDB(
            tenant_id=tenant_id,
            token="a" * 64,
            action_type="set_budget",
            entity_id="camp_123",
            violations=[{"type": "budget_exceeded"}],
            created_at=now,
            expires_at=now + timedelta(hours=1),
        )

    @pytest.mark.asyncio
    async def test_falls_back_to_db_token_and_cleans_up(self):
        """A token missing from memory is loaded from DB, used, and deleted."""
        token_row = self._token_row()
        db = _make_db([_scalars_first(token_row)])
        enforcer = AutopilotEnforcer(db=db)

        success, error = await enforcer.confirm_action(
            tenant_id=1,
            confirmation_token="a" * 64,
            user_id=7,
            override_reason="Manager approved",
        )

        assert success is True
        assert error is None
        db.delete.assert_awaited_once_with(token_row)
        audit_rows = _added_of_type(db, EnforcementAuditLogDB)
        assert len(audit_rows) == 1
        assert audit_rows[0].user_id == 7
        assert audit_rows[0].override_reason == "Manager approved"
        assert audit_rows[0].intervention_action == DBInterventionAction.OVERRIDE_LOGGED

    @pytest.mark.asyncio
    async def test_db_miss_returns_error(self):
        """A token absent from memory and DB is rejected."""
        db = _make_db([_scalars_first(None)])
        enforcer = AutopilotEnforcer(db=db)

        success, error = await enforcer.confirm_action(
            tenant_id=1,
            confirmation_token="missing-token",
            user_id=7,
        )

        assert success is False
        assert "Invalid" in error or "expired" in error

    @pytest.mark.asyncio
    async def test_db_token_wrong_tenant_rejected(self):
        """A DB token belonging to another tenant is rejected (but consumed)."""
        token_row = self._token_row(tenant_id=2)
        db = _make_db([_scalars_first(token_row)])
        enforcer = AutopilotEnforcer(db=db)

        success, error = await enforcer.confirm_action(
            tenant_id=1,
            confirmation_token="a" * 64,
            user_id=7,
        )

        assert success is False
        assert "tenant" in error.lower()
        db.delete.assert_awaited_once_with(token_row)


class TestInterventionLogDbPaths:
    """Tests for _log_intervention() persistence and notification handling."""

    @pytest.mark.asyncio
    async def test_persists_audit_row_with_outcome_estimate(self):
        """The audit row is persisted with an outcome estimate attached."""
        db = _make_db()
        enforcer = AutopilotEnforcer(db=db)

        await enforcer._log_intervention(
            tenant_id=1,
            action_type="budget_decrease",
            entity_type="campaign",
            entity_id="camp_123",
            violation_type=ViolationType.BUDGET_EXCEEDED,
            intervention_action=InterventionAction.WARNED,
            enforcement_mode=EnforcementMode.ADVISORY,
            details={
                "proposed_value": {"daily_budget_cents": 5_000},
                "current_value": {"daily_budget_cents": 10_000},
                "metrics": {"roas": 2.5},
            },
            user_id=3,
        )

        audit_rows = _added_of_type(db, EnforcementAuditLogDB)
        assert len(audit_rows) == 1
        row = audit_rows[0]
        assert row.tenant_id == 1
        assert row.violation_type == DBViolationType.BUDGET_EXCEEDED
        assert row.intervention_action == DBInterventionAction.WARNED
        assert row.enforcement_mode == DBEnforcementMode.ADVISORY
        assert row.user_id == 3
        # budget_decrease with a clean before/after pair -> "saved" outcome
        assert row.outcome_type == "saved"
        assert row.value_delivered_cents > 0
        db.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_outcome_estimation_failure_is_nonfatal(self, monkeypatch):
        """An estimator crash degrades to null outcome fields, never raises."""

        def _boom(**_kwargs: Any) -> None:
            raise RuntimeError("estimator exploded")

        monkeypatch.setattr("app.services.autopilot.outcomes.estimate_outcome", _boom)
        db = _make_db()
        enforcer = AutopilotEnforcer(db=db)

        await enforcer._log_intervention(
            tenant_id=1,
            action_type="set_budget",
            entity_type="campaign",
            entity_id="camp_123",
            violation_type=ViolationType.BUDGET_EXCEEDED,
            intervention_action=InterventionAction.WARNED,
            enforcement_mode=EnforcementMode.ADVISORY,
            details={"proposed_value": {"budget": 100.0}},
        )

        audit_rows = _added_of_type(db, EnforcementAuditLogDB)
        assert len(audit_rows) == 1
        assert audit_rows[0].value_delivered_cents is None
        assert audit_rows[0].outcome_type is None
        assert audit_rows[0].outcome_confidence is None

    @pytest.mark.asyncio
    async def test_notification_failure_is_swallowed(self):
        """A notification transport error never breaks intervention logging."""
        db = _make_db()
        enforcer = AutopilotEnforcer(db=db)

        notify = AsyncMock(side_effect=ConnectionError("smtp down"))
        with patch("app.autopilot.enforcer.send_enforcement_notification", notify):
            await enforcer._log_intervention(
                tenant_id=1,
                action_type="set_budget",
                entity_type="campaign",
                entity_id="camp_123",
                violation_type=ViolationType.BUDGET_EXCEEDED,
                intervention_action=InterventionAction.BLOCKED,
                enforcement_mode=EnforcementMode.HARD_BLOCK,
                details={"violations": []},
            )

        notify.assert_awaited_once()
        # The audit row was still persisted before the notification failed
        assert len(_added_of_type(db, EnforcementAuditLogDB)) == 1


class TestGetInterventionLogDbPaths:
    """Tests for get_intervention_log()."""

    @pytest.mark.asyncio
    async def test_no_db_returns_empty_list(self):
        """Without a DB session the log is empty."""
        enforcer = AutopilotEnforcer(db=None)
        assert await enforcer.get_intervention_log(tenant_id=1) == []

    @pytest.mark.asyncio
    async def test_returns_serialized_rows(self):
        """Audit rows come back serialized via to_dict()."""
        log_row = EnforcementAuditLogDB(
            tenant_id=1,
            timestamp=datetime.now(UTC),
            action_type="set_budget",
            entity_type="campaign",
            entity_id="camp_123",
            violation_type=DBViolationType.BUDGET_EXCEEDED,
            intervention_action=DBInterventionAction.BLOCKED,
            enforcement_mode=DBEnforcementMode.HARD_BLOCK,
            details={"reason": "over budget"},
        )
        log_row.id = uuid4()
        db = _make_db([_scalars_all([log_row])])
        enforcer = AutopilotEnforcer(db=db)

        entries = await enforcer.get_intervention_log(tenant_id=1, days=7, limit=10)

        assert len(entries) == 1
        assert entries[0]["action_type"] == "set_budget"
        assert entries[0]["violation_type"] == "budget_exceeded"
        assert entries[0]["intervention_action"] == "blocked"
        assert entries[0]["enforcement_mode"] == "hard_block"
        db.execute.assert_awaited_once()


class TestAutoPauseExecutorPaths:
    """Tests for auto_pause_campaign() platform executor delegation."""

    async def _arm_hard_block(self, enforcer: AutopilotEnforcer) -> None:
        """Put the tenant in hard-block mode so auto-pause can run."""
        await enforcer.update_settings(
            tenant_id=1,
            updates={
                "default_mode": EnforcementMode.HARD_BLOCK,
                "enforcement_enabled": True,
            },
        )

    @pytest.mark.asyncio
    async def test_uses_platform_specific_executor(self, enforcer):
        """The executor matching metrics['platform'] is used."""
        await self._arm_hard_block(enforcer)
        executor = AsyncMock()
        executor.execute_action = AsyncMock(return_value={"success": True})

        with patch(
            "app.tasks.apply_actions_queue.PLATFORM_EXECUTORS",
            {"google": executor},
        ):
            paused = await enforcer.auto_pause_campaign(
                tenant_id=1,
                campaign_id="camp_9",
                reason="ROAS collapse",
                metrics={"platform": "google", "roas": 0.2},
            )

        assert paused is True
        executor.execute_action.assert_awaited_once()
        assert executor.execute_action.await_args.kwargs["entity_id"] == "camp_9"
        assert (
            executor.execute_action.await_args.kwargs["action_type"] == "pause_campaign"
        )

    @pytest.mark.asyncio
    async def test_returns_false_when_no_executor_available(self, enforcer):
        """Unknown platform with no meta fallback returns False."""
        await self._arm_hard_block(enforcer)

        with patch("app.tasks.apply_actions_queue.PLATFORM_EXECUTORS", {}):
            paused = await enforcer.auto_pause_campaign(
                tenant_id=1,
                campaign_id="camp_9",
                reason="ROAS collapse",
                metrics={"platform": "unknown"},
            )

        assert paused is False

    @pytest.mark.asyncio
    async def test_returns_false_when_executor_reports_failure(self, enforcer):
        """A non-success executor result returns False."""
        await self._arm_hard_block(enforcer)
        executor = AsyncMock()
        executor.execute_action = AsyncMock(
            return_value={"success": False, "error": "api down"}
        )

        with patch(
            "app.tasks.apply_actions_queue.PLATFORM_EXECUTORS",
            {"meta": executor},
        ):
            paused = await enforcer.auto_pause_campaign(
                tenant_id=1,
                campaign_id="camp_9",
                reason="ROAS collapse",
                metrics={"roas": 0.2},
            )

        assert paused is False

    @pytest.mark.asyncio
    async def test_returns_false_on_network_error(self, enforcer):
        """Network errors from the executor are caught, returning False."""
        await self._arm_hard_block(enforcer)
        executor = AsyncMock()
        executor.execute_action = AsyncMock(side_effect=ConnectionError("timeout"))

        with patch(
            "app.tasks.apply_actions_queue.PLATFORM_EXECUTORS",
            {"meta": executor},
        ):
            paused = await enforcer.auto_pause_campaign(
                tenant_id=1,
                campaign_id="camp_9",
                reason="ROAS collapse",
                metrics={"roas": 0.2},
            )

        assert paused is False

    @pytest.mark.asyncio
    async def test_returns_false_on_unexpected_error(self, enforcer):
        """Unexpected executor errors are caught, returning False."""
        await self._arm_hard_block(enforcer)
        executor = AsyncMock()
        executor.execute_action = AsyncMock(side_effect=RuntimeError("boom"))

        with patch(
            "app.tasks.apply_actions_queue.PLATFORM_EXECUTORS",
            {"meta": executor},
        ):
            paused = await enforcer.auto_pause_campaign(
                tenant_id=1,
                campaign_id="camp_9",
                reason="ROAS collapse",
                metrics={"roas": 0.2},
            )

        assert paused is False


class TestNotificationDbPaths:
    """Tests for send_enforcement_notification() email/Slack channels."""

    def _intervention(self) -> InterventionLog:
        """Build a representative blocked-action intervention."""
        return InterventionLog(
            tenant_id=1,
            timestamp=datetime.now(UTC),
            action_type="set_budget",
            entity_type="campaign",
            entity_id="camp_123",
            violation_type=ViolationType.BUDGET_EXCEEDED,
            intervention_action=InterventionAction.BLOCKED,
            enforcement_mode=EnforcementMode.HARD_BLOCK,
            details={"reason": "over budget"},
        )

    @pytest.mark.asyncio
    @patch("app.autopilot.enforcer.get_email_service")
    async def test_email_sent_to_all_admin_users(self, mock_get_email):
        """Emails go to every active admin/manager for the tenant."""
        email_svc = MagicMock()
        email_svc._create_message.return_value = MagicMock()
        email_svc._send_email.return_value = True
        mock_get_email.return_value = email_svc

        db = _make_db(
            [
                _scalar_one_or_none("Acme Corp"),
                _rows_all([("admin@acme.test", "Admin"), ("mgr@acme.test", "Mgr")]),
            ]
        )

        sent = await send_enforcement_notification(
            tenant_id=1,
            intervention=self._intervention(),
            notification_channels=["email"],
            db=db,
        )

        assert sent is True
        assert email_svc._send_email.call_count == 2
        recipients = [c.args[0] for c in email_svc._send_email.call_args_list]
        assert recipients == ["admin@acme.test", "mgr@acme.test"]
        assert email_svc._create_message.call_args.kwargs["to_email"] == "mgr@acme.test"

    @pytest.mark.asyncio
    @patch("app.autopilot.enforcer.get_email_service")
    async def test_email_smtp_failure_returns_false(self, mock_get_email):
        """Per-recipient SMTP failures are logged and produce a False result."""
        email_svc = MagicMock()
        email_svc._create_message.return_value = MagicMock()
        email_svc._send_email.side_effect = smtplib.SMTPException("relay refused")
        mock_get_email.return_value = email_svc

        db = _make_db(
            [
                _scalar_one_or_none("Acme Corp"),
                _rows_all([("admin@acme.test", "Admin")]),
            ]
        )

        sent = await send_enforcement_notification(
            tenant_id=1,
            intervention=self._intervention(),
            notification_channels=["email"],
            db=db,
        )

        assert sent is False

    @pytest.mark.asyncio
    @patch("app.autopilot.enforcer.get_email_service")
    async def test_no_admin_users_sends_nothing(self, mock_get_email):
        """No admin users (and no tenant name) means no email is attempted."""
        db = _make_db([_scalar_one_or_none(None), _rows_all([])])

        sent = await send_enforcement_notification(
            tenant_id=1,
            intervention=self._intervention(),
            notification_channels=["email"],
            db=db,
        )

        assert sent is False
        mock_get_email.assert_not_called()

    @pytest.mark.asyncio
    async def test_email_db_error_is_swallowed(self):
        """A DB connection error during email lookup is caught."""
        db = MagicMock()
        db.execute = AsyncMock(side_effect=ConnectionError("db unreachable"))

        sent = await send_enforcement_notification(
            tenant_id=1,
            intervention=self._intervention(),
            notification_channels=["email"],
            db=db,
        )

        assert sent is False

    @pytest.mark.asyncio
    @patch("app.autopilot.enforcer.SlackNotificationService")
    async def test_slack_failure_is_swallowed(self, mock_slack_cls):
        """A Slack transport error is caught and reported as not sent."""
        slack_instance = MagicMock()
        slack_instance.send_message = AsyncMock(
            side_effect=ConnectionError("webhook down")
        )
        slack_instance.close = AsyncMock()
        mock_slack_cls.return_value = slack_instance

        sent = await send_enforcement_notification(
            tenant_id=1,
            intervention=self._intervention(),
            notification_channels=["slack"],
        )

        assert sent is False


class TestHighRiskActionGate:
    """TRUST-004: high-risk action types require confirmation even with no
    threshold violation, unless the tenant opted into advisory mode."""

    @pytest.mark.asyncio
    async def test_high_risk_requires_confirmation_when_not_advisory(self, enforcer):
        await enforcer.update_settings(
            tenant_id=1, updates={"default_mode": EnforcementMode.SOFT_BLOCK}
        )
        # 10% increase — no threshold violation; risk comes purely from the type.
        result = await enforcer.check_action(
            tenant_id=1,
            action_type="budget_increase",
            entity_type="campaign",
            entity_id="c1",
            proposed_value={"budget": 1100.0},
            current_value={"budget": 1000.0},
        )
        assert result.allowed is False
        assert result.requires_confirmation is True
        assert result.confirmation_token

    @pytest.mark.asyncio
    async def test_safe_action_allowed_under_soft_block_default(self, enforcer):
        await enforcer.update_settings(
            tenant_id=1, updates={"default_mode": EnforcementMode.SOFT_BLOCK}
        )
        result = await enforcer.check_action(
            tenant_id=1,
            action_type="budget_decrease",
            entity_type="campaign",
            entity_id="c1",
            proposed_value={"budget": 900.0},
            current_value={"budget": 1000.0},
        )
        assert result.allowed is True
        assert result.requires_confirmation is False

    @pytest.mark.asyncio
    async def test_high_risk_allowed_when_advisory_opt_out(self, enforcer):
        await enforcer.update_settings(
            tenant_id=1, updates={"default_mode": EnforcementMode.ADVISORY}
        )
        result = await enforcer.check_action(
            tenant_id=1,
            action_type="budget_increase",
            entity_type="campaign",
            entity_id="c1",
            proposed_value={"budget": 1100.0},
            current_value={"budget": 1000.0},
        )
        assert result.allowed is True
