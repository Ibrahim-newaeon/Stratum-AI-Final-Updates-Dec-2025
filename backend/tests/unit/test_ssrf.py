# =============================================================================
# Stratum AI - SSRF outbound-URL validation tests (SEC-001)
# =============================================================================
"""
validate_outbound_url must reject non-http(s) schemes and any host that
resolves to a private/loopback/link-local/reserved address (e.g. the cloud
metadata endpoint), while allowing public hosts.
"""

import socket
from unittest.mock import patch

import pytest

from app.core.ssrf import SSRFError, is_safe_outbound_url, validate_outbound_url

pytestmark = pytest.mark.unit


def _resolves_to(ip: str):
    """Patch getaddrinfo so any host resolves to `ip`."""
    return patch(
        "app.core.ssrf.socket.getaddrinfo",
        return_value=[(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 0))],
    )


@pytest.mark.parametrize(
    "scheme_url",
    ["ftp://host/x", "file:///etc/passwd", "gopher://host", "javascript:alert(1)"],
)
def test_rejects_non_http_schemes(scheme_url):
    with pytest.raises(SSRFError):
        validate_outbound_url(scheme_url)


def test_rejects_missing_host():
    with pytest.raises(SSRFError):
        validate_outbound_url("http://")


@pytest.mark.parametrize(
    "ip",
    [
        "127.0.0.1",  # loopback
        "10.0.0.5",  # private
        "192.168.1.1",  # private
        "172.16.0.9",  # private
        "169.254.169.254",  # link-local cloud metadata
        "0.0.0.0",  # unspecified
    ],
)
def test_rejects_internal_resolved_ips(ip):
    with _resolves_to(ip):
        with pytest.raises(SSRFError):
            validate_outbound_url("https://sneaky.example.com/hook")
        assert is_safe_outbound_url("https://sneaky.example.com/hook") is False


def test_allows_public_resolved_ip():
    with _resolves_to("93.184.216.34"):  # example.com public IP
        validate_outbound_url("https://hooks.example.com/xyz")  # no raise
        assert is_safe_outbound_url("https://hooks.example.com/xyz") is True


def test_dns_failure_is_unsafe():
    with patch(
        "app.core.ssrf.socket.getaddrinfo",
        side_effect=socket.gaierror("no such host"),
    ):
        assert is_safe_outbound_url("https://nope.invalid/x") is False


def test_blocks_when_any_resolved_ip_is_internal():
    # Multi-record DNS: one public, one internal → must be rejected (rebinding).
    infos = [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0)),
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.5", 0)),
    ]
    with patch("app.core.ssrf.socket.getaddrinfo", return_value=infos):
        assert is_safe_outbound_url("https://mixed.example.com") is False
