# =============================================================================
# Stratum AI - WebSocket Tenant Isolation Tests (TEN-001)
# =============================================================================
"""
Tests for deriving the WebSocket tenant from the verified token, not the
client-supplied query param.

The /ws endpoint used to let a client ?tenant_id= override the token claim
(`if not tenant_id: tenant_id = payload.get("tenant_id")`), so any authenticated
user could subscribe to another tenant's real-time stream. `_resolve_ws_tenant`
now pins non-superadmins to their token's tenant.
"""

from app.main import _resolve_ws_tenant


def test_non_superadmin_pinned_to_token_tenant_ignoring_param():
    # Attacker (tenant 7) tries to target victim tenant 42 via the query param.
    payload = {"sub": "9", "tenant_id": 7, "role": "admin"}
    assert _resolve_ws_tenant(payload, requested_tenant=42) == 7


def test_non_superadmin_no_param_uses_token_tenant():
    payload = {"sub": "9", "tenant_id": 7, "role": "member"}
    assert _resolve_ws_tenant(payload, requested_tenant=None) == 7


def test_missing_role_treated_as_non_superadmin():
    payload = {"sub": "9", "tenant_id": 7}
    assert _resolve_ws_tenant(payload, requested_tenant=42) == 7


def test_superadmin_may_target_another_tenant():
    payload = {"sub": "1", "tenant_id": 1, "role": "superadmin"}
    assert _resolve_ws_tenant(payload, requested_tenant=42) == 42


def test_superadmin_without_param_uses_own_tenant():
    payload = {"sub": "1", "tenant_id": 1, "role": "superadmin"}
    assert _resolve_ws_tenant(payload, requested_tenant=None) == 1
