# =============================================================================
# Stratum AI - /metrics Bearer Gate Tests
# =============================================================================
"""
Tests for metrics_access_allowed, the gate protecting the /metrics
exposition. /metrics is exempt from tenant auth (PUBLIC_ENDPOINTS) and the
global registry carries tenant_id-labeled series, so when METRICS_API_KEY
is configured the route must reject anything but the exact bearer token.
"""

from app.main import metrics_access_allowed


class TestMetricsAccessAllowed:
    """Gate behavior for the /metrics endpoint."""

    def test_open_when_no_key_configured(self) -> None:
        assert metrics_access_allowed("", "") is True

    def test_open_when_no_key_ignores_any_header(self) -> None:
        assert metrics_access_allowed("Bearer anything", "") is True

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
