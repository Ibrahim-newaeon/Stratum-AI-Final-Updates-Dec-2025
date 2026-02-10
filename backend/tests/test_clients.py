# =============================================================================
# Stratum AI - Client Entity Tests
# =============================================================================
"""
Tests for Client entity, assignments, portal, permissions, and scope enforcement.
40+ test cases covering CRUD, RBAC, scope, assignments, and portal.

Note: These are unit tests that test the logic without a real database.
Integration tests requiring DB fixtures belong in tests/integration/.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.auth.permissions import (
    RBAC_MATRIX,
    ROLE_HIERARCHY,
    ROLE_PERMISSIONS,
    SIDEBAR_VISIBILITY,
    Permission,
    PermLevel,
    can_manage_role,
    get_accessible_client_ids,
    get_permission_level,
    get_resource_scope,
    get_user_permissions,
    has_all_permissions,
    has_any_permission,
    has_permission,
)
from app.models import UserRole
from app.models.client import (
    Client,
    ClientAssignment,
    ClientRequest,
    ClientRequestStatus,
    ClientRequestType,
)
from app.schemas.client import (
    ClientAssignmentCreate,
    ClientCreate,
    ClientListResponse,
    ClientPortalInvite,
    ClientResponse,
    ClientSummaryResponse,
    ClientUpdate,
)


# =============================================================================
# RBAC Matrix Tests
# =============================================================================


class TestRBACMatrix:
    """Test RBAC matrix correctness."""

    def test_rbac_matrix_has_all_roles(self):
        """Every resource in RBAC_MATRIX should have entries for all 5 roles."""
        for resource, role_map in RBAC_MATRIX.items():
            for role in UserRole:
                assert role in role_map, f"Missing {role} in {resource}"

    def test_superadmin_has_full_on_all_resources(self):
        """SUPERADMIN should have FULL on every resource."""
        for resource, role_map in RBAC_MATRIX.items():
            assert role_map[UserRole.SUPERADMIN] == PermLevel.FULL, (
                f"SUPERADMIN should have FULL on {resource}"
            )

    def test_viewer_has_no_write_on_tenants(self):
        """VIEWER should have NONE on tenant settings."""
        assert get_permission_level(UserRole.VIEWER, "tenants.settings") == PermLevel.NONE

    def test_viewer_can_view_campaigns(self):
        """VIEWER should have VIEW on campaigns."""
        assert get_permission_level(UserRole.VIEWER, "campaigns") == PermLevel.VIEW

    def test_viewer_cannot_delete_campaigns(self):
        """VIEWER should have NONE on campaigns.delete."""
        assert get_permission_level(UserRole.VIEWER, "campaigns.delete") == PermLevel.NONE

    def test_admin_has_full_on_clients(self):
        """ADMIN should have FULL on clients."""
        assert get_permission_level(UserRole.ADMIN, "clients") == PermLevel.FULL

    def test_manager_can_edit_clients(self):
        """MANAGER should have EDIT on clients."""
        assert get_permission_level(UserRole.MANAGER, "clients") == PermLevel.EDIT

    def test_analyst_can_view_clients(self):
        """ANALYST should have VIEW on clients."""
        assert get_permission_level(UserRole.ANALYST, "clients") == PermLevel.VIEW

    def test_viewer_can_view_clients(self):
        """VIEWER should have VIEW on clients."""
        assert get_permission_level(UserRole.VIEWER, "clients") == PermLevel.VIEW

    def test_manager_can_edit_campaigns(self):
        """MANAGER should have EDIT on campaigns."""
        assert get_permission_level(UserRole.MANAGER, "campaigns") == PermLevel.EDIT

    def test_analyst_can_edit_campaigns(self):
        """ANALYST (media_buyer) should have EDIT on campaigns."""
        assert get_permission_level(UserRole.ANALYST, "campaigns") == PermLevel.EDIT

    def test_unknown_resource_returns_none(self):
        """Unknown resource should return NONE."""
        assert get_permission_level(UserRole.ADMIN, "nonexistent.resource") == PermLevel.NONE

    def test_viewer_cannot_manage_portal_users(self):
        """VIEWER should not be able to manage portal users."""
        assert get_permission_level(UserRole.VIEWER, "clients.portal_users") == PermLevel.NONE

    def test_manager_can_edit_portal_users(self):
        """MANAGER should have EDIT on clients.portal_users."""
        assert get_permission_level(UserRole.MANAGER, "clients.portal_users") == PermLevel.EDIT


# =============================================================================
# Role Hierarchy Tests
# =============================================================================


class TestRoleHierarchy:
    """Test role hierarchy configuration."""

    def test_superadmin_highest(self):
        """SUPERADMIN should have the highest hierarchy value."""
        assert ROLE_HIERARCHY[UserRole.SUPERADMIN] == 100

    def test_viewer_lowest(self):
        """VIEWER should have the lowest hierarchy value."""
        assert ROLE_HIERARCHY[UserRole.VIEWER] == 10

    def test_hierarchy_ordering(self):
        """Roles should be ordered correctly."""
        assert (
            ROLE_HIERARCHY[UserRole.SUPERADMIN]
            > ROLE_HIERARCHY[UserRole.ADMIN]
            > ROLE_HIERARCHY[UserRole.MANAGER]
            > ROLE_HIERARCHY[UserRole.ANALYST]
            > ROLE_HIERARCHY[UserRole.VIEWER]
        )

    def test_all_roles_in_hierarchy(self):
        """All UserRole values should be in the hierarchy."""
        for role in UserRole:
            assert role in ROLE_HIERARCHY


# =============================================================================
# Scope Tests
# =============================================================================


class TestResourceScope:
    """Test scope label assignment per role."""

    def test_superadmin_global_scope(self):
        """SUPERADMIN should have global scope."""
        assert get_resource_scope(UserRole.SUPERADMIN) == "global"

    def test_admin_tenant_scope(self):
        """ADMIN should have tenant scope."""
        assert get_resource_scope(UserRole.ADMIN) == "tenant"

    def test_manager_assigned_scope(self):
        """MANAGER should have assigned scope."""
        assert get_resource_scope(UserRole.MANAGER) == "assigned"

    def test_analyst_assigned_scope(self):
        """ANALYST should have assigned scope."""
        assert get_resource_scope(UserRole.ANALYST) == "assigned"

    def test_viewer_own_client_scope(self):
        """VIEWER should have own_client scope."""
        assert get_resource_scope(UserRole.VIEWER) == "own_client"


# =============================================================================
# Role Management Tests (Privilege Escalation Prevention)
# =============================================================================


class TestCanManageRole:
    """Test privilege escalation prevention."""

    def test_superadmin_can_assign_any_role(self):
        """SUPERADMIN should be able to assign any role."""
        for role in UserRole:
            assert can_manage_role(UserRole.SUPERADMIN, role) is True

    def test_admin_can_assign_manager(self):
        """ADMIN should be able to assign MANAGER."""
        assert can_manage_role(UserRole.ADMIN, UserRole.MANAGER) is True

    def test_admin_can_assign_analyst(self):
        """ADMIN should be able to assign ANALYST."""
        assert can_manage_role(UserRole.ADMIN, UserRole.ANALYST) is True

    def test_admin_can_assign_viewer(self):
        """ADMIN should be able to assign VIEWER."""
        assert can_manage_role(UserRole.ADMIN, UserRole.VIEWER) is True

    def test_admin_cannot_assign_admin(self):
        """ADMIN should NOT be able to assign ADMIN (privilege escalation)."""
        assert can_manage_role(UserRole.ADMIN, UserRole.ADMIN) is False

    def test_admin_cannot_assign_superadmin(self):
        """ADMIN should NOT be able to assign SUPERADMIN (privilege escalation)."""
        assert can_manage_role(UserRole.ADMIN, UserRole.SUPERADMIN) is False

    def test_manager_cannot_assign_any_role(self):
        """MANAGER should NOT be able to assign any role."""
        for role in UserRole:
            assert can_manage_role(UserRole.MANAGER, role) is False

    def test_analyst_cannot_assign_any_role(self):
        """ANALYST should NOT be able to assign any role."""
        for role in UserRole:
            assert can_manage_role(UserRole.ANALYST, role) is False

    def test_viewer_cannot_assign_any_role(self):
        """VIEWER should NOT be able to assign any role."""
        for role in UserRole:
            assert can_manage_role(UserRole.VIEWER, role) is False


# =============================================================================
# Sidebar Visibility Tests
# =============================================================================


class TestSidebarVisibility:
    """Test sidebar menu items per role."""

    def test_all_roles_have_sidebar(self):
        """Every role should have sidebar visibility defined."""
        for role in UserRole:
            assert role in SIDEBAR_VISIBILITY

    def test_viewer_sees_limited_items(self):
        """VIEWER should see a limited set of sidebar items."""
        items = SIDEBAR_VISIBILITY[UserRole.VIEWER]
        assert "dashboard" in items
        assert "campaigns" in items
        assert "analytics" in items
        assert "profile" in items
        assert "users" not in items
        assert "settings" not in items
        assert "tenants" not in items

    def test_superadmin_sees_all_items(self):
        """SUPERADMIN should see the most items."""
        items = SIDEBAR_VISIBILITY[UserRole.SUPERADMIN]
        assert "tenants" in items
        assert "users" in items
        assert "settings" in items
        assert "audit" in items

    def test_manager_does_not_see_tenants(self):
        """MANAGER should not see tenant management."""
        items = SIDEBAR_VISIBILITY[UserRole.MANAGER]
        assert "tenants" not in items

    def test_admin_sees_clients(self):
        """ADMIN should see clients in sidebar."""
        items = SIDEBAR_VISIBILITY[UserRole.ADMIN]
        assert "clients" in items


# =============================================================================
# Legacy Permissions Tests
# =============================================================================


class TestLegacyPermissions:
    """Test backwards-compatible Permission enum system."""

    def test_superadmin_has_all_permissions(self):
        """SUPERADMIN should have all Permission enum values."""
        perms = get_user_permissions("superadmin")
        assert len(perms) == len(Permission)

    def test_viewer_has_client_read(self):
        """VIEWER should have CLIENT_READ permission."""
        assert has_permission("viewer", Permission.CLIENT_READ)

    def test_viewer_does_not_have_client_write(self):
        """VIEWER should NOT have CLIENT_WRITE permission."""
        assert not has_permission("viewer", Permission.CLIENT_WRITE)

    def test_admin_has_client_portal(self):
        """ADMIN should have CLIENT_PORTAL permission."""
        assert has_permission("admin", Permission.CLIENT_PORTAL)

    def test_has_any_permission(self):
        """has_any_permission should return True if any permission matches."""
        assert has_any_permission(
            "viewer", [Permission.CAMPAIGN_READ, Permission.SYSTEM_ADMIN]
        )

    def test_has_all_permissions_fail(self):
        """has_all_permissions should fail if any is missing."""
        assert not has_all_permissions(
            "viewer", [Permission.CAMPAIGN_READ, Permission.SYSTEM_ADMIN]
        )

    def test_unknown_role_returns_empty(self):
        """Unknown role should return empty permissions."""
        assert get_user_permissions("nonexistent") == set()


# =============================================================================
# Schema Validation Tests
# =============================================================================


class TestClientSchemas:
    """Test Pydantic schema validation for Client entity."""

    def test_create_valid_client(self):
        """Valid ClientCreate should pass."""
        data = ClientCreate(
            name="Midas Furniture",
            slug="midas-furniture",
            industry="Retail",
            currency="USD",
        )
        assert data.name == "Midas Furniture"
        assert data.slug == "midas-furniture"

    def test_create_client_slug_validation(self):
        """Slug must be lowercase alphanumeric with dashes."""
        with pytest.raises(Exception):
            ClientCreate(name="Test", slug="Invalid Slug!")

    def test_create_client_slug_too_short(self):
        """Slug must be at least 2 characters."""
        with pytest.raises(Exception):
            ClientCreate(name="Test", slug="a")

    def test_create_client_name_required(self):
        """Name is required."""
        with pytest.raises(Exception):
            ClientCreate(slug="test-slug")

    def test_update_all_optional(self):
        """ClientUpdate should accept no fields (all optional)."""
        data = ClientUpdate()
        dump = data.model_dump(exclude_unset=True)
        assert dump == {}

    def test_update_partial_fields(self):
        """ClientUpdate should accept partial fields."""
        data = ClientUpdate(name="New Name", is_active=False)
        dump = data.model_dump(exclude_unset=True)
        assert dump == {"name": "New Name", "is_active": False}

    def test_assignment_create(self):
        """ClientAssignmentCreate should validate correctly."""
        data = ClientAssignmentCreate(user_id=5, is_primary=True)
        assert data.user_id == 5
        assert data.is_primary is True

    def test_portal_invite_valid(self):
        """Valid ClientPortalInvite should pass."""
        data = ClientPortalInvite(
            email="client@example.com",
            full_name="Client User",
            client_id=1,
        )
        assert data.email == "client@example.com"
        assert data.client_id == 1

    def test_portal_invite_invalid_email(self):
        """Invalid email should fail validation."""
        with pytest.raises(Exception):
            ClientPortalInvite(
                email="not-an-email",
                full_name="Client User",
                client_id=1,
            )

    def test_client_response_computed_fields(self):
        """ClientResponse should accept computed fields."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        data = ClientResponse(
            id=1,
            tenant_id=1,
            name="Test",
            slug="test",
            currency="USD",
            timezone="UTC",
            budget_alert_threshold=0.9,
            is_active=True,
            created_at=now,
            updated_at=now,
            total_campaigns=5,
            total_spend_cents=100000,
            assigned_users=[1, 2, 3],
        )
        assert data.total_campaigns == 5
        assert data.assigned_users == [1, 2, 3]

    def test_client_summary_response(self):
        """ClientSummaryResponse should compute correctly."""
        data = ClientSummaryResponse(
            client_id=1,
            client_name="Test",
            total_campaigns=10,
            active_campaigns=7,
            total_spend_cents=500000,
            total_revenue_cents=1500000,
            avg_roas=3.0,
        )
        assert data.avg_roas == 3.0
        assert data.active_campaigns == 7


# =============================================================================
# Model Tests (unit tests, no DB)
# =============================================================================


class TestClientModels:
    """Test model instantiation and enums."""

    def test_client_request_status_values(self):
        """ClientRequestStatus should have all expected values."""
        assert ClientRequestStatus.PENDING.value == "pending"
        assert ClientRequestStatus.APPROVED.value == "approved"
        assert ClientRequestStatus.REJECTED.value == "rejected"
        assert ClientRequestStatus.EXECUTED.value == "executed"
        assert ClientRequestStatus.CANCELLED.value == "cancelled"

    def test_client_request_type_values(self):
        """ClientRequestType should have all expected values."""
        assert ClientRequestType.PAUSE_CAMPAIGN.value == "pause_campaign"
        assert ClientRequestType.ADJUST_BUDGET.value == "adjust_budget"
        assert ClientRequestType.NEW_CAMPAIGN.value == "new_campaign"
        assert ClientRequestType.OTHER.value == "other"

    def test_client_request_status_count(self):
        """There should be 5 request status values."""
        assert len(ClientRequestStatus) == 5

    def test_client_request_type_count(self):
        """There should be 6 request type values."""
        assert len(ClientRequestType) == 6


# =============================================================================
# Permission Level Tests
# =============================================================================


class TestPermLevelComparisons:
    """Test PermLevel integer comparisons."""

    def test_full_greater_than_edit(self):
        """FULL > EDIT."""
        assert PermLevel.FULL > PermLevel.EDIT

    def test_edit_greater_than_view(self):
        """EDIT > VIEW."""
        assert PermLevel.EDIT > PermLevel.VIEW

    def test_view_greater_than_none(self):
        """VIEW > NONE."""
        assert PermLevel.VIEW > PermLevel.NONE

    def test_none_is_zero(self):
        """NONE should be 0."""
        assert PermLevel.NONE == 0

    def test_full_is_three(self):
        """FULL should be 3."""
        assert PermLevel.FULL == 3


# =============================================================================
# Parametrized Permission Checks
# =============================================================================


@pytest.mark.parametrize(
    "role,resource,expected_min",
    [
        (UserRole.SUPERADMIN, "campaigns", PermLevel.FULL),
        (UserRole.ADMIN, "campaigns", PermLevel.FULL),
        (UserRole.MANAGER, "campaigns", PermLevel.EDIT),
        (UserRole.ANALYST, "campaigns", PermLevel.EDIT),
        (UserRole.VIEWER, "campaigns", PermLevel.VIEW),
        (UserRole.SUPERADMIN, "clients", PermLevel.FULL),
        (UserRole.ADMIN, "clients", PermLevel.FULL),
        (UserRole.MANAGER, "clients", PermLevel.EDIT),
        (UserRole.ANALYST, "clients", PermLevel.VIEW),
        (UserRole.VIEWER, "clients", PermLevel.VIEW),
        (UserRole.VIEWER, "tenants.settings", PermLevel.NONE),
        (UserRole.VIEWER, "users.manage", PermLevel.NONE),
        (UserRole.MANAGER, "reports", PermLevel.FULL),
        (UserRole.ANALYST, "reports", PermLevel.EDIT),
        (UserRole.VIEWER, "reports.download", PermLevel.FULL),
    ],
)
def test_permission_check_all_roles(role, resource, expected_min):
    """Parametrized test: check permission levels for various role/resource combos."""
    level = get_permission_level(role, resource)
    assert level >= expected_min, (
        f"{role.value} should have at least {expected_min.name} on {resource}, got {level.name}"
    )


# =============================================================================
# Async Scope Enforcement Tests
# =============================================================================


class TestGetAccessibleClientIds:
    """Test get_accessible_client_ids with mocked DB sessions."""

    @pytest.mark.asyncio
    async def test_superadmin_returns_none(self):
        """SUPERADMIN should get None (unrestricted access)."""
        db = AsyncMock()
        result = await get_accessible_client_ids(
            user_id=1, user_role=UserRole.SUPERADMIN, tenant_id=1, db=db
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_admin_returns_none(self):
        """ADMIN should get None (unrestricted within tenant)."""
        db = AsyncMock()
        result = await get_accessible_client_ids(
            user_id=1, user_role=UserRole.ADMIN, tenant_id=1, db=db
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_viewer_with_client_id_returns_list(self):
        """VIEWER with explicit client_id should get [client_id]."""
        db = AsyncMock()
        result = await get_accessible_client_ids(
            user_id=1, user_role=UserRole.VIEWER, tenant_id=1, db=db, client_id=42
        )
        assert result == [42]

    @pytest.mark.asyncio
    async def test_viewer_without_client_id_queries_db(self):
        """VIEWER without client_id should query User.client_id from DB."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = 99
        db = AsyncMock()
        db.execute.return_value = mock_result

        result = await get_accessible_client_ids(
            user_id=1, user_role=UserRole.VIEWER, tenant_id=1, db=db
        )
        assert result == [99]
        db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_viewer_no_client_returns_empty(self):
        """VIEWER with no client_id in DB should get empty list."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db = AsyncMock()
        db.execute.return_value = mock_result

        result = await get_accessible_client_ids(
            user_id=1, user_role=UserRole.VIEWER, tenant_id=1, db=db
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_manager_queries_assignments(self):
        """MANAGER should query client_assignments table."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [10, 20, 30]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        db = AsyncMock()
        db.execute.return_value = mock_result

        result = await get_accessible_client_ids(
            user_id=5, user_role=UserRole.MANAGER, tenant_id=1, db=db
        )
        assert result == [10, 20, 30]
        db.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyst_queries_assignments(self):
        """ANALYST should also query client_assignments table."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [7]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        db = AsyncMock()
        db.execute.return_value = mock_result

        result = await get_accessible_client_ids(
            user_id=5, user_role=UserRole.ANALYST, tenant_id=1, db=db
        )
        assert result == [7]


class TestEnforceClientAccess:
    """Test enforce_client_access raises 403 when unauthorized."""

    @pytest.mark.asyncio
    async def test_admin_passes_without_check(self):
        """ADMIN should pass — get_accessible_client_ids returns None."""
        from app.auth.permissions import enforce_client_access

        db = AsyncMock()
        # Should not raise
        await enforce_client_access(
            user_id=1, user_role=UserRole.ADMIN, client_id=999,
            tenant_id=1, db=db
        )

    @pytest.mark.asyncio
    async def test_viewer_allowed_own_client(self):
        """VIEWER accessing their own client should pass."""
        from app.auth.permissions import enforce_client_access

        db = AsyncMock()
        await enforce_client_access(
            user_id=1, user_role=UserRole.VIEWER, client_id=42,
            tenant_id=1, db=db, user_client_id=42
        )

    @pytest.mark.asyncio
    async def test_viewer_blocked_other_client(self):
        """VIEWER accessing another client should get 403."""
        from app.auth.permissions import enforce_client_access
        from fastapi import HTTPException

        db = AsyncMock()
        with pytest.raises(HTTPException) as exc_info:
            await enforce_client_access(
                user_id=1, user_role=UserRole.VIEWER, client_id=999,
                tenant_id=1, db=db, user_client_id=42
            )
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_manager_allowed_assigned_client(self):
        """MANAGER accessing an assigned client should pass."""
        from app.auth.permissions import enforce_client_access

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [10, 20]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        db = AsyncMock()
        db.execute.return_value = mock_result

        await enforce_client_access(
            user_id=5, user_role=UserRole.MANAGER, client_id=10,
            tenant_id=1, db=db
        )

    @pytest.mark.asyncio
    async def test_manager_blocked_unassigned_client(self):
        """MANAGER accessing an unassigned client should get 403."""
        from app.auth.permissions import enforce_client_access
        from fastapi import HTTPException

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [10, 20]
        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        db = AsyncMock()
        db.execute.return_value = mock_result

        with pytest.raises(HTTPException) as exc_info:
            await enforce_client_access(
                user_id=5, user_role=UserRole.MANAGER, client_id=999,
                tenant_id=1, db=db
            )
        assert exc_info.value.status_code == 403
