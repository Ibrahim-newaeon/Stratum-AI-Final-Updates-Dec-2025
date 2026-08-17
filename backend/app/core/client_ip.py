# =============================================================================
# Stratum AI - Client IP Resolution
# =============================================================================
"""One place that answers "who sent this request".

Production sits behind Cloudflare and an nginx edge container, so
``request.client.host`` is the *proxy's* address, never the visitor's. Reading it
directly records the same useless IP on every row.

Three middlewares already each carry a private ``_get_client_ip`` with this logic
(``middleware/audit.py``, ``middleware/rate_limit.py``,
``services/embed_widgets/security.py``). This module is the shared version they
should eventually collapse onto; it is introduced for
``POST /cms/contact``, which had reimplemented the resolver as bare
``request.client.host``.

The rule is the same one those three follow: **only trust forwarding headers when
the direct peer is a proxy we operate.** A request arriving straight from the
internet can set ``X-Forwarded-For`` to anything, so honouring it unconditionally
lets any caller choose the IP that gets logged, rate-limited, or stored.

Unlike the string-prefix lists in those three copies, membership is decided with
``ipaddress`` network containment, which gets the 172.16.0.0/12 boundary and IPv6
unique-local addresses right rather than by enumerating ``"172.16."`` …
``"172.31."``.

Deliberately NOT ``ip_address(x).is_private``. Python derives that from the IANA
special-purpose registry, which also contains the documentation blocks
192.0.2.0/24, 198.51.100.0/24 and 203.0.113.0/24 — so ``is_private`` reports
True for addresses that are emphatically not our infrastructure. The networks
below are the ones we actually run on, which keeps the trust decision auditable
here instead of delegating it to a registry with a different purpose.
"""

from ipaddress import ip_address, ip_network

from fastapi import Request

UNKNOWN = "unknown"

# The ranges our own hops live in: Docker bridge networks, the compose network,
# loopback, and IPv6 equivalents. An address inside one of these is treated as a
# proxy we operate, and only then are forwarding headers believed.
_INFRASTRUCTURE_NETWORKS = tuple(
    ip_network(cidr)
    for cidr in (
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "127.0.0.0/8",
        "169.254.0.0/16",
        "::1/128",
        "fc00::/7",
        "fe80::/10",
    )
)


def _is_internal(candidate: str) -> bool:
    """True for addresses that belong to our own infrastructure.

    Anything unparseable counts as external: a hostname or a mangled header
    value must not be mistaken for a proxy we trust.
    """
    try:
        parsed = ip_address(candidate)
    except ValueError:
        return False
    return any(parsed in network for network in _INFRASTRUCTURE_NETWORKS)


def get_client_ip(request: Request) -> str:
    """Resolve the originating client IP for ``request``.

    Returns the direct peer unless that peer is internal, in which case the
    forwarding headers are consulted. ``X-Forwarded-For`` is walked from the
    right, skipping our own hops, so a chain like
    ``"198.51.100.7, 172.18.0.1"`` yields the visitor rather than the last proxy.

    Returns ``"unknown"`` when the peer cannot be determined at all — an ASGI
    scope without a client, which happens for internal/test transports.
    """
    peer = request.client.host if request.client else None
    if not peer:
        return UNKNOWN

    if not _is_internal(peer):
        # Straight from the internet: its own address is the only trustworthy
        # thing about it.
        return peer

    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        hops = [hop.strip() for hop in forwarded.split(",") if hop.strip()]
        for hop in reversed(hops):
            if not _is_internal(hop):
                return hop
        # An all-internal chain is legitimate for internal callers; report the
        # first hop rather than the proxy that happens to be nearest.
        if hops:
            return hops[0]

    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip

    return peer
