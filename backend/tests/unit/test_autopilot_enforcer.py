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

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.autopilot.enforcer import (
    AutopilotEnforcer,
    EnforcementMode,
    EnforcementSettings,
    EnforcementRule,
    EnforcementResult,
    ViolationType,
    InterventionAction,
    InterventionLog,
    send_enforcement_notification,
    clear_enforcement_cache,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def enforcer():
    """Create an AutopilotEnforcer instance without database."""
    # Clear the global cache before each test to ensure clean state
    clear_enforcement_cache()
    return AutopilotEnforcer(db=None)


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
        assert settings.default_mode == EnforcementMode.ADVISORY
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
        await enforcer.update_settings(tenant_id=1, updates={"max_campaign_budget": 7500.0})

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
        roas_violations = [v for v in result.violations if v["type"] == ViolationType.ROAS_BELOW_THRESHOLD.value]
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

        roas_violations = [v for v in result.violations if v["type"] == ViolationType.ROAS_BELOW_THRESHOLD.value]
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
        success2, error2 = await enforcer.confirm_action(
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
        assert any(v.get("rule_id") == "premium_budget_limit" for v in result.violations)

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
    async def test_send_notification(self):
        """Test sending enforcement notification."""
        intervention = InterventionLog(
            tenant_id=1,
            timestamp=datetime.now(timezone.utc),
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
        roas_violations = [v for v in result.violations if v["type"] == ViolationType.ROAS_BELOW_THRESHOLD.value]
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
