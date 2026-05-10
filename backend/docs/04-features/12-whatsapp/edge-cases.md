# WhatsApp Integration Edge Cases

## Overview

This document covers error handling, edge cases, and known limitations for WhatsApp integration.

---

## Edge Cases

### 1. Contact Not Opted In

**Scenario**: Attempt to message a contact who hasn't opted in.

**Behavior**:
- Message rejected at validation
- Error returned to user
- No message sent to Meta API

**Response**:
```json
{
  "error": {
    "code": "CONTACT_NOT_OPTED_IN",
    "message": "Contact has not opted in to receive messages",
    "details": {
      "contact_id": 1,
      "opted_in": false,
      "opted_out_at": "2024-01-10T10:00:00Z"
    }
  }
}
```

---

### 2. 24-Hour Window Expired

**Scenario**: Reply to conversation after 24h window closes.

**Behavior**:
- Text messages blocked
- Only template messages allowed
- User prompted to use template

**Response**:
```json
{
  "error": {
    "code": "CONVERSATION_EXPIRED",
    "message": "24-hour messaging window has expired",
    "details": {
      "conversation_id": 1,
      "expired_at": "2024-01-15T14:00:00Z",
      "solution": "Use an approved template message"
    }
  }
}
```

---

### 3. Template Not Approved

**Scenario**: Attempt to send using pending/rejected template.

**Behavior**:
- Message rejected
- Template status shown
- Rejection reason displayed if available

**Response**:
```json
{
  "error": {
    "code": "TEMPLATE_NOT_APPROVED",
    "message": "Template 'promo_offer' is not approved for sending",
    "details": {
      "template_id": 5,
      "template_name": "promo_offer",
      "status": "rejected",
      "rejection_reason": "Template contains prohibited content"
    }
  }
}
```

---

### 4. Invalid Phone Number

**Scenario**: Import or create contact with invalid phone.

**Behavior**:
- Validation fails
- Specific format error returned
- Valid format explained

**Response**:
```json
{
  "error": {
    "code": "INVALID_PHONE_FORMAT",
    "message": "Phone number must be in E.164 format",
    "details": {
      "provided": "555-1234",
      "expected_format": "+15551234567",
      "example": "+1 followed by 10 digits"
    }
  }
}
```

---

### 5. WhatsApp Rate Limit

**Scenario**: Exceed Meta's messaging rate limit.

**Behavior**:
- Current batch paused
- Retry scheduled with backoff
- Rate limit info returned

**Response**:
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "WhatsApp rate limit exceeded",
    "details": {
      "limit": 80,
      "period": "1 minute",
      "retry_after_seconds": 45,
      "messages_queued": 150
    }
  }
}
```

---

### 6. Webhook Signature Invalid

**Scenario**: Webhook request with invalid HMAC signature.

**Behavior**:
- Request rejected (401)
- Logged as security event
- Alert sent to admin

**Handling**:
```python
def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    expected = hmac.new(
        app_secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(f"sha256={expected}", signature):
        logger.warning(f"Invalid webhook signature: {signature[:20]}...")
        return False
    return True
```

---

### 7. Contact Not on WhatsApp

**Scenario**: Phone number not registered with WhatsApp.

**Behavior**:
- Meta API returns error
- Message marked as failed
- Contact flagged for review

**Response**:
```json
{
  "error": {
    "code": "RECIPIENT_NOT_ON_WHATSAPP",
    "message": "Phone number is not registered on WhatsApp",
    "details": {
      "phone": "+15551234567",
      "meta_error_code": 131047
    }
  }
}
```

---

### 8. Broadcast Partially Fails

**Scenario**: Some messages in broadcast fail while others succeed.

**Behavior**:
- Broadcast continues to next recipients
- Failures logged individually
- Summary shows partial success

**Response**:
```json
{
  "success": true,
  "data": {
    "broadcast_id": 1,
    "status": "completed",
    "results": {
      "total": 1000,
      "sent": 945,
      "failed": 55,
      "failure_breakdown": {
        "not_on_whatsapp": 32,
        "invalid_number": 15,
        "rate_limited": 8
      }
    }
  }
}
```

---

### 9. Template Variable Mismatch

**Scenario**: Wrong number of parameters provided for template.

**Behavior**:
- Validation fails before sending
- Expected parameters listed
- Message not sent

**Response**:
```json
{
  "error": {
    "code": "TEMPLATE_PARAMS_MISMATCH",
    "message": "Template expects 3 parameters, but 2 were provided",
    "details": {
      "template_name": "order_shipped",
      "expected_params": 3,
      "provided_params": 2,
      "param_names": ["customer_name", "order_id", "tracking_url"]
    }
  }
}
```

---

### 10. Duplicate Opt-Out Detection

**Scenario**: Contact sends multiple STOP messages.

**Behavior**:
- First STOP triggers opt-out
- Subsequent STOPs ignored
- No duplicate confirmations sent

**Handling**:
```python
async def process_opt_out(phone: str):
    contact = await get_contact(phone)

    if not contact.opted_in:
        logger.info(f"Already opted out: {phone}")
        return  # No action needed

    contact.opted_in = False
    contact.opted_out_at = datetime.now(timezone.utc)
    await db.commit()
    await send_opt_out_confirmation(phone)
```

---

### 11. Bulk Import with Mixed Results

**Scenario**: CSV import has valid and invalid rows.

**Behavior**:
- Valid rows imported
- Invalid rows skipped
- Detailed error report returned

**Response**:
```json
{
  "success": true,
  "data": {
    "processed": 250,
    "imported": 235,
    "duplicates": 10,
    "errors": 5,
    "error_details": [
      {"row": 45, "phone": "+1555", "error": "Invalid phone format"},
      {"row": 89, "phone": "", "error": "Phone number required"},
      {"row": 156, "phone": "+15551234567", "error": "Duplicate number"}
    ]
  }
}
```

---

### 12. Access Token Expiration

**Scenario**: Meta access token expires.

**Behavior**:
- API calls return 401
- Connection marked as error
- Admin alerted to refresh token

**Response**:
```json
{
  "error": {
    "code": "TOKEN_EXPIRED",
    "message": "WhatsApp access token has expired",
    "details": {
      "action_required": "Reconnect WhatsApp in Settings",
      "expired_at": "2024-01-15T00:00:00Z"
    }
  }
}
```

---

## Known Limitations

### 1. Template Approval Delay

**Limitation**: Template approval can take 24-48 hours.

**Impact**: Cannot use new templates immediately.

**Workaround**: Plan template creation in advance.

---

### 2. 24-Hour Window

**Limitation**: Free-form messages only within 24h of customer message.

**Impact**: Must use templates for outbound after window expires.

**Solution**: Always start conversations with templates.

---

### 3. No Rich Media in Templates

**Limitation**: Limited media types in templates.

**Impact**: Cannot include dynamic images in template body.

**Workaround**: Use header media (static per template).

---

### 4. Single Business Number

**Limitation**: One WhatsApp Business number per tenant.

**Impact**: Cannot segment by department/brand.

**Planned**: Multi-number support.

---

## Error Recovery

### Message Failures

| Error | Recovery |
|-------|----------|
| Rate limited | Auto-retry with backoff |
| Not on WhatsApp | Mark contact, exclude from future |
| Token expired | Alert admin, require reconnect |
| Template rejected | Edit and resubmit |

### Broadcast Failures

| Error | Recovery |
|-------|----------|
| Partial failure | Continue to next recipient |
| Complete failure | Stop broadcast, alert admin |
| Rate limited | Pause and resume |

---

## Monitoring

### Key Metrics

| Metric | Alert Threshold |
|--------|-----------------|
| Delivery rate | < 90% |
| Read rate | < 50% |
| Opt-out rate | > 5% per broadcast |
| API error rate | > 2% |
| Template rejection rate | > 20% |

### Health Checks

```python
async def whatsapp_health():
    return {
        "status": "healthy",
        "checks": {
            "connection": await check_meta_connection(),
            "rate_limit": await check_rate_limit_status(),
            "pending_messages": await count_pending_messages(),
            "failed_messages_24h": await count_failed_messages(24),
            "templates": {
                "approved": await count_templates("approved"),
                "pending": await count_templates("pending"),
                "rejected": await count_templates("rejected")
            }
        }
    }
```

---

## Compliance

### Data Retention

- Message content: 90 days
- Delivery logs: 1 year
- Consent records: Indefinite

### Audit Trail

- All opt-in/opt-out logged
- Message sends tracked
- Template changes recorded

---

## Related Documentation

- [Specification](./spec.md) - Data models and architecture
- [User Flows](./user-flows.md) - Step-by-step user journeys
- [API Contracts](./api-contracts.md) - API endpoints and schemas
