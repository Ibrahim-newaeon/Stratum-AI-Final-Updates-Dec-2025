# WhatsApp Integration Specification

## Overview

The WhatsApp Integration enables tenant communication via the WhatsApp Business Cloud API. It supports contact management, template messaging, broadcast campaigns, and webhook handling for incoming messages.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  WHATSAPP INTEGRATION ARCHITECTURE              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    STRATUM PLATFORM                       │  │
│  │                                                          │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │  │
│  │  │ Contact  │ │ Template │ │ Message  │ │ Broadcast│   │  │
│  │  │ Manager  │ │  Manager │ │  Sender  │ │  Engine  │   │  │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘   │  │
│  │       │            │            │            │          │  │
│  │       └────────────┴─────┬──────┴────────────┘          │  │
│  └──────────────────────────┼───────────────────────────────┘  │
│                             ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   WHATSAPP CONNECTOR                      │  │
│  │                                                          │  │
│  │  • PII Hashing (SHA-256)                                │  │
│  │  • Rate Limiting                                         │  │
│  │  • Retry Logic                                           │  │
│  │  • Webhook Signature Verification                        │  │
│  └────────────────────────┬─────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              META WHATSAPP CLOUD API                      │  │
│  │                                                          │  │
│  │  graph.facebook.com/v18.0/{phone_number_id}/messages    │  │
│  │                                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    WEBHOOK RECEIVER                       │  │
│  │                                                          │  │
│  │  /webhooks/whatsapp ◄─── Meta Webhooks (HMAC verified)  │  │
│  │                                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Models

### WhatsAppContact

```python
class WhatsAppContact:
    id: int
    tenant_id: int
    phone_number: str              # E.164 format
    name: str | None
    email: str | None

    # Consent
    opted_in: bool = False
    opted_in_at: datetime | None
    opted_out_at: datetime | None

    # Metadata
    external_id: str | None        # CRM/CDP reference
    tags: list[str] = []
    custom_fields: dict = {}

    # Tracking
    last_message_at: datetime | None
    message_count: int = 0
    is_active: bool = True

    created_at: datetime
    updated_at: datetime
```

### WhatsAppTemplate

```python
class WhatsAppTemplate:
    id: int
    tenant_id: int
    name: str                      # Template name (unique)
    language: str = "en"           # Language code

    # Content
    category: TemplateCategory     # marketing, utility, authentication
    header: TemplateHeader | None
    body: str                      # Message body with {{variables}}
    footer: str | None
    buttons: list[TemplateButton] = []

    # Meta Status
    meta_template_id: str | None
    status: TemplateStatus         # pending, approved, rejected
    rejection_reason: str | None

    created_at: datetime
    updated_at: datetime
```

### WhatsAppMessage

```python
class WhatsAppMessage:
    id: int
    tenant_id: int
    contact_id: int
    conversation_id: int | None

    # Message Content
    direction: MessageDirection    # inbound, outbound
    message_type: MessageType      # text, template, image, document
    content: str | None
    template_name: str | None
    template_params: dict | None
    media_url: str | None

    # Meta Reference
    wamid: str | None              # WhatsApp Message ID

    # Status
    status: MessageStatus          # queued, sent, delivered, read, failed
    error_message: str | None

    created_at: datetime
    sent_at: datetime | None
    delivered_at: datetime | None
    read_at: datetime | None
```

### WhatsAppConversation

```python
class WhatsAppConversation:
    id: int
    tenant_id: int
    contact_id: int

    # Conversation Window
    started_at: datetime
    expires_at: datetime           # 24h from last customer message
    is_active: bool

    # Pricing
    conversation_type: str         # service, marketing, utility, authentication
    is_billable: bool

    # Tracking
    message_count: int
    last_message_at: datetime

    created_at: datetime
```

### WhatsAppBroadcast

```python
class WhatsAppBroadcast:
    id: int
    tenant_id: int
    name: str
    template_id: int

    # Recipients
    recipient_filter: dict         # Contact filter criteria
    recipient_count: int
    contact_ids: list[int]

    # Status
    status: BroadcastStatus        # draft, scheduled, sending, completed, failed
    scheduled_at: datetime | None

    # Results
    sent_count: int = 0
    delivered_count: int = 0
    failed_count: int = 0
    read_count: int = 0

    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
```

---

## Enums

### MessageDirection

```python
class MessageDirection(str, Enum):
    INBOUND = "inbound"
    OUTBOUND = "outbound"
```

### MessageType

```python
class MessageType(str, Enum):
    TEXT = "text"
    TEMPLATE = "template"
    IMAGE = "image"
    DOCUMENT = "document"
    AUDIO = "audio"
    VIDEO = "video"
    LOCATION = "location"
    INTERACTIVE = "interactive"
```

### MessageStatus

```python
class MessageStatus(str, Enum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    READ = "read"
    FAILED = "failed"
```

### TemplateStatus

```python
class TemplateStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    DISABLED = "disabled"
```

### TemplateCategory

```python
class TemplateCategory(str, Enum):
    MARKETING = "marketing"
    UTILITY = "utility"
    AUTHENTICATION = "authentication"
```

### BroadcastStatus

```python
class BroadcastStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

---

## Consent Management

### Opt-In Flow

```python
async def opt_in_contact(tenant_id: int, phone: str) -> WhatsAppContact:
    contact = await get_or_create_contact(tenant_id, phone)

    if contact.opted_in:
        return contact

    contact.opted_in = True
    contact.opted_in_at = datetime.now(timezone.utc)
    contact.opted_out_at = None

    await db.commit()
    await log_consent_change(contact, "opt_in")

    return contact
```

### Opt-Out Flow

```python
async def opt_out_contact(tenant_id: int, phone: str) -> WhatsAppContact:
    contact = await get_contact_by_phone(tenant_id, phone)

    if not contact or not contact.opted_in:
        return contact

    contact.opted_in = False
    contact.opted_out_at = datetime.now(timezone.utc)

    await db.commit()
    await log_consent_change(contact, "opt_out")

    return contact
```

### Automatic Opt-Out Detection

```python
# Keywords that trigger auto opt-out
OPT_OUT_KEYWORDS = ["stop", "unsubscribe", "cancel", "optout", "opt out"]

async def process_inbound_message(message: dict):
    text = message.get("text", {}).get("body", "").lower()

    if any(keyword in text for keyword in OPT_OUT_KEYWORDS):
        await opt_out_contact(tenant_id, message["from"])
        await send_opt_out_confirmation(message["from"])
```

---

## Webhook Handling

### Signature Verification

```python
import hmac
import hashlib

def verify_webhook_signature(payload: bytes, signature: str, app_secret: str) -> bool:
    """Verify Meta webhook signature (HMAC-SHA256)."""
    expected = hmac.new(
        app_secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(f"sha256={expected}", signature)
```

### Webhook Events

| Event Type | Description |
|------------|-------------|
| `messages` | Incoming message from user |
| `statuses` | Message delivery status update |
| `contacts` | Contact info update |

### Event Processing

```python
async def handle_webhook(event: dict):
    for entry in event.get("entry", []):
        for change in entry.get("changes", []):
            if change["field"] == "messages":
                value = change["value"]

                # Handle messages
                for message in value.get("messages", []):
                    await process_inbound_message(message)

                # Handle statuses
                for status in value.get("statuses", []):
                    await update_message_status(status)
```

---

## Rate Limiting

### Meta API Limits

| Tier | Messages/Second | Unique Users/24h |
|------|-----------------|------------------|
| Standard | 80 | 1,000 |
| Tier 1 | 1,000 | 10,000 |
| Tier 2 | 10,000 | 100,000 |
| Tier 3 | 100,000 | Unlimited |

### Implementation

```python
class WhatsAppRateLimiter:
    def __init__(self, messages_per_second: int = 80):
        self.rate = messages_per_second
        self.tokens = messages_per_second
        self.last_update = time.time()

    async def acquire(self):
        self._refill()
        if self.tokens < 1:
            wait_time = (1 - self.tokens) / self.rate
            await asyncio.sleep(wait_time)
            self._refill()
        self.tokens -= 1
```

---

## Template Management

### Template Variables

```python
# Template body with variables
body = "Hello {{1}}, your order {{2}} has been shipped!"

# Variable substitution
params = ["John", "ORD-12345"]
```

### Header Types

| Type | Content |
|------|---------|
| `TEXT` | Plain text header |
| `IMAGE` | Image URL or media ID |
| `DOCUMENT` | Document URL or media ID |
| `VIDEO` | Video URL or media ID |

### Button Types

| Type | Description |
|------|-------------|
| `QUICK_REPLY` | User selects predefined option |
| `URL` | Opens URL in browser |
| `PHONE_NUMBER` | Initiates phone call |
| `COPY_CODE` | Copies code to clipboard |

---

## Broadcast Engine

### Broadcast Execution

```python
async def execute_broadcast(broadcast_id: int):
    broadcast = await get_broadcast(broadcast_id)
    template = await get_template(broadcast.template_id)

    # Update status
    broadcast.status = BroadcastStatus.SENDING
    broadcast.started_at = datetime.now(timezone.utc)
    await db.commit()

    # Get opted-in contacts
    contacts = await get_broadcast_recipients(broadcast)

    # Send messages with rate limiting
    for contact in contacts:
        try:
            await send_template_message(contact, template)
            broadcast.sent_count += 1
        except Exception as e:
            broadcast.failed_count += 1
            logger.error(f"Broadcast send failed: {e}")

        # Rate limit
        await rate_limiter.acquire()

    # Update completion
    broadcast.status = BroadcastStatus.COMPLETED
    broadcast.completed_at = datetime.now(timezone.utc)
    await db.commit()
```

---

## Security

### PII Handling

- Phone numbers stored as-is (required for API)
- Names and emails optional
- Custom fields can be encrypted

### Webhook Security

- HMAC-SHA256 signature verification
- IP allowlisting (Meta IPs)
- Rate limiting on webhook endpoint

### Access Control

- Tenant isolation enforced
- Role-based access to broadcasts
- Audit logging for all actions

---

## Related Documentation

- [User Flows](./user-flows.md) - Step-by-step user journeys
- [API Contracts](./api-contracts.md) - API endpoints and schemas
- [Edge Cases](./edge-cases.md) - Error handling and edge cases
