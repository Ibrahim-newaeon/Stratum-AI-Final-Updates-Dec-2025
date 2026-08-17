# =============================================================================
# Stratum AI - Stripe Webhook Handler
# =============================================================================
"""
Webhook endpoint for receiving Stripe events.

Handles:
- checkout.session.completed - New subscription created
- customer.subscription.created - Subscription activated
- customer.subscription.updated - Subscription modified
- customer.subscription.deleted - Subscription canceled
- invoice.paid - Payment successful
- invoice.payment_failed - Payment failed
- customer.created - New customer
"""

from datetime import UTC, datetime
from typing import Optional

import stripe
from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.base_models import Tenant, User
from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import decrypt_pii, get_redis_pool, mask_email
from app.db.session import async_session_maker
from app.services import stripe_service
from app.services.email_service import get_email_service

logger = get_logger(__name__)
router = APIRouter(tags=["stripe-webhook"])

# Idempotency lives in Redis, not in the process.
#
# This was a module-level `set()` carrying the comment "in production with
# multiple workers, use Redis instead" — and production runs
# `uvicorn --workers 4`. A Stripe retry had a 3-in-4 chance of landing on a
# worker that had never seen the event, the set was lost on every restart, and
# eviction was `.clear()`, dropping all 10,000 entries at once despite the
# comment claiming it evicted the oldest.
#
# Stripe retries a failing endpoint for up to ~3 days; the key outlives that,
# so even a late retry is still recognised as a duplicate.
_EVENT_KEY_PREFIX = "stripe:event:"
_EVENT_TTL_SECONDS = 7 * 24 * 60 * 60


async def _claim_event(event_id: str) -> Optional[bool]:
    """Claim an event for processing.

    True when this worker won the claim, False when another worker has already
    handled it, None when Redis could not be reached.

    SET NX is what makes this safe when two workers receive the same retry
    concurrently: the loser sees False instead of both proceeding.
    """
    try:
        redis = await get_redis_pool()
        won = await redis.set(
            f"{_EVENT_KEY_PREFIX}{event_id}", "1", nx=True, ex=_EVENT_TTL_SECONDS
        )
        return bool(won)
    except (ConnectionError, TimeoutError, OSError) as exc:
        # Fail closed. Processing without a duplicate guard can double-apply
        # subscription state (and emails) across uvicorn workers. Stripe
        # retries 503s, so a Redis outage delays billing rather than
        # corrupting it.
        logger.error(
            "stripe_webhook_idempotency_unavailable",
            event_id=event_id,
            error=str(exc),
            detail="refusing event until Redis is reachable",
        )
        return None


async def _release_event(event_id: str) -> None:
    """Drop a claim so a Stripe retry is not mistaken for a duplicate.

    Without this, a handler that fails after claiming would have its retry
    skipped as "already processed" — losing the event precisely when it did
    not succeed.
    """
    try:
        redis = await get_redis_pool()
        await redis.delete(f"{_EVENT_KEY_PREFIX}{event_id}")
    except (ConnectionError, TimeoutError, OSError) as exc:
        logger.error(
            "stripe_webhook_claim_release_failed",
            event_id=event_id,
            error=str(exc),
            detail="a retry of this event may be skipped as a duplicate",
        )


async def get_tenant_by_customer_id(
    db: AsyncSession, customer_id: str
) -> Tenant | None:
    """Get tenant by Stripe customer ID."""
    result = await db.execute(
        select(Tenant).where(
            Tenant.stripe_customer_id == customer_id,
            Tenant.is_deleted == False,
        )
    )
    return result.scalar_one_or_none()


async def get_tenant_by_id(db: AsyncSession, tenant_id: int) -> Tenant | None:
    """Get tenant by ID."""
    result = await db.execute(
        select(Tenant).where(
            Tenant.id == tenant_id,
            Tenant.is_deleted == False,
        )
    )
    return result.scalar_one_or_none()


@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request):
    """
    Handle incoming Stripe webhook events.

    This endpoint receives events from Stripe and updates the database accordingly.
    Must verify the webhook signature to ensure authenticity.
    """
    if not stripe_service.STRIPE_CONFIGURED:
        logger.warning("stripe_webhook_not_configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe not configured",
        )

    # Get raw body for signature verification
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        logger.warning("stripe_webhook_missing_signature")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe signature",
        )

    # Verify webhook secret is configured
    if not settings.stripe_webhook_secret:
        logger.error("stripe_webhook_secret_not_configured")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook secret not configured",
        )

    # Verify webhook signature
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except stripe.SignatureVerificationError as e:
        logger.error("stripe_webhook_invalid_signature", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        )
    except (ValueError, KeyError) as e:
        logger.error("stripe_webhook_parse_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload",
        )

    event_type = event.type
    event_data = event.data.object

    # Claim before processing, not after. Claiming afterwards leaves a window
    # in which two workers handling the same retry both run the handlers.
    claimed = await _claim_event(event.id)
    if claimed is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Idempotency store unavailable",
        )
    if claimed is False:
        logger.info("stripe_webhook_duplicate_skipped", event_id=event.id)
        return {"status": "already_processed", "event_type": event_type}

    logger.info(
        "stripe_webhook_received",
        event_type=event_type,
        event_id=event.id,
    )

    # Process event
    async with async_session_maker() as db:
        try:
            if event_type == "checkout.session.completed":
                await handle_checkout_completed(db, event_data)

            elif event_type == "customer.subscription.created":
                await handle_subscription_created(db, event_data)

            elif event_type == "customer.subscription.updated":
                await handle_subscription_updated(db, event_data)

            elif event_type == "customer.subscription.deleted":
                await handle_subscription_deleted(db, event_data)

            elif event_type == "invoice.paid":
                await handle_invoice_paid(db, event_data)

            elif event_type == "invoice.payment_failed":
                await handle_invoice_payment_failed(db, event_data)

            elif event_type == "customer.created":
                await handle_customer_created(db, event_data)

            else:
                logger.debug("stripe_webhook_unhandled", event_type=event_type)

            await db.commit()

        except Exception as e:
            # Every handler failure now asks Stripe to retry.
            #
            # This used to swallow ValueError/KeyError/TypeError and return
            # 200 — "prevent retries for our app logic errors". For billing
            # that is the wrong trade: a KeyError on an unexpected payload
            # shape permanently discarded the event while telling Stripe it
            # had been processed. Lose invoice.payment_failed and a delinquent
            # account keeps full access; lose customer.subscription.deleted
            # and a cancelled customer never downgrades. Either way nothing
            # surfaces, because Stripe considers the delivery successful.
            #
            # A 5xx costs a few days of retries and leaves the event visible
            # as failed in the Stripe dashboard, which is the signal wanted.
            logger.error(
                "stripe_webhook_handler_error",
                event_type=event_type,
                event_id=event.id,
                error=str(e),
                error_type=type(e).__name__,
            )
            await db.rollback()
            # Only this worker's claim is released, and only when it holds one.
            if claimed:
                await _release_event(event.id)
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Webhook handler failed",
            ) from e

    return {"status": "received", "event_type": event_type}


# =============================================================================
# Event Handlers
# =============================================================================


async def handle_checkout_completed(db: AsyncSession, session: dict):
    """
    Handle checkout.session.completed event.

    This fires when a customer completes the checkout process.
    """
    customer_id = session.get("customer")
    subscription_id = session.get("subscription")
    metadata = session.get("metadata", {})
    tenant_id = metadata.get("tenant_id")

    logger.info(
        "stripe_checkout_completed",
        customer_id=customer_id,
        subscription_id=subscription_id,
        tenant_id=tenant_id,
    )

    if not tenant_id:
        logger.warning("stripe_checkout_no_tenant_id")
        return

    tenant_id = int(tenant_id)

    # Update tenant with Stripe customer ID
    if customer_id:
        await db.execute(
            update(Tenant)
            .where(Tenant.id == tenant_id)
            .values(stripe_customer_id=customer_id)
        )

    # Sync subscription if present
    if subscription_id:
        sub = await stripe_service.get_subscription(subscription_id)
        if sub:
            await stripe_service.sync_tenant_subscription(db, tenant_id, sub)


async def handle_subscription_created(db: AsyncSession, subscription: dict):
    """
    Handle customer.subscription.created event.
    """
    customer_id = subscription.get("customer")
    subscription_id = subscription.get("id")
    metadata = subscription.get("metadata", {})
    tenant_id = metadata.get("tenant_id")

    logger.info(
        "stripe_subscription_created",
        customer_id=customer_id,
        subscription_id=subscription_id,
        tenant_id=tenant_id,
    )

    # Try to get tenant from metadata or customer ID
    if tenant_id:
        tenant_id = int(tenant_id)
    else:
        tenant = await get_tenant_by_customer_id(db, customer_id)
        if tenant:
            tenant_id = tenant.id

    if not tenant_id:
        logger.warning("stripe_subscription_no_tenant")
        return

    # Sync subscription
    sub = await stripe_service.get_subscription(subscription_id)
    if sub:
        await stripe_service.sync_tenant_subscription(db, tenant_id, sub)


async def handle_subscription_updated(db: AsyncSession, subscription: dict):
    """
    Handle customer.subscription.updated event.

    This fires when a subscription is modified (upgrade, downgrade, cancel scheduled).
    """
    customer_id = subscription.get("customer")
    subscription_id = subscription.get("id")
    subscription_status = subscription.get("status")

    logger.info(
        "stripe_subscription_updated",
        customer_id=customer_id,
        subscription_id=subscription_id,
        status=subscription_status,
    )

    # Get tenant by customer ID
    tenant = await get_tenant_by_customer_id(db, customer_id)
    if not tenant:
        logger.warning("stripe_subscription_update_no_tenant", customer_id=customer_id)
        return

    # Sync subscription
    sub = await stripe_service.get_subscription(subscription_id)
    if sub:
        await stripe_service.sync_tenant_subscription(db, tenant.id, sub)


async def handle_subscription_deleted(db: AsyncSession, subscription: dict):
    """
    Handle customer.subscription.deleted event.

    This fires when a subscription is fully canceled (not just scheduled for cancellation).
    """
    customer_id = subscription.get("customer")
    subscription_id = subscription.get("id")

    logger.info(
        "stripe_subscription_deleted",
        customer_id=customer_id,
        subscription_id=subscription_id,
    )

    # Get tenant by customer ID
    tenant = await get_tenant_by_customer_id(db, customer_id)
    if not tenant:
        logger.warning("stripe_subscription_delete_no_tenant", customer_id=customer_id)
        return

    # Get the ended date from subscription
    ended_at = subscription.get("ended_at")
    ended_datetime = (
        datetime.fromtimestamp(ended_at, tz=UTC) if ended_at else datetime.now(UTC)
    )

    # Update tenant to free plan with expiry
    await db.execute(
        update(Tenant)
        .where(Tenant.id == tenant.id)
        .values(
            plan="free",
            plan_expires_at=ended_datetime,
        )
    )

    logger.info(
        "tenant_subscription_ended",
        tenant_id=tenant.id,
        ended_at=ended_datetime.isoformat(),
    )


async def handle_invoice_paid(db: AsyncSession, invoice: dict):
    """
    Handle invoice.paid event.

    This confirms a successful payment and extends the subscription.
    """
    customer_id = invoice.get("customer")
    subscription_id = invoice.get("subscription")
    amount_paid = invoice.get("amount_paid", 0)

    logger.info(
        "stripe_invoice_paid",
        customer_id=customer_id,
        subscription_id=subscription_id,
        amount_paid=amount_paid,
    )

    if not subscription_id:
        # One-time payment, not subscription
        return

    # Get tenant by customer ID
    tenant = await get_tenant_by_customer_id(db, customer_id)
    if not tenant:
        logger.warning("stripe_invoice_paid_no_tenant", customer_id=customer_id)
        return

    # Sync subscription to update period end
    sub = await stripe_service.get_subscription(subscription_id)
    if sub:
        await stripe_service.sync_tenant_subscription(db, tenant.id, sub)


async def handle_invoice_payment_failed(db: AsyncSession, invoice: dict):
    """
    Handle invoice.payment_failed event.

    This indicates a payment failure - subscription may become past_due.
    Sends email notification to tenant admins about the failed payment.
    """
    customer_id = invoice.get("customer")
    subscription_id = invoice.get("subscription")
    attempt_count = invoice.get("attempt_count", 0)
    amount_due = invoice.get("amount_due", 0)

    logger.warning(
        "stripe_invoice_payment_failed",
        customer_id=customer_id,
        subscription_id=subscription_id,
        attempt_count=attempt_count,
    )

    # Get tenant by customer ID
    tenant = await get_tenant_by_customer_id(db, customer_id)
    if not tenant:
        return

    # The subscription status will be updated by subscription.updated event
    # Send email notification about failed payment to tenant admins

    # Format amount (Stripe uses cents)
    amount_str = None
    if amount_due:
        currency = invoice.get("currency", "usd").upper()
        amount_str = f"${amount_due / 100:.2f} {currency}"

    # Get tenant admin users to notify
    from app.models import UserRole

    result = await db.execute(
        select(User).where(
            User.tenant_id == tenant.id,
            User.role == UserRole.ADMIN,
            User.is_active == True,
            User.is_deleted == False,
        )
    )
    admin_users = result.scalars().all()

    # Send notification email to each admin
    email_service = get_email_service()
    for user in admin_users:
        try:
            email = decrypt_pii(user.email, user.tenant_id) if user.email else None
            full_name = (
                decrypt_pii(user.full_name, user.tenant_id) if user.full_name else None
            )

            if email:
                email_service.send_payment_failed_email(
                    to_email=email,
                    user_name=full_name,
                    attempt_count=attempt_count,
                    amount_due=amount_str,
                )
                logger.info(
                    "payment_failed_email_sent",
                    tenant_id=tenant.id,
                    user_id=user.id,
                    attempt_count=attempt_count,
                )
        except (ConnectionError, TimeoutError, OSError, ValueError) as e:
            logger.error(
                "payment_failed_email_error",
                tenant_id=tenant.id,
                user_id=user.id,
                error=str(e),
            )


async def handle_customer_created(db: AsyncSession, customer: dict):
    """
    Handle customer.created event.

    This fires when a new customer is created in Stripe.
    """
    customer_id = customer.get("id")
    email = customer.get("email")
    metadata = customer.get("metadata", {})
    tenant_id = metadata.get("tenant_id")

    logger.info(
        "stripe_customer_created",
        customer_id=customer_id,
        email=mask_email(email),
        tenant_id=tenant_id,
    )

    # If we have tenant_id in metadata, update the tenant
    if tenant_id:
        tenant_id = int(tenant_id)
        await db.execute(
            update(Tenant)
            .where(Tenant.id == tenant_id)
            .values(stripe_customer_id=customer_id)
        )
