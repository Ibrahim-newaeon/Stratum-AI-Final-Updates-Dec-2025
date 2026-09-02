# =============================================================================
# Stratum AI - Paddle Webhook Handler
# =============================================================================
"""
Webhook endpoint for receiving Paddle Billing events.

Handles:
- transaction.completed / transaction.paid       - Payment successful
- transaction.payment_failed / transaction.past_due - Payment failed
- subscription.created / activated / trialing / resumed - Subscription entitles
- subscription.updated                           - Plan or schedule changed
- subscription.canceled / paused / past_due      - Entitlement state changed
- customer.created / customer.updated            - Customer record changed

Structure deliberately mirrors ``stripe_webhook.py``: claim-before-process
idempotency in Redis, one database transaction per event owned by this wrapper,
and a 5xx on handler failure so Paddle retries rather than silently dropping a
billing event. The reasoning behind each of those is documented there and is
not repeated here.
"""

from ipaddress import ip_address, ip_network
from typing import Any, Optional

import httpx
from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base_models import Tenant
from app.core.client_ip import get_client_ip
from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import get_redis_pool
from app.db.session import async_session_maker
from app.services import paddle_service

logger = get_logger(__name__)
router = APIRouter(tags=["paddle-webhook"])


# =============================================================================
# Idempotency
# =============================================================================
#
# Same design as the Stripe handler: Redis, not a process-local set, because
# production runs `uvicorn --workers 4`. Paddle retries a failing endpoint over
# ~3 days, so the key must outlive that window.

_EVENT_KEY_PREFIX = "paddle:event:"
_EVENT_TTL_SECONDS = 7 * 24 * 60 * 60


async def _claim_event(event_id: str) -> Optional[bool]:
    """Claim an event for processing.

    True when this worker won the claim, False when another worker already
    handled it, None when Redis could not be reached.
    """
    try:
        redis = await get_redis_pool()
        won = await redis.set(
            f"{_EVENT_KEY_PREFIX}{event_id}", "1", nx=True, ex=_EVENT_TTL_SECONDS
        )
        return bool(won)
    except (ConnectionError, TimeoutError, OSError) as exc:
        # Fail closed: processing without a duplicate guard can double-apply
        # subscription state across workers. Paddle retries 503s, so a Redis
        # outage delays billing rather than corrupting it.
        logger.error(
            "paddle_webhook_idempotency_unavailable",
            event_id=event_id,
            error=str(exc),
            detail="refusing event until Redis is reachable",
        )
        return None


async def _release_event(event_id: str) -> None:
    """Drop a claim so a Paddle retry is not mistaken for a duplicate."""
    try:
        redis = await get_redis_pool()
        await redis.delete(f"{_EVENT_KEY_PREFIX}{event_id}")
    except (ConnectionError, TimeoutError, OSError) as exc:
        logger.error(
            "paddle_webhook_claim_release_failed",
            event_id=event_id,
            error=str(exc),
            detail="a retry of this event may be skipped as a duplicate",
        )


# =============================================================================
# IP allowlist
# =============================================================================
#
# Paddle publishes its webhook source addresses at https://api.paddle.com/ips.
# The list is fetched and cached rather than hard-coded, because Paddle changes
# it and a stale constant would start rejecting genuine deliveries.
#
# This is defence in depth. The HMAC signature check is the real gate: an
# attacker who cannot forge a signature cannot do anything useful from an
# allowlisted IP either. See settings.paddle_webhook_enforce_ip_allowlist for
# why enforcement is opt-in behind Cloudflare.

_OCCURRED_KEY_PREFIX = "paddle:sub:occurred:"
_OCCURRED_TTL_SECONDS = 30 * 24 * 60 * 60


async def _is_stale(subscription_id: str, occurred_at: Optional[str]) -> bool:
    """True when a newer event for this subscription has already been applied.

    Paddle does not order deliveries, and a retry re-sends the *original*
    payload. So a `subscription.updated` can be processed, and a retried
    `subscription.created` carrying older state can arrive afterwards and
    regress the tenant's plan. Comparing `occurred_at` against the newest one
    applied for this subscription makes the handler convergent on latest state.

    Fails open: if Redis is unavailable or the timestamp is missing we apply the
    event. The idempotency claim has already established Redis is reachable at
    this point, so this is a narrow window, and wrongly skipping a real state
    change is worse than wrongly re-applying one.
    """
    if not subscription_id or not occurred_at:
        return False
    key = f"{_OCCURRED_KEY_PREFIX}{subscription_id}"
    try:
        redis = await get_redis_pool()
        previous = await redis.get(key)
        if previous and previous.decode() >= occurred_at:
            return True
        await redis.set(key, occurred_at, ex=_OCCURRED_TTL_SECONDS)
    except (ConnectionError, TimeoutError, OSError, AttributeError):
        return False
    return False


_IPS_URL = "https://api.paddle.com/ips"
_IPS_CACHE_KEY = "paddle:webhook:ips"
_IPS_CACHE_TTL = 60 * 60  # 1 hour


async def _fetch_paddle_ips() -> list[str]:
    """Fetch Paddle's published webhook CIDRs, caching in Redis for an hour.

    Returns an empty list if the list cannot be obtained. Callers must treat
    "no list" as "cannot evaluate" and never as "deny everything" — failing
    closed on a fetch error would take billing down for a Paddle-side outage
    that has nothing to do with us.
    """
    try:
        redis = await get_redis_pool()
        cached = await redis.get(_IPS_CACHE_KEY)
        if cached:
            return [c for c in cached.decode().split(",") if c]
    except (ConnectionError, TimeoutError, OSError, AttributeError):
        redis = None  # Fall through to a direct fetch.

    # Paddle marks any delivery taking >5s as timed out and burns a retry
    # attempt, so this fetch is bounded far below that. Losing the list costs
    # nothing (see the docstring); blowing the budget costs the event.
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(1.5, connect=1.0)) as client:
            response = await client.get(_IPS_URL)
            response.raise_for_status()
            cidrs = response.json().get("data", {}).get("ipv4_cidrs", [])
    except (httpx.HTTPError, ValueError) as exc:
        logger.warning("paddle_webhook_ip_list_unavailable", error=str(exc))
        return []

    if redis is not None and cidrs:
        try:
            await redis.set(_IPS_CACHE_KEY, ",".join(cidrs), ex=_IPS_CACHE_TTL)
        except (ConnectionError, TimeoutError, OSError):
            pass

    return cidrs


async def _check_source_ip(request: Request) -> bool:
    """Check whether the request came from a published Paddle address.

    Returns True when the source is allowlisted OR when the list could not be
    evaluated. The caller decides what to do with a False.
    """
    cidrs = await _fetch_paddle_ips()
    if not cidrs:
        return True  # Cannot evaluate; the signature check still applies.

    client_ip = get_client_ip(request)
    try:
        parsed = ip_address(client_ip)
    except ValueError:
        logger.warning("paddle_webhook_ip_unparseable", client_ip=client_ip)
        return False

    return any(parsed in ip_network(cidr) for cidr in cidrs)


# =============================================================================
# Tenant resolution
# =============================================================================


async def get_tenant_by_customer_id(
    db: AsyncSession, customer_id: str
) -> Tenant | None:
    """Get tenant by Paddle customer ID."""
    result = await db.execute(
        select(Tenant).where(
            Tenant.paddle_customer_id == customer_id,
            Tenant.is_deleted == False,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def get_tenant_by_id(db: AsyncSession, tenant_id: int) -> Tenant | None:
    """Get tenant by ID."""
    result = await db.execute(
        select(Tenant).where(
            Tenant.id == tenant_id,
            Tenant.is_deleted == False,  # noqa: E712
        )
    )
    return result.scalar_one_or_none()


async def _resolve_tenant(db: AsyncSession, entity: dict[str, Any]) -> Tenant | None:
    """Resolve the tenant an event's entity belongs to.

    ``custom_data.tenant_id`` is preferred: it is set at checkout and on the
    customer, and travels onto the subscription Paddle derives from the
    transaction. The ``paddle_customer_id`` lookup is the fallback for entities
    that predate custom_data or lost it.

    Email is deliberately not a fallback. User emails are stored encrypted
    (app.core.security.encrypt_pii), so they are not queryable, and matching on
    a decrypted scan would be both slow and a PII hazard.
    """
    custom = entity.get("custom_data") or {}
    raw_tenant_id = custom.get("tenant_id")
    if raw_tenant_id is not None:
        try:
            return await get_tenant_by_id(db, int(raw_tenant_id))
        except (TypeError, ValueError):
            logger.warning(
                "paddle_webhook_bad_tenant_id",
                raw_tenant_id=str(raw_tenant_id)[:64],
            )

    customer_id = entity.get("customer_id")
    if customer_id:
        return await get_tenant_by_customer_id(db, customer_id)

    return None


# =============================================================================
# Endpoint
# =============================================================================


@router.post("/webhooks/paddle")
async def paddle_webhook(request: Request):
    """
    Handle incoming Paddle webhook events.

    Verifies the ``Paddle-Signature`` HMAC before doing anything else, then
    processes the event inside a single database transaction.
    """
    if not settings.paddle_webhook_secret:
        logger.error("paddle_webhook_secret_not_configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook secret not configured",
        )

    # Raw bytes, exactly as received. Re-serialising the parsed JSON changes
    # key order and whitespace, and the HMAC would never match.
    payload = await request.body()
    signature = request.headers.get("paddle-signature", "")

    if not signature:
        logger.warning("paddle_webhook_missing_signature")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Paddle signature",
        )

    if not paddle_service.verify_webhook_signature(payload, signature):
        logger.error("paddle_webhook_invalid_signature")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        )

    # Source-IP check runs after the signature check, so a spoofed request has
    # already been rejected on cryptography rather than on network position.
    if not await _check_source_ip(request):
        logger.warning(
            "paddle_webhook_ip_not_allowlisted",
            client_ip=get_client_ip(request),
            enforced=settings.paddle_webhook_enforce_ip_allowlist,
            detail="signature was valid; set PADDLE_WEBHOOK_ENFORCE_IP_ALLOWLIST "
            "only once this stops appearing for genuine deliveries",
        )
        if settings.paddle_webhook_enforce_ip_allowlist:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Source address not allowlisted",
            )

    try:
        event = await request.json()
    except ValueError as exc:
        logger.error("paddle_webhook_parse_error", error=str(exc))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload",
        ) from exc

    event_id = event.get("event_id") or event.get("notification_id")
    event_type = event.get("event_type", "")
    entity = event.get("data") or {}

    if not event_id or not event_type:
        logger.error("paddle_webhook_malformed_envelope", event_type=event_type)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing event_id or event_type",
        )

    # Claim before processing, not after: claiming afterwards leaves a window
    # in which two workers handling the same retry both run the handlers.
    claimed = await _claim_event(event_id)
    if claimed is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Idempotency store unavailable",
        )
    if claimed is False:
        logger.info("paddle_webhook_duplicate_skipped", event_id=event_id)
        return {"status": "already_processed", "event_type": event_type}

    logger.info("paddle_webhook_received", event_type=event_type, event_id=event_id)

    async with async_session_maker() as db:
        try:
            if event_type.startswith("subscription."):
                await handle_subscription_event(
                    db, event_type, entity, event.get("occurred_at")
                )

            elif event_type in ("transaction.completed", "transaction.paid"):
                await handle_transaction_paid(db, entity)

            elif event_type in ("transaction.payment_failed", "transaction.past_due"):
                await handle_transaction_failed(db, entity)

            elif event_type in ("customer.created", "customer.updated"):
                await handle_customer_event(db, entity)

            else:
                logger.debug("paddle_webhook_unhandled", event_type=event_type)

            await db.commit()

        except Exception as exc:
            # Every handler failure asks Paddle to retry. Swallowing the error
            # and returning 200 would permanently discard a billing event while
            # telling Paddle it succeeded — lose transaction.payment_failed and
            # a delinquent account keeps full access; lose subscription.canceled
            # and a cancelled customer never downgrades. Neither surfaces.
            logger.error(
                "paddle_webhook_handler_error",
                event_type=event_type,
                event_id=event_id,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            await db.rollback()
            if claimed:
                await _release_event(event_id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Webhook handler failed",
            ) from exc

    return {"status": "received", "event_type": event_type}


# =============================================================================
# Event Handlers
# =============================================================================
#
# None of these commit. The endpoint wrapper owns the transaction so that a
# failure part-way through an event rolls the whole event back — see the
# transaction-ownership note in paddle_service.sync_tenant_subscription.


async def handle_subscription_event(
    db: AsyncSession,
    event_type: str,
    entity: dict[str, Any],
    occurred_at: Optional[str] = None,
) -> None:
    """
    Apply a subscription's current state to the tenant.

    Every ``subscription.*`` event carries the full subscription entity, so one
    handler covers created / activated / updated / trialing / paused / resumed /
    past_due / canceled. Entitlement is decided by
    ``paddle_service.ENTITLING_STATES``, not by which event arrived — that way
    an event type Paddle adds later cannot grant access by default.
    """
    if await _is_stale(entity.get("id", ""), occurred_at):
        logger.info(
            "paddle_webhook_stale_event_skipped",
            event_type=event_type,
            subscription_id=entity.get("id"),
            occurred_at=occurred_at,
            detail="a newer event for this subscription was already applied",
        )
        return

    tenant = await _resolve_tenant(db, entity)
    if tenant is None:
        logger.warning(
            "paddle_webhook_tenant_not_found",
            event_type=event_type,
            subscription_id=entity.get("id"),
            customer_id=entity.get("customer_id"),
        )
        return

    subscription = paddle_service.subscription_from_api(entity)

    # Backfill the customer link if checkout raced ahead of it, so the
    # customer_id fallback in _resolve_tenant works for later events.
    if not tenant.paddle_customer_id and subscription.customer_id:
        tenant.paddle_customer_id = subscription.customer_id

    await paddle_service.sync_tenant_subscription(db, tenant.id, subscription)


async def handle_transaction_paid(db: AsyncSession, entity: dict[str, Any]) -> None:
    """
    Record a successful payment.

    Entitlement is not granted here. A transaction completing is what causes
    Paddle to emit ``subscription.activated``/``updated``, and that event is
    where the plan is applied — deriving the plan from a transaction as well
    would mean two sources of truth that can disagree.
    """
    tenant = await _resolve_tenant(db, entity)
    if tenant is None:
        logger.warning(
            "paddle_webhook_tenant_not_found",
            event_type="transaction.paid",
            transaction_id=entity.get("id"),
        )
        return

    totals = (entity.get("details") or {}).get("totals") or {}
    logger.info(
        "paddle_transaction_paid",
        tenant_id=tenant.id,
        transaction_id=entity.get("id"),
        subscription_id=entity.get("subscription_id"),
        currency=entity.get("currency_code"),
        grand_total=totals.get("grand_total"),
    )


async def handle_transaction_failed(db: AsyncSession, entity: dict[str, Any]) -> None:
    """
    Record a failed payment.

    The plan is deliberately left alone. Paddle moves the subscription to
    ``past_due`` and emits a ``subscription.*`` event for it, and PAST_DUE is an
    entitling state on purpose so a customer is not cut off mid-dunning. When
    Paddle gives up it cancels the subscription, and that event downgrades.
    """
    tenant = await _resolve_tenant(db, entity)
    if tenant is None:
        logger.warning(
            "paddle_webhook_tenant_not_found",
            event_type="transaction.payment_failed",
            transaction_id=entity.get("id"),
        )
        return

    logger.warning(
        "paddle_transaction_failed",
        tenant_id=tenant.id,
        transaction_id=entity.get("id"),
        subscription_id=entity.get("subscription_id"),
    )


async def handle_customer_event(db: AsyncSession, entity: dict[str, Any]) -> None:
    """
    Link a Paddle customer to its tenant.

    Only ever fills in a missing link. Overwriting an existing
    ``paddle_customer_id`` would repoint a tenant's billing at a different
    Paddle customer, which is not something a customer.updated event should be
    able to do.
    """
    customer_id = entity.get("id")
    if not customer_id:
        return

    custom = entity.get("custom_data") or {}
    raw_tenant_id = custom.get("tenant_id")
    if raw_tenant_id is None:
        logger.debug("paddle_customer_event_without_tenant", customer_id=customer_id)
        return

    try:
        tenant = await get_tenant_by_id(db, int(raw_tenant_id))
    except (TypeError, ValueError):
        logger.warning(
            "paddle_webhook_bad_tenant_id", raw_tenant_id=str(raw_tenant_id)[:64]
        )
        return

    if tenant is None:
        logger.warning(
            "paddle_webhook_tenant_not_found",
            event_type="customer",
            customer_id=customer_id,
        )
        return

    if tenant.paddle_customer_id and tenant.paddle_customer_id != customer_id:
        logger.warning(
            "paddle_customer_id_conflict",
            tenant_id=tenant.id,
            existing=tenant.paddle_customer_id,
            incoming=customer_id,
            detail="left unchanged",
        )
        return

    if not tenant.paddle_customer_id:
        tenant.paddle_customer_id = customer_id
        logger.info(
            "paddle_customer_linked", tenant_id=tenant.id, customer_id=customer_id
        )
