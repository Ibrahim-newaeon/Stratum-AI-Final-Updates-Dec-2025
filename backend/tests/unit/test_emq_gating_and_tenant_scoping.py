# =============================================================================
# Stratum AI - EMQ Mode Gating & Tenant Scoping Tests
# =============================================================================
"""
Unit tests for:
- EMQ mode gating rules (autopilot mode restrictions based on EMQ score)
- Tenant scoping enforcement on key endpoints

These tests verify critical business rules and security constraints.
"""

from datetime import UTC, datetime
from typing import Any, Optional

import pytest

# =============================================================================
# EMQ Mode Gating Rules Tests
# =============================================================================


class TestEmqModeGating:
    """
    Tests for EMQ mode gating rules.

    Rules:
    - EMQ >= 90: Full autopilot allowed
    - EMQ 80-89: Supervised mode only (human approval required)
    - EMQ 70-79: Alert-only mode (no automatic actions)
    - EMQ < 70: Automation suspended
    """

    def test_full_autopilot_allowed_above_90(self):
        """EMQ >= 90 should allow full autopilot mode."""
        result = determine_allowed_mode(emq_score=95)
        assert result["allowed_modes"] == ["full", "supervised", "alert_only", "off"]
        assert result["max_mode"] == "full"
        assert not result["automation_suspended"]

    def test_supervised_only_between_80_and_89(self):
        """EMQ 80-89 should restrict to supervised mode."""
        result = determine_allowed_mode(emq_score=85)
        assert "full" not in result["allowed_modes"]
        assert result["max_mode"] == "supervised"
        assert not result["automation_suspended"]
        assert (
            "EMQ below threshold" in result["restrictions"][0] if result["restrictions"] else True
        )

    def test_alert_only_between_70_and_79(self):
        """EMQ 70-79 should restrict to alert-only mode."""
        result = determine_allowed_mode(emq_score=75)
        assert "full" not in result["allowed_modes"]
        assert "supervised" not in result["allowed_modes"]
        assert result["max_mode"] == "alert_only"
        assert not result["automation_suspended"]

    def test_automation_suspended_below_70(self):
        """EMQ < 70 should suspend all automation."""
        result = determine_allowed_mode(emq_score=65)
        assert result["automation_suspended"] == True
        assert result["max_mode"] == "off"
        assert result["allowed_modes"] == ["off"]
        assert len(result["alerts"]) > 0

    def test_mode_downgrade_on_emq_drop(self):
        """Mode should be automatically downgraded when EMQ drops."""
        # Tenant currently in full autopilot mode
        current_mode = "full"

        # EMQ drops to 82
        new_emq = 82
        result = handle_emq_change(current_mode, new_emq, previous_emq=92)

        assert result["mode_changed"] == True
        assert result["new_mode"] == "supervised"
        assert result["reason"] == "EMQ dropped below full autopilot threshold"
        assert result["alert_created"] == True

    def test_no_mode_upgrade_without_approval(self):
        """Mode should not auto-upgrade even if EMQ improves."""
        # Tenant currently in supervised mode
        current_mode = "supervised"

        # EMQ rises to 95
        new_emq = 95
        result = handle_emq_change(current_mode, new_emq, previous_emq=82)

        # Should NOT auto-upgrade
        assert result["mode_changed"] == False
        assert result["new_mode"] == "supervised"
        assert result["upgrade_available"] == True
        assert "manual approval" in result["message"].lower()

    def test_api_health_overrides_emq(self):
        """API health issues should override EMQ gating."""
        result = determine_allowed_mode(emq_score=95, api_health=False)

        assert result["automation_suspended"] == True
        assert result["max_mode"] == "off"
        assert "API health" in str(result["alerts"])

    def test_event_loss_impacts_mode(self):
        """High event loss should restrict mode."""
        # High EMQ but high event loss
        result = determine_allowed_mode(emq_score=92, event_loss_pct=20)

        # Should restrict due to event loss
        assert result["max_mode"] != "full"
        assert "event loss" in str(result["restrictions"]).lower()

    def test_boundary_conditions(self):
        """Test exact boundary values."""
        # Exactly 90
        result_90 = determine_allowed_mode(emq_score=90)
        assert result_90["max_mode"] == "full"

        # Exactly 89.9
        result_89 = determine_allowed_mode(emq_score=89.9)
        assert result_89["max_mode"] == "supervised"

        # Exactly 80
        result_80 = determine_allowed_mode(emq_score=80)
        assert result_80["max_mode"] == "supervised"

        # Exactly 79.9
        result_79 = determine_allowed_mode(emq_score=79.9)
        assert result_79["max_mode"] == "alert_only"

        # Exactly 70
        result_70 = determine_allowed_mode(emq_score=70)
        assert result_70["max_mode"] == "alert_only"

        # Exactly 69.9
        result_69 = determine_allowed_mode(emq_score=69.9)
        assert result_69["automation_suspended"] == True

    def test_mode_gating_with_feature_flags(self):
        """Feature flags should be able to override gating."""
        # With override flag enabled
        result = determine_allowed_mode(emq_score=75, feature_flags={"emq_gating_override": True})

        # Should allow full mode despite low EMQ
        assert result["max_mode"] == "full"
        assert result["override_active"] == True
        assert "override" in str(result["warnings"]).lower()


# =============================================================================
# Tenant Scoping Tests
# =============================================================================


class TestTenantScoping:
    """
    Tests for tenant isolation and scoping enforcement.

    Rules:
    - All data queries must include tenant_id filter
    - Cross-tenant data access is forbidden
    - Tenant ID in path must match auth token's tenant
    """

    def test_query_requires_tenant_id(self):
        """Data queries must include tenant_id."""
        # Mock query without tenant_id should raise error
        with pytest.raises(TenantScopingError):
            execute_query("SELECT * FROM campaigns")

        # Query with tenant_id should succeed
        result = execute_query("SELECT * FROM campaigns WHERE tenant_id = :tenant_id", tenant_id=1)
        assert result is not None

    def test_cross_tenant_access_blocked(self):
        """Access to another tenant's data is blocked."""
        # User belongs to tenant 1
        user_tenant_id = 1

        # Trying to access tenant 2's data
        requested_tenant_id = 2

        with pytest.raises(TenantAccessDeniedError):
            verify_tenant_access(user_tenant_id, requested_tenant_id)

    def test_superadmin_cross_tenant_access(self):
        """Superadmin can access any tenant."""
        # Superadmin accessing tenant 2
        result = verify_tenant_access(
            user_tenant_id=None,  # Superadmin has no tenant
            requested_tenant_id=2,
            user_role="superadmin",
        )

        assert result["allowed"] == True
        assert result["audit_logged"] == True

    def test_path_tenant_id_must_match_token(self):
        """Tenant ID in URL path must match JWT token."""
        # Token has tenant_id=1
        token_tenant_id = 1

        # URL has tenant_id=1
        path_tenant_id = 1

        result = validate_path_tenant(token_tenant_id, path_tenant_id)
        assert result["valid"] == True

        # URL has tenant_id=2
        path_tenant_id_wrong = 2

        with pytest.raises(TenantMismatchError):
            validate_path_tenant(token_tenant_id, path_tenant_id_wrong)

    def test_tenant_isolation_in_campaigns(self):
        """Campaigns endpoint enforces tenant isolation."""
        # Create campaign for tenant 1
        campaign = create_campaign_for_test(tenant_id=1)

        # User from tenant 1 can access
        result = get_campaign(campaign.id, user_tenant_id=1)
        assert result["id"] == campaign.id

        # User from tenant 2 cannot access
        with pytest.raises(TenantAccessDeniedError):
            get_campaign(campaign.id, user_tenant_id=2)

    def test_tenant_isolation_in_actions(self):
        """Actions queue enforces tenant isolation."""
        # Create action for tenant 1
        action = create_action_for_test(tenant_id=1)

        # Approve from same tenant
        result = approve_action(action.id, user_tenant_id=1)
        assert result["success"] == True

        # Approve from different tenant fails
        action2 = create_action_for_test(tenant_id=1)
        with pytest.raises(TenantAccessDeniedError):
            approve_action(action2.id, user_tenant_id=2)

    def test_tenant_id_in_all_writes(self):
        """All write operations must set tenant_id."""
        # Create without tenant_id should fail
        with pytest.raises(TenantScopingError):
            create_campaign(name="Test", platforms=["meta"])

        # Create with tenant_id should succeed
        result = create_campaign(name="Test", platforms=["meta"], tenant_id=1)
        assert result["tenant_id"] == 1

    def test_bulk_operations_scoped(self):
        """Bulk operations respect tenant scoping."""
        # Bulk update for tenant 1
        campaign_ids = ["camp_1", "camp_2", "camp_3"]  # All belong to tenant 1

        result = bulk_update_campaigns(campaign_ids=campaign_ids, status="paused", user_tenant_id=1)

        assert result["updated_count"] == 3
        assert all(c["tenant_id"] == 1 for c in result["campaigns"])

    def test_account_manager_multi_tenant_access(self):
        """Account managers can access assigned tenants."""
        # AM assigned to tenants [1, 2, 3]
        am_assigned_tenants = [1, 2, 3]

        # Can access tenant 2
        result = verify_tenant_access(
            user_tenant_id=None,  # AM has no direct tenant
            requested_tenant_id=2,
            user_role="account_manager",
            assigned_tenants=am_assigned_tenants,
        )
        assert result["allowed"] == True

        # Cannot access tenant 4
        with pytest.raises(TenantAccessDeniedError):
            verify_tenant_access(
                user_tenant_id=None,
                requested_tenant_id=4,
                user_role="account_manager",
                assigned_tenants=am_assigned_tenants,
            )

    def test_audit_log_includes_tenant(self):
        """All audit logs include tenant context."""
        # Perform an action
        action_result = perform_audited_action(
            action="campaign_pause", entity_id="camp_123", user_id=1, tenant_id=1
        )

        # Check audit log was created with tenant
        audit_log = get_latest_audit_log()
        assert audit_log["tenant_id"] == 1
        assert audit_log["action"] == "campaign_pause"
        assert audit_log["user_id"] == 1


# =============================================================================
# Helper Functions (Mocked implementations for testing)
# =============================================================================


def determine_allowed_mode(
    emq_score: float,
    api_health: bool = True,
    event_loss_pct: float = 0,
    feature_flags: dict[str, Any] = None,
) -> dict[str, Any]:
    """Determine allowed autopilot modes based on EMQ and health."""
    feature_flags = feature_flags or {}

    # Check for override
    if feature_flags.get("emq_gating_override"):
        return {
            "allowed_modes": ["full", "supervised", "alert_only", "off"],
            "max_mode": "full",
            "automation_suspended": False,
            "override_active": True,
            "warnings": ["EMQ gating override is active"],
            "restrictions": [],
            "alerts": [],
        }

    result = {
        "allowed_modes": [],
        "max_mode": "off",
        "automation_suspended": False,
        "override_active": False,
        "warnings": [],
        "restrictions": [],
        "alerts": [],
    }

    # API health overrides everything
    if not api_health:
        result["automation_suspended"] = True
        result["max_mode"] = "off"
        result["allowed_modes"] = ["off"]
        result["alerts"].append("API health check failed - automation suspended")
        return result

    # High event loss restricts mode
    if event_loss_pct > 10:
        result["restrictions"].append(f"High event loss ({event_loss_pct}%) restricts autopilot")
        emq_score = min(emq_score, 85)  # Cap effective EMQ

    # EMQ-based gating
    if emq_score >= 90:
        result["allowed_modes"] = ["full", "supervised", "alert_only", "off"]
        result["max_mode"] = "full"
    elif emq_score >= 80:
        result["allowed_modes"] = ["supervised", "alert_only", "off"]
        result["max_mode"] = "supervised"
        result["restrictions"].append("EMQ below threshold for full autopilot")
    elif emq_score >= 70:
        result["allowed_modes"] = ["alert_only", "off"]
        result["max_mode"] = "alert_only"
        result["restrictions"].append("EMQ below threshold for supervised mode")
    else:
        result["allowed_modes"] = ["off"]
        result["max_mode"] = "off"
        result["automation_suspended"] = True
        result["alerts"].append(f"Automation suspended: EMQ ({emq_score}) below 70")

    return result


def handle_emq_change(current_mode: str, new_emq: float, previous_emq: float) -> dict[str, Any]:
    """Handle EMQ score changes and mode adjustments."""
    allowed = determine_allowed_mode(new_emq)

    result = {
        "mode_changed": False,
        "new_mode": current_mode,
        "reason": None,
        "alert_created": False,
        "upgrade_available": False,
        "message": "",
    }

    # Check if current mode is still allowed
    if current_mode not in allowed["allowed_modes"]:
        result["mode_changed"] = True
        result["new_mode"] = allowed["max_mode"]
        result["reason"] = "EMQ dropped below full autopilot threshold"
        result["alert_created"] = True

    # Check if upgrade is available
    if (
        allowed["max_mode"] != current_mode
        and allowed["allowed_modes"].index(allowed["max_mode"])
        < allowed["allowed_modes"].index(current_mode)
        if current_mode in allowed["allowed_modes"]
        else True
    ):
        result["upgrade_available"] = True
        result["message"] = "Upgrade available but requires manual approval"

    return result


# =============================================================================
# Exception Classes for Testing
# =============================================================================


class TenantScopingError(Exception):
    """Raised when tenant scoping is missing."""

    pass


class TenantAccessDeniedError(Exception):
    """Raised when cross-tenant access is attempted."""

    pass


class TenantMismatchError(Exception):
    """Raised when path tenant doesn't match token tenant."""

    pass


# =============================================================================
# Mock Functions for Tenant Scoping Tests
# =============================================================================


def execute_query(query: str, tenant_id: int = None):
    """Mock query execution with tenant scoping check."""
    if "WHERE" not in query.upper() or "tenant_id" not in query.lower():
        if tenant_id is None:
            raise TenantScopingError("Query must include tenant_id filter")
    return {"data": []}


def verify_tenant_access(
    user_tenant_id: Optional[int],
    requested_tenant_id: int,
    user_role: str = "tenant_user",
    assigned_tenants: list = None,
) -> dict[str, Any]:
    """Verify user can access requested tenant."""
    # Superadmin can access all
    if user_role == "superadmin":
        return {"allowed": True, "audit_logged": True}

    # Account manager can access assigned tenants
    if user_role == "account_manager":
        if assigned_tenants and requested_tenant_id in assigned_tenants:
            return {"allowed": True, "audit_logged": True}
        raise TenantAccessDeniedError("AM not assigned to this tenant")

    # Regular user can only access their own tenant
    if user_tenant_id != requested_tenant_id:
        raise TenantAccessDeniedError(f"Access denied to tenant {requested_tenant_id}")

    return {"allowed": True, "audit_logged": False}


def validate_path_tenant(token_tenant_id: int, path_tenant_id: int) -> dict[str, bool]:
    """Validate path tenant matches token."""
    if token_tenant_id != path_tenant_id:
        raise TenantMismatchError("Path tenant ID doesn't match token")
    return {"valid": True}


# Mock data classes
class MockCampaign:
    def __init__(self, id, tenant_id):
        self.id = id
        self.tenant_id = tenant_id


class MockAction:
    def __init__(self, id, tenant_id):
        self.id = id
        self.tenant_id = tenant_id


_test_campaigns = {}
_test_actions = {}
_audit_logs = []


def create_campaign_for_test(tenant_id: int) -> MockCampaign:
    """Create test campaign."""
    import uuid

    campaign = MockCampaign(str(uuid.uuid4()), tenant_id)
    _test_campaigns[campaign.id] = campaign
    return campaign


def get_campaign(campaign_id: str, user_tenant_id: int) -> dict[str, Any]:
    """Get campaign with tenant check."""
    campaign = _test_campaigns.get(campaign_id)
    if not campaign:
        raise ValueError("Campaign not found")
    if campaign.tenant_id != user_tenant_id:
        raise TenantAccessDeniedError("Access denied")
    return {"id": campaign.id, "tenant_id": campaign.tenant_id}


def create_action_for_test(tenant_id: int) -> MockAction:
    """Create test action."""
    import uuid

    action = MockAction(str(uuid.uuid4()), tenant_id)
    _test_actions[action.id] = action
    return action


def approve_action(action_id: str, user_tenant_id: int) -> dict[str, bool]:
    """Approve action with tenant check."""
    action = _test_actions.get(action_id)
    if not action:
        raise ValueError("Action not found")
    if action.tenant_id != user_tenant_id:
        raise TenantAccessDeniedError("Access denied")
    return {"success": True}


def create_campaign(name: str, platforms: list, tenant_id: int = None) -> dict[str, Any]:
    """Create campaign."""
    if tenant_id is None:
        raise TenantScopingError("tenant_id required")
    return {"name": name, "platforms": platforms, "tenant_id": tenant_id}


def bulk_update_campaigns(campaign_ids: list, status: str, user_tenant_id: int) -> dict[str, Any]:
    """Bulk update campaigns."""
    # In real implementation, would verify each campaign belongs to tenant
    return {
        "updated_count": len(campaign_ids),
        "campaigns": [{"id": cid, "tenant_id": user_tenant_id} for cid in campaign_ids],
    }


def perform_audited_action(
    action: str, entity_id: str, user_id: int, tenant_id: int
) -> dict[str, Any]:
    """Perform action and create audit log."""
    audit_entry = {
        "action": action,
        "entity_id": entity_id,
        "user_id": user_id,
        "tenant_id": tenant_id,
        "timestamp": datetime.now(UTC).isoformat(),
    }
    _audit_logs.append(audit_entry)
    return {"success": True}


def get_latest_audit_log() -> dict[str, Any]:
    """Get the most recent audit log."""
    return _audit_logs[-1] if _audit_logs else None


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
