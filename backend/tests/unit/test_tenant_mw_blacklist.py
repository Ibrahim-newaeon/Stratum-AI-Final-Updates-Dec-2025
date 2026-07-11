# =============================================================================
# Stratum AI - TenantMiddleware token enforcement tests (AUTH-001)
# =============================================================================
"""
The tenant middleware decoded the JWT but never checked (a) that it was an
*access* token or (b) that it had been revoked. A refresh token or a
logged-out/blacklisted access token therefore reached protected endpoints
until it naturally expired. These tests pin the new behavior in dispatch().
"""

from unittest.mock import AsyncMock, patch

import pytest
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.security import create_access_token, create_refresh_token
from app.middleware.tenant import TenantMiddleware


def _request(token: str | None, path: str = "/api/v1/campaigns") -> Request:
    headers = []
    if token is not None:
        headers.append((b"authorization", f"Bearer {token}".encode()))
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": headers,
        "query_string": b"",
    }
    return Request(scope)


def _mw() -> TenantMiddleware:
    return TenantMiddleware(app=AsyncMock())


async def _call_next(_request):
    return Response(status_code=200)


@pytest.mark.asyncio
async def test_refresh_token_rejected_on_protected_endpoint():
    token = create_refresh_token(subject=9)
    call_next = AsyncMock(side_effect=_call_next)
    resp = await _mw().dispatch(_request(token), call_next)
    assert isinstance(resp, JSONResponse)
    assert resp.status_code == 401
    call_next.assert_not_awaited()  # never reached the app


@pytest.mark.asyncio
async def test_blacklisted_access_token_rejected():
    token = create_access_token(
        subject=9, additional_claims={"tenant_id": 1, "role": "admin"}
    )
    call_next = AsyncMock(side_effect=_call_next)
    with patch(
        "app.core.security.is_token_blacklisted", new=AsyncMock(return_value=True)
    ):
        resp = await _mw().dispatch(_request(token), call_next)
    assert resp.status_code == 401
    call_next.assert_not_awaited()


@pytest.mark.asyncio
async def test_valid_access_token_passes_through():
    token = create_access_token(
        subject=9, additional_claims={"tenant_id": 1, "role": "admin"}
    )
    call_next = AsyncMock(side_effect=_call_next)
    with patch(
        "app.core.security.is_token_blacklisted", new=AsyncMock(return_value=False)
    ):
        resp = await _mw().dispatch(_request(token), call_next)
    assert resp.status_code == 200
    call_next.assert_awaited_once()


@pytest.mark.asyncio
async def test_redis_outage_fails_open_but_allows():
    token = create_access_token(
        subject=9, additional_claims={"tenant_id": 1, "role": "admin"}
    )
    call_next = AsyncMock(side_effect=_call_next)
    with patch(
        "app.core.security.is_token_blacklisted",
        new=AsyncMock(side_effect=ConnectionError("redis down")),
    ):
        resp = await _mw().dispatch(_request(token), call_next)
    # Blacklist unavailable must not become a total auth outage.
    assert resp.status_code == 200
    call_next.assert_awaited_once()
