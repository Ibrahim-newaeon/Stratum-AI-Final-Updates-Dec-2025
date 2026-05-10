# WhatsApp Integration API Contracts

## Overview

API endpoints for WhatsApp Business Cloud API integration.

**Base URL**: `/api/v1/tenant/{tenant_id}/whatsapp`

---

## Authentication

All endpoints require Bearer token authentication with tenant context.

---

## Contacts

### GET /whatsapp/contacts

List WhatsApp contacts.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `page` | integer | Page number (default: 1) |
| `page_size` | integer | Items per page (default: 20) |
| `opted_in` | boolean | Filter by opt-in status |
| `tags` | string | Comma-separated tags filter |
| `search` | string | Search by name or phone |

#### Response

```json
{
  "success": true,
  "data": {
    "items": [
      {
        "id": 1,
        "phone_number": "+15551234567",
        "name": "John Doe",
        "email": "john@example.com",
        "opted_in": true,
        "opted_in_at": "2024-01-15T10:00:00Z",
        "tags": ["customer", "vip"],
        "last_message_at": "2024-01-15T14:30:00Z",
        "message_count": 5
      }
    ],
    "total": 1234,
    "page": 1,
    "page_size": 20
  }
}
```

### POST /whatsapp/contacts

Create a new contact.

#### Request

```json
{
  "phone_number": "+15551234567",
  "name": "John Doe",
  "email": "john@example.com",
  "opted_in": true,
  "tags": ["customer"],
  "custom_fields": {
    "customer_id": "CUST-123"
  }
}
```

### POST /whatsapp/contacts/import

Bulk import contacts.

#### Request

```json
{
  "contacts": [
    {
      "phone_number": "+15551234567",
      "name": "John Doe",
      "opted_in": true
    },
    {
      "phone_number": "+15559876543",
      "name": "Jane Smith",
      "opted_in": true
    }
  ],
  "default_opted_in": true,
  "skip_duplicates": true
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "imported": 150,
    "skipped": 10,
    "errors": 2,
    "error_details": [
      {"row": 45, "phone": "+1555", "error": "Invalid phone format"}
    ]
  }
}
```

### POST /whatsapp/contacts/{contact_id}/opt-in

Mark contact as opted in.

#### Response

```json
{
  "success": true,
  "data": {
    "contact_id": 1,
    "opted_in": true,
    "opted_in_at": "2024-01-15T14:30:00Z"
  }
}
```

### POST /whatsapp/contacts/{contact_id}/opt-out

Mark contact as opted out.

#### Response

```json
{
  "success": true,
  "data": {
    "contact_id": 1,
    "opted_in": false,
    "opted_out_at": "2024-01-15T14:30:00Z"
  }
}
```

---

## Templates

### GET /whatsapp/templates

List message templates.

#### Response

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "order_shipped",
      "language": "en",
      "category": "utility",
      "status": "approved",
      "body": "Hello {{1}}, your order {{2}} has been shipped!",
      "header": {"type": "text", "text": "Order Update"},
      "footer": "Reply STOP to unsubscribe",
      "buttons": [],
      "meta_template_id": "123456789",
      "created_at": "2024-01-10T10:00:00Z"
    }
  ]
}
```

### POST /whatsapp/templates

Create and submit template for approval.

#### Request

```json
{
  "name": "order_shipped",
  "language": "en",
  "category": "utility",
  "header": {
    "type": "text",
    "text": "Order Update"
  },
  "body": "Hello {{1}}, your order {{2}} has been shipped! Track at: {{3}}",
  "footer": "Reply STOP to unsubscribe",
  "buttons": [
    {
      "type": "url",
      "text": "Track Order",
      "url": "https://example.com/track/{{1}}"
    }
  ]
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "order_shipped",
    "status": "pending",
    "meta_template_id": "123456789"
  },
  "message": "Template submitted for Meta approval"
}
```

### DELETE /whatsapp/templates/{template_id}

Delete a template.

#### Response

```
HTTP 204 No Content
```

---

## Messages

### POST /whatsapp/messages

Send a message to a contact.

#### Request (Template Message)

```json
{
  "contact_id": 1,
  "template_name": "order_shipped",
  "template_params": ["John", "ORD-12345", "https://track.example.com/123"]
}
```

#### Request (Text Message - within 24h window)

```json
{
  "contact_id": 1,
  "message_type": "text",
  "content": "Hi John, how can we help you today?"
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "message_id": 123,
    "wamid": "wamid.HBgL...",
    "status": "sent",
    "sent_at": "2024-01-15T14:30:00Z"
  }
}
```

### GET /whatsapp/messages

Get message history.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `contact_id` | integer | Filter by contact |
| `direction` | string | inbound, outbound |
| `status` | string | sent, delivered, read, failed |
| `since` | datetime | Messages after this time |

#### Response

```json
{
  "success": true,
  "data": [
    {
      "id": 123,
      "contact_id": 1,
      "direction": "outbound",
      "message_type": "template",
      "template_name": "order_shipped",
      "status": "delivered",
      "sent_at": "2024-01-15T14:30:00Z",
      "delivered_at": "2024-01-15T14:30:05Z"
    }
  ]
}
```

---

## Conversations

### GET /whatsapp/conversations

List active conversations.

#### Response

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "contact_id": 1,
      "contact_name": "John Doe",
      "contact_phone": "+15551234567",
      "is_active": true,
      "started_at": "2024-01-15T14:00:00Z",
      "expires_at": "2024-01-16T14:00:00Z",
      "last_message": "Where's my order?",
      "last_message_at": "2024-01-15T14:30:00Z",
      "unread_count": 1
    }
  ]
}
```

### GET /whatsapp/conversations/{conversation_id}/messages

Get conversation message thread.

#### Response

```json
{
  "success": true,
  "data": {
    "conversation": {
      "id": 1,
      "contact_name": "John Doe",
      "is_active": true,
      "expires_at": "2024-01-16T14:00:00Z"
    },
    "messages": [
      {
        "id": 1,
        "direction": "outbound",
        "content": "Your order has been shipped!",
        "status": "delivered",
        "timestamp": "2024-01-15T14:00:00Z"
      },
      {
        "id": 2,
        "direction": "inbound",
        "content": "Where's my order?",
        "timestamp": "2024-01-15T14:30:00Z"
      }
    ]
  }
}
```

---

## Broadcasts

### GET /whatsapp/broadcasts

List broadcast campaigns.

#### Response

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "January Newsletter",
      "template_name": "monthly_newsletter",
      "status": "completed",
      "recipient_count": 1234,
      "sent_count": 1180,
      "delivered_count": 1120,
      "read_count": 845,
      "failed_count": 54,
      "scheduled_at": null,
      "started_at": "2024-01-15T10:00:00Z",
      "completed_at": "2024-01-15T10:25:00Z"
    }
  ]
}
```

### POST /whatsapp/broadcasts

Create a broadcast campaign.

#### Request

```json
{
  "name": "January Newsletter",
  "template_id": 1,
  "template_params": ["January", "https://example.com/newsletter"],
  "recipient_filter": {
    "tags": ["customer", "newsletter"],
    "opted_in": true,
    "last_message_days_ago": 30
  },
  "scheduled_at": "2024-01-15T10:00:00Z"
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "January Newsletter",
    "status": "scheduled",
    "recipient_count": 1234,
    "scheduled_at": "2024-01-15T10:00:00Z"
  }
}
```

### POST /whatsapp/broadcasts/{broadcast_id}/send

Execute broadcast immediately.

#### Response

```json
{
  "success": true,
  "data": {
    "id": 1,
    "status": "sending",
    "started_at": "2024-01-15T14:30:00Z"
  }
}
```

### POST /whatsapp/broadcasts/{broadcast_id}/cancel

Cancel scheduled or running broadcast.

#### Response

```json
{
  "success": true,
  "data": {
    "id": 1,
    "status": "cancelled",
    "messages_sent": 500,
    "messages_cancelled": 734
  }
}
```

---

## Webhooks

### POST /webhooks/whatsapp

Receive Meta webhook events (public endpoint).

#### Headers

| Header | Description |
|--------|-------------|
| `X-Hub-Signature-256` | HMAC-SHA256 signature |

#### Verification Request

```
GET /webhooks/whatsapp?hub.mode=subscribe&hub.verify_token=TOKEN&hub.challenge=CHALLENGE
```

#### Event Payload

```json
{
  "object": "whatsapp_business_account",
  "entry": [
    {
      "id": "BUSINESS_ACCOUNT_ID",
      "changes": [
        {
          "field": "messages",
          "value": {
            "messaging_product": "whatsapp",
            "messages": [
              {
                "from": "15551234567",
                "id": "wamid.HBgL...",
                "timestamp": "1705329600",
                "type": "text",
                "text": {"body": "Hello"}
              }
            ]
          }
        }
      ]
    }
  ]
}
```

---

## Error Responses

### Error Format

```json
{
  "success": false,
  "error": {
    "code": "CONTACT_NOT_OPTED_IN",
    "message": "Contact has not opted in to receive messages",
    "details": {
      "contact_id": 1,
      "phone": "+15551234567"
    }
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `CONTACT_NOT_FOUND` | 404 | Contact not found |
| `CONTACT_NOT_OPTED_IN` | 400 | Contact not opted in |
| `TEMPLATE_NOT_APPROVED` | 400 | Template not approved by Meta |
| `CONVERSATION_EXPIRED` | 400 | 24h window expired |
| `RATE_LIMIT_EXCEEDED` | 429 | WhatsApp rate limit |
| `INVALID_PHONE_FORMAT` | 400 | Invalid phone number |
| `WEBHOOK_SIGNATURE_INVALID` | 401 | Invalid webhook signature |

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| GET endpoints | 120/min |
| Send message | 80/min (Meta limit) |
| Broadcast creation | 10/hour |
| Contact import | 5/min |

---

## Related Documentation

- [Specification](./spec.md) - Data models and architecture
- [User Flows](./user-flows.md) - Step-by-step user journeys
- [Edge Cases](./edge-cases.md) - Error handling and edge cases
