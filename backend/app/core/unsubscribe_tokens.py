# =============================================================================
# Stratum AI - Newsletter Unsubscribe Tokens
# =============================================================================
"""Signed tokens for the public newsletter unsubscribe link.

The previous scheme was ``base64("<campaign_id>:<subscriber_id>")`` — no
signature, despite the helper's docstring calling it signed. Both values are
small sequential integers, so anyone holding one link could decrement the
subscriber id and unsubscribe a stranger, or walk the range and unsubscribe the
whole list. There is no authentication on the endpoint, by necessity: the
request is a person clicking a link in an email.

Tokens are now ``<payload>.<signature>``, signed with HMAC-SHA256 under the
application secret and compared with :func:`hmac.compare_digest`. The payload
still carries only the two ids, so nothing new is exposed in the URL.

Legacy tokens are still accepted while
``settings.newsletter_accept_legacy_unsubscribe_tokens`` is true, because links
in already-delivered mail cannot be reissued — an inbox is forever, and a
broken unsubscribe link is worse than the forgery risk it closes. Every legacy
use is logged; once the logs go quiet, set the flag to false and the old format
stops working. That is a one-line change, deliberately, rather than a date this
file would have to be edited to honour.
"""

import base64
import hashlib
import hmac
from typing import Optional

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

#: Separates the payload from its signature.
_SEP = "."


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(value: str) -> Optional[bytes]:
    try:
        return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))
    except (ValueError, TypeError):
        return None


def _signature(payload: str) -> str:
    digest = hmac.new(
        settings.secret_key.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return _b64encode(digest)


def make_unsubscribe_token(campaign_id: int, subscriber_id: int) -> str:
    """Build a tamper-proof unsubscribe token."""
    payload = f"{campaign_id}:{subscriber_id}"
    return f"{_b64encode(payload.encode('utf-8'))}{_SEP}{_signature(payload)}"


def _parse_payload(payload: str) -> Optional[tuple[int, int]]:
    campaign_part, sep, subscriber_part = payload.partition(":")
    if not sep:
        return None
    try:
        return int(campaign_part), int(subscriber_part)
    except ValueError:
        return None


def parse_unsubscribe_token(token: str) -> Optional[tuple[int, int]]:
    """Return ``(campaign_id, subscriber_id)``, or ``None`` if unusable.

    A single ``None`` for every failure — malformed, truncated, wrong
    signature — so a caller cannot accidentally tell "forged" from "corrupt"
    and turn the endpoint into an oracle.
    """
    if not token:
        return None

    encoded, sep, signature = token.partition(_SEP)

    if sep:
        raw = _b64decode(encoded)
        if raw is None:
            return None
        try:
            payload = raw.decode("utf-8")
        except UnicodeDecodeError:
            return None
        if not hmac.compare_digest(signature, _signature(payload)):
            return None
        return _parse_payload(payload)

    # No separator: the pre-signature format.
    if not settings.newsletter_accept_legacy_unsubscribe_tokens:
        return None

    raw = _b64decode(encoded)
    if raw is None:
        return None
    try:
        payload = raw.decode("utf-8")
    except UnicodeDecodeError:
        return None

    parsed = _parse_payload(payload)
    if parsed is not None:
        logger.warning(
            "newsletter_legacy_unsubscribe_token_used",
            campaign_id=parsed[0],
            detail=(
                "Unsigned token accepted for backward compatibility. When these "
                "stop appearing, set NEWSLETTER_ACCEPT_LEGACY_UNSUBSCRIBE_TOKENS"
                "=false."
            ),
        )
    return parsed
