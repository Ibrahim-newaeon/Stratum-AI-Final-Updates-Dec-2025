# =============================================================================
# Stratum AI - Outbound URL / SSRF validation (SEC-001)
# =============================================================================
"""
Shared guard for outbound HTTP requests to operator- or tenant-supplied URLs
(alert webhooks, CDN purge, notification/report webhooks, ...).

A scheme check alone is not enough: ``http://169.254.169.254/latest/meta-data``
(cloud metadata → credentials), ``http://10.0.0.5/`` (internal service), or a
public hostname whose DNS resolves to a private IP are all valid https/http
URLs. This module resolves the host and rejects any URL that resolves to a
private / loopback / link-local / reserved address.
"""

import ipaddress
import socket
from urllib.parse import urlparse

ALLOWED_SCHEMES = ("http", "https")


class SSRFError(ValueError):
    """Raised when an outbound URL fails SSRF validation."""


def _ip_is_blocked(ip_str: str) -> bool:
    """True if the IP is in a range we must never let outbound requests reach."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # unparseable → treat as unsafe
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local  # 169.254.0.0/16 — cloud metadata lives here
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def validate_outbound_url(url: str) -> None:
    """Validate an outbound URL, raising SSRFError if it is unsafe.

    Rejects non-http(s) schemes, missing hosts, and any host that resolves
    (via DNS) to a private/loopback/link-local/reserved address.
    """
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise SSRFError(f"scheme not allowed: {parsed.scheme!r}")

    host = parsed.hostname
    if not host:
        raise SSRFError("URL has no host")

    try:
        infos = socket.getaddrinfo(host, parsed.port or None, proto=socket.IPPROTO_TCP)
    except socket.gaierror as exc:
        raise SSRFError(f"DNS resolution failed for {host!r}: {exc}") from exc

    if not infos:
        raise SSRFError(f"{host!r} did not resolve to any address")

    for info in infos:
        # info[4] is the sockaddr; [0] is the IP address string (str for both
        # AF_INET and AF_INET6). Cast for mypy since sockaddr is a union type.
        ip_str = str(info[4][0])
        if _ip_is_blocked(ip_str):
            raise SSRFError(f"{host!r} resolves to a disallowed address: {ip_str}")


def is_safe_outbound_url(url: str) -> bool:
    """Boolean convenience wrapper around validate_outbound_url."""
    try:
        validate_outbound_url(url)
        return True
    except SSRFError:
        return False
