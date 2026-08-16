# =============================================================================
# Stratum AI - CRM OAuth state (CSRF + tenant binding)
# =============================================================================
"""Server-side state for CRM OAuth flows.

The CRM callbacks used to derive the tenant straight out of the ``state`` query
parameter::

    tenant_id_str, _ = state.split(":", 1)
    tenant_id = int(tenant_id_str)

That is not authentication. ``state`` arrives from the user's browser and can
say anything, so a caller who completes a HubSpot authorisation with
``state="7:whatever"`` binds their own HubSpot portal to tenant 7 — and can
then read and write that tenant's CRM through it.

The connect endpoint did generate a proper ``secrets.token_urlsafe(32)``; it
simply had nowhere to put it, and said so in a comment ("in production use
Redis"). This is that store.

Same shape as ``OAuthService.create_state`` / ``validate_state`` for the ad
platforms: random token, short TTL, and an atomic ``GETDEL`` on read so a state
cannot be replayed. The tenant lives in Redis under the token, never in
anything the caller can edit.
"""

from __future__ import annotations

import secrets
from typing import Optional

from app.core.logging import get_logger
from app.core.security import get_redis_pool

logger = get_logger(__name__)

CRM_OAUTH_STATE_PREFIX = "crm_oauth_state:"

# Long enough for a human to finish an OAuth consent screen, short enough that
# an intercepted state is not useful later.
CRM_OAUTH_STATE_TTL_SECONDS = 600


def _key(provider: str, token: str) -> str:
    return f"{CRM_OAUTH_STATE_PREFIX}{provider}:{token}"


async def create_crm_oauth_state(provider: str, tenant_id: int) -> str:
    """Mint a single-use state token bound server-side to ``tenant_id``."""
    token = secrets.token_urlsafe(32)
    client = await get_redis_pool()
    await client.setex(
        _key(provider, token), CRM_OAUTH_STATE_TTL_SECONDS, str(tenant_id)
    )
    return token


async def consume_crm_oauth_state(provider: str, token: str) -> Optional[int]:
    """Return the tenant bound to ``token``, consuming it. ``None`` if invalid.

    ``GETDEL`` is atomic, so two concurrent callbacks cannot both succeed with
    the same state — the second sees nothing. Fails closed on every unexpected
    condition: an unknown token, an unparseable payload, or Redis being
    unreachable all return ``None`` and the caller must reject the callback.
    Refusing a legitimate reconnect is a retry; accepting a forged one hands
    over a tenant's CRM.
    """
    if not token:
        return None

    try:
        client = await get_redis_pool()
        raw = await client.getdel(_key(provider, token))
    except (ConnectionError, TimeoutError, OSError) as exc:
        logger.error("crm_oauth_state_unavailable", provider=provider, error=str(exc))
        return None

    if raw is None:
        logger.warning("crm_oauth_state_not_found", provider=provider)
        return None

    try:
        return int(raw)
    except (TypeError, ValueError):
        logger.error("crm_oauth_state_corrupt", provider=provider)
        return None
