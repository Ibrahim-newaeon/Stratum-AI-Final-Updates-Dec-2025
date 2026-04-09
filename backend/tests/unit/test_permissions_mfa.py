# =============================================================================
# Stratum AI - RBAC Permissions & MFA Test Suite
# =============================================================================
"""
Comprehensive tests for the two untested Authentication sub-systems:

1. RBAC Permissions (app/auth/permissions.py)
   - Permission & PermLevel enums
   - Role-permission mappings (7 roles × 43 permissions)
   - Helper functions: get_user_permissions, has_permission, has_any/all_permissions
   - Role hierarchy & can_manage_role (privilege-escalation prevention)
   - RBAC matrix & get_permission_level
   - Resource scope per role
   - Sidebar visibility per role
   - FastAPI dependencies: require_permissions, require_role, require_super_admin
   - check_permission decorator, require_permission (PermLevel-based)
   - Client-scope helpers: enforce_client_access, get_accessible_client_ids

2. MFA / TOTP (app/services/mfa_service.py)
   - TOTP secret generation and URI provisioning
   - QR code generation
   - TOTP verification (valid, expired, malformed)
   - Backup code generation, hashing, and verification
   - MFAService class (get_mfa_status, initiate_setup, verify_and_enable,
     disable, verify_code with lockout, regenerate_backup_codes, _verify_code)
   - Convenience functions: check_mfa_required, is_user_locked
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pyotp
import pytest

from app.auth.permissions import (
    RBAC_MATRIX,
    ROLE_HIERARCHY,
    ROLE_PERMISSIONS,
    SIDEBAR_VISIBILITY,
    Permission,
    PermLevel,
    _PERM_LEVEL_ROLES,
    _ROLE_SCOPE,
    can_manage_role,
    check_permission,
    get_permission_level,
    get_resource_scope,
    get_user_permissions,
    has_all_permissions,
    has_any_permission,
    has_permission,
    require_permission,
    require_permissions,
    require_role,
    require_super_admin,
)
from app.base_models import UserRole
from app.services.mfa_service import (
    BACKUP_CODE_COUNT,
    BACKUP_CODE_LENGTH,
    LOCKOUT_DURATION_MINUTES,
    MAX_FAILED_ATTEMPTS,
    MFAService,
    MFAStatus,
    TOTP_DIGITS,
    TOTP_INTERVAL,
    TOTP_ISSUER,
    TOTPSetupData,
    check_mfa_required,
    generate_backup_codes,
    generate_qr_code,
    generate_totp_secret,
    get_totp_uri,
    hash_backup_code,
    is_user_locked,
    verify_backup_code,
    verify_totp,
)


# =============================================================================
# Helpers
# =============================================================================

ALL_ROLES = ["superadmin", "admin", "manager", "media_buyer", "analyst", "account_manager", "viewer"]
ALL_USER_ROLES = [UserRole.SUPERADMIN, UserRole.ADMIN, UserRole.MANAGER, UserRole.ANALYST, UserRole.VIEWER]


def _make_request(role: Optional[str] = None, user_id: Optional[int] = None) -> MagicMock:
    """Create a mock FastAPI Request with state."""
    req = MagicMock()
    req.state = SimpleNamespace()
    if role is not None:
        req.state.role = role
    if user_id is not None:
        req.state.user_id = user_id
    return req


def _make_db() -> AsyncMock:
    """Create a mock async DB session."""
    db = AsyncMock()
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    return db


def _make_scalar_result(value):
    """Create a mock DB result that returns a scalar."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _make_scalars_result(values):
    """Create a mock DB result that returns scalars."""
    result = MagicMock()
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = values
    result.scalars.return_value = scalars_mock
    return result


def _make_user(
    *,
    user_id: int = 1,
    totp_enabled: bool = False,
    totp_secret: Optional[str] = None,
    totp_verified_at: Optional[datetime] = None,
    backup_codes: Optional[dict] = None,
    failed_totp_attempts: int = 0,
    totp_lockout_until: Optional[datetime] = None,
):
    """Create a mock User model for MFA tests."""
    user = MagicMock()
    user.id = user_id
    user.totp_enabled = totp_enabled
    user.totp_secret = totp_secret
    user.totp_verified_at = totp_verified_at
    user.backup_codes = backup_codes
    user.failed_totp_attempts = failed_totp_attempts
    user.totp_lockout_until = totp_lockout_until
    return user


# #############################################################################
#
#  PART 1: RBAC PERMISSIONS
#
# #############################################################################


@pytest.mark.unit
class TestPermissionEnum:
    """Verify the Permission enum is correctly structured."""

    def test_permission_count(self) -> None:
        """All 42 granular permissions exist."""
        assert len(Permission) == 42

    def test_permission_values_are_colon_separated(self) -> None:
        """Every permission value follows resource:action naming."""
        for perm in Permission:
            assert ":" in perm.value, f"{perm.name} has no colon in value"

    def test_permission_is_string_enum(self) -> None:
        """Permissions are str enums usable as strings."""
        assert isinstance(Permission.TENANT_READ, str)
        assert Permission.TENANT_READ == "tenant:read"

    def test_all_resource_categories_present(self) -> None:
        """Expected resource categories exist."""
        prefixes = {p.value.split(":")[0] for p in Permission}
        expected = {"tenant", "user", "campaign", "analytics", "billing",
                    "system", "connector", "audit", "alert", "asset", "rule", "client"}
        assert prefixes == expected


@pytest.mark.unit
class TestPermLevelEnum:
    """Verify PermLevel integer enum."""

    def test_perm_level_ordering(self) -> None:
        assert PermLevel.NONE < PermLevel.VIEW < PermLevel.EDIT < PermLevel.FULL

    def test_perm_level_values(self) -> None:
        assert PermLevel.NONE == 0
        assert PermLevel.VIEW == 1
        assert PermLevel.EDIT == 2
        assert PermLevel.FULL == 3

    def test_perm_level_is_int(self) -> None:
        """PermLevel values are usable as ints."""
        assert isinstance(PermLevel.FULL, int)
        assert PermLevel.FULL + 1 == 4


# =============================================================================
# Role-Permission Mappings
# =============================================================================

@pytest.mark.unit
class TestRolePermissions:
    """Verify ROLE_PERMISSIONS mapping for all 7 roles."""

    def test_all_seven_roles_present(self) -> None:
        assert set(ROLE_PERMISSIONS.keys()) == set(ALL_ROLES)

    def test_superadmin_has_all_permissions(self) -> None:
        """Superadmin must have every single permission."""
        assert ROLE_PERMISSIONS["superadmin"] == set(Permission)

    def test_admin_lacks_system_permissions(self) -> None:
        """Admin should not have system:admin, system:write, system:read."""
        admin_perms = ROLE_PERMISSIONS["admin"]
        assert Permission.SYSTEM_ADMIN not in admin_perms
        assert Permission.SYSTEM_WRITE not in admin_perms
        assert Permission.SYSTEM_READ not in admin_perms

    def test_admin_lacks_tenant_delete(self) -> None:
        assert Permission.TENANT_DELETE not in ROLE_PERMISSIONS["admin"]

    def test_viewer_is_read_only(self) -> None:
        """Viewer should have no write/delete/manage permissions."""
        viewer_perms = ROLE_PERMISSIONS["viewer"]
        for perm in viewer_perms:
            action = perm.value.split(":")[1]
            assert action in {"read"}, f"Viewer has non-read perm: {perm.value}"

    def test_analyst_has_advanced_analytics(self) -> None:
        assert Permission.ANALYTICS_ADVANCED in ROLE_PERMISSIONS["analyst"]

    def test_media_buyer_has_campaign_budget(self) -> None:
        assert Permission.CAMPAIGN_BUDGET in ROLE_PERMISSIONS["media_buyer"]

    def test_media_buyer_lacks_user_management(self) -> None:
        mb = ROLE_PERMISSIONS["media_buyer"]
        assert Permission.USER_WRITE not in mb
        assert Permission.USER_DELETE not in mb
        assert Permission.USER_ROLE_ASSIGN not in mb

    def test_account_manager_has_billing_read(self) -> None:
        assert Permission.BILLING_READ in ROLE_PERMISSIONS["account_manager"]

    def test_account_manager_lacks_campaign_write(self) -> None:
        assert Permission.CAMPAIGN_WRITE not in ROLE_PERMISSIONS["account_manager"]

    def test_manager_has_rule_execute(self) -> None:
        assert Permission.RULE_EXECUTE in ROLE_PERMISSIONS["manager"]

    def test_each_role_is_subset_of_superadmin(self) -> None:
        """Every role's permissions are a subset of superadmin's."""
        sa = ROLE_PERMISSIONS["superadmin"]
        for role, perms in ROLE_PERMISSIONS.items():
            assert perms <= sa, f"{role} has permissions not in superadmin"


# =============================================================================
# Permission Helper Functions
# =============================================================================

@pytest.mark.unit
class TestGetUserPermissions:

    def test_returns_permissions_for_known_role(self) -> None:
        perms = get_user_permissions("admin")
        assert isinstance(perms, set)
        assert Permission.TENANT_READ in perms

    def test_case_insensitive(self) -> None:
        assert get_user_permissions("ADMIN") == get_user_permissions("admin")

    def test_unknown_role_returns_empty(self) -> None:
        assert get_user_permissions("unknown_role") == set()

    def test_empty_string_returns_empty(self) -> None:
        assert get_user_permissions("") == set()


@pytest.mark.unit
class TestHasPermission:

    def test_superadmin_has_every_permission(self) -> None:
        for perm in Permission:
            assert has_permission("superadmin", perm), f"superadmin missing {perm}"

    def test_viewer_lacks_write(self) -> None:
        assert has_permission("viewer", Permission.CAMPAIGN_WRITE) is False

    def test_viewer_has_read(self) -> None:
        assert has_permission("viewer", Permission.CAMPAIGN_READ) is True

    def test_unknown_role_always_false(self) -> None:
        assert has_permission("hacker", Permission.SYSTEM_ADMIN) is False


@pytest.mark.unit
class TestHasAnyPermission:

    def test_returns_true_when_one_matches(self) -> None:
        assert has_any_permission("viewer", [Permission.SYSTEM_ADMIN, Permission.CAMPAIGN_READ]) is True

    def test_returns_false_when_none_match(self) -> None:
        assert has_any_permission("viewer", [Permission.SYSTEM_ADMIN, Permission.CAMPAIGN_WRITE]) is False

    def test_empty_list_returns_false(self) -> None:
        assert has_any_permission("superadmin", []) is False


@pytest.mark.unit
class TestHasAllPermissions:

    def test_returns_true_when_all_match(self) -> None:
        assert has_all_permissions("superadmin", [Permission.SYSTEM_ADMIN, Permission.BILLING_MANAGE]) is True

    def test_returns_false_when_one_missing(self) -> None:
        assert has_all_permissions("viewer", [Permission.CAMPAIGN_READ, Permission.CAMPAIGN_WRITE]) is False

    def test_empty_list_returns_true(self) -> None:
        assert has_all_permissions("viewer", []) is True


# =============================================================================
# Role Hierarchy & can_manage_role
# =============================================================================

@pytest.mark.unit
class TestRoleHierarchy:

    def test_hierarchy_values(self) -> None:
        assert ROLE_HIERARCHY[UserRole.SUPERADMIN] == 100
        assert ROLE_HIERARCHY[UserRole.ADMIN] == 80
        assert ROLE_HIERARCHY[UserRole.MANAGER] == 60
        assert ROLE_HIERARCHY[UserRole.ANALYST] == 40
        assert ROLE_HIERARCHY[UserRole.VIEWER] == 10

    def test_superadmin_is_highest(self) -> None:
        for role, val in ROLE_HIERARCHY.items():
            assert ROLE_HIERARCHY[UserRole.SUPERADMIN] >= val


@pytest.mark.unit
class TestCanManageRole:

    def test_superadmin_can_manage_anyone(self) -> None:
        for target in ALL_USER_ROLES:
            assert can_manage_role(UserRole.SUPERADMIN, target) is True

    def test_admin_can_manage_lower_roles(self) -> None:
        assert can_manage_role(UserRole.ADMIN, UserRole.MANAGER) is True
        assert can_manage_role(UserRole.ADMIN, UserRole.ANALYST) is True
        assert can_manage_role(UserRole.ADMIN, UserRole.VIEWER) is True

    def test_admin_cannot_manage_superadmin(self) -> None:
        assert can_manage_role(UserRole.ADMIN, UserRole.SUPERADMIN) is False

    def test_admin_cannot_manage_self_level(self) -> None:
        assert can_manage_role(UserRole.ADMIN, UserRole.ADMIN) is False

    def test_non_admin_roles_cannot_manage(self) -> None:
        """Manager, analyst, viewer cannot manage any role."""
        for actor in [UserRole.MANAGER, UserRole.ANALYST, UserRole.VIEWER]:
            for target in ALL_USER_ROLES:
                assert can_manage_role(actor, target) is False


# =============================================================================
# RBAC Matrix & get_permission_level
# =============================================================================

@pytest.mark.unit
class TestRBACMatrix:

    def test_all_expected_resources_present(self) -> None:
        expected = {
            "campaigns", "campaigns.delete", "clients", "clients.portal_users",
            "analytics", "reports", "reports.download", "tenants.settings",
            "users.manage", "connectors", "billing", "audit",
        }
        assert set(RBAC_MATRIX.keys()) == expected

    def test_superadmin_is_full_everywhere(self) -> None:
        for resource, role_map in RBAC_MATRIX.items():
            assert role_map.get(UserRole.SUPERADMIN) == PermLevel.FULL, f"{resource}"

    def test_viewer_cannot_delete_campaigns(self) -> None:
        assert get_permission_level(UserRole.VIEWER, "campaigns.delete") == PermLevel.NONE

    def test_unknown_resource_returns_none(self) -> None:
        assert get_permission_level(UserRole.SUPERADMIN, "nonexistent") == PermLevel.NONE

    def test_unknown_role_returns_none(self) -> None:
        # Build a mock UserRole-like value that isn't in the matrix
        fake_role = MagicMock()
        assert get_permission_level(fake_role, "campaigns") == PermLevel.NONE

    def test_reports_download_available_to_all(self) -> None:
        for role in ALL_USER_ROLES:
            if role in RBAC_MATRIX["reports.download"]:
                assert RBAC_MATRIX["reports.download"][role] == PermLevel.FULL

    def test_audit_restricted_to_admins(self) -> None:
        assert get_permission_level(UserRole.MANAGER, "audit") == PermLevel.NONE
        assert get_permission_level(UserRole.ADMIN, "audit") == PermLevel.VIEW
        assert get_permission_level(UserRole.SUPERADMIN, "audit") == PermLevel.FULL


# =============================================================================
# Resource Scope
# =============================================================================

@pytest.mark.unit
class TestResourceScope:

    def test_superadmin_global(self) -> None:
        assert get_resource_scope(UserRole.SUPERADMIN) == "global"

    def test_admin_tenant(self) -> None:
        assert get_resource_scope(UserRole.ADMIN) == "tenant"

    def test_manager_assigned(self) -> None:
        assert get_resource_scope(UserRole.MANAGER) == "assigned"

    def test_analyst_assigned(self) -> None:
        assert get_resource_scope(UserRole.ANALYST) == "assigned"

    def test_viewer_own_client(self) -> None:
        assert get_resource_scope(UserRole.VIEWER) == "own_client"

    def test_unknown_role_returns_none_string(self) -> None:
        assert get_resource_scope(MagicMock()) == "none"


# =============================================================================
# Sidebar Visibility
# =============================================================================

@pytest.mark.unit
class TestSidebarVisibility:

    def test_all_user_roles_have_visibility(self) -> None:
        for role in ALL_USER_ROLES:
            assert role in SIDEBAR_VISIBILITY

    def test_superadmin_sees_everything(self) -> None:
        sa = SIDEBAR_VISIBILITY[UserRole.SUPERADMIN]
        assert "tenants" in sa
        assert "audit" in sa
        assert "billing" in sa
        assert "profile" in sa

    def test_viewer_minimal(self) -> None:
        v = SIDEBAR_VISIBILITY[UserRole.VIEWER]
        assert v == {"dashboard", "campaigns", "analytics", "profile"}

    def test_admin_no_tenants_tab(self) -> None:
        """Admin can manage their tenant but shouldn't see cross-tenant tab."""
        assert "tenants" not in SIDEBAR_VISIBILITY[UserRole.ADMIN]

    def test_analyst_no_clients(self) -> None:
        assert "clients" not in SIDEBAR_VISIBILITY[UserRole.ANALYST]

    def test_each_role_has_profile(self) -> None:
        for role in ALL_USER_ROLES:
            assert "profile" in SIDEBAR_VISIBILITY[role]

    def test_each_role_has_dashboard(self) -> None:
        for role in ALL_USER_ROLES:
            assert "dashboard" in SIDEBAR_VISIBILITY[role]


# =============================================================================
# FastAPI Dependencies
# =============================================================================

@pytest.mark.unit
class TestRequirePermissions:

    @pytest.mark.asyncio
    async def test_authorized_passes(self) -> None:
        checker = require_permissions([Permission.CAMPAIGN_READ])
        req = _make_request(role="admin", user_id=1)
        await checker(req)  # should not raise

    @pytest.mark.asyncio
    async def test_unauthorized_raises_403(self) -> None:
        from fastapi import HTTPException
        checker = require_permissions([Permission.SYSTEM_ADMIN])
        req = _make_request(role="viewer", user_id=1)
        with pytest.raises(HTTPException) as exc:
            await checker(req)
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_no_auth_raises_401(self) -> None:
        from fastapi import HTTPException
        checker = require_permissions([Permission.CAMPAIGN_READ])
        req = _make_request()  # no role/user_id
        with pytest.raises(HTTPException) as exc:
            await checker(req)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_require_all_false_any_match_passes(self) -> None:
        checker = require_permissions(
            [Permission.SYSTEM_ADMIN, Permission.CAMPAIGN_READ],
            require_all=False,
        )
        req = _make_request(role="viewer", user_id=1)
        await checker(req)  # viewer has CAMPAIGN_READ

    @pytest.mark.asyncio
    async def test_require_all_true_missing_one_fails(self) -> None:
        from fastapi import HTTPException
        checker = require_permissions(
            [Permission.CAMPAIGN_READ, Permission.CAMPAIGN_WRITE],
            require_all=True,
        )
        req = _make_request(role="viewer", user_id=1)
        with pytest.raises(HTTPException) as exc:
            await checker(req)
        assert exc.value.status_code == 403


@pytest.mark.unit
class TestRequireRole:

    @pytest.mark.asyncio
    async def test_allowed_role_passes(self) -> None:
        checker = require_role(["admin", "superadmin"])
        req = _make_request(role="admin", user_id=1)
        await checker(req)

    @pytest.mark.asyncio
    async def test_disallowed_role_raises_403(self) -> None:
        from fastapi import HTTPException
        checker = require_role(["admin", "superadmin"])
        req = _make_request(role="viewer", user_id=1)
        with pytest.raises(HTTPException) as exc:
            await checker(req)
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_no_auth_raises_401(self) -> None:
        from fastapi import HTTPException
        checker = require_role(["admin"])
        req = _make_request()
        with pytest.raises(HTTPException) as exc:
            await checker(req)
        assert exc.value.status_code == 401

    @pytest.mark.asyncio
    async def test_case_insensitive(self) -> None:
        checker = require_role(["Admin"])
        req = _make_request(role="ADMIN", user_id=1)
        await checker(req)


@pytest.mark.unit
class TestRequireSuperAdmin:

    @pytest.mark.asyncio
    async def test_superadmin_passes(self) -> None:
        req = _make_request(role="superadmin", user_id=1)
        await require_super_admin(req)

    @pytest.mark.asyncio
    async def test_admin_raises_403(self) -> None:
        from fastapi import HTTPException
        req = _make_request(role="admin", user_id=1)
        with pytest.raises(HTTPException) as exc:
            await require_super_admin(req)
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_no_auth_raises_401(self) -> None:
        from fastapi import HTTPException
        req = _make_request()
        with pytest.raises(HTTPException) as exc:
            await require_super_admin(req)
        assert exc.value.status_code == 401


# =============================================================================
# check_permission Decorator
# =============================================================================

@pytest.mark.unit
class TestCheckPermissionDecorator:

    @pytest.mark.asyncio
    async def test_authorized_call_succeeds(self) -> None:
        @check_permission(Permission.CAMPAIGN_WRITE)
        async def create_campaign(data, *, role):
            return "created"

        result = await create_campaign({}, role="admin")
        assert result == "created"

    @pytest.mark.asyncio
    async def test_unauthorized_raises_403(self) -> None:
        from fastapi import HTTPException

        @check_permission(Permission.SYSTEM_ADMIN)
        async def nuke(*, role):
            return "boom"

        with pytest.raises(HTTPException) as exc:
            await nuke(role="viewer")
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_missing_role_raises_value_error(self) -> None:
        @check_permission(Permission.CAMPAIGN_READ)
        async def read_camp():
            return "data"

        with pytest.raises(ValueError, match="Role argument required"):
            await read_camp()


# =============================================================================
# require_permission (PermLevel-based)
# =============================================================================

@pytest.mark.unit
class TestRequirePermissionPermLevel:

    @pytest.mark.asyncio
    async def test_allowed_role_passes(self) -> None:
        checker = require_permission("clients", PermLevel.VIEW)
        req = _make_request(role="admin", user_id=1)
        await checker(req)

    @pytest.mark.asyncio
    async def test_disallowed_role_raises_403(self) -> None:
        from fastapi import HTTPException
        # PermLevel.FULL requires superadmin or admin per _PERM_LEVEL_ROLES
        checker = require_permission("clients", PermLevel.FULL)
        req = _make_request(role="viewer", user_id=1)
        with pytest.raises(HTTPException) as exc:
            await checker(req)
        assert exc.value.status_code == 403

    @pytest.mark.asyncio
    async def test_no_auth_raises_401(self) -> None:
        from fastapi import HTTPException
        checker = require_permission("clients", PermLevel.VIEW)
        req = _make_request()
        with pytest.raises(HTTPException) as exc:
            await checker(req)
        assert exc.value.status_code == 401


# =============================================================================
# PermLevel Role Mapping
# =============================================================================

@pytest.mark.unit
class TestPermLevelRoles:

    def test_view_includes_all_six_roles(self) -> None:
        assert _PERM_LEVEL_ROLES[PermLevel.VIEW] == {
            "superadmin", "admin", "manager", "analyst", "account_manager", "viewer",
        }

    def test_edit_limited(self) -> None:
        assert _PERM_LEVEL_ROLES[PermLevel.EDIT] == {"superadmin", "admin", "manager"}

    def test_full_admin_only(self) -> None:
        assert _PERM_LEVEL_ROLES[PermLevel.FULL] == {"superadmin", "admin"}


# =============================================================================
# Client-Scope Access Helpers
# =============================================================================

@pytest.mark.unit
class TestEnforceClientAccess:

    @pytest.mark.asyncio
    async def test_superadmin_always_allowed(self) -> None:
        from app.auth.permissions import enforce_client_access
        db = _make_db()
        await enforce_client_access(
            user_id=1, user_role="superadmin", client_id=99,
            tenant_id=1, db=db,
        )
        # No exception means success

    @pytest.mark.asyncio
    async def test_admin_always_allowed(self) -> None:
        from app.auth.permissions import enforce_client_access
        db = _make_db()
        await enforce_client_access(
            user_id=1, user_role="admin", client_id=99,
            tenant_id=1, db=db,
        )

    @pytest.mark.asyncio
    async def test_user_with_matching_client_id_allowed(self) -> None:
        from app.auth.permissions import enforce_client_access
        db = _make_db()
        # user_client_id matches client_id -> allowed
        await enforce_client_access(
            user_id=1, user_role="viewer", client_id=42,
            tenant_id=1, db=db, user_client_id=42,
        )

    @pytest.mark.asyncio
    async def test_viewer_without_access_raises_403(self) -> None:
        from fastapi import HTTPException
        from app.auth.permissions import enforce_client_access
        db = _make_db()
        # get_accessible_client_ids will be called internally
        # For a viewer with no client_id, returns empty list
        db.execute.return_value = _make_scalar_result(None)
        with pytest.raises(HTTPException) as exc:
            await enforce_client_access(
                user_id=1, user_role="viewer", client_id=99,
                tenant_id=1, db=db,
            )
        assert exc.value.status_code == 403


@pytest.mark.unit
class TestGetAccessibleClientIds:

    @pytest.mark.asyncio
    async def test_superadmin_returns_none(self) -> None:
        from app.auth.permissions import get_accessible_client_ids
        db = _make_db()
        result = await get_accessible_client_ids(
            user_id=1, user_role="superadmin", tenant_id=1, db=db,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_admin_returns_none(self) -> None:
        from app.auth.permissions import get_accessible_client_ids
        db = _make_db()
        result = await get_accessible_client_ids(
            user_id=1, user_role="admin", tenant_id=1, db=db,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_viewer_with_client_id(self) -> None:
        from app.auth.permissions import get_accessible_client_ids
        db = _make_db()
        result = await get_accessible_client_ids(
            user_id=1, user_role="viewer", tenant_id=1, db=db, client_id=42,
        )
        assert result == [42]

    @pytest.mark.asyncio
    async def test_viewer_without_client_id_queries_db(self) -> None:
        from app.auth.permissions import get_accessible_client_ids
        db = _make_db()
        db.execute.return_value = _make_scalar_result(77)
        result = await get_accessible_client_ids(
            user_id=1, user_role="viewer", tenant_id=1, db=db,
        )
        assert result == [77]

    @pytest.mark.asyncio
    async def test_manager_queries_assignments(self) -> None:
        from app.auth.permissions import get_accessible_client_ids
        db = _make_db()
        db.execute.return_value = _make_scalars_result([10, 20, 30])
        result = await get_accessible_client_ids(
            user_id=1, user_role="manager", tenant_id=1, db=db,
        )
        assert result == [10, 20, 30]


# #############################################################################
#
#  PART 2: MFA / TOTP
#
# #############################################################################


@pytest.mark.unit
class TestMFAConstants:

    def test_totp_config(self) -> None:
        assert TOTP_DIGITS == 6
        assert TOTP_INTERVAL == 30
        assert TOTP_ISSUER == "Stratum AI"

    def test_rate_limiting_config(self) -> None:
        assert MAX_FAILED_ATTEMPTS == 5
        assert LOCKOUT_DURATION_MINUTES == 15

    def test_backup_code_config(self) -> None:
        assert BACKUP_CODE_COUNT == 10
        assert BACKUP_CODE_LENGTH == 8


# =============================================================================
# TOTP Functions
# =============================================================================

@pytest.mark.unit
class TestGenerateTOTPSecret:

    def test_returns_base32_string(self) -> None:
        secret = generate_totp_secret()
        assert isinstance(secret, str)
        assert len(secret) > 0

    def test_secrets_are_unique(self) -> None:
        secrets_set = {generate_totp_secret() for _ in range(20)}
        assert len(secrets_set) == 20

    def test_secret_is_valid_base32(self) -> None:
        import base64
        secret = generate_totp_secret()
        # Should decode without error
        base64.b32decode(secret)


@pytest.mark.unit
class TestGetTOTPUri:

    def test_contains_otpauth_scheme(self) -> None:
        secret = generate_totp_secret()
        uri = get_totp_uri(secret, "user@test.com")
        assert uri.startswith("otpauth://totp/")

    def test_contains_issuer(self) -> None:
        secret = generate_totp_secret()
        uri = get_totp_uri(secret, "user@test.com")
        assert "Stratum" in uri

    def test_contains_email(self) -> None:
        secret = generate_totp_secret()
        uri = get_totp_uri(secret, "alice@example.com")
        assert "alice" in uri

    def test_contains_secret_param(self) -> None:
        secret = generate_totp_secret()
        uri = get_totp_uri(secret, "user@test.com")
        assert f"secret={secret}" in uri


@pytest.mark.unit
class TestGenerateQRCode:

    def test_returns_base64_string(self) -> None:
        secret = generate_totp_secret()
        uri = get_totp_uri(secret, "user@test.com")
        qr = generate_qr_code(uri)
        assert isinstance(qr, str)
        assert len(qr) > 100  # Base64 PNG is substantial

    def test_is_valid_base64(self) -> None:
        import base64
        secret = generate_totp_secret()
        uri = get_totp_uri(secret, "user@test.com")
        qr = generate_qr_code(uri)
        decoded = base64.b64decode(qr)
        # PNG magic bytes
        assert decoded[:4] == b"\x89PNG"


@pytest.mark.unit
class TestVerifyTOTP:

    def test_valid_code_passes(self) -> None:
        secret = generate_totp_secret()
        totp = pyotp.TOTP(secret, digits=TOTP_DIGITS, interval=TOTP_INTERVAL)
        code = totp.now()
        assert verify_totp(secret, code) is True

    def test_wrong_code_fails(self) -> None:
        secret = generate_totp_secret()
        assert verify_totp(secret, "000000") is False

    def test_empty_secret_fails(self) -> None:
        assert verify_totp("", "123456") is False

    def test_empty_code_fails(self) -> None:
        secret = generate_totp_secret()
        assert verify_totp(secret, "") is False

    def test_non_digit_code_fails(self) -> None:
        secret = generate_totp_secret()
        assert verify_totp(secret, "abcdef") is False

    def test_wrong_length_code_fails(self) -> None:
        secret = generate_totp_secret()
        assert verify_totp(secret, "12345") is False    # 5 digits
        assert verify_totp(secret, "1234567") is False   # 7 digits

    def test_code_with_spaces_is_cleaned(self) -> None:
        secret = generate_totp_secret()
        totp = pyotp.TOTP(secret, digits=TOTP_DIGITS, interval=TOTP_INTERVAL)
        code = totp.now()
        spaced = f"{code[:3]} {code[3:]}"
        assert verify_totp(secret, spaced) is True


# =============================================================================
# Backup Codes
# =============================================================================

@pytest.mark.unit
class TestGenerateBackupCodes:

    def test_generates_correct_count(self) -> None:
        codes = generate_backup_codes()
        assert len(codes) == BACKUP_CODE_COUNT

    def test_codes_are_formatted(self) -> None:
        """Each code should be XXXX-XXXX format."""
        codes = generate_backup_codes()
        for code in codes:
            assert "-" in code
            parts = code.split("-")
            assert len(parts) == 2
            assert len(parts[0]) == 4
            assert len(parts[1]) == 4

    def test_codes_are_unique(self) -> None:
        codes = generate_backup_codes()
        assert len(set(codes)) == len(codes)

    def test_codes_are_hex_uppercase(self) -> None:
        codes = generate_backup_codes()
        for code in codes:
            clean = code.replace("-", "")
            assert clean == clean.upper()
            int(clean, 16)  # Should not raise if valid hex


@pytest.mark.unit
class TestHashBackupCode:

    def test_returns_sha256_hex(self) -> None:
        h = hash_backup_code("ABCD-1234")
        assert len(h) == 64  # SHA-256 hex digest
        int(h, 16)  # valid hex

    def test_deterministic(self) -> None:
        assert hash_backup_code("ABCD-1234") == hash_backup_code("ABCD-1234")

    def test_normalizes_dashes(self) -> None:
        assert hash_backup_code("ABCD-1234") == hash_backup_code("ABCD1234")

    def test_normalizes_case(self) -> None:
        assert hash_backup_code("abcd-1234") == hash_backup_code("ABCD-1234")


@pytest.mark.unit
class TestVerifyBackupCode:

    def test_valid_code_found(self) -> None:
        codes = generate_backup_codes()
        hashed = [hash_backup_code(c) for c in codes]
        is_valid, idx = verify_backup_code(codes[3], hashed)
        assert is_valid is True
        assert idx == 3

    def test_invalid_code_not_found(self) -> None:
        hashed = [hash_backup_code("AAAA-BBBB")]
        is_valid, idx = verify_backup_code("CCCC-DDDD", hashed)
        assert is_valid is False
        assert idx is None

    def test_empty_code_returns_false(self) -> None:
        assert verify_backup_code("", ["somehash"]) == (False, None)

    def test_empty_hashed_list_returns_false(self) -> None:
        assert verify_backup_code("AAAA-BBBB", []) == (False, None)

    def test_none_entries_skipped(self) -> None:
        """Used codes are set to None; they should be skipped."""
        codes = generate_backup_codes()
        hashed = [hash_backup_code(c) for c in codes]
        hashed[0] = None  # "used" code
        is_valid, idx = verify_backup_code(codes[0], hashed)
        assert is_valid is False

    def test_finds_correct_index_with_nones(self) -> None:
        codes = generate_backup_codes()
        hashed = [hash_backup_code(c) for c in codes]
        hashed[0] = None
        hashed[1] = None
        is_valid, idx = verify_backup_code(codes[2], hashed)
        assert is_valid is True
        assert idx == 2


# =============================================================================
# MFA Data Models
# =============================================================================

@pytest.mark.unit
class TestMFADataModels:

    def test_totp_setup_data(self) -> None:
        data = TOTPSetupData(secret="abc", provisioning_uri="otpauth://...", qr_code_base64="base64...")
        assert data.secret == "abc"
        assert data.provisioning_uri == "otpauth://..."

    def test_mfa_status(self) -> None:
        status = MFAStatus(
            enabled=True, verified_at=datetime.now(UTC),
            backup_codes_remaining=8, is_locked=False, lockout_until=None,
        )
        assert status.enabled is True
        assert status.backup_codes_remaining == 8


# =============================================================================
# MFAService Class
# =============================================================================

@pytest.mark.unit
class TestMFAServiceGetStatus:

    @pytest.mark.asyncio
    async def test_mfa_disabled_user(self) -> None:
        db = _make_db()
        user = _make_user(totp_enabled=False, backup_codes=None)
        db.execute.return_value = _make_scalar_result(user)

        svc = MFAService(db)
        status = await svc.get_mfa_status(1)

        assert status.enabled is False
        assert status.backup_codes_remaining == 0
        assert status.is_locked is False

    @pytest.mark.asyncio
    async def test_mfa_enabled_with_backup_codes(self) -> None:
        db = _make_db()
        codes = ["hash1", "hash2", None, "hash4"]  # 3 remaining
        user = _make_user(
            totp_enabled=True,
            totp_verified_at=datetime.now(UTC),
            backup_codes={"codes": codes},
        )
        db.execute.return_value = _make_scalar_result(user)

        svc = MFAService(db)
        status = await svc.get_mfa_status(1)

        assert status.enabled is True
        assert status.backup_codes_remaining == 3

    @pytest.mark.asyncio
    async def test_locked_user(self) -> None:
        db = _make_db()
        future = datetime.now(UTC) + timedelta(minutes=10)
        user = _make_user(totp_enabled=True, totp_lockout_until=future)
        db.execute.return_value = _make_scalar_result(user)

        svc = MFAService(db)
        status = await svc.get_mfa_status(1)

        assert status.is_locked is True
        assert status.lockout_until == future

    @pytest.mark.asyncio
    async def test_expired_lockout(self) -> None:
        db = _make_db()
        past = datetime.now(UTC) - timedelta(minutes=1)
        user = _make_user(totp_enabled=True, totp_lockout_until=past)
        db.execute.return_value = _make_scalar_result(user)

        svc = MFAService(db)
        status = await svc.get_mfa_status(1)

        assert status.is_locked is False
        assert status.lockout_until is None

    @pytest.mark.asyncio
    async def test_user_not_found_raises(self) -> None:
        db = _make_db()
        db.execute.return_value = _make_scalar_result(None)

        svc = MFAService(db)
        with pytest.raises(ValueError, match="User 999 not found"):
            await svc.get_mfa_status(999)


@pytest.mark.unit
class TestMFAServiceInitiateSetup:

    @pytest.mark.asyncio
    async def test_returns_setup_data(self) -> None:
        db = _make_db()
        svc = MFAService(db)

        with patch("app.services.mfa_service.encrypt_pii", return_value="encrypted"):
            result = await svc.initiate_setup(user_id=1, email="user@test.com")

        assert isinstance(result, TOTPSetupData)
        assert len(result.secret) > 0
        assert result.provisioning_uri.startswith("otpauth://")
        assert len(result.qr_code_base64) > 100
        db.commit.assert_awaited_once()


@pytest.mark.unit
class TestMFAServiceVerifyAndEnable:

    @pytest.mark.asyncio
    async def test_valid_code_enables_mfa(self) -> None:
        db = _make_db()
        secret = generate_totp_secret()
        totp = pyotp.TOTP(secret, digits=TOTP_DIGITS, interval=TOTP_INTERVAL)
        valid_code = totp.now()

        user = _make_user(totp_secret="encrypted_secret", totp_enabled=False)
        db.execute.return_value = _make_scalar_result(user)

        svc = MFAService(db)
        with patch("app.services.mfa_service.decrypt_pii", return_value=secret):
            success, backup_codes = await svc.verify_and_enable(1, valid_code)

        assert success is True
        assert len(backup_codes) == BACKUP_CODE_COUNT
        db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_invalid_code_returns_false(self) -> None:
        db = _make_db()
        secret = generate_totp_secret()
        user = _make_user(totp_secret="encrypted_secret", totp_enabled=False)
        db.execute.return_value = _make_scalar_result(user)

        svc = MFAService(db)
        with patch("app.services.mfa_service.decrypt_pii", return_value=secret):
            success, backup_codes = await svc.verify_and_enable(1, "000000")

        assert success is False
        assert backup_codes == []

    @pytest.mark.asyncio
    async def test_user_not_found_raises(self) -> None:
        db = _make_db()
        db.execute.return_value = _make_scalar_result(None)

        svc = MFAService(db)
        with pytest.raises(ValueError, match="not found"):
            await svc.verify_and_enable(1, "123456")

    @pytest.mark.asyncio
    async def test_no_secret_raises(self) -> None:
        db = _make_db()
        user = _make_user(totp_secret=None, totp_enabled=False)
        db.execute.return_value = _make_scalar_result(user)

        svc = MFAService(db)
        with pytest.raises(ValueError, match="not initiated"):
            await svc.verify_and_enable(1, "123456")

    @pytest.mark.asyncio
    async def test_already_enabled_raises(self) -> None:
        db = _make_db()
        user = _make_user(totp_secret="secret", totp_enabled=True)
        db.execute.return_value = _make_scalar_result(user)

        svc = MFAService(db)
        with pytest.raises(ValueError, match="already enabled"):
            await svc.verify_and_enable(1, "123456")


@pytest.mark.unit
class TestMFAServiceDisable:

    @pytest.mark.asyncio
    async def test_valid_code_disables(self) -> None:
        db = _make_db()
        secret = generate_totp_secret()
        totp = pyotp.TOTP(secret, digits=TOTP_DIGITS, interval=TOTP_INTERVAL)
        valid_code = totp.now()

        user = _make_user(totp_enabled=True, totp_secret="enc_secret")
        db.execute.return_value = _make_scalar_result(user)

        svc = MFAService(db)
        with patch("app.services.mfa_service.decrypt_pii", return_value=secret):
            result = await svc.disable(1, valid_code)

        assert result is True
        db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_invalid_code_returns_false(self) -> None:
        db = _make_db()
        secret = generate_totp_secret()
        user = _make_user(totp_enabled=True, totp_secret="enc_secret", backup_codes=None)
        db.execute.return_value = _make_scalar_result(user)

        svc = MFAService(db)
        with patch("app.services.mfa_service.decrypt_pii", return_value=secret):
            result = await svc.disable(1, "000000")

        assert result is False

    @pytest.mark.asyncio
    async def test_not_enabled_raises(self) -> None:
        db = _make_db()
        user = _make_user(totp_enabled=False)
        db.execute.return_value = _make_scalar_result(user)

        svc = MFAService(db)
        with pytest.raises(ValueError, match="not enabled"):
            await svc.disable(1, "123456")


@pytest.mark.unit
class TestMFAServiceVerifyCode:

    @pytest.mark.asyncio
    async def test_mfa_not_enabled_returns_true(self) -> None:
        db = _make_db()
        user = _make_user(totp_enabled=False)
        db.execute.return_value = _make_scalar_result(user)

        svc = MFAService(db)
        is_valid, msg = await svc.verify_code(1, "123456")
        assert is_valid is True
        assert msg == "MFA not enabled"

    @pytest.mark.asyncio
    async def test_locked_account_rejected(self) -> None:
        db = _make_db()
        future = datetime.now(UTC) + timedelta(minutes=10)
        user = _make_user(totp_enabled=True, totp_lockout_until=future)
        db.execute.return_value = _make_scalar_result(user)

        svc = MFAService(db)
        is_valid, msg = await svc.verify_code(1, "123456")
        assert is_valid is False
        assert "locked" in msg.lower()

    @pytest.mark.asyncio
    async def test_valid_totp_resets_attempts(self) -> None:
        db = _make_db()
        secret = generate_totp_secret()
        totp = pyotp.TOTP(secret, digits=TOTP_DIGITS, interval=TOTP_INTERVAL)
        valid_code = totp.now()

        user = _make_user(
            totp_enabled=True, totp_secret="enc",
            failed_totp_attempts=3,
        )
        db.execute.return_value = _make_scalar_result(user)

        svc = MFAService(db)
        with patch("app.services.mfa_service.decrypt_pii", return_value=secret):
            is_valid, msg = await svc.verify_code(1, valid_code)

        assert is_valid is True
        assert msg == "Code verified"
        db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_invalid_code_increments_attempts(self) -> None:
        db = _make_db()
        secret = generate_totp_secret()
        user = _make_user(
            totp_enabled=True, totp_secret="enc",
            failed_totp_attempts=2, backup_codes=None,
        )
        db.execute.return_value = _make_scalar_result(user)

        svc = MFAService(db)
        with patch("app.services.mfa_service.decrypt_pii", return_value=secret):
            is_valid, msg = await svc.verify_code(1, "000000")

        assert is_valid is False
        assert "2 attempts remaining" in msg
        db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_max_failures_triggers_lockout(self) -> None:
        db = _make_db()
        secret = generate_totp_secret()
        user = _make_user(
            totp_enabled=True, totp_secret="enc",
            failed_totp_attempts=MAX_FAILED_ATTEMPTS - 1,
            backup_codes=None,
        )
        db.execute.return_value = _make_scalar_result(user)

        svc = MFAService(db)
        with patch("app.services.mfa_service.decrypt_pii", return_value=secret):
            is_valid, msg = await svc.verify_code(1, "000000")

        assert is_valid is False
        assert "locked" in msg.lower()

    @pytest.mark.asyncio
    async def test_user_not_found(self) -> None:
        db = _make_db()
        db.execute.return_value = _make_scalar_result(None)

        svc = MFAService(db)
        is_valid, msg = await svc.verify_code(999, "123456")
        assert is_valid is False
        assert "not found" in msg.lower()


@pytest.mark.unit
class TestMFAServiceRegenerateBackupCodes:

    @pytest.mark.asyncio
    async def test_valid_totp_regenerates(self) -> None:
        db = _make_db()
        secret = generate_totp_secret()
        totp = pyotp.TOTP(secret, digits=TOTP_DIGITS, interval=TOTP_INTERVAL)
        valid_code = totp.now()

        user = _make_user(totp_enabled=True, totp_secret="enc")
        db.execute.return_value = _make_scalar_result(user)

        svc = MFAService(db)
        with patch("app.services.mfa_service.decrypt_pii", return_value=secret):
            success, codes = await svc.regenerate_backup_codes(1, valid_code)

        assert success is True
        assert len(codes) == BACKUP_CODE_COUNT
        db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_invalid_totp_fails(self) -> None:
        db = _make_db()
        secret = generate_totp_secret()
        user = _make_user(totp_enabled=True, totp_secret="enc")
        db.execute.return_value = _make_scalar_result(user)

        svc = MFAService(db)
        with patch("app.services.mfa_service.decrypt_pii", return_value=secret):
            success, codes = await svc.regenerate_backup_codes(1, "000000")

        assert success is False
        assert codes == []

    @pytest.mark.asyncio
    async def test_mfa_not_enabled_raises(self) -> None:
        db = _make_db()
        user = _make_user(totp_enabled=False)
        db.execute.return_value = _make_scalar_result(user)

        svc = MFAService(db)
        with pytest.raises(ValueError, match="not enabled"):
            await svc.regenerate_backup_codes(1, "123456")


@pytest.mark.unit
class TestMFAServiceInternalVerifyCode:

    @pytest.mark.asyncio
    async def test_totp_preferred_over_backup(self) -> None:
        """If TOTP matches, backup codes are not consumed."""
        db = _make_db()
        secret = generate_totp_secret()
        totp = pyotp.TOTP(secret, digits=TOTP_DIGITS, interval=TOTP_INTERVAL)
        valid_code = totp.now()

        codes = generate_backup_codes()
        hashed = [hash_backup_code(c) for c in codes]
        user = _make_user(
            totp_enabled=True, totp_secret="enc",
            backup_codes={"codes": hashed},
        )

        svc = MFAService(db)
        with patch("app.services.mfa_service.decrypt_pii", return_value=secret):
            result = await svc._verify_code(user, valid_code)

        assert result is True
        # DB should NOT have been called to update backup codes
        db.execute.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_backup_code_marks_used(self) -> None:
        db = _make_db()
        codes = generate_backup_codes()
        hashed = [hash_backup_code(c) for c in codes]

        # _verify_code uses type(user).id, so we need a real class with an `id` attr
        class FakeUser:
            id = 1
            totp_secret = "enc"
            backup_codes = {"codes": hashed.copy()}

        user = FakeUser()

        # Make TOTP fail so it falls through to backup
        # Patch sqlalchemy.update so type(user) doesn't fail
        svc = MFAService(db)
        mock_update = MagicMock()
        mock_update.return_value.where.return_value.values.return_value = "stmt"
        with (
            patch("app.services.mfa_service.decrypt_pii", return_value="invalid_secret"),
            patch("app.services.mfa_service.update", mock_update),
        ):
            result = await svc._verify_code(user, codes[5])

        assert result is True
        db.execute.assert_awaited()  # backup code update
        db.commit.assert_awaited()

    @pytest.mark.asyncio
    async def test_neither_totp_nor_backup_returns_false(self) -> None:
        db = _make_db()
        # No totp_secret -> TOTP branch skipped; no backup_codes -> backup branch skipped
        user = _make_user(totp_secret=None, backup_codes=None)

        svc = MFAService(db)
        result = await svc._verify_code(user, "000000")

        assert result is False


# =============================================================================
# Convenience Functions
# =============================================================================

@pytest.mark.unit
class TestCheckMFARequired:

    @pytest.mark.asyncio
    async def test_returns_true_when_enabled(self) -> None:
        db = _make_db()
        db.execute.return_value = _make_scalar_result(True)
        assert await check_mfa_required(db, 1) is True

    @pytest.mark.asyncio
    async def test_returns_false_when_disabled(self) -> None:
        db = _make_db()
        db.execute.return_value = _make_scalar_result(False)
        assert await check_mfa_required(db, 1) is False

    @pytest.mark.asyncio
    async def test_returns_false_when_user_not_found(self) -> None:
        db = _make_db()
        db.execute.return_value = _make_scalar_result(None)
        assert await check_mfa_required(db, 999) is False


@pytest.mark.unit
class TestIsUserLocked:

    @pytest.mark.asyncio
    async def test_locked_user(self) -> None:
        db = _make_db()
        future = datetime.now(UTC) + timedelta(minutes=10)
        db.execute.return_value = _make_scalar_result(future)
        locked, until = await is_user_locked(db, 1)
        assert locked is True
        assert until == future

    @pytest.mark.asyncio
    async def test_expired_lockout(self) -> None:
        db = _make_db()
        past = datetime.now(UTC) - timedelta(minutes=1)
        db.execute.return_value = _make_scalar_result(past)
        locked, until = await is_user_locked(db, 1)
        assert locked is False
        assert until is None

    @pytest.mark.asyncio
    async def test_no_lockout(self) -> None:
        db = _make_db()
        db.execute.return_value = _make_scalar_result(None)
        locked, until = await is_user_locked(db, 1)
        assert locked is False
        assert until is None
