# =============================================================================
# Stratum AI - Paddle Billing Service
# =============================================================================
"""
Paddle Billing gateway.

Mirrors the public surface of ``app.services.stripe_service`` so that
``api/v1/endpoints/payments.py`` can dispatch to either module by name and the
frontend contract is unchanged. Where the two gateways genuinely differ, the
difference is documented at the call site rather than smoothed over:

* **Checkout.** Stripe creates a Checkout Session; Paddle creates a
  *transaction* and returns ``checkout.url`` on it. Both give us a URL to
  redirect to, so ``CheckoutSession`` is reused verbatim and the frontend's
  ``window.location.href = result.checkout_url`` needs no change. The URL is
  only populated once a default payment link is configured on the Paddle
  account (Checkout > Checkout settings) — see ``create_checkout_session``.

* **Trials.** Stripe takes ``trial_period_days`` per session. Paddle attaches
  the trial to the *price*, so each paid tier has two prices and we pick one.
  ``_trial_days_for_tenant`` in payments.py stays the single source of truth
  for whether a tenant gets a trial at all.

* **Invoices.** Paddle has no separate invoice object; a billed transaction is
  the invoice. ``get_customer_invoices`` projects transactions onto the same
  ``Invoice`` dataclass Stripe returns.

Amounts from Paddle are strings in the currency's lowest denomination
("49900" = $499.00). They are converted to ``int`` at the boundary here so no
caller has to know that.
"""

import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Optional

import httpx
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.tiers import SubscriptionTier

logger = get_logger(__name__)


# =============================================================================
# Configuration
# =============================================================================

_API_BASES = {
    "production": "https://api.paddle.com",
    "sandbox": "https://sandbox-api.paddle.com",
}

# Paddle's own timeout guidance for webhook consumers is 5s; for outbound calls
# we allow longer but still bound them so a Paddle incident cannot pin a worker.
_TIMEOUT = httpx.Timeout(15.0, connect=5.0)

# Paddle expires a `ready` transaction 24h after creation. Paddle returns no
# explicit expiry, so CheckoutSession.expires_at reports that window rather
# than inventing a longer one a caller might cache against.
_CHECKOUT_TTL = timedelta(hours=24)


def configure_paddle() -> bool:
    """
    Validate Paddle configuration.

    Returns:
        True if a server-side API key is present, False otherwise.
    """
    if not settings.paddle_api_key:
        logger.warning("paddle_not_configured", message="PADDLE_API_KEY not set")
        return False
    return True


PADDLE_CONFIGURED = configure_paddle()

API_BASE = _API_BASES[settings.paddle_environment]


def _checkout_page_url() -> str:
    """The page that hosts the Paddle.js checkout overlay."""
    configured = settings.paddle_checkout_url
    if configured:
        return configured.rstrip("/")
    return f"{settings.frontend_url.rstrip('/')}/checkout"


def _headers() -> dict[str, str]:
    """Auth headers for the Paddle API."""
    return {
        "Authorization": f"Bearer {settings.paddle_api_key}",
        "Content-Type": "application/json",
    }


class PaddleError(RuntimeError):
    """A Paddle API call failed.

    Carries the HTTP status and Paddle's ``error.code`` so callers can
    distinguish "customer not found" from "we are rate limited" without
    re-parsing the body.
    """

    def __init__(self, status_code: int, code: str, detail: str) -> None:
        self.status_code = status_code
        self.code = code
        self.detail = detail
        super().__init__(f"paddle {status_code} {code}: {detail}")


async def _request(
    method: str,
    path: str,
    *,
    json: Optional[dict[str, Any]] = None,
    params: Optional[dict[str, Any]] = None,
) -> Any:
    """
    Call the Paddle API and return the unwrapped ``data`` payload.

    Raises:
        PaddleError: on any non-2xx response.
    """
    url = f"{API_BASE}{path}"
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.request(
            method, url, headers=_headers(), json=json, params=params
        )

    if response.status_code >= 400:
        try:
            error = response.json().get("error", {})
        except ValueError:
            error = {}
        code = error.get("code", "unknown")
        detail = error.get("detail", response.text[:300])
        # The API key is in the request headers, never in the body or URL, so
        # logging method/path/code here cannot leak it.
        logger.error(
            "paddle_api_error",
            method=method,
            path=path,
            status_code=response.status_code,
            code=code,
        )
        raise PaddleError(response.status_code, code, detail)

    if not response.content:
        return None
    return response.json().get("data")


# =============================================================================
# Data Models
# =============================================================================
#
# Deliberately the same shapes stripe_service exposes, so payments.py can build
# its response models from either gateway without branching.


class PaymentStatus(str, Enum):
    """Payment status types."""

    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"
    REFUNDED = "refunded"


class SubscriptionState(str, Enum):
    """Paddle subscription states.

    Paddle has a smaller set than Stripe: there is no ``incomplete`` or
    ``unpaid``, because Paddle only creates the subscription once the first
    transaction completes. ``PAUSED`` has no Stripe-default equivalent.
    """

    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    PAUSED = "paused"
    CANCELED = "canceled"


# The only states that entitle a tenant to the plan they subscribed to.
# Everything absent from this set downgrades to free, so a state Paddle adds
# later fails closed rather than silently granting access.
#
# PAST_DUE is included for the same reason as in stripe_service: it means a
# payment failed and Paddle is still retrying under its dunning schedule, and
# app.core.subscription already carries GRACE_PERIOD_DAYS for that window.
# When Paddle gives up it moves the subscription to canceled, which downgrades.
#
# PAUSED is excluded: a paused subscription is not billing, so it should not
# entitle. Paddle keeps the subscription row alive across a pause, so without
# this exclusion a paused tenant would retain a paid plan indefinitely.
ENTITLING_STATES = frozenset(
    {
        SubscriptionState.ACTIVE,
        SubscriptionState.TRIALING,
        SubscriptionState.PAST_DUE,
    }
)


@dataclass
class PaddleCustomer:
    """Paddle customer data."""

    id: str
    email: str
    name: Optional[str]
    metadata: dict[str, Any]


@dataclass
class PaddleSubscription:
    """Paddle subscription data."""

    id: str
    customer_id: str
    status: SubscriptionState
    tier: Optional[SubscriptionTier]
    price_id: str
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    canceled_at: Optional[datetime]
    trial_end: Optional[datetime]


@dataclass
class CheckoutSession:
    """Checkout session data. Same shape stripe_service returns."""

    id: str
    url: str
    customer_id: Optional[str]
    subscription_id: Optional[str]
    expires_at: datetime


@dataclass
class Invoice:
    """Invoice data, projected from a Paddle transaction."""

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
# Parsing helpers
# =============================================================================


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    """Parse a Paddle RFC 3339 timestamp into an aware datetime."""
    if not value:
        return None
    # Paddle returns e.g. "2026-09-02T01:51:52.622913Z"; fromisoformat only
    # learned to accept a trailing "Z" in 3.11, and this runs on 3.12, but the
    # replace keeps it correct if the suffix is ever "+00:00" instead.
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _to_cents(amount: Optional[str]) -> int:
    """Paddle sends amounts as strings in the lowest denomination."""
    if amount is None:
        return 0
    return int(amount)


# =============================================================================
# Tier / price mapping
# =============================================================================


def get_price_id_for_tier(
    tier: SubscriptionTier, *, with_trial: bool = False
) -> Optional[str]:
    """
    Get the Paddle Price ID for a subscription tier.

    Args:
        tier: The tier being purchased.
        with_trial: Select the trial-bearing price. Paddle attaches trials to
            the price, so this is the only way to grant one.

    Returns:
        The price ID, or None when the tier has no self-serve price. Enterprise
        is contact-sales and is expected to return None.
    """
    if with_trial:
        mapping = {
            SubscriptionTier.STARTER: settings.paddle_starter_trial_price_id,
            SubscriptionTier.PROFESSIONAL: settings.paddle_professional_trial_price_id,
            # Enterprise has no trial variant; fall back to its base price so a
            # trial request never silently resolves to a *different tier*.
            SubscriptionTier.ENTERPRISE: settings.paddle_enterprise_price_id,
        }
    else:
        mapping = {
            SubscriptionTier.STARTER: settings.paddle_starter_price_id,
            SubscriptionTier.PROFESSIONAL: settings.paddle_professional_price_id,
            SubscriptionTier.ENTERPRISE: settings.paddle_enterprise_price_id,
        }
    return mapping.get(tier)


def get_tier_for_price_id(price_id: str) -> Optional[SubscriptionTier]:
    """
    Get the subscription tier for a Paddle Price ID.

    Both the base and trial price of a tier map back to that tier, so a
    subscription that started on a trial price is still recognised after the
    trial converts.
    """
    if not price_id:
        return None

    for tier, ids in (
        (
            SubscriptionTier.STARTER,
            (settings.paddle_starter_price_id, settings.paddle_starter_trial_price_id),
        ),
        (
            SubscriptionTier.PROFESSIONAL,
            (
                settings.paddle_professional_price_id,
                settings.paddle_professional_trial_price_id,
            ),
        ),
        (SubscriptionTier.ENTERPRISE, (settings.paddle_enterprise_price_id,)),
    ):
        if any(candidate and price_id == candidate for candidate in ids):
            return tier
    return None


# =============================================================================
# Customer Management
# =============================================================================


async def create_customer(
    email: str,
    name: Optional[str] = None,
    tenant_id: Optional[int] = None,
) -> PaddleCustomer:
    """
    Create a Paddle customer.

    ``tenant_id`` goes into ``custom_data`` so webhooks can resolve the tenant
    without a database lookup keyed on email — which matters because emails are
    stored encrypted (see app.core.security.encrypt_pii) and are therefore not
    queryable.

    Paddle rejects a duplicate email with ``customer_already_exists`` and puts
    the existing ID in the error detail; we recover that rather than failing,
    so a retried checkout does not dead-end.
    """
    payload: dict[str, Any] = {"email": email}
    if name:
        payload["name"] = name
    if tenant_id is not None:
        payload["custom_data"] = {"tenant_id": str(tenant_id)}

    try:
        data = await _request("POST", "/customers", json=payload)
    except PaddleError as exc:
        if exc.code != "customer_already_exists":
            raise
        existing = await _find_customer_by_email(email)
        if existing is None:
            raise
        logger.info(
            "paddle_customer_reused", tenant_id=tenant_id, customer_id=existing.id
        )
        return existing

    logger.info("paddle_customer_created", tenant_id=tenant_id, customer_id=data["id"])
    return PaddleCustomer(
        id=data["id"],
        email=data["email"],
        name=data.get("name"),
        metadata=data.get("custom_data") or {},
    )


async def _find_customer_by_email(email: str) -> Optional[PaddleCustomer]:
    """Look up a customer by exact email. Used only to recover from a duplicate."""
    data = await _request("GET", "/customers", params={"email": email, "per_page": 1})
    if not data:
        return None
    record = data[0]
    return PaddleCustomer(
        id=record["id"],
        email=record["email"],
        name=record.get("name"),
        metadata=record.get("custom_data") or {},
    )


async def get_customer(customer_id: str) -> Optional[PaddleCustomer]:
    """Get a Paddle customer by ID, or None if it does not exist."""
    try:
        data = await _request("GET", f"/customers/{customer_id}")
    except PaddleError as exc:
        if exc.status_code == 404:
            return None
        raise
    return PaddleCustomer(
        id=data["id"],
        email=data["email"],
        name=data.get("name"),
        metadata=data.get("custom_data") or {},
    )


async def update_customer(
    customer_id: str,
    email: Optional[str] = None,
    name: Optional[str] = None,
) -> PaddleCustomer:
    """Update a Paddle customer's email and/or name."""
    payload: dict[str, Any] = {}
    if email is not None:
        payload["email"] = email
    if name is not None:
        payload["name"] = name

    data = await _request("PATCH", f"/customers/{customer_id}", json=payload)
    return PaddleCustomer(
        id=data["id"],
        email=data["email"],
        name=data.get("name"),
        metadata=data.get("custom_data") or {},
    )


# =============================================================================
# Checkout
# =============================================================================


async def create_checkout_session(
    customer_id: Optional[str],
    tier: SubscriptionTier,
    success_url: str,
    cancel_url: str,
    tenant_id: int,
    trial_days: int = 0,
) -> CheckoutSession:
    """
    Create a Paddle transaction and return its hosted checkout URL.

    **The returned URL is one of our own pages, not a Paddle-hosted one.**
    Paddle has no equivalent of Stripe's hosted Checkout Session page. It takes
    ``checkout.url`` — the page that will *host* the checkout — appends
    ``?_ptxn=<transaction_id>``, and relies on Paddle.js loaded on that page to
    open the overlay. Redirecting a customer there without Paddle.js present
    shows them the bare page and no checkout.

    ``checkout.url`` therefore comes from ``settings.paddle_checkout_url``
    (default ``{frontend_url}/checkout``), NOT from ``success_url``. Passing
    ``success_url`` here — which this function originally did — sent customers
    to the post-payment page to *begin* paying.

    ``success_url`` and ``cancel_url`` are accepted for signature-compatibility
    with ``stripe_service`` and are returned to the caller rather than sent to
    Paddle: the post-payment redirect is a Paddle.js
    ``settings.successUrl`` concern, applied by the checkout page.

    Raises:
        ValueError: if the tier has no configured price. Enterprise always
            lands here, which is what makes it contact-sales.
        PaddleError: if Paddle rejects the transaction.
    """
    price_id = get_price_id_for_tier(tier, with_trial=trial_days > 0)
    if not price_id:
        raise ValueError(
            f"No Paddle price configured for tier '{tier.value}'. "
            "Enterprise is contact-sales; set PADDLE_*_PRICE_ID for self-serve tiers."
        )

    payload: dict[str, Any] = {
        "items": [{"price_id": price_id, "quantity": 1}],
        # tenant_id on the transaction propagates to the subscription Paddle
        # creates from it, so every downstream webhook can resolve the tenant.
        "custom_data": {"tenant_id": str(tenant_id), "tier": tier.value},
        "checkout": {"url": _checkout_page_url()},
    }
    if customer_id:
        payload["customer_id"] = customer_id

    try:
        data = await _request("POST", "/transactions", json=payload)
    except PaddleError as exc:
        # Paddle refuses to create the transaction at all until a default
        # payment link is configured on the account (Checkout > Checkout
        # settings). Confirmed against sandbox: the API returns
        # 400 transaction_default_checkout_url_not_set rather than creating a
        # transaction with an empty checkout.url. Left unhandled this reaches
        # the customer as an opaque 500 on the first click of "Upgrade", with
        # nothing in the message saying which dashboard setting is missing.
        if exc.code == "transaction_default_checkout_url_not_set":
            logger.error(
                "paddle_default_payment_link_missing",
                tenant_id=tenant_id,
                environment=settings.paddle_environment,
                detail="set a default payment link in Paddle > Checkout > "
                "Checkout settings; required in sandbox and live alike",
            )
            raise PaddleError(
                503,
                exc.code,
                "Paddle has no default payment link configured for this account, "
                "so checkout cannot open. Set one under Checkout > Checkout "
                "settings in the Paddle dashboard.",
            ) from exc
        raise

    checkout_url = (data.get("checkout") or {}).get("url")
    if not checkout_url:
        # Paddle only populates checkout.url when a default payment link is set
        # on the account. Without it the transaction is created but unusable,
        # and returning None here would surface as a blank redirect.
        logger.error(
            "paddle_checkout_url_missing",
            tenant_id=tenant_id,
            transaction_id=data.get("id"),
            detail="set a default payment link in Paddle > Checkout > Checkout settings",
        )
        raise PaddleError(
            502,
            "checkout_url_missing",
            "Paddle returned no checkout URL. Set a default payment link under "
            "Checkout > Checkout settings in the Paddle dashboard.",
        )

    logger.info(
        "paddle_checkout_created",
        tenant_id=tenant_id,
        tier=tier.value,
        trial_days=trial_days,
        transaction_id=data["id"],
    )

    created = _parse_dt(data.get("created_at")) or datetime.now(timezone.utc)
    return CheckoutSession(
        id=data["id"],
        url=checkout_url,
        customer_id=data.get("customer_id"),
        subscription_id=data.get("subscription_id"),
        expires_at=created.replace(microsecond=0) + _CHECKOUT_TTL,
    )


async def create_portal_session(customer_id: str, return_url: str) -> str:
    """
    Create a Paddle customer portal session and return its overview URL.

    ``return_url`` is accepted for signature-compatibility with stripe_service.
    Paddle's portal has no return-URL parameter; the customer closes the tab or
    uses the portal's own navigation.

    Portal sessions are short-lived and must not be cached.
    """
    subscription_ids = [s.id for s in await get_customer_subscriptions(customer_id)]

    payload: dict[str, Any] = {}
    if subscription_ids:
        # Including these produces deep links that let the customer manage the
        # subscription directly, rather than only viewing an overview.
        payload["subscription_ids"] = subscription_ids

    data = await _request(
        "POST", f"/customers/{customer_id}/portal-sessions", json=payload
    )
    return data["urls"]["general"]["overview"]


# =============================================================================
# Subscriptions
# =============================================================================


def subscription_from_api(data: dict[str, Any]) -> PaddleSubscription:
    """Project a Paddle subscription payload onto PaddleSubscription."""
    items = data.get("items") or []
    price_id = ""
    trial_end: Optional[datetime] = None
    if items:
        price_id = (items[0].get("price") or {}).get("id", "")
        trial_end = _parse_dt((items[0].get("trial_dates") or {}).get("ends_at"))

    period = data.get("current_billing_period") or {}
    started = _parse_dt(period.get("starts_at")) or _parse_dt(data.get("started_at"))
    ends = _parse_dt(period.get("ends_at"))

    # A canceled or paused subscription has no current billing period. Falling
    # back to the cancellation instant keeps plan_expires_at meaningful instead
    # of raising on a None, which is the shape sync_tenant_subscription needs.
    canceled_at = _parse_dt(data.get("canceled_at"))
    now = datetime.now(timezone.utc)
    started = started or canceled_at or now
    ends = ends or canceled_at or now

    scheduled = data.get("scheduled_change") or {}

    return PaddleSubscription(
        id=data["id"],
        customer_id=data["customer_id"],
        status=SubscriptionState(data["status"]),
        tier=get_tier_for_price_id(price_id),
        price_id=price_id,
        current_period_start=started,
        current_period_end=ends,
        cancel_at_period_end=scheduled.get("action") == "cancel",
        canceled_at=canceled_at,
        trial_end=trial_end,
    )


async def get_subscription(subscription_id: str) -> Optional[PaddleSubscription]:
    """Get a Paddle subscription by ID, or None if it does not exist."""
    try:
        data = await _request("GET", f"/subscriptions/{subscription_id}")
    except PaddleError as exc:
        if exc.status_code == 404:
            return None
        raise
    return subscription_from_api(data)


async def get_customer_subscriptions(customer_id: str) -> list[PaddleSubscription]:
    """List a customer's subscriptions, newest first."""
    data = await _request(
        "GET",
        "/subscriptions",
        params={"customer_id": customer_id, "per_page": 50},
    )
    return [subscription_from_api(record) for record in (data or [])]


async def update_subscription_tier(
    subscription_id: str,
    new_tier: SubscriptionTier,
    prorate: bool = True,
) -> PaddleSubscription:
    """
    Move a subscription to a different tier.

    Always targets the *base* (non-trial) price: a tier change is a deliberate
    purchase decision, and routing it through a trial price would hand the
    customer a second free period on every upgrade.

    Raises:
        ValueError: if the target tier has no configured price.
    """
    price_id = get_price_id_for_tier(new_tier, with_trial=False)
    if not price_id:
        raise ValueError(
            f"No Paddle price configured for tier '{new_tier.value}'. "
            "Enterprise is contact-sales."
        )

    data = await _request(
        "PATCH",
        f"/subscriptions/{subscription_id}",
        json={
            "items": [{"price_id": price_id, "quantity": 1}],
            "proration_billing_mode": (
                "prorated_immediately" if prorate else "full_next_billing_period"
            ),
        },
    )
    logger.info(
        "paddle_subscription_tier_updated",
        subscription_id=subscription_id,
        new_tier=new_tier.value,
        prorate=prorate,
    )
    return subscription_from_api(data)


async def cancel_subscription(
    subscription_id: str,
    at_period_end: bool = True,
) -> PaddleSubscription:
    """
    Cancel a subscription, at period end by default.

    Paddle models a period-end cancellation as a *scheduled change* rather than
    a status change: the subscription stays ``active`` with
    ``scheduled_change.action == "cancel"`` until the period actually ends. So
    a tenant who cancels keeps their plan for the rest of the paid period,
    which is what ENTITLING_STATES already implies.
    """
    data = await _request(
        "POST",
        f"/subscriptions/{subscription_id}/cancel",
        json={
            "effective_from": "next_billing_period" if at_period_end else "immediately"
        },
    )
    logger.info(
        "paddle_subscription_canceled",
        subscription_id=subscription_id,
        at_period_end=at_period_end,
    )
    return subscription_from_api(data)


async def reactivate_subscription(subscription_id: str) -> PaddleSubscription:
    """
    Undo a scheduled cancellation.

    Only meaningful while the cancellation is still scheduled. Once Paddle has
    actually canceled the subscription it cannot be revived, and the customer
    must check out again — Paddle has no resume-from-canceled operation.
    """
    data = await _request(
        "PATCH",
        f"/subscriptions/{subscription_id}",
        json={"scheduled_change": None},
    )
    logger.info("paddle_subscription_reactivated", subscription_id=subscription_id)
    return subscription_from_api(data)


# =============================================================================
# Invoices & payment methods
# =============================================================================


async def get_customer_invoices(customer_id: str, limit: int = 20) -> list[Invoice]:
    """
    List a customer's billed transactions, projected as invoices.

    Only ``billed``, ``paid`` and ``completed`` transactions are returned;
    drafts and ready-but-unpaid transactions are checkout attempts, not
    invoices, and listing them would show customers charges that never existed.
    """
    data = await _request(
        "GET",
        "/transactions",
        params={
            "customer_id": customer_id,
            "status": "billed,paid,completed",
            "per_page": min(limit, 200),
        },
    )

    invoices: list[Invoice] = []
    for record in data or []:
        totals = (record.get("details") or {}).get("totals") or {}
        grand_total = _to_cents(totals.get("grand_total"))
        status = record.get("status", "")
        paid = grand_total if status in ("paid", "completed") else 0

        invoices.append(
            Invoice(
                id=record["id"],
                number=record.get("invoice_number") or "",
                status=status,
                amount_due=grand_total,
                amount_paid=paid,
                currency=record.get("currency_code", "USD"),
                created=_parse_dt(record.get("created_at"))
                or datetime.now(timezone.utc),
                due_date=_parse_dt(record.get("billed_at")),
                # Paddle serves the PDF from an authenticated endpoint that
                # returns a short-lived link, so there is no durable hosted URL
                # to hand out here. The customer portal is the supported route.
                hosted_invoice_url=None,
                pdf_url=None,
            )
        )
    return invoices


async def get_invoice_pdf_url(transaction_id: str) -> Optional[str]:
    """
    Get a short-lived signed URL for a transaction's invoice PDF.

    The URL expires; fetch it on demand rather than storing it.
    """
    try:
        data = await _request("GET", f"/transactions/{transaction_id}/invoice")
    except PaddleError as exc:
        if exc.status_code == 404:
            return None
        raise
    return (data or {}).get("url")


async def get_upcoming_invoice(customer_id: str) -> Optional[Invoice]:
    """
    Preview the customer's next renewal charge.

    Returns None when the customer has no entitling subscription — a canceled
    or paused subscription has no next charge to preview.
    """
    subscriptions = await get_customer_subscriptions(customer_id)
    active = next(
        (s for s in subscriptions if s.status in ENTITLING_STATES),
        None,
    )
    if active is None:
        return None

    try:
        data = await _request("GET", f"/subscriptions/{active.id}/preview-next-payment")
    except PaddleError as exc:
        if exc.status_code == 404:
            return None
        raise
    if not data:
        return None

    totals = (data.get("details") or {}).get("totals") or {}
    return Invoice(
        id=f"upcoming_{active.id}",
        number="",
        status="upcoming",
        amount_due=_to_cents(totals.get("grand_total")),
        amount_paid=0,
        currency=data.get("currency_code", "USD"),
        created=datetime.now(timezone.utc),
        due_date=active.current_period_end,
        hosted_invoice_url=None,
        pdf_url=None,
    )


async def get_customer_payment_methods(customer_id: str) -> list[dict[str, Any]]:
    """
    List a customer's saved payment methods.

    Shaped to match stripe_service's projection so payments.py can build
    ``PaymentMethodResponse`` without branching. Paddle does not expose a
    default-method flag, so ``is_default`` is False throughout; customers
    change their method through the portal.
    """
    data = await _request(
        "GET",
        f"/customers/{customer_id}/payment-methods",
        params={"per_page": 50},
    )

    methods: list[dict[str, Any]] = []
    for record in data or []:
        card = record.get("card") or {}
        methods.append(
            {
                "id": record["id"],
                "type": record.get("type", "card"),
                "brand": card.get("type", ""),
                "last4": card.get("last4", ""),
                "exp_month": card.get("expiry_month", 0),
                "exp_year": card.get("expiry_year", 0),
                "is_default": False,
            }
        )
    return methods


# =============================================================================
# Webhook signature verification
# =============================================================================


def verify_webhook_signature(
    raw_body: bytes,
    signature_header: str,
    secret: Optional[str] = None,
    tolerance_seconds: Optional[int] = None,
) -> bool:
    """
    Verify a ``Paddle-Signature`` header.

    The header looks like ``ts=1671552777;h1=<hex digest>``. Paddle signs
    ``"{ts}:{raw_body}"`` with the destination's ``endpoint_secret_key`` using
    HMAC-SHA256.

    ``raw_body`` must be the exact bytes received. Re-serialising the parsed
    JSON changes key order and whitespace and will never match.

    Args:
        raw_body: Exact request body bytes.
        signature_header: Value of the ``Paddle-Signature`` header.
        secret: Signing secret; defaults to ``settings.paddle_webhook_secret``.
        tolerance_seconds: Maximum accepted clock skew, to bound replay.
            Defaults to settings.paddle_webhook_signature_tolerance_seconds
            (5s, matching Paddle). This is the one knob that can reject every
            webhook: if this host's clock drifts past the window, no signature
            ever validates and billing stops without any error from Paddle.

    Returns:
        True only if the signature is present, well-formed, within tolerance
        and matches. Never raises — a malformed header is a failed
        verification, not a 500.
    """
    if tolerance_seconds is None:
        tolerance_seconds = settings.paddle_webhook_signature_tolerance_seconds
    signing_secret = secret if secret is not None else settings.paddle_webhook_secret
    if not signing_secret or not signature_header:
        return False

    timestamp: Optional[str] = None
    received: Optional[str] = None
    for part in signature_header.split(";"):
        key, _, value = part.partition("=")
        if key.strip() == "ts":
            timestamp = value.strip()
        elif key.strip() == "h1":
            received = value.strip()

    if not timestamp or not received:
        return False

    try:
        signed_at = int(timestamp)
    except ValueError:
        return False

    # Bound replay. Paddle retries with a fresh signature, so rejecting a stale
    # timestamp costs nothing and closes the window on a captured request.
    age = abs(int(datetime.now(timezone.utc).timestamp()) - signed_at)
    if age > tolerance_seconds:
        logger.warning(
            "paddle_webhook_signature_stale",
            age_seconds=age,
            tolerance_seconds=tolerance_seconds,
            detail="if this persists for every delivery, check this host's clock "
            "(NTP) before widening PADDLE_WEBHOOK_SIGNATURE_TOLERANCE_SECONDS",
        )
        return False

    expected = hmac.new(
        signing_secret.encode("utf-8"),
        f"{timestamp}:".encode("utf-8") + raw_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected, received)


# =============================================================================
# Tenant synchronisation
# =============================================================================


async def sync_tenant_subscription(
    db: AsyncSession,
    tenant_id: int,
    subscription: PaddleSubscription,
) -> None:
    """
    Sync Paddle subscription data to the tenant record.

    Carries the same three invariants stripe_service.sync_tenant_subscription
    documents, for the same reasons:

    1. **The caller owns the transaction.** This issues the UPDATE and does not
       commit, so the webhook wrapper's rollback-on-failure actually rolls the
       plan change back. An inner commit here would persist the plan before the
       wrapper decided the event succeeded, and a later failure would ask
       Paddle to retry an event whose plan change had already landed.
    2. **An entitling state with an unrecognised price changes nothing.** The
       price is not one of PADDLE_*_PRICE_ID, so guessing would either
       over-grant or strip a paying customer's plan. Log loudly and return.
    3. **Every non-entitling state downgrades to free**, so a state Paddle adds
       later fails closed.
    """
    from app.base_models import Tenant

    entitled = subscription.status in ENTITLING_STATES

    if entitled:
        if subscription.tier is None:
            logger.error(
                "paddle_subscription_unmapped_price",
                tenant_id=tenant_id,
                subscription_id=subscription.id,
                price_id=subscription.price_id,
                status=subscription.status.value,
                detail="price is not any of PADDLE_{STARTER,PROFESSIONAL,"
                "ENTERPRISE}_PRICE_ID (base or trial); tenant plan left unchanged",
            )
            return

        plan = subscription.tier.value
        plan_expires_at = subscription.current_period_end
    else:
        plan = "free"
        plan_expires_at = subscription.canceled_at or subscription.current_period_end

    await db.execute(
        update(Tenant)
        .where(Tenant.id == tenant_id)
        .values(plan=plan, plan_expires_at=plan_expires_at)
    )

    logger.info(
        "tenant_subscription_synced",
        gateway="paddle",
        tenant_id=tenant_id,
        plan=plan,
        entitled=entitled,
        subscription_status=subscription.status.value,
        plan_expires_at=plan_expires_at.isoformat(),
    )


async def sync_tenant_paddle_customer(
    db: AsyncSession,
    tenant_id: int,
    customer_id: str,
) -> None:
    """Update the tenant's Paddle customer ID. Commits."""
    from app.base_models import Tenant

    await db.execute(
        update(Tenant)
        .where(Tenant.id == tenant_id)
        .values(paddle_customer_id=customer_id)
    )
    await db.commit()

    logger.info(
        "tenant_paddle_customer_synced",
        tenant_id=tenant_id,
        customer_id=customer_id,
    )


# =============================================================================
# Uniform gateway interface
# =============================================================================
#
# app.services.payment_gateway selects between this module and stripe_service at
# runtime. These aliases are the contract it dispatches through, so payments.py
# never has to branch on which gateway is active.

GATEWAY_NAME = "paddle"
CONFIGURED = PADDLE_CONFIGURED
TENANT_CUSTOMER_FIELD = "paddle_customer_id"
sync_tenant_customer = sync_tenant_paddle_customer
