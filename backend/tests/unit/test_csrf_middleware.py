# =============================================================================
# Stratum AI - CSRF Middleware unit tests
# =============================================================================
"""Unit tests for app.middleware.csrf.

Pure request-dispatch logic, no real network. Exercises the CSRFMiddleware
dispatch path with a stub call_next: safe-method skip, webhook-path exempt,
Bearer-token bypass, and Origin / Referer allow-listing for cookie-based
state-changing requests.
"""

import asyncio

import pytest
from fastapi import Response
from starlette.requests import Request

from app.middleware.csrf import CSRFMiddleware

pytestmark = pytest.mark.unit

ALLOWED = "https://app.stratum.ai"


@pytest.fixture()
def mw():
    middleware = CSRFMiddleware(app=lambda scope, receive, send: None)
    middleware.allowed_origins = {ALLOWED}
    return middleware


def _request(method="POST", path="/api/v1/campaigns", headers=None):
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [
            (k.lower().encode(), v.encode()) for k, v in (headers or {}).items()
        ],
        "client": ("203.0.113.5", 12345),
        "server": ("testserver", 80),
        "scheme": "https",
    }
    return Request(scope)


async def _call_next(request):
    return Response(status_code=200, content="ok")


def _dispatch(mw, request):
    return asyncio.run(mw.dispatch(request, _call_next))


# =============================================================================
# Skip paths
# =============================================================================
class TestSkips:
    def test_safe_method_passes_and_sets_header(self, mw):
        resp = _dispatch(mw, _request(method="GET"))
        assert resp.status_code == 200
        assert resp.headers["X-Content-Type-Options"] == "nosniff"

    @pytest.mark.parametrize(
        "path",
        [
            "/health",
            "/metrics",
            "/api/v1/stripe-webhook",
            "/api/v1/whatsapp/webhooks/inbound",
        ],
    )
    def test_exempt_paths_skip_csrf(self, mw, path):
        # disallowed origin would normally 403, but exempt path bypasses
        resp = _dispatch(
            mw, _request(path=path, headers={"origin": "https://evil.com"})
        )
        assert resp.status_code == 200

    def test_bearer_token_bypasses_origin_check(self, mw):
        resp = _dispatch(
            mw,
            _request(
                headers={
                    "authorization": "Bearer abc.def.ghi",
                    "origin": "https://evil.com",
                }
            ),
        )
        assert resp.status_code == 200
        assert resp.headers["X-Content-Type-Options"] == "nosniff"


# =============================================================================
# Origin / Referer validation
# =============================================================================
class TestOriginValidation:
    def test_allowed_origin_passes(self, mw):
        resp = _dispatch(mw, _request(headers={"origin": ALLOWED}))
        assert resp.status_code == 200

    def test_allowed_origin_trailing_slash_normalized(self, mw):
        resp = _dispatch(mw, _request(headers={"origin": ALLOWED + "/"}))
        assert resp.status_code == 200

    def test_disallowed_origin_rejected(self, mw):
        resp = _dispatch(mw, _request(headers={"origin": "https://evil.com"}))
        assert resp.status_code == 403
        body = bytes(resp.body).decode()
        assert "origin not allowed" in body

    def test_allowed_referer_passes(self, mw):
        resp = _dispatch(mw, _request(headers={"referer": f"{ALLOWED}/dashboard/page"}))
        assert resp.status_code == 200

    def test_disallowed_referer_rejected(self, mw):
        resp = _dispatch(mw, _request(headers={"referer": "https://evil.com/x"}))
        assert resp.status_code == 403
        assert "referer not allowed" in bytes(resp.body).decode()

    def test_no_origin_or_referer_passes(self, mw):
        # cookie-auth request without browser headers falls through
        resp = _dispatch(mw, _request())
        assert resp.status_code == 200
        assert resp.headers["X-Content-Type-Options"] == "nosniff"
