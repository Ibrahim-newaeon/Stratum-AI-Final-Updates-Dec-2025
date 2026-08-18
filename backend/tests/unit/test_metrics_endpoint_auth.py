# =============================================================================
# Stratum AI - /metrics Bearer Gate Tests
# =============================================================================
"""
Tests for metrics_access_allowed, the gate protecting the /metrics
exposition. /metrics is exempt from tenant auth (PUBLIC_ENDPOINTS) and the
global registry carries tenant_id-labeled series, so when METRICS_API_KEY
is configured the route must reject anything but the exact bearer token.
"""

from app.main import (
    docs_access_allowed,
    extract_ws_access_token,
    metrics_access_allowed,
)


class TestMetricsAccessAllowed:
    """Gate behavior for the /metrics endpoint."""

    def test_open_when_no_key_configured(self) -> None:
        assert metrics_access_allowed("", "") is True

    def test_open_when_no_key_ignores_any_header(self) -> None:
        assert metrics_access_allowed("Bearer anything", "") is True

    def test_closed_when_no_key_and_required(self) -> None:
        assert metrics_access_allowed("", "", require_key=True) is False
        assert metrics_access_allowed("Bearer anything", "", require_key=True) is False

    def test_correct_bearer_token_allowed(self) -> None:
        assert metrics_access_allowed("Bearer s3cret", "s3cret") is True

    def test_missing_header_rejected_when_key_set(self) -> None:
        assert metrics_access_allowed("", "s3cret") is False

    def test_wrong_token_rejected(self) -> None:
        assert metrics_access_allowed("Bearer wrong", "s3cret") is False

    def test_scheme_required(self) -> None:
        # A bare token without the Bearer scheme must not match.
        assert metrics_access_allowed("s3cret", "s3cret") is False

    def test_scheme_is_case_sensitive(self) -> None:
        assert metrics_access_allowed("bearer s3cret", "s3cret") is False

    def test_token_prefix_not_sufficient(self) -> None:
        assert metrics_access_allowed("Bearer s3cret-and-more", "s3cret") is False


class TestDocsAccessAllowed:
    """Production docs gate: empty key disables the surface."""

    def test_empty_configured_key_denies(self) -> None:
        assert docs_access_allowed("", "") is False
        assert docs_access_allowed("anything", "") is False

    def test_matching_key_allowed(self) -> None:
        assert docs_access_allowed("s3cret", "s3cret") is True

    def test_wrong_key_denied(self) -> None:
        assert docs_access_allowed("wrong", "s3cret") is False

    def test_empty_provided_denied_when_configured(self) -> None:
        assert docs_access_allowed("", "s3cret") is False


class TestExtractWsAccessToken:
    """WebSocket token comes from subprotocol, never the query string."""

    def test_bearer_prefix_extracted(self) -> None:
        assert extract_ws_access_token(["bearer.eyJhbGciOiJIUzI1NiJ9.abc"]) == (
            "eyJhbGciOiJIUzI1NiJ9.abc"
        )

    def test_empty_or_missing_denied(self) -> None:
        assert extract_ws_access_token(None) is None
        assert extract_ws_access_token([]) is None
        assert extract_ws_access_token(["bearer."]) is None

    def test_unrelated_subprotocol_ignored(self) -> None:
        assert extract_ws_access_token(["chat", "json"]) is None

    def test_picks_first_bearer_protocol(self) -> None:
        assert extract_ws_access_token(["chat", "bearer.tok-1", "bearer.tok-2"]) == (
            "tok-1"
        )
