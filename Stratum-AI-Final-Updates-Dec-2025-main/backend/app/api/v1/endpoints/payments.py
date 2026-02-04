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

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base_models import Tenant
from app.core.config import settings
from app.core.logging import get_logger
from app.core.tiers import TIER_PRICING, SubscriptionTier
from app.db.session import get_async_session
from app.services import stripe_service

logger = get_logger(__name__)
router = APIRouter(prefix="/payments", tags=["payments"])


# =============================================================================
# Request/Response Models
# =============================================================================


class CreateCheckoutRequest(BaseModel):
    """Request to create a checkout session."""

    tier: str = Field(..., description="Subscription tier: starter, professional, or enterprise")
    success_url: str = Field(..., description="URL to redirect on successful payment")
    cancel_url: str = Field(..., description="URL to redirect on canceled payment")
    trial_days: int = Field(default=14, ge=0, le=30, description="Trial period in days")


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
    subscription_id: Optional[str]
    status: Optional[str]
    tier: Optional[str]
    current_period_start: Optional[str]
    current_period_end: Optional[str]
    cancel_at_period_end: bool = False
    trial_end: Optional[str]


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

    stripe_configured: bool
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
):
    """
    Get complete billing overview for the current tenant.

    Includes subscription status, payment methods, upcoming invoice, and available tiers.
    """
    if not stripe_service.STRIPE_CONFIGURED:
        return BillingOverviewResponse(
            stripe_configured=False,
            has_customer=False,
            customer_id=None,
            subscription=None,
            upcoming_invoice=None,
            payment_methods=[],
            available_tiers=list(TIER_PRICING.values()),
        )

    tenant = await get_tenant_from_request(request, db)

    # Get customer info
    customer_id = tenant.stripe_customer_id
    has_customer = bool(customer_id)

    subscription = None
    upcoming_invoice = None
    payment_methods = []

    if customer_id:
        # Get subscription
        subscriptions = await stripe_service.get_customer_subscriptions(customer_id)
        active_sub = next(
            (s for s in subscriptions if s.status.value in ["active", "trialing", "past_due"]), None
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
                trial_end=active_sub.trial_end.isoformat() if active_sub.trial_end else None,
            )

        # Get upcoming invoice
        inv = await stripe_service.get_upcoming_invoice(customer_id)
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
        methods = await stripe_service.get_customer_payment_methods(customer_id)
        payment_methods = [PaymentMethodResponse(**m) for m in methods]

    return BillingOverviewResponse(
        stripe_configured=True,
        has_customer=has_customer,
        customer_id=customer_id,
        subscription=subscription or SubscriptionResponse(has_subscription=False),
        upcoming_invoice=upcoming_invoice,
        payment_methods=payment_methods,
        available_tiers=[{"tier": tier.value, **pricing} for tier, pricing in TIER_PRICING.items()],
    )


@router.post("/checkout", response_model=CreateCheckoutResponse)
async def create_checkout(
    body: CreateCheckoutRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Create a Stripe Checkout session for subscribing to a plan.

    Returns a checkout URL that the user should be redirected to.
    """
    if not stripe_service.STRIPE_CONFIGURED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment processing is not configured",
        )

    tenant = await get_tenant_from_request(request, db)
    tier = validate_tier(body.tier)

    # Get or create Stripe customer
    customer_id = tenant.stripe_customer_id

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

            email = decrypt_pii(admin_user.email)
            customer = await stripe_service.create_customer(
                email=email,
                name=tenant.name,
                tenant_id=tenant.id,
            )
            customer_id = customer.id

            # Save customer ID to tenant
            await stripe_service.sync_tenant_stripe_customer(db, tenant.id, customer_id)

    # Create checkout session
    session = await stripe_service.create_checkout_session(
        customer_id=customer_id,
        tier=tier,
        success_url=body.success_url,
        cancel_url=body.cancel_url,
        tenant_id=tenant.id,
        trial_days=body.trial_days,
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
):
    """
    Create a Stripe Customer Portal session.

    Allows customers to manage their subscription, update payment methods,
    view invoices, and cancel subscription.
    """
    if not stripe_service.STRIPE_CONFIGURED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment processing is not configured",
        )

    tenant = await get_tenant_from_request(request, db)

    if not tenant.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No billing account found. Please subscribe to a plan first.",
        )

    portal_url = await stripe_service.create_portal_session(
        customer_id=tenant.stripe_customer_id,
        return_url=body.return_url,
    )

    return CreatePortalResponse(portal_url=portal_url)


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get current subscription status for the tenant.
    """
    if not stripe_service.STRIPE_CONFIGURED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment processing is not configured",
        )

    tenant = await get_tenant_from_request(request, db)

    if not tenant.stripe_customer_id:
        return SubscriptionResponse(has_subscription=False)

    subscriptions = await stripe_service.get_customer_subscriptions(tenant.stripe_customer_id)
    active_sub = next(
        (s for s in subscriptions if s.status.value in ["active", "trialing", "past_due"]), None
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
):
    """
    Upgrade or downgrade subscription to a different tier.

    Prorates charges by default.
    """
    if not stripe_service.STRIPE_CONFIGURED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment processing is not configured",
        )

    tenant = await get_tenant_from_request(request, db)
    new_tier = validate_tier(body.new_tier)

    if not tenant.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No billing account found. Please subscribe to a plan first.",
        )

    # Get current subscription
    subscriptions = await stripe_service.get_customer_subscriptions(tenant.stripe_customer_id)
    active_sub = next((s for s in subscriptions if s.status.value in ["active", "trialing"]), None)

    if not active_sub:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription to upgrade.",
        )

    # Upgrade subscription
    updated_sub = await stripe_service.update_subscription_tier(
        subscription_id=active_sub.id,
        new_tier=new_tier,
        prorate=body.prorate,
    )

    # Sync to tenant record
    await stripe_service.sync_tenant_subscription(db, tenant.id, updated_sub)

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
):
    """
    Cancel subscription.

    By default, cancels at the end of the billing period to allow continued
    access until the subscription expires.
    """
    if not stripe_service.STRIPE_CONFIGURED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment processing is not configured",
        )

    tenant = await get_tenant_from_request(request, db)

    if not tenant.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No billing account found.",
        )

    # Get current subscription
    subscriptions = await stripe_service.get_customer_subscriptions(tenant.stripe_customer_id)
    active_sub = next((s for s in subscriptions if s.status.value in ["active", "trialing"]), None)

    if not active_sub:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscription to cancel.",
        )

    # Cancel subscription
    canceled_sub = await stripe_service.cancel_subscription(
        subscription_id=active_sub.id,
        at_period_end=at_period_end,
    )

    # Sync to tenant record
    await stripe_service.sync_tenant_subscription(db, tenant.id, canceled_sub)

    return SubscriptionResponse(
        has_subscription=True,
        subscription_id=canceled_sub.id,
        status=canceled_sub.status.value,
        tier=canceled_sub.tier.value,
        current_period_start=canceled_sub.current_period_start.isoformat(),
        current_period_end=canceled_sub.current_period_end.isoformat(),
        cancel_at_period_end=canceled_sub.cancel_at_period_end,
        trial_end=canceled_sub.trial_end.isoformat() if canceled_sub.trial_end else None,
    )


@router.post("/subscription/reactivate", response_model=SubscriptionResponse)
async def reactivate_subscription(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Reactivate a subscription that was scheduled for cancellation.
    """
    if not stripe_service.STRIPE_CONFIGURED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment processing is not configured",
        )

    tenant = await get_tenant_from_request(request, db)

    if not tenant.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No billing account found.",
        )

    # Get subscription scheduled for cancellation
    subscriptions = await stripe_service.get_customer_subscriptions(tenant.stripe_customer_id)
    sub_to_reactivate = next(
        (s for s in subscriptions if s.status.value == "active" and s.cancel_at_period_end), None
    )

    if not sub_to_reactivate:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No subscription scheduled for cancellation to reactivate.",
        )

    # Reactivate subscription
    reactivated_sub = await stripe_service.reactivate_subscription(sub_to_reactivate.id)

    # Sync to tenant record
    await stripe_service.sync_tenant_subscription(db, tenant.id, reactivated_sub)

    return SubscriptionResponse(
        has_subscription=True,
        subscription_id=reactivated_sub.id,
        status=reactivated_sub.status.value,
        tier=reactivated_sub.tier.value,
        current_period_start=reactivated_sub.current_period_start.isoformat(),
        current_period_end=reactivated_sub.current_period_end.isoformat(),
        cancel_at_period_end=reactivated_sub.cancel_at_period_end,
        trial_end=reactivated_sub.trial_end.isoformat() if reactivated_sub.trial_end else None,
    )


@router.get("/invoices", response_model=list[InvoiceResponse])
async def get_invoices(
    request: Request,
    limit: int = 10,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get invoice history for the tenant.
    """
    if not stripe_service.STRIPE_CONFIGURED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment processing is not configured",
        )

    tenant = await get_tenant_from_request(request, db)

    if not tenant.stripe_customer_id:
        return []

    invoices = await stripe_service.get_customer_invoices(
        customer_id=tenant.stripe_customer_id,
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
):
    """
    Get payment methods for the tenant.
    """
    if not stripe_service.STRIPE_CONFIGURED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Payment processing is not configured",
        )

    tenant = await get_tenant_from_request(request, db)

    if not tenant.stripe_customer_id:
        return []

    methods = await stripe_service.get_customer_payment_methods(tenant.stripe_customer_id)

    return [PaymentMethodResponse(**m) for m in methods]


@router.get("/config")
async def get_payment_config():
    """
    Get public payment configuration.

    Returns Stripe publishable key and available tiers.
    """
    return {
        "stripe_configured": stripe_service.STRIPE_CONFIGURED,
        "publishable_key": settings.stripe_publishable_key,
        "tiers": [{"tier": tier.value, **pricing} for tier, pricing in TIER_PRICING.items()],
    }
