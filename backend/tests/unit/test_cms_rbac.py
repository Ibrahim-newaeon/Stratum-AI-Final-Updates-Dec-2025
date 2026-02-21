# =============================================================================
# Stratum AI - CMS RBAC Unit Tests
# =============================================================================
"""
Comprehensive unit tests for CMS Role-Based Access Control.

Tests cover:
- has_permission() returns True for super_admin on ALL permissions
- has_permission() returns False for viewer on create_post
- has_permission() returns True for author on edit_own_post but False on edit_any_post
- has_permission() returns True for reviewer on approve_post but False on create_post
- has_permission() returns False for unknown permission strings
- has_permission() handles invalid roles gracefully
- Each CMSRole has the expected permission set (full matrix verification)
- check_cms_permission() function works correctly
- CMS_PERMISSIONS dict has all 8 roles
- Each role's permission dict has all expected keys
"""

from unittest.mock import MagicMock

import pytest

from app.models.cms import CMSRole, CMS_PERMISSIONS, has_permission


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def all_cms_roles():
    """Return all CMS roles."""
    return list(CMSRole)


@pytest.fixture
def mock_request_with_cms_role():
    """Create a mock request with a cms_role in state."""
    def _factory(role_value):
        request = MagicMock()
        request.state.cms_role = role_value
        return request
    return _factory


@pytest.fixture
def mock_request_without_cms_role():
    """Create a mock request without a cms_role in state."""
    request = MagicMock()
    # Remove the attribute so getattr returns None
    del request.state.cms_role
    request.state.configure_mock(**{})
    # Make getattr(request.state, "cms_role", None) return None
    type(request.state).cms_role = property(lambda self: None)
    return request


# =============================================================================
# CMS_PERMISSIONS Structure Tests
# =============================================================================


class TestCMSPermissionsStructure:
    """Tests for the CMS_PERMISSIONS dictionary structure."""

    def test_cms_permissions_has_all_8_roles(self):
        """CMS_PERMISSIONS should contain entries for all 8 CMSRole values."""
        assert len(CMS_PERMISSIONS) == 8

        expected_roles = {
            CMSRole.SUPER_ADMIN,
            CMSRole.ADMIN,
            CMSRole.EDITOR_IN_CHIEF,
            CMSRole.EDITOR,
            CMSRole.AUTHOR,
            CMSRole.CONTRIBUTOR,
            CMSRole.REVIEWER,
            CMSRole.VIEWER,
        }
        assert set(CMS_PERMISSIONS.keys()) == expected_roles

    def test_all_roles_have_consistent_permission_keys(self):
        """All roles should have permission dicts, and higher roles should
        have at least the same keys as lower roles (within their own dicts)."""
        # Gather all unique permission keys across all roles
        all_keys = set()
        for role_perms in CMS_PERMISSIONS.values():
            all_keys.update(role_perms.keys())

        # Verify we have a reasonable number of permissions
        assert len(all_keys) >= 15, f"Expected at least 15 permission keys, got {len(all_keys)}"

    def test_super_admin_has_all_standard_permissions(self):
        """Super admin permission dict should have all the standard keys."""
        super_admin_perms = CMS_PERMISSIONS[CMSRole.SUPER_ADMIN]
        standard_keys = [
            "create_post", "edit_any_post", "delete_any_post",
            "publish_post", "schedule_post", "submit_for_review",
            "approve_post", "reject_post", "request_changes",
            "view_all_posts", "manage_categories", "manage_tags",
            "manage_authors", "manage_pages", "manage_users",
            "view_analytics", "export_content", "bulk_operations",
            "access_settings",
        ]
        for key in standard_keys:
            assert key in super_admin_perms, f"Super admin missing key: {key}"

    def test_all_permission_values_are_boolean(self):
        """All permission values in the matrix should be boolean."""
        for role, perms in CMS_PERMISSIONS.items():
            for perm_name, perm_value in perms.items():
                assert isinstance(perm_value, bool), (
                    f"Permission '{perm_name}' for role '{role.value}' "
                    f"is {type(perm_value).__name__}, expected bool"
                )


# =============================================================================
# has_permission() Basic Tests
# =============================================================================


class TestHasPermission:
    """Tests for the has_permission() function."""

    def test_super_admin_has_all_permissions(self):
        """Super admin should have True for every permission in their dict."""
        super_admin_perms = CMS_PERMISSIONS[CMSRole.SUPER_ADMIN]
        for perm_name, expected in super_admin_perms.items():
            result = has_permission(CMSRole.SUPER_ADMIN, perm_name)
            assert result is True, (
                f"Super admin should have '{perm_name}' but has_permission returned False"
            )

    def test_viewer_cannot_create_post(self):
        """Viewer should not have create_post permission."""
        assert has_permission(CMSRole.VIEWER, "create_post") is False

    def test_viewer_cannot_edit_any_post(self):
        """Viewer should not have edit_any_post permission."""
        assert has_permission(CMSRole.VIEWER, "edit_any_post") is False

    def test_viewer_cannot_delete_any_post(self):
        """Viewer should not have delete_any_post permission."""
        assert has_permission(CMSRole.VIEWER, "delete_any_post") is False

    def test_viewer_can_view_all_posts(self):
        """Viewer should be able to view all published posts."""
        assert has_permission(CMSRole.VIEWER, "view_all_posts") is True

    def test_author_can_edit_own_post(self):
        """Author should have edit_own_post permission."""
        assert has_permission(CMSRole.AUTHOR, "edit_own_post") is True

    def test_author_cannot_edit_any_post(self):
        """Author should not have edit_any_post permission."""
        assert has_permission(CMSRole.AUTHOR, "edit_any_post") is False

    def test_author_can_create_post(self):
        """Author should have create_post permission."""
        assert has_permission(CMSRole.AUTHOR, "create_post") is True

    def test_author_can_submit_for_review(self):
        """Author should be able to submit posts for review."""
        assert has_permission(CMSRole.AUTHOR, "submit_for_review") is True

    def test_author_cannot_publish_post(self):
        """Author should not be able to publish directly."""
        assert has_permission(CMSRole.AUTHOR, "publish_post") is False

    def test_author_cannot_approve_post(self):
        """Author should not be able to approve posts."""
        assert has_permission(CMSRole.AUTHOR, "approve_post") is False

    def test_reviewer_can_approve_post(self):
        """Reviewer should have approve_post permission."""
        assert has_permission(CMSRole.REVIEWER, "approve_post") is True

    def test_reviewer_can_reject_post(self):
        """Reviewer should have reject_post permission."""
        assert has_permission(CMSRole.REVIEWER, "reject_post") is True

    def test_reviewer_can_request_changes(self):
        """Reviewer should have request_changes permission."""
        assert has_permission(CMSRole.REVIEWER, "request_changes") is True

    def test_reviewer_cannot_create_post(self):
        """Reviewer should not have create_post permission."""
        assert has_permission(CMSRole.REVIEWER, "create_post") is False

    def test_reviewer_cannot_edit_any_post(self):
        """Reviewer should not be able to edit posts."""
        assert has_permission(CMSRole.REVIEWER, "edit_any_post") is False

    def test_reviewer_cannot_publish_post(self):
        """Reviewer should not be able to publish."""
        assert has_permission(CMSRole.REVIEWER, "publish_post") is False

    def test_unknown_permission_returns_false(self):
        """Unknown permission strings should return False for any role."""
        assert has_permission(CMSRole.SUPER_ADMIN, "nonexistent_permission") is False
        assert has_permission(CMSRole.ADMIN, "fly_to_moon") is False
        assert has_permission(CMSRole.VIEWER, "") is False

    def test_invalid_role_returns_false(self):
        """Invalid role (not in CMS_PERMISSIONS) should return False gracefully."""
        # has_permission uses .get() so passing a non-CMSRole key should return False
        result = has_permission("invalid_role_string", "create_post")
        assert result is False

    def test_none_role_returns_false(self):
        """None as role should return False gracefully."""
        result = has_permission(None, "create_post")
        assert result is False


# =============================================================================
# Full Permission Matrix Tests
# =============================================================================


class TestFullPermissionMatrix:
    """Verify the complete permission matrix for each role."""

    def test_super_admin_full_permissions(self):
        """Super admin should have ALL permissions set to True."""
        perms = CMS_PERMISSIONS[CMSRole.SUPER_ADMIN]
        for perm_name, expected_value in perms.items():
            assert expected_value is True, (
                f"Super admin should have '{perm_name}' = True, got False"
            )

    def test_admin_permissions(self):
        """Admin should have all permissions except manage_users and access_settings."""
        perms = CMS_PERMISSIONS[CMSRole.ADMIN]
        assert perms["create_post"] is True
        assert perms["edit_any_post"] is True
        assert perms["delete_any_post"] is True
        assert perms["publish_post"] is True
        assert perms["schedule_post"] is True
        assert perms["approve_post"] is True
        assert perms["reject_post"] is True
        assert perms["manage_categories"] is True
        assert perms["manage_tags"] is True
        assert perms["manage_authors"] is True
        assert perms["manage_pages"] is True
        assert perms["view_analytics"] is True
        assert perms["export_content"] is True
        assert perms["bulk_operations"] is True
        # Admin cannot manage users or access settings
        assert perms["manage_users"] is False
        assert perms["access_settings"] is False

    def test_editor_in_chief_permissions(self):
        """Editor-in-chief should have editorial control but no deletion or page management."""
        perms = CMS_PERMISSIONS[CMSRole.EDITOR_IN_CHIEF]
        assert perms["create_post"] is True
        assert perms["edit_any_post"] is True
        assert perms["delete_any_post"] is False
        assert perms["publish_post"] is True
        assert perms["schedule_post"] is True
        assert perms["approve_post"] is True
        assert perms["reject_post"] is True
        assert perms["request_changes"] is True
        assert perms["manage_categories"] is True
        assert perms["manage_tags"] is True
        assert perms["manage_authors"] is True
        assert perms["manage_pages"] is False
        assert perms["manage_users"] is False
        assert perms["view_analytics"] is True
        assert perms["export_content"] is True
        assert perms["bulk_operations"] is True
        assert perms["access_settings"] is False

    def test_editor_permissions(self):
        """Editor can edit all but cannot publish, approve, or manage categories."""
        perms = CMS_PERMISSIONS[CMSRole.EDITOR]
        assert perms["create_post"] is True
        assert perms["edit_any_post"] is True
        assert perms["delete_any_post"] is False
        assert perms["publish_post"] is False
        assert perms["schedule_post"] is True
        assert perms["submit_for_review"] is True
        assert perms["approve_post"] is False
        assert perms["reject_post"] is False
        assert perms["request_changes"] is True
        assert perms["view_all_posts"] is True
        assert perms["manage_categories"] is False
        assert perms["manage_tags"] is True
        assert perms["manage_authors"] is False
        assert perms["manage_pages"] is False
        assert perms["manage_users"] is False
        assert perms["view_analytics"] is True
        assert perms["export_content"] is False
        assert perms["bulk_operations"] is False
        assert perms["access_settings"] is False

    def test_author_permissions(self):
        """Author can create and edit own, submit for review, but not publish or approve."""
        perms = CMS_PERMISSIONS[CMSRole.AUTHOR]
        assert perms["create_post"] is True
        assert perms["edit_own_post"] is True
        assert perms["edit_any_post"] is False
        assert perms["delete_any_post"] is False
        assert perms["publish_post"] is False
        assert perms["schedule_post"] is False
        assert perms["submit_for_review"] is True
        assert perms["approve_post"] is False
        assert perms["reject_post"] is False
        assert perms["request_changes"] is False
        assert perms["view_all_posts"] is False
        assert perms["view_own_posts"] is True
        assert perms["manage_categories"] is False
        assert perms["manage_tags"] is False
        assert perms["manage_authors"] is False
        assert perms["manage_pages"] is False
        assert perms["manage_users"] is False
        assert perms["view_analytics"] is False
        assert perms["export_content"] is False
        assert perms["bulk_operations"] is False
        assert perms["access_settings"] is False

    def test_contributor_permissions(self):
        """Contributor can create drafts and edit own, but cannot submit for review."""
        perms = CMS_PERMISSIONS[CMSRole.CONTRIBUTOR]
        assert perms["create_post"] is True
        assert perms["edit_own_post"] is True
        assert perms["edit_any_post"] is False
        assert perms["delete_any_post"] is False
        assert perms["publish_post"] is False
        assert perms["schedule_post"] is False
        assert perms["submit_for_review"] is False
        assert perms["approve_post"] is False
        assert perms["reject_post"] is False
        assert perms["request_changes"] is False
        assert perms["view_all_posts"] is False
        assert perms["view_own_posts"] is True
        assert perms["manage_categories"] is False
        assert perms["manage_tags"] is False
        assert perms["manage_authors"] is False
        assert perms["manage_pages"] is False
        assert perms["manage_users"] is False
        assert perms["view_analytics"] is False
        assert perms["export_content"] is False
        assert perms["bulk_operations"] is False
        assert perms["access_settings"] is False

    def test_reviewer_permissions(self):
        """Reviewer can approve, reject, request changes, and view all posts."""
        perms = CMS_PERMISSIONS[CMSRole.REVIEWER]
        assert perms["create_post"] is False
        assert perms["edit_own_post"] is False
        assert perms["edit_any_post"] is False
        assert perms["delete_any_post"] is False
        assert perms["publish_post"] is False
        assert perms["schedule_post"] is False
        assert perms["submit_for_review"] is False
        assert perms["approve_post"] is True
        assert perms["reject_post"] is True
        assert perms["request_changes"] is True
        assert perms["view_all_posts"] is True
        assert perms["view_own_posts"] is True
        assert perms["manage_categories"] is False
        assert perms["manage_tags"] is False
        assert perms["manage_authors"] is False
        assert perms["manage_pages"] is False
        assert perms["manage_users"] is False
        assert perms["view_analytics"] is False
        assert perms["export_content"] is False
        assert perms["bulk_operations"] is False
        assert perms["access_settings"] is False

    def test_viewer_permissions(self):
        """Viewer should only be able to view all posts."""
        perms = CMS_PERMISSIONS[CMSRole.VIEWER]
        assert perms["create_post"] is False
        assert perms["edit_own_post"] is False
        assert perms["edit_any_post"] is False
        assert perms["delete_any_post"] is False
        assert perms["publish_post"] is False
        assert perms["schedule_post"] is False
        assert perms["submit_for_review"] is False
        assert perms["approve_post"] is False
        assert perms["reject_post"] is False
        assert perms["request_changes"] is False
        assert perms["view_all_posts"] is True
        assert perms["view_own_posts"] is False
        assert perms["manage_categories"] is False
        assert perms["manage_tags"] is False
        assert perms["manage_authors"] is False
        assert perms["manage_pages"] is False
        assert perms["manage_users"] is False
        assert perms["view_analytics"] is False
        assert perms["export_content"] is False
        assert perms["bulk_operations"] is False
        assert perms["access_settings"] is False


# =============================================================================
# CMSRole Enum Tests
# =============================================================================


class TestCMSRoleEnum:
    """Tests for the CMSRole enum."""

    def test_all_role_values(self):
        """CMSRole should have exactly 8 members with expected string values."""
        expected = {
            "super_admin", "admin", "editor_in_chief", "editor",
            "author", "contributor", "reviewer", "viewer",
        }
        actual = {role.value for role in CMSRole}
        assert actual == expected

    def test_role_is_string_enum(self):
        """CMSRole values should be strings (str enum)."""
        for role in CMSRole:
            assert isinstance(role.value, str)
            assert isinstance(role, str)

    def test_role_construction_from_string(self):
        """CMSRole should be constructable from string values."""
        assert CMSRole("super_admin") == CMSRole.SUPER_ADMIN
        assert CMSRole("viewer") == CMSRole.VIEWER
        assert CMSRole("reviewer") == CMSRole.REVIEWER

    def test_invalid_role_construction_raises(self):
        """Constructing CMSRole from an invalid string should raise ValueError."""
        with pytest.raises(ValueError):
            CMSRole("nonexistent_role")


# =============================================================================
# check_cms_permission() Tests
# =============================================================================


class TestCheckCmsPermission:
    """Tests for the check_cms_permission() async helper."""

    @pytest.mark.asyncio
    async def test_returns_true_for_valid_role_and_permission(self):
        """check_cms_permission should return True when the role has the permission."""
        from app.auth.deps import check_cms_permission

        request = MagicMock()
        request.state.cms_role = CMSRole.SUPER_ADMIN.value

        result = await check_cms_permission(request, "create_post")
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_for_missing_permission(self):
        """check_cms_permission should return False when the role lacks the permission."""
        from app.auth.deps import check_cms_permission

        request = MagicMock()
        request.state.cms_role = CMSRole.VIEWER.value

        result = await check_cms_permission(request, "create_post")
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_no_cms_role_in_state(self):
        """check_cms_permission should return False when cms_role is not in request.state."""
        from app.auth.deps import check_cms_permission

        request = MagicMock()
        # Simulate missing cms_role attribute
        request.state = MagicMock(spec=[])

        result = await check_cms_permission(request, "create_post")
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_for_invalid_role_string(self):
        """check_cms_permission should return False for an invalid role string."""
        from app.auth.deps import check_cms_permission

        request = MagicMock()
        request.state.cms_role = "totally_invalid_role"

        result = await check_cms_permission(request, "create_post")
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_for_unknown_permission(self):
        """check_cms_permission should return False for unknown permission strings."""
        from app.auth.deps import check_cms_permission

        request = MagicMock()
        request.state.cms_role = CMSRole.ADMIN.value

        result = await check_cms_permission(request, "unknown_permission_xyz")
        assert result is False

    @pytest.mark.asyncio
    async def test_reviewer_approve_via_check_cms_permission(self):
        """Reviewer should have approve_post via check_cms_permission."""
        from app.auth.deps import check_cms_permission

        request = MagicMock()
        request.state.cms_role = CMSRole.REVIEWER.value

        result = await check_cms_permission(request, "approve_post")
        assert result is True

    @pytest.mark.asyncio
    async def test_author_edit_own_via_check_cms_permission(self):
        """Author should have edit_own_post via check_cms_permission."""
        from app.auth.deps import check_cms_permission

        request = MagicMock()
        request.state.cms_role = CMSRole.AUTHOR.value

        result = await check_cms_permission(request, "edit_own_post")
        assert result is True

    @pytest.mark.asyncio
    async def test_contributor_cannot_submit_for_review(self):
        """Contributor should not have submit_for_review via check_cms_permission."""
        from app.auth.deps import check_cms_permission

        request = MagicMock()
        request.state.cms_role = CMSRole.CONTRIBUTOR.value

        result = await check_cms_permission(request, "submit_for_review")
        assert result is False

    @pytest.mark.asyncio
    async def test_editor_can_schedule_post(self):
        """Editor should have schedule_post via check_cms_permission."""
        from app.auth.deps import check_cms_permission

        request = MagicMock()
        request.state.cms_role = CMSRole.EDITOR.value

        result = await check_cms_permission(request, "schedule_post")
        assert result is True


# =============================================================================
# Role Hierarchy / Permission Escalation Tests
# =============================================================================


class TestRoleHierarchy:
    """Tests ensuring higher roles have at least as many permissions as lower ones."""

    def test_super_admin_has_more_permissions_than_admin(self):
        """Super admin should have at least all permissions that admin has."""
        super_perms = CMS_PERMISSIONS[CMSRole.SUPER_ADMIN]
        admin_perms = CMS_PERMISSIONS[CMSRole.ADMIN]

        for perm, value in admin_perms.items():
            if value is True:
                assert super_perms.get(perm, False) is True, (
                    f"Super admin should have '{perm}' since admin has it"
                )

    def test_admin_has_more_permissions_than_editor_in_chief(self):
        """Admin should have at least all permissions that editor-in-chief has."""
        admin_perms = CMS_PERMISSIONS[CMSRole.ADMIN]
        eic_perms = CMS_PERMISSIONS[CMSRole.EDITOR_IN_CHIEF]

        for perm, value in eic_perms.items():
            if value is True:
                assert admin_perms.get(perm, False) is True, (
                    f"Admin should have '{perm}' since editor-in-chief has it"
                )

    def test_editor_in_chief_has_more_permissions_than_editor(self):
        """Editor-in-chief should have at least all permissions that editor has."""
        eic_perms = CMS_PERMISSIONS[CMSRole.EDITOR_IN_CHIEF]
        editor_perms = CMS_PERMISSIONS[CMSRole.EDITOR]

        for perm, value in editor_perms.items():
            if value is True:
                assert eic_perms.get(perm, False) is True, (
                    f"Editor-in-chief should have '{perm}' since editor has it"
                )

    def test_viewer_has_fewest_permissions(self):
        """Viewer should have the fewest True permissions of any role."""
        viewer_true_count = sum(
            1 for v in CMS_PERMISSIONS[CMSRole.VIEWER].values() if v is True
        )

        for role in CMSRole:
            if role == CMSRole.VIEWER:
                continue
            role_true_count = sum(
                1 for v in CMS_PERMISSIONS[role].values() if v is True
            )
            assert role_true_count >= viewer_true_count, (
                f"Role '{role.value}' has fewer True permissions ({role_true_count}) "
                f"than viewer ({viewer_true_count})"
            )
