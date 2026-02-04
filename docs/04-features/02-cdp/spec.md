# CDP (Customer Data Platform) Specification

## Overview

The Stratum CDP is a comprehensive Customer Data Platform that unifies customer profiles across all touchpoints, enabling identity resolution, behavioral segmentation, and audience activation.

---

## Core Capabilities

| Capability | Description |
|------------|-------------|
| **Unified Profiles** | Single customer view from anonymous to customer lifecycle |
| **Identity Resolution** | Merge cross-device and cross-channel identifiers |
| **Event Ingestion** | Real-time append-only event store |
| **Segmentation** | Dynamic behavioral segments with rule builder |
| **Computed Traits** | Derived attributes (RFM, totals, averages) |
| **Funnels** | Conversion funnel analysis |
| **Consent Management** | GDPR/CCPA compliant consent tracking |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       CDP ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    DATA SOURCES                           │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │  │
│  │  │ Website  │ │ Server   │ │  SGTM    │ │   CRM    │     │  │
│  │  │  Pixel   │ │   API    │ │          │ │  Import  │     │  │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘     │  │
│  └───────┼────────────┼────────────┼────────────┼───────────┘  │
│          │            │            │            │               │
│          └────────────┴────────────┴────────────┘               │
│                          │                                      │
│                          ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │               EVENT INGESTION LAYER                       │  │
│  │  • Rate limiting (100 req/min)                           │  │
│  │  • Deduplication via idempotency_key                     │  │
│  │  • Source key authentication                             │  │
│  │  • EMQ scoring                                           │  │
│  └───────────────────────┬──────────────────────────────────┘  │
│                          │                                      │
│                          ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              IDENTITY RESOLUTION ENGINE                   │  │
│  │  • Identifier hashing (SHA256)                           │  │
│  │  • Profile matching & merging                            │  │
│  │  • Canonical identity selection                          │  │
│  │  • Merge history tracking                                │  │
│  └───────────────────────┬──────────────────────────────────┘  │
│                          │                                      │
│                          ▼                                      │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                 UNIFIED PROFILES                          │  │
│  │  • Profile data (JSON)                                   │  │
│  │  • Computed traits                                       │  │
│  │  • Lifecycle stage                                       │  │
│  │  • Aggregated metrics                                    │  │
│  └───────────────────────┬──────────────────────────────────┘  │
│                          │                                      │
│          ┌───────────────┼───────────────┐                     │
│          ▼               ▼               ▼                     │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐           │
│  │  Segments    │ │   Funnels    │ │  Audience    │           │
│  │              │ │              │ │    Sync      │           │
│  └──────────────┘ └──────────────┘ └──────────────┘           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Models

### CDPProfile

The unified customer profile aggregating all known data about a customer.

```python
class CDPProfile:
    id: UUID                      # Primary key
    tenant_id: int                # Multi-tenant isolation
    external_id: str | None       # Client's customer ID

    # Timestamps
    first_seen_at: datetime
    last_seen_at: datetime

    # Flexible data
    profile_data: dict            # Custom attributes
    computed_traits: dict         # Derived values (RFM, totals)

    # Lifecycle
    lifecycle_stage: LifecycleStage  # anonymous, known, customer, churned

    # Aggregated counters (denormalized)
    total_events: int
    total_sessions: int
    total_purchases: int
    total_revenue: Decimal

    # Relationships
    identifiers: list[CDPProfileIdentifier]
    events: list[CDPEvent]
    consents: list[CDPConsent]
```

### Lifecycle Stages

| Stage | Criteria |
|-------|----------|
| `anonymous` | No PII collected, only device/session IDs |
| `known` | Email or phone collected |
| `customer` | Has made at least one purchase |
| `churned` | Inactive for configured period (default: 90 days) |

### CDPProfileIdentifier

Links identifiers (email, phone, device) to profiles with hashing for privacy.

```python
class CDPProfileIdentifier:
    id: UUID
    profile_id: UUID
    identifier_type: IdentifierType  # email, phone, device_id, etc.
    identifier_value: str | None     # Original (can be redacted)
    identifier_hash: str             # SHA256 hash for matching
    is_primary: bool
    confidence_score: Decimal        # 0.00 - 1.00
    verified_at: datetime | None
```

### Identifier Types

| Type | Priority | Description |
|------|----------|-------------|
| `external_id` | 100 | Customer ID from client system |
| `email` | 80 | Email address (strongest common) |
| `phone` | 70 | Phone number |
| `device_id` | 40 | Device fingerprint |
| `anonymous_id` | 10 | Cookie/session ID (weakest) |

### CDPEvent

Append-only event store for behavioral data.

```python
class CDPEvent:
    id: UUID
    profile_id: UUID | None       # Linked profile (if identifiable)
    source_id: UUID | None        # Data source that sent the event

    # Event data
    event_name: str               # e.g., "PageView", "Purchase"
    event_time: datetime          # When event occurred
    received_at: datetime         # When CDP received it

    # Deduplication
    idempotency_key: str | None

    # Payload
    properties: dict              # Event-specific data
    context: dict                 # User agent, IP, campaign, etc.
    identifiers: list             # Identifiers sent with event

    # Processing
    processed: bool
    emq_score: Decimal | None     # Event Match Quality score
```

### CDPSegment

Dynamic customer segments based on behavioral rules.

```python
class CDPSegment:
    id: UUID
    name: str
    description: str | None
    slug: str                     # URL-friendly identifier

    segment_type: SegmentType     # static, dynamic, computed
    status: SegmentStatus         # draft, computing, active, stale

    # Rules (JSON structure)
    rules: dict                   # {"logic": "and", "conditions": [...]}

    # Metrics
    profile_count: int
    last_computed_at: datetime
    computation_duration_ms: int

    # Scheduling
    auto_refresh: bool
    refresh_interval_hours: int
    next_refresh_at: datetime
```

### Segment Rule Structure

```json
{
  "logic": "and",
  "conditions": [
    {
      "field": "lifecycle_stage",
      "operator": "equals",
      "value": "customer"
    },
    {
      "field": "computed_traits.total_purchases",
      "operator": "greater_than",
      "value": 3
    },
    {
      "field": "event",
      "event_name": "Purchase",
      "operator": "within_last",
      "value": 30,
      "unit": "days"
    }
  ],
  "groups": [
    {
      "logic": "or",
      "conditions": [
        {
          "field": "profile_data.country",
          "operator": "in",
          "value": ["US", "CA", "UK"]
        }
      ]
    }
  ]
}
```

### Condition Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `equals` | Exact match | `country = "US"` |
| `not_equals` | Not equal | `status != "churned"` |
| `contains` | String contains | `email contains "@gmail"` |
| `greater_than` | Numeric comparison | `purchases > 5` |
| `less_than` | Numeric comparison | `age < 30` |
| `between` | Range | `revenue between [100, 1000]` |
| `in` | In list | `country in ["US", "CA"]` |
| `within_last` | Time window | `event within_last 30 days` |
| `before` / `after` | Date comparison | `signup before "2024-01-01"` |

---

## Identity Resolution

### Resolution Flow

```
┌──────────────────────────────────────────────────────────────┐
│                  IDENTITY RESOLUTION FLOW                     │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Event arrives with identifiers                           │
│     ┌────────────────────────────────────────────────────┐  │
│     │ identifiers: [                                     │  │
│     │   {type: "anonymous_id", value: "abc123"},         │  │
│     │   {type: "email", value: "user@example.com"}       │  │
│     │ ]                                                  │  │
│     └────────────────────────────────────────────────────┘  │
│                          │                                   │
│                          ▼                                   │
│  2. Hash identifiers                                         │
│     email_hash = SHA256("user@example.com")                  │
│                          │                                   │
│                          ▼                                   │
│  3. Search for existing profiles                             │
│     Query: identifier_hash IN (email_hash, anon_hash)        │
│                          │                                   │
│         ┌────────────────┴────────────────┐                 │
│         ▼                                  ▼                 │
│  ┌─────────────────┐              ┌─────────────────┐       │
│  │  0 matches      │              │  1+ matches     │       │
│  │  Create new     │              │  Link/Merge     │       │
│  │  profile        │              │  profiles       │       │
│  └────────┬────────┘              └────────┬────────┘       │
│           │                                │                 │
│           └────────────────┬───────────────┘                │
│                            ▼                                 │
│  4. Update canonical identity                                │
│     Select strongest identifier as canonical                 │
│                            │                                 │
│                            ▼                                 │
│  5. Record event and update profile                          │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Profile Merging

When two profiles are identified as the same person:

1. **Select surviving profile** - Older profile typically survives
2. **Transfer identifiers** - Move all identifiers to surviving profile
3. **Merge events** - Reassign events to surviving profile
4. **Combine metrics** - Sum counters, merge attributes
5. **Record merge** - Create audit trail in `cdp_profile_merges`
6. **Delete merged profile** - Remove the absorbed profile

### Canonical Identity

Each profile has one "golden" canonical identity:

- Selected based on identifier type priority (external_id > email > phone > device)
- Used for audience sync matching
- Updated when stronger identifier is collected

---

## EMQ (Event Match Quality)

CDP contributes to the Trust Engine's signal health through EMQ scoring.

### EMQ Components

| Component | Weight | Description |
|-----------|--------|-------------|
| Identifier Quality | 35% | Presence of high-priority identifiers |
| Data Completeness | 25% | Required fields present |
| Timeliness | 20% | Time between occurrence and receipt |
| Context Richness | 20% | Additional context data provided |

### EMQ Score Calculation

```python
def calculate_emq(event: CDPEvent) -> float:
    identifier_score = calculate_identifier_quality(event.identifiers)
    completeness_score = calculate_data_completeness(event.properties)
    timeliness_score = calculate_timeliness(event.event_time, event.received_at)
    context_score = calculate_context_richness(event.context)

    return (
        identifier_score * 0.35 +
        completeness_score * 0.25 +
        timeliness_score * 0.20 +
        context_score * 0.20
    )
```

---

## Computed Traits

Derived values calculated from profile events.

### Trait Types

| Type | Description | Example |
|------|-------------|---------|
| `count` | Count of events | `total_page_views` |
| `sum` | Sum of property values | `total_revenue` |
| `average` | Average of property values | `avg_order_value` |
| `min` / `max` | Extreme values | `max_purchase_amount` |
| `first` / `last` | First/last occurrence | `first_purchase_date` |
| `unique_count` | Count of unique values | `unique_products_viewed` |
| `exists` | Boolean existence | `has_made_purchase` |

### RFM Analysis

Built-in RFM (Recency, Frequency, Monetary) scoring:

```python
class RFMConfig:
    recency_event: str = "Purchase"
    frequency_event: str = "Purchase"
    monetary_property: str = "total"
    lookback_days: int = 365
    quintile_scoring: bool = True  # 1-5 scores

class RFMScores:
    recency_score: int      # 1-5 (5 = most recent)
    frequency_score: int    # 1-5 (5 = most frequent)
    monetary_score: int     # 1-5 (5 = highest spend)
    rfm_segment: str        # "Champions", "At Risk", etc.
```

### RFM Segments

| Segment | R | F | M | Description |
|---------|---|---|---|-------------|
| Champions | 5 | 5 | 5 | Best customers |
| Loyal | 4-5 | 4-5 | 4-5 | Regular high-value |
| Potential Loyal | 4-5 | 2-3 | 2-3 | Recent, moderate |
| New | 5 | 1 | 1 | Very recent, first purchase |
| At Risk | 2-3 | 4-5 | 4-5 | High-value, becoming inactive |
| Hibernating | 1-2 | 1-2 | 1-2 | Low across all |

---

## Funnels

Conversion funnel analysis for user journey tracking.

### Funnel Definition

```python
class CDPFunnel:
    name: str
    steps: list[FunnelStep]
    conversion_window_days: int = 30
    step_timeout_hours: int | None

class FunnelStep:
    step_name: str
    event_name: str
    conditions: list[Condition] | None
```

### Example Funnel

```json
{
  "name": "Purchase Funnel",
  "steps": [
    {"step_name": "View Product", "event_name": "ProductView"},
    {"step_name": "Add to Cart", "event_name": "AddToCart"},
    {"step_name": "Begin Checkout", "event_name": "BeginCheckout"},
    {"step_name": "Complete Purchase", "event_name": "Purchase"}
  ],
  "conversion_window_days": 7
}
```

### Funnel Metrics

| Metric | Description |
|--------|-------------|
| Total Entered | Users who completed step 1 |
| Total Converted | Users who completed all steps |
| Overall Conversion Rate | Converted / Entered × 100 |
| Step Conversion Rate | Step N completions / Step N-1 completions |
| Drop-off Rate | 1 - Step Conversion Rate |
| Avg Time to Convert | Average duration from first to last step |

---

## Consent Management

GDPR/CCPA compliant consent tracking.

### Consent Types

| Type | Description |
|------|-------------|
| `analytics` | Analytics and tracking |
| `ads` | Advertising and targeting |
| `email` | Email marketing |
| `sms` | SMS marketing |
| `all` | Global consent toggle |

### Consent Record

```python
class CDPConsent:
    profile_id: UUID
    consent_type: ConsentType
    granted: bool
    granted_at: datetime | None
    revoked_at: datetime | None
    source: str                   # Where consent was collected
    ip_address: str | None        # For audit
    consent_text: str | None      # Exact text shown
    consent_version: str | None   # Version tracking
```

---

## Webhooks

Real-time notifications for CDP events.

### Webhook Event Types

| Event | Trigger |
|-------|---------|
| `event.received` | New event ingested |
| `profile.created` | New profile created |
| `profile.updated` | Profile data changed |
| `profile.merged` | Profiles merged |
| `consent.updated` | Consent status changed |

### Webhook Payload

```json
{
  "event_type": "profile.created",
  "timestamp": "2024-01-15T14:32:18Z",
  "data": {
    "profile_id": "uuid-...",
    "lifecycle_stage": "known",
    "identifiers": [
      {"type": "email", "hash": "sha256..."}
    ]
  },
  "signature": "HMAC-SHA256..."
}
```

---

## Rate Limits

| Operation | Limit | Notes |
|-----------|-------|-------|
| Event ingestion | 100/min | Per tenant, batch allowed |
| Profile lookups | 300/min | Per tenant |
| Source operations | 30/min | Per tenant |
| Webhook operations | 30/min | Per tenant |

---

## Related Documentation

- [User Flows](./user-flows.md) - Step-by-step user journeys
- [API Contracts](./api-contracts.md) - API endpoints and schemas
- [Edge Cases](./edge-cases.md) - Error handling and edge cases
- [Audience Sync](../03-audience-sync/spec.md) - Platform audience syncing
