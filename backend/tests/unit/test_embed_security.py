# =============================================================================
# Stratum AI - Embed Security Service unit tests
# =============================================================================
"""Unit tests for app.services.embed_widgets.security.

Pure security logic, no real I/O (Starlette Requests built from scopes).
Covers CSP/CORS header generation, origin allow-listing with wildcards,
device detection, proxy-aware client-IP resolution (spoofing guard),
HMAC-SHA256 signing, signed-response envelopes, and XSS sanitization.
"""

import hashlib
import hmac
import json
from datetime import datetime, timezone

import pytest
from starlette.requests import Request

from app.services.embed_widgets.security import EmbedSecurityService

pytestmark = pytest.mark.unit

# Non-secret HMAC key used only to exercise signing determinism in tests.
SIGNING_KEY = "unit-test-key"  # gitleaks:allow  pragma: allowlist secret


@pytest.fixture()
def svc():
    return EmbedSecurityService(SIGNING_KEY)


def _request(headers=None, client_host="203.0.113.5", query_string=b""):
    headers = headers or {}
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/embed",
        "query_string": query_string,
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": (client_host, 12345) if client_host else None,
    }
    return Request(scope)


# =============================================================================
# CSP headers
# =============================================================================
class TestCSP:
    def test_csp_headers_shape(self, svc):
        headers = svc.get_csp_headers(["example.com"], "dashboard")
        csp = headers["Content-Security-Policy"]
        assert "frame-ancestors" in csp
        assert "object-src 'none'" in csp
        assert "form-action 'none'" in csp
        assert headers["X-Content-Type-Options"] == "nosniff"
        assert headers["Referrer-Policy"] == "strict-origin-when-cross-origin"

    def test_domains_to_csp_includes_http_https_and_self(self, svc):
        csp = svc._domains_to_csp(["example.com"])
        assert "https://example.com" in csp
        assert "http://example.com" in csp
        assert "'self'" in csp

    def test_wildcard_domain(self, svc):
        csp = svc._domains_to_csp(["*.example.com"])
        assert "https://*.example.com" in csp


# =============================================================================
# CORS / origin allow-listing
# =============================================================================
class TestCORS:
    def test_allowed_origin_returns_headers(self, svc):
        headers = svc.get_cors_headers("https://example.com", ["example.com"])
        assert headers["Access-Control-Allow-Origin"] == "https://example.com"
        assert headers["Access-Control-Allow-Credentials"] == "false"

    def test_disallowed_origin_returns_none(self, svc):
        assert svc.get_cors_headers("https://evil.com", ["example.com"]) is None

    @pytest.mark.parametrize(
        "origin,domains,allowed",
        [
            ("https://example.com", ["example.com"], True),
            ("https://example.com:8443", ["example.com"], True),  # port stripped
            ("https://sub.example.com", ["*.example.com"], True),  # wildcard
            ("https://example.com", ["*.example.com"], True),  # base matches wildcard
            ("https://evil.com", ["example.com"], False),
            ("https://notexample.com", ["example.com"], False),
            ("", ["example.com"], False),
            ("https://example.com.evil.com", ["example.com"], False),
        ],
    )
    def test_is_origin_allowed(self, svc, origin, domains, allowed):
        assert svc._is_origin_allowed(origin, domains) is allowed

    def test_bare_hostname_origin(self, svc):
        assert svc._is_origin_allowed("example.com", ["example.com"]) is True


# =============================================================================
# Request validation + device detection
# =============================================================================
class TestRequestValidation:
    def test_validate_pulls_origin_token_device(self, svc):
        req = _request(
            headers={
                "origin": "https://example.com",
                "X-Embed-Token": "tok_123",
                "user-agent": "Mozilla/5.0 (iPhone; Mobile)",
            }
        )
        result = svc.validate_embed_request(req)
        assert result["origin"] == "https://example.com"
        assert result["token"] == "tok_123"
        assert result["device_type"] == "mobile"

    def test_origin_falls_back_to_referer(self, svc):
        req = _request(headers={"referer": "https://example.com/page/sub"})
        result = svc.validate_embed_request(req)
        assert result["origin"] == "https://example.com"

    def test_token_from_query_param(self, svc):
        req = _request(query_string=b"token=qtok")
        result = svc.validate_embed_request(req)
        assert result["token"] == "qtok"

    @pytest.mark.parametrize(
        "ua,expected",
        [
            ("Mozilla/5.0 (iPhone; Mobile)", "mobile"),
            ("Mozilla/5.0 (Android Mobile)", "mobile"),
            ("Mozilla/5.0 (iPad; Mobile)", "tablet"),
            ("Mozilla/5.0 (Macintosh)", "desktop"),
            ("", "desktop"),
        ],
    )
    def test_device_detection(self, svc, ua, expected):
        assert svc._detect_device_type(ua) == expected


# =============================================================================
# Client IP (proxy spoofing guard)
# =============================================================================
class TestClientIP:
    def test_direct_public_ip_trusted_over_xff(self, svc):
        # untrusted direct connection -> X-Forwarded-For is ignored
        req = _request(
            headers={"x-forwarded-for": "1.2.3.4"}, client_host="203.0.113.5"
        )
        assert svc._get_client_ip(req) == "203.0.113.5"

    def test_trusted_proxy_uses_xff(self, svc):
        req = _request(
            headers={"x-forwarded-for": "9.9.9.9, 10.0.0.1"}, client_host="10.0.0.1"
        )
        # returns the last non-private (real client) address
        assert svc._get_client_ip(req) == "9.9.9.9"

    def test_trusted_proxy_x_real_ip_fallback(self, svc):
        req = _request(headers={"x-real-ip": "8.8.8.8"}, client_host="127.0.0.1")
        assert svc._get_client_ip(req) == "8.8.8.8"

    def test_no_client(self, svc):
        assert svc._get_client_ip(_request(client_host=None)) is None


# =============================================================================
# Signing
# =============================================================================
class TestSigning:
    def test_signature_matches_hmac(self, svc):
        ts = datetime(2026, 6, 1, tzinfo=timezone.utc)
        sig = svc.sign_widget_data({"a": 1}, "tok", ts)
        canonical = json.dumps(
            {"data": {"a": 1}, "token_id": "tok", "timestamp": ts.isoformat()},
            sort_keys=True,
            separators=(",", ":"),
        )
        expected = hmac.new(
            SIGNING_KEY.encode(), canonical.encode(), hashlib.sha256
        ).hexdigest()
        assert sig == expected

    def test_signature_deterministic_and_key_sensitive(self, svc):
        ts = datetime(2026, 6, 1, tzinfo=timezone.utc)
        sig1 = svc.sign_widget_data({"a": 1}, "tok", ts)
        sig2 = svc.sign_widget_data({"a": 1}, "tok", ts)
        assert sig1 == sig2
        other = EmbedSecurityService("different-key").sign_widget_data(
            {"a": 1}, "tok", ts
        )
        assert other != sig1

    def test_tampered_data_changes_signature(self, svc):
        ts = datetime(2026, 6, 1, tzinfo=timezone.utc)
        assert svc.sign_widget_data({"a": 1}, "tok", ts) != svc.sign_widget_data(
            {"a": 2}, "tok", ts
        )

    def test_signed_response_envelope(self, svc):
        resp = svc.create_signed_response({"x": 1}, "tok", ttl_seconds=300)
        assert resp["data"] == {"x": 1}
        assert "signature" in resp
        signed = datetime.fromisoformat(resp["signed_at"])
        expires = datetime.fromisoformat(resp["expires_at"])
        assert (expires - signed).total_seconds() == pytest.approx(300, abs=1)


# =============================================================================
# Sanitization (XSS)
# =============================================================================
class TestSanitization:
    def test_strips_script_tags(self, svc):
        out = svc._sanitize_string("hello<script>alert(1)</script>world")
        assert "script" not in out.lower()
        assert "alert" not in out

    def test_strips_event_handlers(self, svc):
        out = svc._sanitize_string('<div onclick="evil()">x</div>')
        assert "onclick" not in out.lower()

    def test_strips_javascript_urls(self, svc):
        out = svc._sanitize_string("javascript:alert(1)")
        assert "javascript:" not in out.lower()

    def test_escapes_html_entities(self, svc):
        out = svc._sanitize_string("a<b>&\"'")
        assert "&lt;" in out and "&gt;" in out
        assert "&amp;" in out and "&quot;" in out and "&#x27;" in out

    def test_sanitize_config_recurses(self, svc):
        config = {
            "title": "<script>x</script>Safe",
            "nested": {"label": "<b>bold</b>"},
            "tags": ["<i>a</i>", "plain"],
            "count": 5,
            "enabled": True,
        }
        out = svc.sanitize_widget_config(config)
        assert "script" not in out["title"].lower()
        assert "&lt;b&gt;" in out["nested"]["label"]
        assert "&lt;i&gt;" in out["tags"][0]
        assert out["tags"][1] == "plain"
        assert out["count"] == 5  # non-strings untouched
        assert out["enabled"] is True
