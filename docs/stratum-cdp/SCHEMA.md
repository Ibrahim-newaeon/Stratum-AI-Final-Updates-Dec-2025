# Stratum CDP - Database Schema

> Simplified schema for MVP. All tables are multi-tenant with `tenant_id` column.

---

## Table Overview

| Table | Purpose | Retention |
|-------|---------|-----------|
| `cdp_sources` | Data source configurations | Permanent |
| `cdp_profiles` | Unified customer profiles | Permanent |
| `cdp_profile_identifiers` | Identity mappings (email, phone, device) | Permanent |
| `cdp_events` | Append-only event store | 13 months rolling |
| `cdp_consents` | Privacy consent records | Permanent |

---

## 1. cdp_sources

Tracks data sources that send events to the CDP.

```sql
CREATE TABLE cdp_sources (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    name            VARCHAR(255) NOT NULL,
    source_type     VARCHAR(50) NOT NULL,  -- 'website', 'server', 'sgtm', 'import', 'crm'
    source_key      VARCHAR(64) NOT NULL,  -- API key for this source

    config          JSONB DEFAULT '{}',    -- Source-specific configuration
    is_active       BOOLEAN DEFAULT TRUE,

    event_count     BIGINT DEFAULT 0,      -- Running count of events
    last_event_at   TIMESTAMPTZ,           -- Last event received

    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(tenant_id, source_key)
);

CREATE INDEX idx_cdp_sources_tenant ON cdp_sources(tenant_id);
CREATE INDEX idx_cdp_sources_key ON cdp_sources(source_key);
```

**Notes:**
- `source_type` values: `website` (pixel), `server` (API), `sgtm` (Server GTM), `import` (CSV), `crm` (CRM sync)
- `config` stores source-specific settings (e.g., allowed domains, IP whitelist)
- `source_key` is used to authenticate incoming events

---

## 2. cdp_profiles

Unified customer profile - one row per unique customer.

```sql
CREATE TABLE cdp_profiles (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,

    external_id         VARCHAR(255),          -- Client's customer ID (optional)

    first_seen_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Aggregated profile data
    profile_data        JSONB DEFAULT '{}',    -- Flexible attributes
    computed_traits     JSONB DEFAULT '{}',    -- Computed/derived traits

    lifecycle_stage     VARCHAR(50) DEFAULT 'anonymous',  -- anonymous, known, customer, churned

    -- Counters
    total_events        INTEGER DEFAULT 0,
    total_sessions      INTEGER DEFAULT 0,
    total_purchases     INTEGER DEFAULT 0,
    total_revenue       DECIMAL(15,2) DEFAULT 0,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(tenant_id, external_id) WHERE external_id IS NOT NULL
);

CREATE INDEX idx_cdp_profiles_tenant ON cdp_profiles(tenant_id);
CREATE INDEX idx_cdp_profiles_external ON cdp_profiles(tenant_id, external_id) WHERE external_id IS NOT NULL;
CREATE INDEX idx_cdp_profiles_lifecycle ON cdp_profiles(tenant_id, lifecycle_stage);
CREATE INDEX idx_cdp_profiles_last_seen ON cdp_profiles(tenant_id, last_seen_at DESC);
```

**Notes:**
- `profile_data` stores flexible attributes (name, preferences, etc.)
- `computed_traits` stores derived data (LTV prediction, churn score, etc.)
- `lifecycle_stage` tracks customer journey stage
- Counters denormalized for fast dashboard queries

**profile_data Example:**
```json
{
  "first_name": "Ahmed",
  "last_name": "Al-Rashid",
  "city": "Dubai",
  "country": "AE",
  "preferred_language": "ar",
  "acquisition_source": "google_ads",
  "first_purchase_date": "2025-03-15"
}
```

---

## 3. cdp_profile_identifiers

Maps identifiers (email, phone, device) to profiles.

```sql
CREATE TABLE cdp_profile_identifiers (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    profile_id          UUID NOT NULL REFERENCES cdp_profiles(id) ON DELETE CASCADE,

    identifier_type     VARCHAR(50) NOT NULL,  -- 'email', 'phone', 'device_id', 'anonymous_id', 'external_id'
    identifier_value    VARCHAR(512),          -- Original value (nullable, may be redacted)
    identifier_hash     VARCHAR(64) NOT NULL,  -- SHA256 hash of normalized value

    is_primary          BOOLEAN DEFAULT FALSE, -- Primary identifier for this type
    confidence_score    DECIMAL(3,2) DEFAULT 1.0,  -- 0.00-1.00 confidence

    verified_at         TIMESTAMPTZ,           -- When identity was verified (e.g., email confirmation)
    first_seen_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(tenant_id, identifier_type, identifier_hash)
);

CREATE INDEX idx_cdp_identifiers_tenant ON cdp_profile_identifiers(tenant_id);
CREATE INDEX idx_cdp_identifiers_profile ON cdp_profile_identifiers(profile_id);
CREATE INDEX idx_cdp_identifiers_lookup ON cdp_profile_identifiers(tenant_id, identifier_type, identifier_hash);
CREATE INDEX idx_cdp_identifiers_hash ON cdp_profile_identifiers(identifier_hash);
```

**Notes:**
- `identifier_value` stores original value (can be NULL for privacy-first mode)
- `identifier_hash` is SHA256 of normalized value (always stored)
- Unique constraint on (tenant_id, identifier_type, identifier_hash) prevents duplicate mappings
- `confidence_score` for probabilistic matching (future use)

**Identifier Types:**
| Type | Normalization | Example |
|------|---------------|---------|
| `email` | Lowercase, trim | `user@example.com` |
| `phone` | E.164 format | `+971501234567` |
| `device_id` | As-is | `ABC123-DEF456` |
| `anonymous_id` | As-is | `anon_abc123` |
| `external_id` | As-is | `CRM-12345` |

---

## 4. cdp_events

Append-only event store. Never update or delete raw events.

```sql
CREATE TABLE cdp_events (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    profile_id          UUID REFERENCES cdp_profiles(id) ON DELETE SET NULL,
    source_id           UUID REFERENCES cdp_sources(id) ON DELETE SET NULL,

    -- Event identification
    event_name          VARCHAR(255) NOT NULL,
    event_time          TIMESTAMPTZ NOT NULL,
    received_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Deduplication
    idempotency_key     VARCHAR(128),          -- Client-provided dedup key

    -- Event data
    properties          JSONB DEFAULT '{}',    -- Event-specific properties
    context             JSONB DEFAULT '{}',    -- Device, geo, page context
    identifiers         JSONB DEFAULT '[]',    -- Identifiers sent with event

    -- Processing status
    processed           BOOLEAN DEFAULT FALSE,
    processing_errors   JSONB DEFAULT '[]',

    -- EMQ (Event Match Quality)
    emq_score           DECIMAL(5,2),          -- 0-100 quality score

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()

    -- Note: No updated_at - events are immutable
);

-- Partition by month for efficient retention and queries
-- In production, use native partitioning:
-- PARTITION BY RANGE (event_time)

CREATE INDEX idx_cdp_events_tenant ON cdp_events(tenant_id);
CREATE INDEX idx_cdp_events_profile ON cdp_events(profile_id);
CREATE INDEX idx_cdp_events_name ON cdp_events(tenant_id, event_name);
CREATE INDEX idx_cdp_events_time ON cdp_events(tenant_id, event_time DESC);
CREATE INDEX idx_cdp_events_idempotency ON cdp_events(tenant_id, idempotency_key) WHERE idempotency_key IS NOT NULL;
CREATE INDEX idx_cdp_events_source ON cdp_events(source_id);
CREATE INDEX idx_cdp_events_received ON cdp_events(received_at DESC);
```

**Notes:**
- **Append-only**: Never UPDATE or DELETE event rows
- **Partitioning**: Partition by `event_time` monthly in production
- **Retention**: Delete partitions older than 13 months
- `idempotency_key` prevents duplicate events (TTL: 24 hours)
- `emq_score` tracks event quality (signal health integration)

**Partitioning Strategy:**
```sql
-- Example partition creation (run monthly via cron)
CREATE TABLE cdp_events_2026_01 PARTITION OF cdp_events
    FOR VALUES FROM ('2026-01-01') TO ('2026-02-01');

CREATE TABLE cdp_events_2026_02 PARTITION OF cdp_events
    FOR VALUES FROM ('2026-02-01') TO ('2026-03-01');
```

**Retention Job:**
```sql
-- Drop partitions older than 13 months
DROP TABLE IF EXISTS cdp_events_2024_12;
```

---

## 5. cdp_consents

Tracks privacy consent per profile per consent type.

```sql
CREATE TABLE cdp_consents (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id           INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    profile_id          UUID NOT NULL REFERENCES cdp_profiles(id) ON DELETE CASCADE,

    consent_type        VARCHAR(50) NOT NULL,  -- 'analytics', 'ads', 'email', 'sms', 'all'

    granted             BOOLEAN NOT NULL,
    granted_at          TIMESTAMPTZ,           -- When consent was granted
    revoked_at          TIMESTAMPTZ,           -- When consent was revoked

    source              VARCHAR(100),          -- Where consent was collected
    ip_address          VARCHAR(45),           -- IP at time of consent
    user_agent          VARCHAR(512),          -- UA at time of consent

    -- Audit trail
    consent_text        TEXT,                  -- Legal text shown to user
    consent_version     VARCHAR(50),           -- Version of consent form

    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    UNIQUE(tenant_id, profile_id, consent_type)
);

CREATE INDEX idx_cdp_consents_tenant ON cdp_consents(tenant_id);
CREATE INDEX idx_cdp_consents_profile ON cdp_consents(profile_id);
CREATE INDEX idx_cdp_consents_type ON cdp_consents(tenant_id, consent_type, granted);
```

**Notes:**
- One row per (profile, consent_type) - updated on change
- `consent_type` values: `analytics`, `ads`, `email`, `sms`, `all`
- Store audit info (IP, UA, text, version) for compliance
- Query for consent before data processing/export

---

## Event Spec (Minimal)

### Required Fields
```json
{
  "event_name": "string (required)",
  "event_time": "ISO8601 timestamp (required)",
  "identifiers": [
    {
      "type": "string (required)",
      "value": "string (required)"
    }
  ]
}
```

### Full Event Schema
```json
{
  "event_name": "PageView",
  "event_time": "2026-01-13T15:30:00Z",
  "idempotency_key": "evt_abc123_1705159800",

  "identifiers": [
    {"type": "anonymous_id", "value": "anon_xyz789"},
    {"type": "email", "value": "user@example.com"}
  ],

  "properties": {
    "page_url": "/products/milano-sofa",
    "page_title": "Milano Sofa | Stratum Store",
    "referrer": "https://google.com",
    "product_id": "SKU-12345",
    "product_name": "Milano Sofa",
    "product_price": 2499.00,
    "product_currency": "AED"
  },

  "context": {
    "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)...",
    "ip": "185.23.45.67",
    "locale": "ar-AE",
    "timezone": "Asia/Dubai",
    "screen": {"width": 390, "height": 844},
    "campaign": {
      "source": "google",
      "medium": "cpc",
      "campaign": "spring_sale_2026"
    }
  },

  "consent": {
    "analytics": true,
    "ads": true
  }
}
```

---

## Deduplication Approach

### Idempotency Key
- Client provides `idempotency_key` (recommended format: `{source}_{event_name}_{user_id}_{timestamp}`)
- Server checks for existing event with same key within TTL
- TTL: 24 hours (configurable per tenant)

### Implementation
```python
async def check_duplicate(tenant_id: int, idempotency_key: str) -> bool:
    """Check if event with same key exists within TTL."""
    ttl_hours = 24
    cutoff = datetime.utcnow() - timedelta(hours=ttl_hours)

    result = await db.execute(
        select(CDPEvent.id)
        .where(
            CDPEvent.tenant_id == tenant_id,
            CDPEvent.idempotency_key == idempotency_key,
            CDPEvent.received_at >= cutoff
        )
        .limit(1)
    )
    return result.scalar_one_or_none() is not None
```

---

## Multi-Tenant Isolation

### Row-Level Security
- All tables have `tenant_id` column with FK to `tenants`
- All queries filter by `tenant_id`
- Cascade delete ensures cleanup when tenant deleted

### API Enforcement
```python
# All CDP endpoints extract tenant from JWT
@router.post("/events")
async def ingest_events(
    events: EventBatchIngest,
    db: AsyncSession = Depends(get_async_session),
    current_user: User = Depends(get_current_user),
):
    tenant_id = current_user.tenant_id  # Enforced at auth layer

    for event in events.events:
        # All operations scoped to tenant_id
        await process_event(db, tenant_id, event)
```

### Index Strategy
All primary indexes include `tenant_id` first:
- `(tenant_id, identifier_hash)` - identifier lookup
- `(tenant_id, event_name)` - event queries
- `(tenant_id, profile_id)` - profile queries

---

## Data Retention Rules

| Data Type | Retention | Cleanup Method |
|-----------|-----------|----------------|
| Events (raw) | 13 months | Drop monthly partitions |
| Profiles | Permanent | Soft delete only |
| Identifiers | Permanent | Cascade with profile |
| Consents | Permanent | Legal requirement |
| Sources | Permanent | Soft delete only |

### Retention Job (Cron)
```sql
-- Run monthly: Drop event partitions older than 13 months
-- Example for January 2026 (drops December 2024)
DO $$
DECLARE
    partition_name TEXT;
    cutoff_date DATE := CURRENT_DATE - INTERVAL '13 months';
BEGIN
    FOR partition_name IN
        SELECT tablename FROM pg_tables
        WHERE tablename LIKE 'cdp_events_%'
        AND tablename < 'cdp_events_' || to_char(cutoff_date, 'YYYY_MM')
    LOOP
        EXECUTE format('DROP TABLE IF EXISTS %I', partition_name);
        RAISE NOTICE 'Dropped partition: %', partition_name;
    END LOOP;
END $$;
```

---

## EMQ Score Calculation

EMQ (Event Match Quality) stored per event, calculated based on:

| Factor | Weight | Criteria |
|--------|--------|----------|
| Identifier Quality | 40% | Has hashed email or phone |
| Data Completeness | 25% | Required fields present |
| Timeliness | 20% | Event time within 5 min of received |
| Context Richness | 15% | Has device, geo, campaign data |

```python
def calculate_emq_score(event: dict) -> float:
    score = 0.0

    # Identifier quality (40%)
    identifiers = event.get("identifiers", [])
    has_email = any(i["type"] == "email" for i in identifiers)
    has_phone = any(i["type"] == "phone" for i in identifiers)
    if has_email or has_phone:
        score += 40
    elif identifiers:
        score += 20

    # Data completeness (25%)
    properties = event.get("properties", {})
    if properties:
        score += 25

    # Timeliness (20%)
    event_time = parse_datetime(event["event_time"])
    received_at = datetime.utcnow()
    latency = (received_at - event_time).total_seconds()
    if latency < 300:  # Within 5 minutes
        score += 20
    elif latency < 3600:  # Within 1 hour
        score += 10

    # Context richness (15%)
    context = event.get("context", {})
    if context.get("campaign"):
        score += 5
    if context.get("user_agent"):
        score += 5
    if context.get("ip"):
        score += 5

    return min(score, 100.0)
```

---

## Migration Files

Create these Alembic migrations in order:

1. `20260113_001_create_cdp_sources.py`
2. `20260113_002_create_cdp_profiles.py`
3. `20260113_003_create_cdp_profile_identifiers.py`
4. `20260113_004_create_cdp_events.py`
5. `20260113_005_create_cdp_consents.py`

Each migration should:
- Create table with all columns
- Create all indexes
- Add appropriate comments
- Be reversible (include downgrade)
