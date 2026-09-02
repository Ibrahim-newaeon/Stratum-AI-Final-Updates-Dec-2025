# =============================================================================
# Stratum AI - Payment API Endpoints
# =============================================================================
"""
API endpoints for Stripe payment processing and subscription management.

Endpoints:
- POST /payments/checkout - Create checkout session
- POST /payments/portal - Create customer portal session
- GET /payments/subscription - Get current subscription
- POST /payments/subscription/upgrade - Upgrade subscription tier
- POST /payments/subscription/cancel - Cancel subscription
- POST /payments/subscription/reactivate - Reactivate canceled subscription
- GET /payments/invoices - Get invoice history
- GET /payments/payment-methods - Get payment methods
- POST /payments/webhook - Stripe webhook handler
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.permissions import Permission, require_permissions
from app.base_models import Tenant
from app.core.config import settings
from app.core.logging import get_logger
from app.core.tiers import TIER_PRICING, SubscriptionTier
from app.db.session import get_async_session
from app.services.payment_gateway import get_gateway as _gateway
from app.services.payment_gateway import get_tenant_customer_id as _customer_id

logger = get_logger(__name__)
router = APIRouter(prefix="/payments", tags=["payments"])


# =============================================================================
# Request/Response Models
# =============================================================================


class CreateCheckoutRequest(BaseModel):
    """Request to create a checkout session."""

    tier: str = Field(
        ..., description="Subscription tier: starter, professional, or enterprise"
    )
    success_url: str = Field(..., description="URL to redirect on successful payment")
    cancel_url: str = Field(..., description="URL to redirect on canceled payment")

    # trial_days was a request field — `Field(default=14, ge=0, le=30)`. The
    # caller picked its own trial length, and nothing recorded that a tenant
    # had already had one, so cancel/resubscribe granted another 30 days
    # indefinitely. Length is now a server constant and eligibility is decided
    # from the tenant row; see TRIAL_PERIOD_DAYS and _trial_days_for_tenant.


class CreateCheckoutResponse(BaseModel):
    """Response with checkout session URL."""

    checkout_url: str
    session_id: str
    expires_at: str


class CreatePortalRequest(BaseModel):
    """Request to create a customer portal session."""

    return_url: str = Field(..., description="URL to return after portal session")


class CreatePortalResponse(BaseModel):
    """Response with portal URL."""

    portal_url: str


class SubscriptionResponse(BaseModel):
    """Current subscription information."""

    has_subscription: bool
    subscription_id: Optional[str] = None
    status: Optional[str] = None
    tier: Optional[str] = None
    current_period_start: Optional[str] = None
    current_period_end: Optional[str] = None
    cancel_at_period_end: bool = False
    trial_end: Optional[str] = None


class UpgradeRequest(BaseModel):
    """Request to upgrade subscription."""

    new_tier: str = Field(..., description="New tier to upgrade to")
    prorate: bool = Field(default=True, description="Prorate the charge")


class InvoiceResponse(BaseModel):
    """Invoice information."""

    id: str
    number: str
    status: str
    amount_due: int
    amount_paid: int
    currency: str
    created: str
    due_date: Optional[str]
    hosted_invoice_url: Optional[str]
    pdf_url: Optional[str]


class PaymentMethodResponse(BaseModel):
    """Payment method information."""

    id: str
    type: str
    brand: str
    last4: str
    exp_month: int
    exp_year: int
    is_default: bool


class BillingOverviewResponse(BaseModel):
    """Complete billing overview."""

    # `stripe_configured` predates Paddle and is what the frontend currently
    # reads to decide whether billing is available at all. It is kept, and now
    # reports whether the *active* gateway is configured, so existing clients
    # keep working through the switch. New clients should read `configured`
    # and `gateway`; `stripe_configured` can be dropped once they do.
    stripe_configured: bool
    gateway: str
    configured: bool
    has_customer: bool
    customer_id: Optional[str]
    subscription: Optional[SubscriptionResponse]
    upcoming_invoice: Optional[InvoiceResponse]
    payment_methods: list[PaymentMethodResponse]
    available_tiers: list[dict]


# =============================================================================
# Helper Functions
# =============================================================================


async def get_tenant_from_request(request: Request, db: AsyncSession) -> Tenant:
    """Get the authenticated tenant from request."""
    tenant_id = getattr(request.state, "tenant_id", None)

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()

    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    return tenant


# One trial per tenant, fixed length. Registration already grants exactly this
# (auth.py sets trial_ends_at = now + 14 days on signup), so for any tenant that
# arrived through signup the answer here is zero — checkout was handing out a
# *second* trial on top of the one they already had.
TRIAL_PERIOD_DAYS = 14


def _trial_days_for_tenant(tenant: Tenant) -> int:
    """Trial length to request from Stripe for this tenant.

    trial_ends_at is the record of a trial having been granted; it is never
    cleared, so it stays truthy after the trial ends. That is what makes
    cancel-and-resubscribe stop working: the row still says a trial was used.
    """
    return 0 if tenant.trial_ends_at is not None else TRIAL_PERIOD_DAYS


def validate_tier(tier_str: str) -> SubscriptionTier:
    """Validate and convert tier string to enum."""
    try:
        return SubscriptionTier(tier_str.lower())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid tier: {tier_str}. Must be starter, professional, or enterprise.",
        )


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/overview", response_model=BillingOverviewResponse)
async def get_billing_overview(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(require_permissions([Permission.BILLING_READ])),
):
    """
    Get complete billing overview for the current tenant.

    Includes subscription status, payment methods, upcoming invoice, and available tiers.
    """
    if not _gateway().CONFIGURED:
        return BillingOverviewResponse(
            stripe_configured=False,
            gateway=_gateway().GATEWAY_NAME,
            configured=False,
            has_customer=False,
            customer_id=None,
            subscription=None,
            upcoming_invoice=None,
            payment_methods=[],
            available_tiers=list(TIER_PRICING.values()),
        )

    tenant = await get_tenant_from_request(request, db)

    # Get customer info
    customer_id = _customer_id(tenant)
    has_customer = bool(customer_id)

    subscription = None
    upcoming_invoice = None
    payment_methods = []

    if customer_id:
        # Get subscription
        subscriptions = await _gateway().get_customer_subscriptions(customer_id)
        active_sub = next(
            (
                s
                for s in subscriptions
                if s.status.value in ["active", "trialing", "past_due"]
            ),
            None,
        )

        if active_sub:
            subscription = SubscriptionResponse(
                has_subscription=True,
                subscription_id=active_sub.id,
                status=active_sub.status.value,
                tier=active_sub.tier.value,
                current_period_start=active_sub.current_period_start.isoformat(),
                current_period_end=active_sub.current_period_end.isoformat(),
                cancel_at_period_end=active_sub.cancel_at_period_end,
                trial_end=(
                    active_sub.trial_end.isoformat() if active_sub.trial_end else None
                ),
            )

        # Get upcoming invoice
        inv = await _gateway().get_upcoming_invoice(customer_id)
        if inv:
            upcoming_invoice = InvoiceResponse(
                id=inv.id,
                number=inv.number,
                status=inv.status,
                amount_due=inv.amount_due,
                amount_paid=inv.amount_paid,
                currency=inv.currency,
                created=inv.created.isoformat(),
                due_date=inv.due_date.isoformat() if inv.due_date else None,
                hosted_invoice_url=inv.hosted_invoice_url,
                pdf_url=inv.pdf_url,
            )

        # Get payment methods
        methods = await _gateway().get_customer_payment_methods(customer_id)
        payment_methods = [PaymentMethodResponse(**m) for m in methods]

    return BillingOverviewResponse(
        stripe_configured=True,
        gateway=_gateway().GATEWAY_NAME,
        configured=True,
        has_customer=has_customer,
        customer_id=customer_id,
        subscription=subscription or SubscriptionResponse(has_subscription=False),
        upcoming_invoice=upcoming_invoice,
        payment_methods=payment_methods,
        available_tiers=[
            {"tier": tier.value, **pricing} for tier, pricing in TIER_PRICING.items()
        ],
    )


@router.post("/checkout", response_model=CreateCheckoutResponse)
async def create_checkout(
    body: CreateCheckoutRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(require_permissions([Permission.BILLING_WRITE])),
):
    """
    Create a Stripe Checkout session for subscribing to a plan.

    Returns a checkout URL that the user should be redirected to.
    """
    if not _gateway().CONFIGURED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment processing is not configured",
        )

    tenant = await get_tenant_from_request(request, db)
    tier = validate_tier(body.tier)

    # Get or create Stripe customer
    customer_id = _customer_id(tenant)

    if not customer_id:
        # Get user email for customer creation
        from app.base_models import User

        result = await db.execute(
            select(User)
            .where(
                User.tenant_id == tenant.id,
                User.role.in_(["admin", "owner", "superadmin"]),
                User.is_deleted == False,
            )
            .limit(1)
        )
        admin_user = result.scalar_one_or_none()

        if admin_user:
            from app.core.security import decrypt_pii

            email = decrypt_pii(admin_user.email, admin_user.tenant_id)
            customer = await _gateway().create_customer(
                email=email,
                name=tenant.name,
                tenant_id=tenant.id,
            )
            customer_id = customer.id

            # Save customer ID to tenant
            await _gateway().sync_tenant_customer(db, tenant.id, customer_id)

    trial_days = _trial_days_for_tenant(tenant)

    # Claim the trial before Stripe is asked for one, and in the same request
    # that asks. Recording it afterwards — or on the webhook — would let two
    # concurrent checkouts each see an unused trial and both be granted one.
    if trial_days:
        await db.execute(
            update(Tenant)
            .where(Tenant.id == tenant.id, Tenant.trial_ends_at.is_(None))
            .values(
                trial_ends_at=datetime.now(timezone.utc) + timedelta(days=trial_days)
            )
        )
        await db.commit()

    logger.info(
        "checkout_session_requested",
        tenant_id=tenant.id,
        tier=tier.value,
        trial_days=trial_days,
    )

    # Create checkout session
    session = await _gateway().create_checkout_session(
        customer_id=customer_id,
        tier=tier,
        success_url=body.success_url,
        cancel_url=body.cancel_url,
        tenant_id=tenant.id,
        trial_days=trial_days,
    )

    return CreateCheckoutResponse(
        checkout_url=session.url,
        session_id=session.id,
        expires_at=session.expires_at.isoformat(),
    )


@router.post("/portal", response_model=CreatePortalResponse)
async def create_portal_session(
    body: CreatePortalRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(require_permissions([Permission.BILLING_WRITE])),
):
    """
    Create a Stripe Customer Portal session.

    Allows customers to manage their subscription, update payment methods,
    view invoices, and cancel subscription.
    """
    if not _gateway().CONFIGURED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment processing is not configured",
        )

    tenant = await get_tenant_from_request(request, db)

    if not _customer_id(tenant):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No billing account found. Please subscribe to a plan first.",
        )

    portal_url = await _gateway().create_portal_session(
        customer_id=_customer_id(tenant),
        return_url=body.return_url,
    )

    return CreatePortalResponse(portal_url=portal_url)


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(require_permissions([Permission.BILLING_READ])),
):
    """
    Get current subscription status for the tenant.
    """
    if not _gateway().CONFIGURED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment processing is not configured",
        )

    tenant = await get_tenant_from_request(request, db)

    if not _customer_id(tenant):
        return SubscriptionResponse(has_subscription=False)

    subscriptions = await _gateway().get_customer_subscriptions(_customer_id(tenant))
    active_sub = next(
        (
            s
            for s in subscriptions
            if s.status.value in ["active", "trialing", "past_due"]
        ),
        None,
    )

    if not active_sub:
        return SubscriptionResponse(has_subscription=False)

    return SubscriptionResponse(
        has_subscription=True,
        subscription_id=active_sub.id,
        status=active_sub.status.value,
        tier=active_sub.tier.value,
        current_period_start=active_sub.current_period_start.isoformat(),
        current_period_end=active_sub.current_period_end.isoformat(),
        cancel_at_period_end=active_sub.cancel_at_period_end,
        trial_end=active_sub.trial_end.isoformat() if active_sub.trial_end else None,
    )


@router.post("/subscription/upgrade", response_model=SubscriptionResponse)
async def upgrade_subscription(
    body: UpgradeRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(require_permissions([Permission.BILLING_WRITE])),
):
    """
    Upgrade or downgrade subscription to a different tier.

    Prorates charges by default.
    """
    if not _gateway().CONFIGURED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment processing is not configured",
        )

    tenant = await get_tenant_from_request(request, db)
    new_tier = validate_tier(body.new_tier)

    if not _customer_id(tenant):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No billing account found. Please subscribe to a plan first.",
        )

    # Get current subscription
    subscriptions = await _gateway().get_customer_subscriptions(_customer_id(tenant))
    active_sub = next(
        (s for s in subscriptions if s.status.value in ["active", "trialing"]), None
    )

    if not active_sub:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription to upgrade.",
        )

    # Upgrade subscription
    updated_sub = await _gateway().update_subscription_tier(
        subscription_id=active_sub.id,
        new_tier=new_tier,
        prorate=body.prorate,
    )

    # Sync to tenant record
    # sync_tenant_subscription only issues the UPDATE; the caller commits.
    # There is no webhook wrapper on this path to do it.
    await _gateway().sync_tenant_subscription(db, tenant.id, updated_sub)
    await db.commit()

    return SubscriptionResponse(
        has_subscription=True,
        subscription_id=updated_sub.id,
        status=updated_sub.status.value,
        tier=updated_sub.tier.value,
        current_period_start=updated_sub.current_period_start.isoformat(),
        current_period_end=updated_sub.current_period_end.isoformat(),
        cancel_at_period_end=updated_sub.cancel_at_period_end,
        trial_end=updated_sub.trial_end.isoformat() if updated_sub.trial_end else None,
    )


@router.post("/subscription/cancel", response_model=SubscriptionResponse)
async def cancel_subscription(
    request: Request,
    at_period_end: bool = True,
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(require_permissions([Permission.BILLING_WRITE])),
):
    """
    Cancel subscription.

    By default, cancels at the end of the billing period to allow continued
    access until the subscription expires.
    """
    if not _gateway().CONFIGURED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment processing is not configured",
        )

    tenant = await get_tenant_from_request(request, db)

    if not _customer_id(tenant):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No billing account found.",
        )

    # Get current subscription
    subscriptions = await _gateway().get_customer_subscriptions(_customer_id(tenant))
    active_sub = next(
        (s for s in subscriptions if s.status.value in ["active", "trialing"]), None
    )

    if not active_sub:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription to cancel.",
        )

    # Cancel subscription
    canceled_sub = await _gateway().cancel_subscription(
        subscription_id=active_sub.id,
        at_period_end=at_period_end,
    )

    # Sync to tenant record
    # sync_tenant_subscription only issues the UPDATE; the caller commits.
    # There is no webhook wrapper on this path to do it.
    await _gateway().sync_tenant_subscription(db, tenant.id, canceled_sub)
    await db.commit()

    return SubscriptionResponse(
        has_subscription=True,
        subscription_id=canceled_sub.id,
        status=canceled_sub.status.value,
        tier=canceled_sub.tier.value,
        current_period_start=canceled_sub.current_period_start.isoformat(),
        current_period_end=canceled_sub.current_period_end.isoformat(),
        cancel_at_period_end=canceled_sub.cancel_at_period_end,
        trial_end=(
            canceled_sub.trial_end.isoformat() if canceled_sub.trial_end else None
        ),
    )


@router.post("/subscription/reactivate", response_model=SubscriptionResponse)
async def reactivate_subscription(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(require_permissions([Permission.BILLING_WRITE])),
):
    """
    Reactivate a subscription that was scheduled for cancellation.
    """
    if not _gateway().CONFIGURED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment processing is not configured",
        )

    tenant = await get_tenant_from_request(request, db)

    if not _customer_id(tenant):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No billing account found.",
        )

    # Get subscription scheduled for cancellation
    subscriptions = await _gateway().get_customer_subscriptions(_customer_id(tenant))
    sub_to_reactivate = next(
        (
            s
            for s in subscriptions
            if s.status.value == "active" and s.cancel_at_period_end
        ),
        None,
    )

    if not sub_to_reactivate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No subscription scheduled for cancellation to reactivate.",
        )

    # Reactivate subscription
    reactivated_sub = await _gateway().reactivate_subscription(sub_to_reactivate.id)

    # Sync to tenant record
    # sync_tenant_subscription only issues the UPDATE; the caller commits.
    # There is no webhook wrapper on this path to do it.
    await _gateway().sync_tenant_subscription(db, tenant.id, reactivated_sub)
    await db.commit()

    return SubscriptionResponse(
        has_subscription=True,
        subscription_id=reactivated_sub.id,
        status=reactivated_sub.status.value,
        tier=reactivated_sub.tier.value,
        current_period_start=reactivated_sub.current_period_start.isoformat(),
        current_period_end=reactivated_sub.current_period_end.isoformat(),
        cancel_at_period_end=reactivated_sub.cancel_at_period_end,
        trial_end=(
            reactivated_sub.trial_end.isoformat() if reactivated_sub.trial_end else None
        ),
    )


@router.get("/invoices", response_model=list[InvoiceResponse])
async def get_invoices(
    request: Request,
    limit: int = 10,
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(require_permissions([Permission.BILLING_READ])),
):
    """
    Get invoice history for the tenant.
    """
    if not _gateway().CONFIGURED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment processing is not configured",
        )

    tenant = await get_tenant_from_request(request, db)

    if not _customer_id(tenant):
        return []

    invoices = await _gateway().get_customer_invoices(
        customer_id=_customer_id(tenant),
        limit=min(limit, 100),
    )

    return [
        InvoiceResponse(
            id=inv.id,
            number=inv.number,
            status=inv.status,
            amount_due=inv.amount_due,
            amount_paid=inv.amount_paid,
            currency=inv.currency,
            created=inv.created.isoformat(),
            due_date=inv.due_date.isoformat() if inv.due_date else None,
            hosted_invoice_url=inv.hosted_invoice_url,
            pdf_url=inv.pdf_url,
        )
        for inv in invoices
    ]


@router.get("/payment-methods", response_model=list[PaymentMethodResponse])
async def get_payment_methods(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(require_permissions([Permission.BILLING_READ])),
):
    """
    Get payment methods for the tenant.
    """
    if not _gateway().CONFIGURED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment processing is not configured",
        )

    tenant = await get_tenant_from_request(request, db)

    if not _customer_id(tenant):
        return []

    methods = await _gateway().get_customer_payment_methods(_customer_id(tenant))

    return [PaymentMethodResponse(**m) for m in methods]


@router.get("/config")
async def get_payment_config():
    """
    Get public payment configuration.

    Returns the active gateway's public client token and available tiers.

    `publishable_key` carries whichever public token the active gateway uses —
    Stripe's publishable key or Paddle's client-side token — because that is the
    field the frontend already reads. Both are safe to expose to the browser by
    design. `client_token` is the unambiguous name for new clients.
    """
    gateway = _gateway()
    public_token = (
        settings.paddle_client_token
        if gateway.GATEWAY_NAME == "paddle"
        else settings.stripe_publishable_key
    )
    return {
        "stripe_configured": gateway.CONFIGURED,
        "gateway": gateway.GATEWAY_NAME,
        "configured": gateway.CONFIGURED,
        "environment": (
            settings.paddle_environment if gateway.GATEWAY_NAME == "paddle" else None
        ),
        "publishable_key": public_token,
        "client_token": public_token,
        "tiers": [
            {"tier": tier.value, **pricing} for tier, pricing in TIER_PRICING.items()
        ],
    }
