# =============================================================================
# Stratum AI - Action Approver Serialization Tests
# =============================================================================
"""
Tests for the accountability surface on the actions API: _approver_info /
action_to_response serialize which user accepted an autopilot action
(name + department). The approver relationship is only touched when
eager-loaded — a lazy load would raise under the async session — so the
guard behavior matters as much as the happy path.
"""

from datetime import date, datetime, timezone

import pytest

from app.api.v1.endpoints.autopilot import (
    ApproverInfo,
    _approver_info,
    action_to_response,
)
from app.base_models import User, UserRole
from app.core.security import encrypt_pii
from app.models.trust_layer import FactActionsQueue


def make_action(**overrides) -> FactActionsQueue:
    """Transient action instance with everything action_to_response reads."""
    action = FactActionsQueue(
        tenant_id=1,
        date=date(2026, 7, 5),
        action_type="budget_increase",
        entity_type="campaign",
        entity_id="cmp-1",
        entity_name="Summer Sale",
        platform="meta",
        action_json='{"budget": 500}',
        status="applied",
        created_at=datetime(2026, 7, 5, 12, 0, tzinfo=timezone.utc),
    )
    for key, value in overrides.items():
        setattr(action, key, value)
    return action


def make_approver(**overrides) -> User:
    defaults = dict(
        id=42,
        tenant_id=1,
        email=encrypt_pii("approver@stratum.ai"),
        email_hash="x" * 64,
        password_hash="hash",
        full_name=encrypt_pii("Sara Kim"),
        role=UserRole.MANAGER,
        department="Media Buying",
    )
    defaults.update(overrides)
    return User(**defaults)


class TestApproverInfo:
    def test_no_approver_id_returns_none(self):
        action = make_action(approved_by_user_id=None)
        assert _approver_info(action) is None

    def test_unloaded_relationship_returns_none(self):
        # approved_by_user_id set but the relationship was never loaded —
        # the guard must return None instead of triggering a lazy load.
        action = make_action(approved_by_user_id=42)
        assert _approver_info(action) is None

    def test_loaded_approver_serialized_with_decrypted_name(self):
        approver = make_approver()
        action = make_action(approved_by_user_id=42, approved_by=approver)

        info = _approver_info(action)

        assert info == ApproverInfo(id=42, name="Sara Kim", department="Media Buying")

    def test_approver_without_department(self):
        approver = make_approver(department=None)
        action = make_action(approved_by_user_id=42, approved_by=approver)

        info = _approver_info(action)

        assert info is not None
        assert info.department is None

    def test_approver_with_undecryptable_name_degrades_to_none_name(self):
        approver = make_approver(full_name="not-fernet-ciphertext")
        action = make_action(approved_by_user_id=42, approved_by=approver)

        info = _approver_info(action)

        assert info is not None
        assert info.name is None
        assert info.department == "Media Buying"

    def test_deleted_approver_row_returns_none(self):
        # FK is SET NULL on hard delete, but a race can leave the id set
        # while the relationship resolves to no row.
        action = make_action(approved_by_user_id=42, approved_by=None)
        assert _approver_info(action) is None

    def test_cross_tenant_approver_pii_is_not_exposed(self):
        # A superadmin from another tenant can approve via the X-Tenant-ID
        # override; their name/department must never be served to this
        # tenant. (Tenancy audit finding on PR #519.)
        approver = make_approver(tenant_id=999)
        action = make_action(approved_by_user_id=42, approved_by=approver)

        info = _approver_info(action)

        assert info == ApproverInfo(id=42, name="Platform staff", department=None)


class TestActionResponseApprover:
    def test_response_includes_approver(self):
        approver = make_approver()
        action = make_action(approved_by_user_id=42, approved_by=approver)

        response = action_to_response(action)

        assert response.approved_by is not None
        assert response.approved_by.name == "Sara Kim"
        assert response.approved_by.department == "Media Buying"

    def test_response_without_approver(self):
        action = make_action(approved_by_user_id=None)

        response = action_to_response(action)

        assert response.approved_by is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
