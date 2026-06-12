# =============================================================================
# Stratum AI - Exceptions + Tenant Context unit tests
# =============================================================================
"""Unit tests for app.core.exceptions and app.tenancy.context.

Pure logic, no real I/O (Starlette Requests built from scopes). Covers
the AppException / StratumError hierarchies (status/error-code mapping,
to_dict serialization, the ERROR_CODES registry) and the TenantContext
RBAC properties + super-admin-bypass extraction guard.
"""

import pytest
from starlette.requests import Request

from app.core.exceptions import (
    ERROR_CODES,
    AppException,
    NotFoundError,
    SignalDegradedError,
    StratumError,
    TierLimitError,
    TokenExpiredError,
    TrustGateError,
    ValidationError,
)
from app.tenancy.context import (
    TenantContext,
    create_system_context,
    get_tenant_context,
)

pytestmark = pytest.mark.unit


# =============================================================================
# AppException hierarchy
# =============================================================================
class TestAppException:
    def test_defaults(self):
        exc = AppException()
        assert exc.status_code == 500
        assert exc.error_code == "INTERNAL_ERROR"
        assert exc.details == {}

    @pytest.mark.parametrize(
        "cls,status,code",
        [
            (NotFoundError, 404, "NOT_FOUND"),
            (ValidationError, 422, "VALIDATION_ERROR"),
        ],
    )
    def test_subclass_mapping(self, cls, status, code):
        exc = cls("boom")
        assert exc.status_code == status
        assert exc.error_code == code
        assert str(exc) == "boom"

    def test_to_dict_with_details(self):
        exc = NotFoundError("missing", details={"id": 7})
        assert exc.to_dict() == {
            "error": "NOT_FOUND",
            "message": "missing",
            "details": {"id": 7},
        }

    def test_to_dict_without_details_omits_key(self):
        assert "details" not in ValidationError("bad").to_dict()

    def test_overrides(self):
        exc = AppException("x", error_code="CUSTOM", status_code=418)
        assert exc.error_code == "CUSTOM"
        assert exc.status_code == 418

    def test_tier_limit_injects_required_tier(self):
        exc = TierLimitError(required_tier="enterprise")
        assert exc.status_code == 403
        assert exc.details["required_tier"] == "enterprise"


# =============================================================================
# StratumError hierarchy + registry
# =============================================================================
class TestStratumError:
    def test_default_detail_used(self):
        exc = TokenExpiredError()
        assert exc.error_code == "TOKEN_EXPIRED"
        assert exc.status_code == 401  # inherited from AuthenticationError
        assert "expired" in exc.detail.lower()

    def test_custom_detail_and_context(self):
        exc = StratumError("oops", context={"k": "v"})
        assert exc.detail == "oops"
        assert exc.context == {"k": "v"}

    def test_trust_gate_inheritance(self):
        exc = SignalDegradedError()
        assert isinstance(exc, TrustGateError)
        assert exc.status_code == 403  # inherited
        assert exc.error_code == "SIGNAL_DEGRADED"

    def test_error_code_registry(self):
        assert ERROR_CODES["TOKEN_EXPIRED"]["status_code"] == 401
        assert ERROR_CODES["TRUST_GATE_BLOCKED"]["status_code"] == 403
        assert (
            ERROR_CODES["SIGNAL_UNHEALTHY"]["exception_class"] == "SignalUnhealthyError"
        )
        # every registered code carries the required metadata
        for meta in ERROR_CODES.values():
            assert {"status_code", "detail", "exception_class"} <= set(meta)


# =============================================================================
# TenantContext RBAC
# =============================================================================
class TestTenantContext:
    def test_super_admin_flags(self):
        ctx = TenantContext(
            tenant_id=1, user_id=2, role="superadmin", is_super_admin_bypass=True
        )
        assert ctx.is_super_admin is True
        assert ctx.is_tenant_admin is True
        assert ctx.can_bypass_tenant is True

    def test_super_admin_without_bypass_flag(self):
        ctx = TenantContext(tenant_id=1, user_id=2, role="SuperAdmin")
        assert ctx.is_super_admin is True
        assert ctx.can_bypass_tenant is False  # bypass flag not set

    def test_admin_not_super(self):
        ctx = TenantContext(tenant_id=1, user_id=2, role="admin")
        assert ctx.is_super_admin is False
        assert ctx.is_tenant_admin is True
        assert ctx.can_bypass_tenant is False

    def test_member_role(self):
        ctx = TenantContext(tenant_id=1, user_id=2, role="member")
        assert ctx.is_tenant_admin is False

    def test_audit_dict(self):
        ctx = TenantContext(
            tenant_id=5, user_id=9, role="admin", workspace_id=3, request_id="req_1"
        )
        audit = ctx.to_audit_dict()
        assert audit["tenant_id"] == 5
        assert audit["workspace_id"] == 3
        assert audit["request_id"] == "req_1"
        assert "request_time" in audit


# =============================================================================
# get_tenant_context extraction
# =============================================================================
class _State:
    pass


def _request(state_attrs=None, headers=None):
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [
            (k.lower().encode(), v.encode()) for k, v in (headers or {}).items()
        ],
        "client": ("127.0.0.1", 1234),
    }
    req = Request(scope)
    for k, v in (state_attrs or {}).items():
        setattr(req.state, k, v)
    return req


class TestGetTenantContext:
    def test_missing_required_fields_returns_none(self):
        assert get_tenant_context(_request()) is None
        assert get_tenant_context(_request({"tenant_id": 1, "user_id": 2})) is None

    def test_builds_and_caches_context(self):
        req = _request(
            {"tenant_id": 1, "user_id": 2, "role": "admin", "email": "a@b.com"},
            headers={"X-Request-ID": "req_9"},
        )
        ctx = get_tenant_context(req)
        assert ctx.tenant_id == 1
        assert ctx.email == "a@b.com"
        assert ctx.request_id == "req_9"
        # cached on request.state and returned on second call
        assert get_tenant_context(req) is ctx

    def test_superadmin_bypass_header_honored(self):
        req = _request(
            {"tenant_id": 1, "user_id": 2, "role": "superadmin"},
            headers={"X-Superadmin-Bypass": "true"},
        )
        ctx = get_tenant_context(req)
        assert ctx.is_super_admin_bypass is True
        assert ctx.can_bypass_tenant is True

    def test_bypass_header_ignored_for_non_superadmin(self):
        req = _request(
            {"tenant_id": 1, "user_id": 2, "role": "admin"},
            headers={"X-Superadmin-Bypass": "true"},
        )
        ctx = get_tenant_context(req)
        assert ctx.is_super_admin_bypass is False


# =============================================================================
# create_system_context
# =============================================================================
class TestSystemContext:
    def test_system_context_privileges(self):
        ctx = create_system_context(tenant_id=42)
        assert ctx.tenant_id == 42
        assert ctx.user_id == 0
        assert ctx.role == "superadmin"
        assert ctx.can_bypass_tenant is True
        assert ctx.request_id == "system"
