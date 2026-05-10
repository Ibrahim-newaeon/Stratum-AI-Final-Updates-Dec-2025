# Payments & Billing Edge Cases

## Overview

This document covers error handling, edge cases, and known limitations for payments and billing.

---

## Edge Cases

### 1. Payment Declined

**Scenario**: Credit card payment fails.

**Behavior**:
- Payment attempt logged
- User notified with specific reason
- Retry available
- Grace period applies

**Response**:
```json
{
  "error": {
    "code": "PAYMENT_FAILED",
    "message": "Payment could not be processed",
    "details": {
      "decline_code": "insufficient_funds",
      "retry_available": true,
      "grace_period_ends": "2024-01-18T00:00:00Z"
    }
  }
}
```

**Decline Codes**:

| Code | Meaning | User Action |
|------|---------|-------------|
| `insufficient_funds` | Card has no funds | Use different card |
| `card_declined` | Generic decline | Contact bank |
| `expired_card` | Card expired | Update card |
| `incorrect_cvc` | Wrong CVC | Re-enter card |
| `processing_error` | Temporary error | Retry |

---

### 2. Subscription Expired During Grace Period

**Scenario**: Grace period ends without payment.

**Behavior**:
- Access restricted to read-only
- Automations paused
- Data preserved for 30 days
- Re-activation available

**Response**:
```json
{
  "error": {
    "code": "SUBSCRIPTION_EXPIRED",
    "message": "Your subscription has expired",
    "details": {
      "expired_at": "2024-01-18T00:00:00Z",
      "data_deletion_at": "2024-02-17T00:00:00Z",
      "reactivation_available": true
    }
  }
}
```

---

### 3. Downgrade with Usage Over New Limit

**Scenario**: User tries to downgrade but exceeds new plan limits.

**Behavior**:
- Downgrade blocked
- Current usage shown
- Required reduction explained

**Response**:
```json
{
  "error": {
    "code": "DOWNGRADE_NOT_ALLOWED",
    "message": "Cannot downgrade: current usage exceeds new plan limits",
    "details": {
      "current_plan": "growth",
      "target_plan": "starter",
      "over_limits": {
        "campaigns": {
          "current": 25,
          "new_limit": 10,
          "action": "Archive or delete 15 campaigns"
        },
        "team_members": {
          "current": 5,
          "new_limit": 2,
          "action": "Remove 3 team members"
        }
      }
    }
  }
}
```

---

### 4. Duplicate Subscription Attempt

**Scenario**: User tries to subscribe when already subscribed.

**Behavior**:
- New subscription blocked
- Existing subscription info returned
- Upgrade option provided

**Response**:
```json
{
  "error": {
    "code": "SUBSCRIPTION_EXISTS",
    "message": "You already have an active subscription",
    "details": {
      "current_plan": "starter",
      "status": "active",
      "action": "Use upgrade endpoint to change plans"
    }
  }
}
```

---

### 5. Invalid Coupon

**Scenario**: User enters expired or invalid coupon.

**Behavior**:
- Coupon validation fails
- Specific reason provided
- Checkout continues without discount

**Response**:
```json
{
  "error": {
    "code": "COUPON_INVALID",
    "message": "Coupon code is not valid",
    "details": {
      "code": "SUMMER2023",
      "reason": "expired",
      "expired_at": "2023-09-01T00:00:00Z"
    }
  }
}
```

---

### 6. Payment Method Removal with Active Subscription

**Scenario**: User tries to remove last payment method.

**Behavior**:
- Removal blocked
- User must add new method first

**Response**:
```json
{
  "error": {
    "code": "PAYMENT_METHOD_REQUIRED",
    "message": "Cannot remove last payment method with active subscription",
    "details": {
      "subscription_status": "active",
      "action": "Add new payment method before removing this one"
    }
  }
}
```

---

### 7. Proration Calculation

**Scenario**: Mid-cycle plan change.

**Behavior**:
- Unused time credited
- New plan prorated
- Net charge calculated

**Example**:
```
Current Plan: Starter ($99/mo)
New Plan: Growth ($299/mo)
Days remaining: 15 of 30

Credit for Starter: $99 × (15/30) = -$49.50
Charge for Growth: $299 × (15/30) = $149.50
Net due: $100.00
```

---

### 8. Webhook Delivery Failure

**Scenario**: Stripe webhook fails to deliver.

**Behavior**:
- Stripe retries with backoff
- System polls for missed events
- Manual sync available

**Handling**:
```python
async def sync_stripe_data(tenant_id: int):
    # Fetch latest from Stripe
    stripe_sub = await stripe.Subscription.retrieve(subscription.stripe_subscription_id)

    # Update local state
    subscription.status = stripe_sub.status
    subscription.current_period_end = datetime.fromtimestamp(stripe_sub.current_period_end)
    await db.commit()
```

---

### 9. Currency Conversion

**Scenario**: User in non-USD region.

**Behavior**:
- Prices shown in USD
- Payment processed in USD
- Bank handles conversion

**Display**:
```
Growth Plan: $299.00 USD/month
Note: Your bank may apply currency conversion fees
```

---

### 10. Trial to Paid Conversion Failure

**Scenario**: Payment fails when trial ends.

**Behavior**:
- Grace period starts (3 days)
- Daily retry attempts
- Access restricted if unpaid

**Timeline**:
```
Day 0: Trial ends, payment attempted, fails
Day 1: Retry 1
Day 2: Retry 2
Day 3: Retry 3, access restricted if still unpaid
Day 30: Data deletion warning
Day 60: Data deleted
```

---

### 11. Usage Limit Exceeded

**Scenario**: Tenant exceeds plan limits.

**Behavior**:
- Soft limit: Warning shown
- Hard limit: Action blocked
- Upgrade prompted

**Response**:
```json
{
  "error": {
    "code": "USAGE_LIMIT_EXCEEDED",
    "message": "Campaign limit reached for your plan",
    "details": {
      "metric": "campaigns",
      "current": 10,
      "limit": 10,
      "plan": "starter",
      "upgrade_to": "growth",
      "new_limit": 50
    }
  }
}
```

---

### 12. Invoice Payment Retry

**Scenario**: User manually retries failed invoice.

**Behavior**:
- Attempts payment with default method
- Updates subscription if successful
- Returns specific error if fails

**Response (Success)**:
```json
{
  "success": true,
  "data": {
    "invoice_id": "in_abc123",
    "status": "paid",
    "subscription_status": "active"
  },
  "message": "Payment successful. Subscription restored."
}
```

---

## Known Limitations

### 1. Single Currency

**Limitation**: All billing in USD.

**Impact**: Non-US users pay in USD.

**Planned**: Multi-currency support.

---

### 2. No Partial Refunds

**Limitation**: Refunds are full-month only.

**Impact**: Mid-month cancellations lose remaining days.

**Workaround**: Cancel at period end to use full month.

---

### 3. Annual Plan Early Cancellation

**Limitation**: No refund for early annual cancellation.

**Impact**: Users lose remaining months.

**Mitigation**: Clear warning before annual commitment.

---

### 4. No Plan Pause

**Limitation**: Subscriptions cannot be paused.

**Impact**: Users must cancel and resubscribe.

**Planned**: Subscription pause feature.

---

## Error Recovery

### Payment Errors

| Error | Recovery |
|-------|----------|
| Card declined | Try different card |
| Expired card | Update card details |
| Insufficient funds | Use different card |
| Network error | Retry payment |

### Subscription Errors

| Error | Recovery |
|-------|----------|
| Expired | Reactivate with payment |
| Past due | Pay outstanding invoice |
| Canceled | Create new subscription |

---

## Monitoring

### Key Metrics

| Metric | Alert Threshold |
|--------|-----------------|
| Payment failure rate | > 5% |
| Churn rate | > 3%/month |
| Revenue leakage | > 1% |
| Webhook failure rate | > 1% |

### Health Checks

```python
async def billing_health():
    return {
        "status": "healthy",
        "checks": {
            "stripe_api": await check_stripe_connection(),
            "webhook_recent": await check_recent_webhooks(),
            "failed_payments_24h": await count_failed_payments(24),
            "expired_subscriptions": await count_expired_subscriptions()
        }
    }
```

---

## Compliance

### PCI Compliance

- No card data stored locally
- Stripe Elements for card input
- All payment data on Stripe

### Data Retention

- Invoice records: 7 years
- Payment logs: 7 years
- Subscription history: Indefinite

---

## Related Documentation

- [Specification](./spec.md) - Data models and architecture
- [User Flows](./user-flows.md) - Step-by-step user journeys
- [API Contracts](./api-contracts.md) - API endpoints and schemas
