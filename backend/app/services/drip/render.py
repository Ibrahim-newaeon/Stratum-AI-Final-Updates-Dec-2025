# =============================================================================
# Stratum AI - Drip Email Rendering, Tracking and Unsubscribe Tokens
# =============================================================================
"""Turns an email node into a sendable message.

Personalisation and tracking follow the shape ``newsletter_tasks`` established
(open pixel before ``</body>``, ``href`` rewritten through a tracking route),
so drip and newsletter behave the same way in a mail client.

The unsubscribe token deliberately does **not** follow the newsletter's. That
one base64-encodes ``campaign_id:subscriber_id`` and calls the result signed;
decrementing an integer unsubscribes a stranger. Here the payload is HMAC-SHA256
signed with the application secret and compared with ``hmac.compare_digest``, so
a token cannot be forged or walked.
"""

import base64
import hashlib
import hmac
import re
from typing import Any, Optional
from urllib.parse import quote

from app.core.config import settings

#: Separates payload from signature inside the token.
_TOKEN_SEP = "."


# ---------------------------------------------------------------------------
# Unsubscribe tokens
# ---------------------------------------------------------------------------


def _sign(payload: str) -> str:
    digest = hmac.new(
        settings.secret_key.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def sign_unsubscribe_token(tenant_id: int, recipient_hash: str) -> str:
    """Create a tamper-proof unsubscribe token.

    Carries the recipient *hash*, never the address, so the token can appear in
    a URL, a mail log or a referrer header without leaking an email address.
    """
    payload = f"{tenant_id}:{recipient_hash}"
    encoded = base64.urlsafe_b64encode(payload.encode("utf-8")).decode("ascii")
    encoded = encoded.rstrip("=")
    return f"{encoded}{_TOKEN_SEP}{_sign(payload)}"


def verify_unsubscribe_token(token: str) -> Optional[tuple[int, str]]:
    """Return ``(tenant_id, recipient_hash)``, or ``None`` if the token is bad.

    ``None`` covers every failure — malformed, truncated, wrong signature — so
    a caller cannot accidentally distinguish "forged" from "corrupt" and turn
    the endpoint into an oracle.
    """
    if not token or _TOKEN_SEP not in token:
        return None
    encoded, _, signature = token.partition(_TOKEN_SEP)
    try:
        padding = "=" * (-len(encoded) % 4)
        payload = base64.urlsafe_b64decode(encoded + padding).decode("utf-8")
    except (ValueError, TypeError, UnicodeDecodeError):
        return None

    if not hmac.compare_digest(signature, _sign(payload)):
        return None

    tenant_part, _, recipient_hash = payload.partition(":")
    if not recipient_hash:
        return None
    try:
        return int(tenant_part), recipient_hash
    except ValueError:
        return None


def build_unsubscribe_url(
    tenant_id: int, recipient_hash: str, api_base_url: str
) -> str:
    token = sign_unsubscribe_token(tenant_id, recipient_hash)
    return f"{api_base_url}/api/v1/drip-campaigns/unsubscribe?token={token}"


# ---------------------------------------------------------------------------
# Personalisation
# ---------------------------------------------------------------------------


def personalize(html: str, context: dict[str, Any]) -> str:
    """Replace ``{{token}}`` placeholders with recipient values.

    Unknown placeholders are left untouched rather than blanked, so a typo in a
    template is visible in the delivered email instead of silently vanishing.
    """
    if not html:
        return ""
    out = html
    for key, value in (context or {}).items():
        out = out.replace("{{%s}}" % key, "" if value is None else str(value))
    return out


def personalization_context(
    recipient_email: str,
    profile_name: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """The standard placeholder set, matching the newsletter's vocabulary."""
    first = (profile_name or "").strip().split(" ")[0] if profile_name else ""
    context: dict[str, Any] = {
        "email": recipient_email,
        "first_name": first or "there",
        "full_name": profile_name or "",
    }
    if extra:
        context.update(extra)
    return context


# ---------------------------------------------------------------------------
# Tracking
# ---------------------------------------------------------------------------

_HREF_RE = re.compile(r'href="([^"]+)"')


def inject_tracking(html: str, execution_id: str, api_base_url: str) -> str:
    """Add an open pixel and rewrite links for click tracking.

    Keyed on the execution record rather than the enrollment, so a sequence
    that mails the same person twice attributes each open to the right step.
    """
    if not html:
        return ""

    base = f"{api_base_url}/api/v1/drip-campaigns/track"
    pixel = (
        f'<img src="{base}/open/{execution_id}" width="1" height="1" '
        f'style="display:none" alt="" />'
    )
    out = (
        html.replace("</body>", f"{pixel}</body>")
        if "</body>" in html
        else html + pixel
    )

    def rewrite(match: re.Match) -> str:
        href = match.group(1)
        # Leave non-navigational and already-tracked links alone. Rewriting the
        # unsubscribe link in particular would make opting out register as
        # engagement, which is both wrong and hostile.
        if href.startswith(("mailto:", "tel:", "#")) or "/drip-campaigns/" in href:
            return match.group(0)
        return f'href="{base}/click/{execution_id}?url={quote(href, safe="")}"'

    return _HREF_RE.sub(rewrite, out)


def append_unsubscribe_footer(html: str, unsubscribe_url: str) -> str:
    """Guarantee a visible opt-out even when the template forgot one.

    The ``List-Unsubscribe`` header alone is not enough: it is honoured by some
    clients and invisible in others.
    """
    if not unsubscribe_url or unsubscribe_url in (html or ""):
        return html or ""
    footer = (
        '<div style="margin-top:24px;font-size:12px;color:#9A9A9A;'
        'text-align:center">'
        f'<a href="{unsubscribe_url}" style="color:#9A9A9A">Unsubscribe</a>'
        "</div>"
    )
    if "</body>" in html:
        return html.replace("</body>", f"{footer}</body>")
    return html + footer
