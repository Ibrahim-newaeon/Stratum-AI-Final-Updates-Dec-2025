# =============================================================================
# Stratum AI - P0 alert webhook tests (MON-002)
# =============================================================================
"""
Critical pipeline-health failures must escalate to the configured on-call
webhook. The escalation existed but read a setting (alert_webhook_url) that was
never declared, so it was always off. These pin the helper's behavior.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.core.config import settings
from app.workers.tasks.monitoring import post_alert_webhook

pytestmark = pytest.mark.unit


def test_setting_exists():
    # The escalation depends on this setting being declared (was getattr-None).
    assert hasattr(settings, "alert_webhook_url")


def test_noop_when_no_url():
    with patch("urllib.request.urlopen") as urlopen:
        assert post_alert_webhook(None, {"status": "critical"}) is False
        urlopen.assert_not_called()


def test_rejects_non_http_scheme():
    with patch("urllib.request.urlopen") as urlopen:
        assert post_alert_webhook("file:///etc/passwd", {"x": 1}) is False
        urlopen.assert_not_called()


def test_posts_to_https_url():
    # SSRF validation (SEC-001) is exercised separately; here isolate the POST.
    with patch("app.core.ssrf.is_safe_outbound_url", return_value=True), patch(
        "urllib.request.urlopen", return_value=MagicMock()
    ) as urlopen:
        ok = post_alert_webhook("https://hooks.example.com/xyz", {"status": "critical"})
    assert ok is True
    urlopen.assert_called_once()


def test_swallows_errors():
    with patch("app.core.ssrf.is_safe_outbound_url", return_value=True), patch(
        "urllib.request.urlopen", side_effect=OSError("network down")
    ):
        # Alerting failure must not raise into the monitoring task.
        assert post_alert_webhook("https://hooks.example.com/xyz", {"x": 1}) is False


def test_ssrf_unsafe_url_is_not_posted():
    # A URL that resolves to an internal address must never be contacted.
    with patch("app.core.ssrf.is_safe_outbound_url", return_value=False), patch(
        "urllib.request.urlopen"
    ) as urlopen:
        assert post_alert_webhook("http://169.254.169.254/latest/", {"x": 1}) is False
        urlopen.assert_not_called()
