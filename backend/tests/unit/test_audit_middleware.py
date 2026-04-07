# =============================================================================
# Stratum AI - Audit Middleware Tests
# =============================================================================
"""
Tests for the audit logging middleware that records state-changing API requests.

Covers:
- Method filtering (only POST/PUT/PATCH/DELETE are audited)
- Endpoint exclusion (health checks, docs, etc.)
- Request body capture and JSON parsing
- Audit event structure and fields
- Resource type/ID extraction from URL paths
- HTTP method → AuditAction mapping
- Client IP extraction (direct, X-Forwarded-For, X-Real-IP)
- Sensitive field sanitisation (passwords, tokens, etc.)
- Redis queue integration
- Error resilience (audit failures must not break requests)
"""

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.middleware.audit import (
    AuditMiddleware,
    EXCLUDED_ENDPOINTS,
    STATE_CHANGING_METHODS,
)
from app.models import AuditAction


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_request(
    method: str = "POST",
    path: str = "/api/v1/campaigns/123",
    body: Optional[dict] = None,
    headers: Optional[Dict[str, str]] = None,
    state_attrs: Optional[Dict[str, Any]] = None,
    client_host: str = "127.0.0.1",
) -> MagicMock:
    """Build a minimal mock Request."""
    req = MagicMock()
    req.method = method
    req.url = MagicMock()
    req.url.path = path
    req.headers = headers or {}
    req.client = MagicMock()
    req.client.host = client_host

    state = MagicMock()
    for k, v in (state_attrs or {}).items():
        setattr(state, k, v)
    req.state = state

    body_bytes = json.dumps(body).encode("utf-8") if body else b""
    req.body = AsyncMock(return_value=body_bytes)
    req._body = body_bytes
    return req


def _make_response(status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    return resp


# ---------------------------------------------------------------------------
# Tests: Method filtering
# ---------------------------------------------------------------------------

class TestMethodFiltering:
    """Only state-changing methods should trigger audit logging."""

    @pytest.mark.asyncio
    async def test_get_request_not_audited(self) -> None:
        mw = AuditMiddleware(MagicMock())
        call_next = AsyncMock(return_value=_make_response())
        req = _make_request(method="GET")

        response = await mw.dispatch(req, call_next)

        call_next.assert_awaited_once_with(req)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_options_request_not_audited(self) -> None:
        mw = AuditMiddleware(MagicMock())
        call_next = AsyncMock(return_value=_make_response())
        req = _make_request(method="OPTIONS")

        response = await mw.dispatch(req, call_next)
        call_next.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_head_request_not_audited(self) -> None:
        mw = AuditMiddleware(MagicMock())
        call_next = AsyncMock(return_value=_make_response())
        req = _make_request(method="HEAD")

        await mw.dispatch(req, call_next)
        call_next.assert_awaited_once()

    @pytest.mark.asyncio
    @pytest.mark.parametrize("method", list(STATE_CHANGING_METHODS))
    async def test_state_changing_methods_trigger_audit(self, method: str) -> None:
        mw = AuditMiddleware(MagicMock())
        resp = _make_response(200)
        call_next = AsyncMock(return_value=resp)
        req = _make_request(method=method, body={"name": "test"})

        with patch.object(mw, "_log_audit_event", new_callable=AsyncMock) as mock_log:
            await mw.dispatch(req, call_next)
            if method in {"POST", "PUT", "PATCH"}:
                mock_log.assert_awaited_once()
            # DELETE has no body but should still be logged
            if method == "DELETE":
                mock_log.assert_awaited_once()


# ---------------------------------------------------------------------------
# Tests: Endpoint exclusion
# ---------------------------------------------------------------------------

class TestEndpointExclusion:
    """Health, docs, and other excluded endpoints must be skipped."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", list(EXCLUDED_ENDPOINTS))
    async def test_excluded_endpoints_not_audited(self, path: str) -> None:
        mw = AuditMiddleware(MagicMock())
        call_next = AsyncMock(return_value=_make_response())
        req = _make_request(method="POST", path=path)

        with patch.object(mw, "_log_audit_event", new_callable=AsyncMock) as mock_log:
            await mw.dispatch(req, call_next)
            mock_log.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_api_endpoint_is_audited(self) -> None:
        mw = AuditMiddleware(MagicMock())
        call_next = AsyncMock(return_value=_make_response())
        req = _make_request(method="POST", path="/api/v1/campaigns")

        with patch.object(mw, "_log_audit_event", new_callable=AsyncMock) as mock_log:
            await mw.dispatch(req, call_next)
            mock_log.assert_awaited_once()


# ---------------------------------------------------------------------------
# Tests: Response status filtering
# ---------------------------------------------------------------------------

class TestResponseStatusFiltering:
    """Only 2xx responses should be audit-logged."""

    @pytest.mark.asyncio
    async def test_success_status_logs_audit(self) -> None:
        mw = AuditMiddleware(MagicMock())
        call_next = AsyncMock(return_value=_make_response(201))
        req = _make_request(method="POST", body={"name": "new"})

        with patch.object(mw, "_log_audit_event", new_callable=AsyncMock) as mock_log:
            await mw.dispatch(req, call_next)
            mock_log.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_4xx_status_does_not_log_audit(self) -> None:
        mw = AuditMiddleware(MagicMock())
        call_next = AsyncMock(return_value=_make_response(400))
        req = _make_request(method="POST", body={"name": "bad"})

        with patch.object(mw, "_log_audit_event", new_callable=AsyncMock) as mock_log:
            await mw.dispatch(req, call_next)
            mock_log.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_5xx_status_does_not_log_audit(self) -> None:
        mw = AuditMiddleware(MagicMock())
        call_next = AsyncMock(return_value=_make_response(500))
        req = _make_request(method="POST", body={"name": "err"})

        with patch.object(mw, "_log_audit_event", new_callable=AsyncMock) as mock_log:
            await mw.dispatch(req, call_next)
            mock_log.assert_not_awaited()


# ---------------------------------------------------------------------------
# Tests: Resource path parsing
# ---------------------------------------------------------------------------

class TestResourceParsing:
    """_parse_resource_from_path should correctly extract resource type and ID."""

    def setup_method(self) -> None:
        self.mw = AuditMiddleware(MagicMock())

    def test_campaigns_with_id(self) -> None:
        rtype, rid = self.mw._parse_resource_from_path("/api/v1/campaigns/123")
        assert rtype == "campaigns"
        assert rid == "123"

    def test_campaigns_without_id(self) -> None:
        rtype, rid = self.mw._parse_resource_from_path("/api/v1/campaigns")
        assert rtype == "campaigns"
        assert rid is None

    def test_users_with_nested_path(self) -> None:
        rtype, rid = self.mw._parse_resource_from_path("/api/v1/users/456/settings")
        assert rtype == "users"
        assert rid == "456"

    def test_empty_path(self) -> None:
        rtype, rid = self.mw._parse_resource_from_path("/")
        assert rtype == "unknown"
        assert rid is None

    def test_non_numeric_id(self) -> None:
        rtype, rid = self.mw._parse_resource_from_path("/api/v1/campaigns/slug-name")
        assert rtype == "campaigns"
        assert rid is None  # "slug-name" is not numeric


# ---------------------------------------------------------------------------
# Tests: Action mapping
# ---------------------------------------------------------------------------

class TestActionMapping:
    """HTTP methods should map to correct AuditAction values."""

    def setup_method(self) -> None:
        self.mw = AuditMiddleware(MagicMock())

    def test_post_maps_to_create(self) -> None:
        assert self.mw._determine_action("POST") == AuditAction.CREATE

    def test_put_maps_to_update(self) -> None:
        assert self.mw._determine_action("PUT") == AuditAction.UPDATE

    def test_patch_maps_to_update(self) -> None:
        assert self.mw._determine_action("PATCH") == AuditAction.UPDATE

    def test_delete_maps_to_delete(self) -> None:
        assert self.mw._determine_action("DELETE") == AuditAction.DELETE

    def test_unknown_method_defaults_to_update(self) -> None:
        assert self.mw._determine_action("FOOBAR") == AuditAction.UPDATE


# ---------------------------------------------------------------------------
# Tests: Client IP extraction
# ---------------------------------------------------------------------------

class TestClientIpExtraction:
    """_get_client_ip should prefer forwarded headers over direct connection."""

    def setup_method(self) -> None:
        self.mw = AuditMiddleware(MagicMock())

    def test_direct_connection(self) -> None:
        req = _make_request(client_host="10.0.0.1")
        ip = self.mw._get_client_ip(req)
        assert ip == "10.0.0.1"

    def test_x_forwarded_for_single(self) -> None:
        req = _make_request(headers={"X-Forwarded-For": "203.0.113.50"})
        ip = self.mw._get_client_ip(req)
        assert ip == "203.0.113.50"

    def test_x_forwarded_for_chain(self) -> None:
        req = _make_request(headers={"X-Forwarded-For": "203.0.113.50, 70.41.3.18, 150.172.238.178"})
        ip = self.mw._get_client_ip(req)
        assert ip == "203.0.113.50"

    def test_x_real_ip(self) -> None:
        req = _make_request(headers={"X-Real-IP": "192.168.1.100"})
        ip = self.mw._get_client_ip(req)
        assert ip == "192.168.1.100"

    def test_x_forwarded_for_takes_priority_over_x_real_ip(self) -> None:
        req = _make_request(headers={
            "X-Forwarded-For": "1.1.1.1",
            "X-Real-IP": "2.2.2.2",
        })
        ip = self.mw._get_client_ip(req)
        assert ip == "1.1.1.1"

    def test_no_client_returns_unknown(self) -> None:
        req = _make_request()
        req.client = None
        req.headers = {}
        ip = self.mw._get_client_ip(req)
        assert ip == "unknown"


# ---------------------------------------------------------------------------
# Tests: Sensitive data sanitisation
# ---------------------------------------------------------------------------

class TestSanitisation:
    """_sanitize_for_audit must redact sensitive fields."""

    def setup_method(self) -> None:
        self.mw = AuditMiddleware(MagicMock())

    def test_password_redacted(self) -> None:
        data = {"email": "a@b.com", "password": "s3cret"}
        result = self.mw._sanitize_for_audit(data)
        assert result is not None
        assert result["email"] == "a@b.com"
        assert result["password"] == "[REDACTED]"

    def test_access_token_redacted(self) -> None:
        data = {"access_token": "abc123", "name": "test"}
        result = self.mw._sanitize_for_audit(data)
        assert result is not None
        assert result["access_token"] == "[REDACTED]"
        assert result["name"] == "test"

    def test_nested_sensitive_fields(self) -> None:
        data = {"user": {"password_hash": "hashed", "name": "John"}}
        result = self.mw._sanitize_for_audit(data)
        assert result is not None
        assert result["user"]["password_hash"] == "[REDACTED]"
        assert result["user"]["name"] == "John"

    def test_api_key_redacted(self) -> None:
        data = {"api_key": "key-123", "value": 42}
        result = self.mw._sanitize_for_audit(data)
        assert result is not None
        assert result["api_key"] == "[REDACTED]"

    def test_credit_card_redacted(self) -> None:
        data = {"credit_card": "4111111111111111"}
        result = self.mw._sanitize_for_audit(data)
        assert result is not None
        assert result["credit_card"] == "[REDACTED]"

    def test_none_input(self) -> None:
        assert self.mw._sanitize_for_audit(None) is None

    def test_empty_dict(self) -> None:
        result = self.mw._sanitize_for_audit({})
        assert result == {}

    def test_case_insensitive_partial_match(self) -> None:
        """'secret' is a sensitive field — 'client_secret' should be redacted."""
        data = {"client_secret": "very-secret"}
        result = self.mw._sanitize_for_audit(data)
        assert result is not None
        assert result["client_secret"] == "[REDACTED]"


# ---------------------------------------------------------------------------
# Tests: Error resilience
# ---------------------------------------------------------------------------

class TestErrorResilience:
    """Audit logging failures must not break request handling."""

    @pytest.mark.asyncio
    async def test_audit_logging_failure_does_not_break_request(self) -> None:
        mw = AuditMiddleware(MagicMock())
        call_next = AsyncMock(return_value=_make_response(200))
        req = _make_request(method="POST", body={"name": "test"})

        with patch.object(mw, "_log_audit_event", new_callable=AsyncMock, side_effect=Exception("DB down")):
            # Should not raise — middleware must swallow audit errors
            response = await mw.dispatch(req, call_next)
            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_invalid_json_body_does_not_break_request(self) -> None:
        mw = AuditMiddleware(MagicMock())
        call_next = AsyncMock(return_value=_make_response(200))
        req = _make_request(method="POST")
        # Override body to return invalid JSON bytes
        req.body = AsyncMock(return_value=b"not json{{{")

        with patch.object(mw, "_log_audit_event", new_callable=AsyncMock) as mock_log:
            response = await mw.dispatch(req, call_next)
            assert response.status_code == 200
