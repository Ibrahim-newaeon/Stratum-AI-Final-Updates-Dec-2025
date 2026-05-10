# Payments & Billing Specification

## Overview

The Payments & Billing module handles subscription management, usage-based billing, payment processing, and invoicing for the Stratum AI platform.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   PAYMENTS ARCHITECTURE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  STRATUM BILLING                          │  │
│  │                                                          │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │  │
│  │  │Subscription│ │  Usage   │ │ Invoice  │ │ Payment  │   │  │
│  │  │  Manager │ │ Tracker  │ │Generator │ │ Processor│   │  │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘   │  │
│  │       │            │            │            │          │  │
│  │       └────────────┴─────┬──────┴────────────┘          │  │
│  └──────────────────────────┼───────────────────────────────┘  │
│                             ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   STRIPE INTEGRATION                      │  │
│  │                                                          │  │
│  │  • Customer management                                   │  │
│  │  • Subscription lifecycle                                │  │
│  │  • Payment method handling                               │  │
│  │  • Invoice generation                                    │  │
│  │  • Webhook processing                                    │  │
│  │                                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Models

### Subscription

```python
class Subscription:
    id: int
    tenant_id: int
    stripe_subscription_id: str
    stripe_customer_id: str

    # Plan
    plan: SubscriptionPlan
    status: SubscriptionStatus
    billing_cycle: BillingCycle      # monthly, annual

    # Dates
    current_period_start: datetime
    current_period_end: datetime
    trial_end: datetime | None
    canceled_at: datetime | None

    # Usage
    included_campaigns: int
    included_events: int
    used_campaigns: int
    used_events: int

    created_at: datetime
    updated_at: datetime
```

### SubscriptionPlan

```python
class SubscriptionPlan:
    id: str
    name: str                          # Starter, Growth, Enterprise
    stripe_price_id: str

    # Pricing
    base_price_cents: int
    billing_cycle: BillingCycle

    # Limits
    max_campaigns: int
    max_events_per_month: int
    max_team_members: int
    max_platforms: int

    # Features
    features: list[str]
    is_custom: bool = False
```

### Invoice

```python
class Invoice:
    id: int
    tenant_id: int
    subscription_id: int
    stripe_invoice_id: str

    # Amounts
    subtotal_cents: int
    tax_cents: int
    total_cents: int
    amount_paid_cents: int

    # Status
    status: InvoiceStatus             # draft, open, paid, void
    paid_at: datetime | None
    due_date: datetime

    # Details
    line_items: list[InvoiceLineItem]
    pdf_url: str | None

    created_at: datetime
```

### PaymentMethod

```python
class PaymentMethod:
    id: int
    tenant_id: int
    stripe_payment_method_id: str

    type: str                          # card, bank_transfer
    is_default: bool

    # Card details (if card)
    card_brand: str | None             # visa, mastercard
    card_last4: str | None
    card_exp_month: int | None
    card_exp_year: int | None

    created_at: datetime
```

### UsageRecord

```python
class UsageRecord:
    id: int
    tenant_id: int
    subscription_id: int

    metric: UsageMetric               # campaigns, events, api_calls
    quantity: int
    timestamp: datetime
    billing_period: str               # 2024-01
```

---

## Enums

### SubscriptionStatus

```python
class SubscriptionStatus(str, Enum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"
    PAUSED = "paused"
```

### BillingCycle

```python
class BillingCycle(str, Enum):
    MONTHLY = "monthly"
    ANNUAL = "annual"
```

### InvoiceStatus

```python
class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    OPEN = "open"
    PAID = "paid"
    VOID = "void"
    UNCOLLECTIBLE = "uncollectible"
```

### UsageMetric

```python
class UsageMetric(str, Enum):
    CAMPAIGNS = "campaigns"
    EVENTS = "events"
    API_CALLS = "api_calls"
    WHATSAPP_MESSAGES = "whatsapp_messages"
```

---

## Pricing Plans

### Plan Tiers

| Plan | Monthly | Annual | Campaigns | Events/mo | Team | Platforms |
|------|---------|--------|-----------|-----------|------|-----------|
| Starter | $99 | $990 | 10 | 50K | 2 | 2 |
| Growth | $299 | $2,990 | 50 | 250K | 10 | 4 |
| Enterprise | Custom | Custom | Unlimited | Unlimited | Unlimited | All |

### Feature Matrix

| Feature | Starter | Growth | Enterprise |
|---------|---------|--------|------------|
| Trust-Gated Autopilot | ✓ | ✓ | ✓ |
| Rules Engine | ✓ | ✓ | ✓ |
| CDP | Basic | Full | Full |
| Audience Sync | 2 platforms | 4 platforms | All |
| WhatsApp | - | ✓ | ✓ |
| Custom Reports | - | ✓ | ✓ |
| API Access | - | ✓ | ✓ |
| Dedicated Support | - | - | ✓ |
| Custom Integrations | - | - | ✓ |

---

## Subscription Lifecycle

### Trial Flow

```python
async def start_trial(tenant_id: int, plan: str) -> Subscription:
    # Create Stripe customer
    customer = await stripe.Customer.create(
        metadata={"tenant_id": str(tenant_id)}
    )

    # Create subscription with trial
    stripe_sub = await stripe.Subscription.create(
        customer=customer.id,
        items=[{"price": get_price_id(plan)}],
        trial_period_days=14,
    )

    # Create local subscription
    subscription = Subscription(
        tenant_id=tenant_id,
        stripe_subscription_id=stripe_sub.id,
        stripe_customer_id=customer.id,
        plan=plan,
        status=SubscriptionStatus.TRIALING,
        trial_end=datetime.fromtimestamp(stripe_sub.trial_end),
    )

    await db.add(subscription)
    await db.commit()

    return subscription
```

### Upgrade/Downgrade

```python
async def change_plan(subscription_id: int, new_plan: str) -> Subscription:
    subscription = await get_subscription(subscription_id)

    # Update Stripe subscription
    await stripe.Subscription.modify(
        subscription.stripe_subscription_id,
        items=[{
            "id": subscription.stripe_item_id,
            "price": get_price_id(new_plan),
        }],
        proration_behavior="create_prorations",
    )

    # Update local subscription
    subscription.plan = new_plan
    await db.commit()

    return subscription
```

### Cancellation

```python
async def cancel_subscription(subscription_id: int, at_period_end: bool = True):
    subscription = await get_subscription(subscription_id)

    await stripe.Subscription.modify(
        subscription.stripe_subscription_id,
        cancel_at_period_end=at_period_end,
    )

    if not at_period_end:
        subscription.status = SubscriptionStatus.CANCELED
        subscription.canceled_at = datetime.now(timezone.utc)
    else:
        # Will be canceled at period end
        subscription.canceled_at = subscription.current_period_end

    await db.commit()
```

---

## Usage Tracking

### Event Counting

```python
async def record_usage(tenant_id: int, metric: UsageMetric, quantity: int):
    subscription = await get_active_subscription(tenant_id)
    billing_period = datetime.now(timezone.utc).strftime("%Y-%m")

    # Record locally
    record = UsageRecord(
        tenant_id=tenant_id,
        subscription_id=subscription.id,
        metric=metric,
        quantity=quantity,
        timestamp=datetime.now(timezone.utc),
        billing_period=billing_period,
    )
    await db.add(record)

    # Report to Stripe for metered billing
    if subscription.has_metered_billing:
        await stripe.SubscriptionItem.create_usage_record(
            subscription.stripe_item_id,
            quantity=quantity,
            action="increment",
        )

    await db.commit()
```

### Usage Limits

```python
async def check_usage_limit(tenant_id: int, metric: UsageMetric) -> bool:
    subscription = await get_active_subscription(tenant_id)
    plan = get_plan_details(subscription.plan)

    current_usage = await get_current_usage(tenant_id, metric)

    if metric == UsageMetric.CAMPAIGNS:
        return current_usage < plan.max_campaigns
    elif metric == UsageMetric.EVENTS:
        return current_usage < plan.max_events_per_month

    return True
```

---

## Webhook Handling

### Stripe Events

```python
HANDLED_EVENTS = [
    "customer.subscription.created",
    "customer.subscription.updated",
    "customer.subscription.deleted",
    "invoice.paid",
    "invoice.payment_failed",
    "customer.updated",
    "payment_method.attached",
    "payment_method.detached",
]

async def handle_stripe_webhook(event: dict):
    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "customer.subscription.updated":
        await sync_subscription(data)
    elif event_type == "invoice.paid":
        await record_payment(data)
    elif event_type == "invoice.payment_failed":
        await handle_payment_failure(data)
```

---

## Payment Methods

### Add Card

```python
async def add_payment_method(tenant_id: int, payment_method_id: str):
    subscription = await get_active_subscription(tenant_id)

    # Attach to Stripe customer
    await stripe.PaymentMethod.attach(
        payment_method_id,
        customer=subscription.stripe_customer_id,
    )

    # Set as default
    await stripe.Customer.modify(
        subscription.stripe_customer_id,
        invoice_settings={"default_payment_method": payment_method_id},
    )

    # Store locally
    pm = await stripe.PaymentMethod.retrieve(payment_method_id)
    payment_method = PaymentMethod(
        tenant_id=tenant_id,
        stripe_payment_method_id=payment_method_id,
        type=pm.type,
        is_default=True,
        card_brand=pm.card.brand if pm.card else None,
        card_last4=pm.card.last4 if pm.card else None,
        card_exp_month=pm.card.exp_month if pm.card else None,
        card_exp_year=pm.card.exp_year if pm.card else None,
    )
    await db.add(payment_method)
    await db.commit()
```

---

## Invoicing

### Invoice Generation

- Automatic via Stripe subscription
- Usage reported at billing period end
- PDF generated and stored
- Email sent to billing contact

### Invoice Line Items

| Type | Description |
|------|-------------|
| subscription | Base subscription fee |
| usage | Overage charges |
| proration | Plan change adjustments |
| discount | Applied coupons |
| tax | Applicable taxes |

---

## Related Documentation

- [User Flows](./user-flows.md) - Step-by-step user journeys
- [API Contracts](./api-contracts.md) - API endpoints and schemas
- [Edge Cases](./edge-cases.md) - Error handling and edge cases
