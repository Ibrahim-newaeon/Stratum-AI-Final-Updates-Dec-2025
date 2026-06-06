# =============================================================================
# Stratum AI - Tenant Context Dependency Tests
# =============================================================================
"""
Regression tests for the shared tenant-context resolver (P0-2).

`require_tenant_id` replaces the unsafe `getattr(user, "tenant_id", None) or 1`
pattern that silently leaked tenant 1's data when a user carried no tenant
context. It must fail closed (HTTP 401), never default.
"""

import pytest
from fastapi import HTTPException

from app.auth.deps import require_tenant_id


class _User:
    """Minimal stand-in for CurrentUser with a settable tenant_id."""

    def __init__(self, tenant_id):
        self.tenant_id = tenant_id


def test_returns_tenant_id_when_present():
    assert require_tenant_id(_User(7)) == 7


@pytest.mark.parametrize("missing", [None, 0])
def test_fails_closed_on_missing_tenant(missing):
    """A null/zero tenant must raise 401 — not resolve to a default tenant."""
    with pytest.raises(HTTPException) as exc_info:
        require_tenant_id(_User(missing))
    assert exc_info.value.status_code == 401
    assert "Tenant context required" in exc_info.value.detail


def test_fails_closed_when_attribute_absent():
    """An object with no tenant_id attribute also fails closed."""
    with pytest.raises(HTTPException) as exc_info:
        require_tenant_id(object())
    assert exc_info.value.status_code == 401
