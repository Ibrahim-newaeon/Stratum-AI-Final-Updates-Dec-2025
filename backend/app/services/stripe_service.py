# =============================================================================
# Stratum AI - Stripe Payment Service
# =============================================================================
"""
Stripe integration for subscription billing and payment processing.

Features:
- Customer management (create, update, retrieve)
- Subscription management (create, update, cancel)
- Checkout session creation
- Payment method management
- Invoice retrieval
- Webhook event handling
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any

import stripe
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.tiers import SubscriptionTier

logger = get_logger(__name__)


# =============================================================================
# Configuration
# =============================================================================

def configure_stripe() -> bool:
    """
    Configure Stripe SDK with API key.

    Returns:
        True if configured successfully, False otherwise
    """
    if not settings.stripe_secret_key:
        logger.warning("stripe_not_configured", message="STRIPE_SECRET_KEY not set")
        return False

    stripe.api_key = settings.stripe_secret_key
    stripe.api_version = "2024-12-18.acacia"  # Use latest stable API version
    return True


# Initialize on module load
STRIPE_CONFIGURED = configure_stripe()


# =============================================================================
# Data Models
# =============================================================================

class PaymentStatus(str, Enum):
    """Payment status types."""
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    REFUNDED = "refunded"


class SubscriptionState(str, Enum):
    """Stripe subscription states."""
    ACTIVE = "active"
    PAST_DUE = "past_due"
    UNPAID = "unpaid"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    TRIALING = "trialing"
    PAUSED = "paused"


@dataclass
class StripeCustomer:
    """Stripe customer data."""
    id: str
    email: str
    name: Optional[str]
    metadata: Dict[str, Any]


@dataclass
class StripeSubscription:
    """Stripe subscription data."""
    id: str
    customer_id: str
    status: SubscriptionState
    tier: SubscriptionTier
    price_id: str
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    canceled_at: Optional[datetime]
    trial_end: Optional[datetime]


@dataclass
class CheckoutSession:
    """Checkout session data."""
    id: str
    url: str
    customer_id: Optional[str]
    subscription_id: Optional[str]
    expires_at: datetime


@dataclass
class Invoice:
    """Invoice data."""
    id: str
    number: str
    status: str
    amount_due: int
    amount_paid: int
    currency: str
    created: datetime
    due_date: Optional[datetime]
    hosted_invoice_url: Optional[str]
    pdf_url: Optional[str]


# =============================================================================
# Price ID Mapping
# =============================================================================

def get_price_id_for_tier(tier: SubscriptionTier) -> Optional[str]:
    """Get Stripe Price ID for a subscription tier."""
    mapping = {
        SubscriptionTier.STARTER: settings.stripe_starter_price_id,
        SubscriptionTier.PROFESSIONAL: settings.stripe_professional_price_id,
        SubscriptionTier.ENTERPRISE: settings.stripe_enterprise_price_id,
    }
    return mapping.get(tier)


def get_tier_for_price_id(price_id: str) -> Optional[SubscriptionTier]:
    """Get subscription tier for a Stripe Price ID."""
    if price_id == settings.stripe_starter_price_id:
        return SubscriptionTier.STARTER
    elif price_id == settings.stripe_professional_price_id:
        return SubscriptionTier.PROFESSIONAL
    elif price_id == settings.stripe_enterprise_price_id:
        return SubscriptionTier.ENTERPRISE
    return None


# =============================================================================
# Customer Management
# =============================================================================

async def create_customer(
    email: str,
    name: Optional[str] = None,
    tenant_id: Optional[int] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> StripeCustomer:
    """
    Create a new Stripe customer.

    Args:
        email: Customer email
        name: Customer name
        tenant_id: Associated tenant ID
        metadata: Additional metadata

    Returns:
        StripeCustomer object
    """
    if not STRIPE_CONFIGURED:
        raise ValueError("Stripe is not configured")

    customer_metadata = metadata or {}
    if tenant_id:
        customer_metadata["tenant_id"] = str(tenant_id)

    try:
        customer = stripe.Customer.create(
            email=email,
            name=name,
            metadata=customer_metadata,
        )

        logger.info(
            "stripe_customer_created",
            customer_id=customer.id,
            tenant_id=tenant_id,
        )

        return StripeCustomer(
            id=customer.id,
            email=customer.email,
            name=customer.name,
            metadata=customer.metadata,
        )
    except stripe.StripeError as e:
        logger.error("stripe_customer_create_failed", error=str(e))
        raise


async def get_customer(customer_id: str) -> Optional[StripeCustomer]:
    """Retrieve a Stripe customer."""
    if not STRIPE_CONFIGURED:
        raise ValueError("Stripe is not configured")

    try:
        customer = stripe.Customer.retrieve(customer_id)

        if customer.deleted:
            return None

        return StripeCustomer(
            id=customer.id,
            email=customer.email,
            name=customer.name,
            metadata=customer.metadata or {},
        )
    except stripe.InvalidRequestError:
        return None
    except stripe.StripeError as e:
        logger.error("stripe_customer_retrieve_failed", error=str(e))
        raise


async def update_customer(
    customer_id: str,
    email: Optional[str] = None,
    name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> StripeCustomer:
    """Update a Stripe customer."""
    if not STRIPE_CONFIGURED:
        raise ValueError("Stripe is not configured")

    update_params = {}
    if email:
        update_params["email"] = email
    if name:
        update_params["name"] = name
    if metadata:
        update_params["metadata"] = metadata

    try:
        customer = stripe.Customer.modify(customer_id, **update_params)

        return StripeCustomer(
            id=customer.id,
            email=customer.email,
            name=customer.name,
            metadata=customer.metadata or {},
        )
    except stripe.StripeError as e:
        logger.error("stripe_customer_update_failed", error=str(e))
        raise


# =============================================================================
# Checkout Sessions
# =============================================================================

async def create_checkout_session(
    customer_id: Optional[str],
    tier: SubscriptionTier,
    success_url: str,
    cancel_url: str,
    tenant_id: int,
    trial_days: int = 14,
    customer_email: Optional[str] = None,
) -> CheckoutSession:
    """
    Create a Stripe Checkout session for subscription.

    Args:
        customer_id: Existing Stripe customer ID (or None for new)
        tier: Subscription tier to purchase
        success_url: URL to redirect on success
        cancel_url: URL to redirect on cancel
        tenant_id: Tenant ID for metadata
        trial_days: Free trial period (0 for no trial)
        customer_email: Email for new customers

    Returns:
        CheckoutSession with URL
    """
    if not STRIPE_CONFIGURED:
        raise ValueError("Stripe is not configured")

    price_id = get_price_id_for_tier(tier)
    if not price_id:
        raise ValueError(f"No price configured for tier: {tier}")

    session_params = {
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        "success_url": success_url,
        "cancel_url": cancel_url,
        "metadata": {
            "tenant_id": str(tenant_id),
            "tier": tier.value,
        },
        "subscription_data": {
            "metadata": {
                "tenant_id": str(tenant_id),
                "tier": tier.value,
            }
        },
        "allow_promotion_codes": True,
        "billing_address_collection": "required",
    }

    # Add trial period
    if trial_days > 0:
        session_params["subscription_data"]["trial_period_days"] = trial_days

    # Use existing customer or create new
    if customer_id:
        session_params["customer"] = customer_id
    elif customer_email:
        session_params["customer_email"] = customer_email

    try:
        session = stripe.checkout.Session.create(**session_params)

        logger.info(
            "stripe_checkout_created",
            session_id=session.id,
            tenant_id=tenant_id,
            tier=tier.value,
        )

        return CheckoutSession(
            id=session.id,
            url=session.url,
            customer_id=session.customer,
            subscription_id=session.subscription,
            expires_at=datetime.fromtimestamp(session.expires_at, tz=timezone.utc),
        )
    except stripe.StripeError as e:
        logger.error("stripe_checkout_create_failed", error=str(e))
        raise


async def create_portal_session(
    customer_id: str,
    return_url: str,
) -> str:
    """
    Create a Stripe Customer Portal session.

    Allows customers to manage their subscription, payment methods, and invoices.

    Returns:
        Portal URL
    """
    if not STRIPE_CONFIGURED:
        raise ValueError("Stripe is not configured")

    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=return_url,
        )

        logger.info("stripe_portal_created", customer_id=customer_id)

        return session.url
    except stripe.StripeError as e:
        logger.error("stripe_portal_create_failed", error=str(e))
        raise


# =============================================================================
# Subscription Management
# =============================================================================

async def get_subscription(subscription_id: str) -> Optional[StripeSubscription]:
    """Retrieve a Stripe subscription."""
    if not STRIPE_CONFIGURED:
        raise ValueError("Stripe is not configured")

    try:
        sub = stripe.Subscription.retrieve(subscription_id)

        # Get the price ID from the first item
        price_id = sub.items.data[0].price.id if sub.items.data else None
        tier = get_tier_for_price_id(price_id) if price_id else SubscriptionTier.STARTER

        return StripeSubscription(
            id=sub.id,
            customer_id=sub.customer,
            status=SubscriptionState(sub.status),
            tier=tier,
            price_id=price_id,
            current_period_start=datetime.fromtimestamp(sub.current_period_start, tz=timezone.utc),
            current_period_end=datetime.fromtimestamp(sub.current_period_end, tz=timezone.utc),
            cancel_at_period_end=sub.cancel_at_period_end,
            canceled_at=datetime.fromtimestamp(sub.canceled_at, tz=timezone.utc) if sub.canceled_at else None,
            trial_end=datetime.fromtimestamp(sub.trial_end, tz=timezone.utc) if sub.trial_end else None,
        )
    except stripe.InvalidRequestError:
        return None
    except stripe.StripeError as e:
        logger.error("stripe_subscription_retrieve_failed", error=str(e))
        raise


async def get_customer_subscriptions(customer_id: str) -> List[StripeSubscription]:
    """Get all subscriptions for a customer."""
    if not STRIPE_CONFIGURED:
        raise ValueError("Stripe is not configured")

    try:
        subscriptions = stripe.Subscription.list(
            customer=customer_id,
            status="all",
            limit=10,
        )

        result = []
        for sub in subscriptions.data:
            price_id = sub.items.data[0].price.id if sub.items.data else None
            tier = get_tier_for_price_id(price_id) if price_id else SubscriptionTier.STARTER

            result.append(StripeSubscription(
                id=sub.id,
                customer_id=sub.customer,
                status=SubscriptionState(sub.status),
                tier=tier,
                price_id=price_id,
                current_period_start=datetime.fromtimestamp(sub.current_period_start, tz=timezone.utc),
                current_period_end=datetime.fromtimestamp(sub.current_period_end, tz=timezone.utc),
                cancel_at_period_end=sub.cancel_at_period_end,
                canceled_at=datetime.fromtimestamp(sub.canceled_at, tz=timezone.utc) if sub.canceled_at else None,
                trial_end=datetime.fromtimestamp(sub.trial_end, tz=timezone.utc) if sub.trial_end else None,
            ))

        return result
    except stripe.StripeError as e:
        logger.error("stripe_subscriptions_list_failed", error=str(e))
        raise


async def update_subscription_tier(
    subscription_id: str,
    new_tier: SubscriptionTier,
    prorate: bool = True,
) -> StripeSubscription:
    """
    Update subscription to a new tier.

    Args:
        subscription_id: Stripe subscription ID
        new_tier: New tier to upgrade/downgrade to
        prorate: Whether to prorate the charge

    Returns:
        Updated StripeSubscription
    """
    if not STRIPE_CONFIGURED:
        raise ValueError("Stripe is not configured")

    new_price_id = get_price_id_for_tier(new_tier)
    if not new_price_id:
        raise ValueError(f"No price configured for tier: {new_tier}")

    try:
        # Get current subscription
        sub = stripe.Subscription.retrieve(subscription_id)

        # Update the subscription item with new price
        stripe.Subscription.modify(
            subscription_id,
            items=[{
                "id": sub.items.data[0].id,
                "price": new_price_id,
            }],
            proration_behavior="create_prorations" if prorate else "none",
            metadata={
                "tier": new_tier.value,
            },
        )

        logger.info(
            "stripe_subscription_tier_updated",
            subscription_id=subscription_id,
            new_tier=new_tier.value,
        )

        return await get_subscription(subscription_id)
    except stripe.StripeError as e:
        logger.error("stripe_subscription_update_failed", error=str(e))
        raise


async def cancel_subscription(
    subscription_id: str,
    at_period_end: bool = True,
) -> StripeSubscription:
    """
    Cancel a subscription.

    Args:
        subscription_id: Stripe subscription ID
        at_period_end: If True, cancel at end of billing period

    Returns:
        Updated StripeSubscription
    """
    if not STRIPE_CONFIGURED:
        raise ValueError("Stripe is not configured")

    try:
        if at_period_end:
            # Schedule cancellation at period end
            stripe.Subscription.modify(
                subscription_id,
                cancel_at_period_end=True,
            )
        else:
            # Cancel immediately
            stripe.Subscription.cancel(subscription_id)

        logger.info(
            "stripe_subscription_canceled",
            subscription_id=subscription_id,
            at_period_end=at_period_end,
        )

        return await get_subscription(subscription_id)
    except stripe.StripeError as e:
        logger.error("stripe_subscription_cancel_failed", error=str(e))
        raise


async def reactivate_subscription(subscription_id: str) -> StripeSubscription:
    """
    Reactivate a subscription that was scheduled for cancellation.
    """
    if not STRIPE_CONFIGURED:
        raise ValueError("Stripe is not configured")

    try:
        stripe.Subscription.modify(
            subscription_id,
            cancel_at_period_end=False,
        )

        logger.info("stripe_subscription_reactivated", subscription_id=subscription_id)

        return await get_subscription(subscription_id)
    except stripe.StripeError as e:
        logger.error("stripe_subscription_reactivate_failed", error=str(e))
        raise


# =============================================================================
# Invoice Management
# =============================================================================

async def get_customer_invoices(
    customer_id: str,
    limit: int = 10,
) -> List[Invoice]:
    """Get invoices for a customer."""
    if not STRIPE_CONFIGURED:
        raise ValueError("Stripe is not configured")

    try:
        invoices = stripe.Invoice.list(
            customer=customer_id,
            limit=limit,
        )

        result = []
        for inv in invoices.data:
            result.append(Invoice(
                id=inv.id,
                number=inv.number or "",
                status=inv.status,
                amount_due=inv.amount_due,
                amount_paid=inv.amount_paid,
                currency=inv.currency,
                created=datetime.fromtimestamp(inv.created, tz=timezone.utc),
                due_date=datetime.fromtimestamp(inv.due_date, tz=timezone.utc) if inv.due_date else None,
                hosted_invoice_url=inv.hosted_invoice_url,
                pdf_url=inv.invoice_pdf,
            ))

        return result
    except stripe.StripeError as e:
        logger.error("stripe_invoices_list_failed", error=str(e))
        raise


async def get_upcoming_invoice(customer_id: str) -> Optional[Invoice]:
    """Get the upcoming invoice for a customer."""
    if not STRIPE_CONFIGURED:
        raise ValueError("Stripe is not configured")

    try:
        inv = stripe.Invoice.upcoming(customer=customer_id)

        return Invoice(
            id="upcoming",
            number="",
            status="draft",
            amount_due=inv.amount_due,
            amount_paid=0,
            currency=inv.currency,
            created=datetime.now(timezone.utc),
            due_date=datetime.fromtimestamp(inv.next_payment_attempt, tz=timezone.utc) if inv.next_payment_attempt else None,
            hosted_invoice_url=None,
            pdf_url=None,
        )
    except stripe.InvalidRequestError:
        # No upcoming invoice
        return None
    except stripe.StripeError as e:
        logger.error("stripe_upcoming_invoice_failed", error=str(e))
        raise


# =============================================================================
# Payment Methods
# =============================================================================

async def get_customer_payment_methods(customer_id: str) -> List[Dict[str, Any]]:
    """Get payment methods for a customer."""
    if not STRIPE_CONFIGURED:
        raise ValueError("Stripe is not configured")

    try:
        methods = stripe.PaymentMethod.list(
            customer=customer_id,
            type="card",
        )

        result = []
        for pm in methods.data:
            card = pm.card
            result.append({
                "id": pm.id,
                "type": "card",
                "brand": card.brand,
                "last4": card.last4,
                "exp_month": card.exp_month,
                "exp_year": card.exp_year,
                "is_default": pm.id == (stripe.Customer.retrieve(customer_id).invoice_settings.default_payment_method),
            })

        return result
    except stripe.StripeError as e:
        logger.error("stripe_payment_methods_list_failed", error=str(e))
        raise


async def set_default_payment_method(
    customer_id: str,
    payment_method_id: str,
) -> None:
    """Set the default payment method for a customer."""
    if not STRIPE_CONFIGURED:
        raise ValueError("Stripe is not configured")

    try:
        stripe.Customer.modify(
            customer_id,
            invoice_settings={"default_payment_method": payment_method_id},
        )

        logger.info(
            "stripe_default_payment_method_set",
            customer_id=customer_id,
            payment_method_id=payment_method_id,
        )
    except stripe.StripeError as e:
        logger.error("stripe_set_default_payment_failed", error=str(e))
        raise


async def detach_payment_method(payment_method_id: str) -> None:
    """Remove a payment method from a customer."""
    if not STRIPE_CONFIGURED:
        raise ValueError("Stripe is not configured")

    try:
        stripe.PaymentMethod.detach(payment_method_id)

        logger.info("stripe_payment_method_detached", payment_method_id=payment_method_id)
    except stripe.StripeError as e:
        logger.error("stripe_detach_payment_failed", error=str(e))
        raise


# =============================================================================
# Database Sync Helpers
# =============================================================================

async def sync_tenant_subscription(
    db: AsyncSession,
    tenant_id: int,
    subscription: StripeSubscription,
) -> None:
    """
    Sync Stripe subscription data to tenant record.

    Updates the tenant's plan and plan_expires_at based on Stripe subscription.
    """
    from app.base_models import Tenant

    # Map subscription status to plan
    plan = subscription.tier.value

    # Determine expiry date
    if subscription.status in [SubscriptionState.ACTIVE, SubscriptionState.TRIALING]:
        plan_expires_at = subscription.current_period_end
    elif subscription.status == SubscriptionState.CANCELED:
        # If canceled, use the period end or canceled_at
        plan_expires_at = subscription.canceled_at or subscription.current_period_end
    else:
        # Past due, unpaid, etc. - keep current period end
        plan_expires_at = subscription.current_period_end

    # Update tenant
    await db.execute(
        update(Tenant)
        .where(Tenant.id == tenant_id)
        .values(
            plan=plan,
            plan_expires_at=plan_expires_at,
        )
    )
    await db.commit()

    logger.info(
        "tenant_subscription_synced",
        tenant_id=tenant_id,
        plan=plan,
        plan_expires_at=plan_expires_at.isoformat(),
    )


async def sync_tenant_stripe_customer(
    db: AsyncSession,
    tenant_id: int,
    customer_id: str,
) -> None:
    """Update tenant's Stripe customer ID."""
    from app.base_models import Tenant

    await db.execute(
        update(Tenant)
        .where(Tenant.id == tenant_id)
        .values(stripe_customer_id=customer_id)
    )
    await db.commit()

    logger.info(
        "tenant_stripe_customer_synced",
        tenant_id=tenant_id,
        customer_id=customer_id,
    )
