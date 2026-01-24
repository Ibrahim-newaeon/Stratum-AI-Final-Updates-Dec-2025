# Payments & Billing API Contracts

## Overview

API endpoints for subscription and billing management.

**Base URL**: `/api/v1/tenant/{tenant_id}/billing`

---

## Authentication

All endpoints require Bearer token authentication with tenant admin role.

---

## Subscription

### GET /billing/subscription

Get current subscription details.

#### Response

```json
{
  "success": true,
  "data": {
    "id": 1,
    "plan": "growth",
    "plan_name": "Growth",
    "status": "active",
    "billing_cycle": "monthly",
    "current_period_start": "2024-01-01T00:00:00Z",
    "current_period_end": "2024-02-01T00:00:00Z",
    "trial_end": null,
    "canceled_at": null,
    "limits": {
      "max_campaigns": 50,
      "max_events": 250000,
      "max_team_members": 10,
      "max_platforms": 4
    },
    "usage": {
      "campaigns": 8,
      "events": 35240,
      "team_members": 2
    },
    "price_cents": 29900,
    "next_invoice_date": "2024-02-01T00:00:00Z"
  }
}
```

### POST /billing/subscription

Create new subscription.

#### Request

```json
{
  "plan": "growth",
  "billing_cycle": "monthly",
  "payment_method_id": "pm_abc123",
  "coupon_code": "WELCOME20"
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "id": 1,
    "plan": "growth",
    "status": "active",
    "current_period_end": "2024-02-01T00:00:00Z"
  },
  "message": "Subscription created successfully"
}
```

### PATCH /billing/subscription

Update subscription (upgrade/downgrade).

#### Request

```json
{
  "plan": "enterprise",
  "billing_cycle": "annual"
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "id": 1,
    "plan": "enterprise",
    "status": "active",
    "proration": {
      "credit_cents": -14950,
      "charge_cents": 99900,
      "net_cents": 84950
    }
  },
  "message": "Plan upgraded successfully"
}
```

### DELETE /billing/subscription

Cancel subscription.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `at_period_end` | boolean | Cancel at period end (default: true) |
| `reason` | string | Cancellation reason |

#### Response

```json
{
  "success": true,
  "data": {
    "id": 1,
    "status": "active",
    "cancel_at_period_end": true,
    "canceled_at": "2024-02-01T00:00:00Z"
  },
  "message": "Subscription will cancel on Feb 1, 2024"
}
```

---

## Plans

### GET /billing/plans

Get available subscription plans.

#### Response

```json
{
  "success": true,
  "data": [
    {
      "id": "starter",
      "name": "Starter",
      "prices": {
        "monthly": {"cents": 9900, "price_id": "price_starter_monthly"},
        "annual": {"cents": 99000, "price_id": "price_starter_annual"}
      },
      "limits": {
        "max_campaigns": 10,
        "max_events": 50000,
        "max_team_members": 2,
        "max_platforms": 2
      },
      "features": [
        "Trust-Gated Autopilot",
        "Rules Engine",
        "Basic CDP",
        "Email Support"
      ]
    },
    {
      "id": "growth",
      "name": "Growth",
      "recommended": true,
      "prices": {
        "monthly": {"cents": 29900, "price_id": "price_growth_monthly"},
        "annual": {"cents": 299000, "price_id": "price_growth_annual"}
      },
      "limits": {
        "max_campaigns": 50,
        "max_events": 250000,
        "max_team_members": 10,
        "max_platforms": 4
      },
      "features": [
        "Everything in Starter",
        "Full CDP",
        "WhatsApp Integration",
        "API Access",
        "Priority Support"
      ]
    }
  ]
}
```

---

## Payment Methods

### GET /billing/payment-methods

List payment methods.

#### Response

```json
{
  "success": true,
  "data": [
    {
      "id": "pm_abc123",
      "type": "card",
      "is_default": true,
      "card": {
        "brand": "visa",
        "last4": "4242",
        "exp_month": 12,
        "exp_year": 2025
      },
      "created_at": "2024-01-01T10:00:00Z"
    }
  ]
}
```

### POST /billing/payment-methods

Add payment method.

#### Request

```json
{
  "payment_method_id": "pm_xyz789",
  "set_default": true
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "id": "pm_xyz789",
    "type": "card",
    "is_default": true,
    "card": {
      "brand": "mastercard",
      "last4": "5555",
      "exp_month": 6,
      "exp_year": 2026
    }
  },
  "message": "Payment method added successfully"
}
```

### DELETE /billing/payment-methods/{payment_method_id}

Remove payment method.

#### Response

```
HTTP 204 No Content
```

### POST /billing/payment-methods/{payment_method_id}/default

Set as default payment method.

#### Response

```json
{
  "success": true,
  "data": {
    "id": "pm_xyz789",
    "is_default": true
  }
}
```

---

## Invoices

### GET /billing/invoices

List invoices.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter: paid, open, void |
| `limit` | integer | Max results (default: 20) |

#### Response

```json
{
  "success": true,
  "data": [
    {
      "id": "in_abc123",
      "number": "INV-2024-0001",
      "status": "paid",
      "total_cents": 29900,
      "currency": "usd",
      "period_start": "2024-01-01T00:00:00Z",
      "period_end": "2024-02-01T00:00:00Z",
      "paid_at": "2024-01-01T00:05:00Z",
      "pdf_url": "https://pay.stripe.com/invoice/..."
    }
  ]
}
```

### GET /billing/invoices/{invoice_id}

Get invoice details.

#### Response

```json
{
  "success": true,
  "data": {
    "id": "in_abc123",
    "number": "INV-2024-0001",
    "status": "paid",
    "subtotal_cents": 29900,
    "tax_cents": 0,
    "total_cents": 29900,
    "amount_paid_cents": 29900,
    "line_items": [
      {
        "description": "Growth Plan (Jan 1 - Feb 1)",
        "quantity": 1,
        "amount_cents": 29900
      }
    ],
    "pdf_url": "https://pay.stripe.com/invoice/..."
  }
}
```

### POST /billing/invoices/{invoice_id}/pay

Pay open invoice.

#### Response

```json
{
  "success": true,
  "data": {
    "id": "in_abc123",
    "status": "paid",
    "paid_at": "2024-01-15T14:30:00Z"
  }
}
```

---

## Usage

### GET /billing/usage

Get current usage.

#### Response

```json
{
  "success": true,
  "data": {
    "billing_period": "2024-01",
    "usage": {
      "campaigns": {
        "used": 8,
        "limit": 50,
        "percentage": 16
      },
      "events": {
        "used": 35240,
        "limit": 250000,
        "percentage": 14
      },
      "team_members": {
        "used": 2,
        "limit": 10,
        "percentage": 20
      },
      "api_calls": {
        "used": 12450,
        "limit": null,
        "percentage": null
      }
    },
    "alerts": [
      {
        "metric": "campaigns",
        "threshold": 80,
        "message": "You're using 80% of your campaign limit"
      }
    ]
  }
}
```

### GET /billing/usage/history

Get usage history.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `months` | integer | Months of history (default: 6) |

#### Response

```json
{
  "success": true,
  "data": [
    {
      "period": "2024-01",
      "campaigns": 8,
      "events": 35240,
      "api_calls": 12450
    },
    {
      "period": "2023-12",
      "campaigns": 6,
      "events": 28100,
      "api_calls": 9800
    }
  ]
}
```

---

## Coupons

### POST /billing/coupons/validate

Validate a coupon code.

#### Request

```json
{
  "code": "WELCOME20"
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "code": "WELCOME20",
    "valid": true,
    "discount": {
      "type": "percent",
      "value": 20,
      "duration": "repeating",
      "duration_months": 3
    },
    "description": "20% off for 3 months"
  }
}
```

---

## Webhooks

### POST /webhooks/stripe

Stripe webhook endpoint (internal).

#### Headers

| Header | Description |
|--------|-------------|
| `Stripe-Signature` | Webhook signature |

#### Response

```json
{
  "received": true
}
```

---

## Checkout

### POST /billing/checkout/session

Create Stripe Checkout session.

#### Request

```json
{
  "plan": "growth",
  "billing_cycle": "monthly",
  "success_url": "https://app.stratum.ai/billing/success",
  "cancel_url": "https://app.stratum.ai/billing"
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "checkout_url": "https://checkout.stripe.com/..."
  }
}
```

### POST /billing/portal/session

Create Stripe Customer Portal session.

#### Response

```json
{
  "success": true,
  "data": {
    "portal_url": "https://billing.stripe.com/..."
  }
}
```

---

## Error Responses

### Error Format

```json
{
  "success": false,
  "error": {
    "code": "PAYMENT_FAILED",
    "message": "Payment could not be processed",
    "details": {
      "decline_code": "insufficient_funds"
    }
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `SUBSCRIPTION_EXISTS` | 400 | Active subscription exists |
| `PLAN_NOT_FOUND` | 404 | Invalid plan ID |
| `PAYMENT_FAILED` | 402 | Payment declined |
| `PAYMENT_METHOD_REQUIRED` | 400 | No payment method |
| `COUPON_INVALID` | 400 | Invalid or expired coupon |
| `USAGE_LIMIT_EXCEEDED` | 400 | Plan limit exceeded |
| `DOWNGRADE_NOT_ALLOWED` | 400 | Cannot downgrade with current usage |

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| GET endpoints | 60/min |
| POST endpoints | 20/min |
| Checkout creation | 10/min |

---

## Related Documentation

- [Specification](./spec.md) - Data models and architecture
- [User Flows](./user-flows.md) - Step-by-step user journeys
- [Edge Cases](./edge-cases.md) - Error handling and edge cases
