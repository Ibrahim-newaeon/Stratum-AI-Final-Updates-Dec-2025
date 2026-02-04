# Database Schema

Complete reference for Stratum AI database models.

---

## Overview

- **Database**: PostgreSQL 16
- **ORM**: SQLAlchemy 2.x (async)
- **Migrations**: Alembic

---

## Base Classes

All models inherit from these base classes:

### TimestampMixin
```python
class TimestampMixin:
    created_at: datetime  # Auto-set on creation
    updated_at: datetime  # Auto-updated on modification
```

### SoftDeleteMixin
```python
class SoftDeleteMixin:
    is_deleted: bool = False
    deleted_at: datetime | None
```

### TenantMixin
```python
class TenantMixin:
    tenant_id: int  # Foreign key to tenants table
```

---

## Enums

### UserRole
```python
class UserRole(str, Enum):
    SUPERADMIN = "superadmin"  # Platform-wide admin
    ADMIN = "admin"            # Tenant admin
    MANAGER = "manager"        # Team manager
    ANALYST = "analyst"        # Data analyst
    VIEWER = "viewer"          # Read-only
```

### AdPlatform
```python
class AdPlatform(str, Enum):
    META = "meta"
    GOOGLE = "google"
    TIKTOK = "tiktok"
    SNAPCHAT = "snapchat"
```

### CampaignStatus
```python
class CampaignStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"
```

### RuleStatus
```python
class RuleStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    DRAFT = "draft"
```

### RuleAction
```python
class RuleAction(str, Enum):
    APPLY_LABEL = "apply_label"
    SEND_ALERT = "send_alert"
    PAUSE_CAMPAIGN = "pause_campaign"
    ADJUST_BUDGET = "adjust_budget"
    NOTIFY_SLACK = "notify_slack"
    NOTIFY_WHATSAPP = "notify_whatsapp"
```

---

## Core Models

### Tenant

Multi-tenancy root entity. All other entities belong to a tenant.

```sql
CREATE TABLE tenants (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    domain VARCHAR(255),

    -- Subscription
    plan VARCHAR(50) DEFAULT 'free',
    plan_expires_at TIMESTAMP WITH TIME ZONE,
    stripe_customer_id VARCHAR(255),

    -- Settings
    settings JSONB DEFAULT '{}',
    feature_flags JSONB DEFAULT '{}',

    -- Limits
    max_users INTEGER DEFAULT 5,
    max_campaigns INTEGER DEFAULT 50,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX ix_tenants_slug ON tenants(slug);
CREATE INDEX ix_tenants_active ON tenants(is_deleted, plan);
```

### User

User accounts with role-based access control.

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id),

    -- Authentication
    email VARCHAR(255) NOT NULL,
    email_hash VARCHAR(64) NOT NULL,  -- SHA-256 for lookups
    password_hash VARCHAR(255) NOT NULL,

    -- Profile
    full_name VARCHAR(255),
    phone VARCHAR(100),
    avatar_url VARCHAR(500),

    -- Role & Permissions
    role user_role DEFAULT 'analyst',
    permissions JSONB DEFAULT '{}',

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_verified BOOLEAN DEFAULT FALSE,
    is_protected BOOLEAN DEFAULT FALSE,
    last_login_at TIMESTAMP WITH TIME ZONE,

    -- MFA
    totp_secret VARCHAR(255),
    totp_enabled BOOLEAN DEFAULT FALSE,
    totp_verified_at TIMESTAMP WITH TIME ZONE,
    backup_codes JSONB,
    failed_totp_attempts INTEGER DEFAULT 0,
    totp_lockout_until TIMESTAMP WITH TIME ZONE,

    -- Preferences
    locale VARCHAR(10) DEFAULT 'en',
    timezone VARCHAR(50) DEFAULT 'UTC',
    preferences JSONB DEFAULT '{}',

    -- GDPR
    consent_marketing BOOLEAN DEFAULT FALSE,
    consent_analytics BOOLEAN DEFAULT TRUE,
    gdpr_anonymized_at TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP WITH TIME ZONE,

    UNIQUE(tenant_id, email_hash)
);

CREATE INDEX ix_users_email_hash ON users(email_hash);
CREATE INDEX ix_users_tenant_active ON users(tenant_id, is_active, is_deleted);
```

### Campaign

Unified campaign model across ad platforms.

```sql
CREATE TABLE campaigns (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id),

    -- Platform Reference
    platform ad_platform NOT NULL,
    external_id VARCHAR(255) NOT NULL,
    account_id VARCHAR(255) NOT NULL,

    -- Campaign Info
    name VARCHAR(500) NOT NULL,
    status campaign_status DEFAULT 'draft',
    objective VARCHAR(100),

    -- Budget (stored in cents)
    daily_budget_cents INTEGER,
    lifetime_budget_cents INTEGER,
    total_spend_cents INTEGER DEFAULT 0,
    currency VARCHAR(3) DEFAULT 'USD',

    -- Performance Metrics
    impressions INTEGER DEFAULT 0,
    clicks INTEGER DEFAULT 0,
    conversions INTEGER DEFAULT 0,
    revenue_cents INTEGER DEFAULT 0,

    -- Computed Metrics
    ctr FLOAT,
    cpc_cents INTEGER,
    cpm_cents INTEGER,
    cpa_cents INTEGER,
    roas FLOAT,

    -- Targeting
    targeting_age_min INTEGER,
    targeting_age_max INTEGER,
    targeting_genders JSONB,
    targeting_locations JSONB,
    targeting_interests JSONB,

    -- Demographics Breakdown
    demographics_age JSONB,
    demographics_gender JSONB,
    demographics_location JSONB,

    -- Scheduling
    start_date DATE,
    end_date DATE,

    -- Organization
    labels JSONB DEFAULT '[]',
    raw_data JSONB,

    -- Sync
    last_synced_at TIMESTAMP WITH TIME ZONE,
    sync_error TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,

    UNIQUE(tenant_id, platform, external_id)
);

CREATE INDEX ix_campaigns_tenant_status ON campaigns(tenant_id, status);
CREATE INDEX ix_campaigns_platform ON campaigns(tenant_id, platform);
CREATE INDEX ix_campaigns_date_range ON campaigns(tenant_id, start_date, end_date);
CREATE INDEX ix_campaigns_roas ON campaigns(tenant_id, roas);
```

---

## CDP Models

### CDPProfile

Unified customer profile.

```sql
CREATE TABLE cdp_profiles (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id),

    -- Identity
    canonical_id UUID UNIQUE NOT NULL,
    anonymous_id VARCHAR(255),
    external_id VARCHAR(255),

    -- PII (encrypted)
    email VARCHAR(255),
    email_hash VARCHAR(64),
    phone VARCHAR(100),
    phone_hash VARCHAR(64),

    -- Profile Data
    first_name VARCHAR(255),
    last_name VARCHAR(255),

    -- Lifecycle
    lifecycle_stage VARCHAR(50) DEFAULT 'anonymous',
    first_seen_at TIMESTAMP WITH TIME ZONE,
    last_seen_at TIMESTAMP WITH TIME ZONE,

    -- Computed
    traits JSONB DEFAULT '{}',
    computed_traits JSONB DEFAULT '{}',

    -- Consent
    consent JSONB DEFAULT '{}',

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX ix_cdp_profiles_tenant ON cdp_profiles(tenant_id);
CREATE INDEX ix_cdp_profiles_email_hash ON cdp_profiles(tenant_id, email_hash);
CREATE INDEX ix_cdp_profiles_lifecycle ON cdp_profiles(tenant_id, lifecycle_stage);
```

### CDPEvent

Customer events.

```sql
CREATE TABLE cdp_events (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id),
    profile_id INTEGER REFERENCES cdp_profiles(id),

    -- Event Data
    event_name VARCHAR(255) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    properties JSONB DEFAULT '{}',
    context JSONB DEFAULT '{}',

    -- Tracking
    message_id UUID UNIQUE,
    anonymous_id VARCHAR(255),

    -- Timestamps
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    received_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX ix_cdp_events_profile ON cdp_events(profile_id);
CREATE INDEX ix_cdp_events_name ON cdp_events(tenant_id, event_name);
CREATE INDEX ix_cdp_events_timestamp ON cdp_events(tenant_id, timestamp);
```

### CDPSegment

Dynamic customer segments.

```sql
CREATE TABLE cdp_segments (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id),

    -- Segment Info
    name VARCHAR(255) NOT NULL,
    description TEXT,
    slug VARCHAR(100),

    -- Definition
    conditions JSONB NOT NULL,

    -- Computed
    profile_count INTEGER DEFAULT 0,
    last_computed_at TIMESTAMP WITH TIME ZONE,

    -- Status
    is_active BOOLEAN DEFAULT TRUE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### CDPAudienceSync

Audience sync to ad platforms.

```sql
CREATE TABLE cdp_audience_syncs (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id),
    segment_id INTEGER REFERENCES cdp_segments(id),

    -- Platform
    platform ad_platform NOT NULL,
    platform_audience_id VARCHAR(255),

    -- Config
    name VARCHAR(255) NOT NULL,
    sync_interval VARCHAR(50) DEFAULT 'daily',
    identifier_types JSONB DEFAULT '["email"]',

    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    last_sync_at TIMESTAMP WITH TIME ZONE,
    last_sync_status VARCHAR(50),
    last_sync_error TEXT,

    -- Metrics
    profiles_synced INTEGER DEFAULT 0,
    match_rate FLOAT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

## Trust Layer Models

### FactSignalHealthDaily

Daily signal health snapshots.

```sql
CREATE TABLE fact_signal_health_daily (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id),

    -- Date
    date DATE NOT NULL,

    -- Platform Scores
    platform ad_platform NOT NULL,
    health_score INTEGER NOT NULL,  -- 0-100

    -- Components
    data_freshness_score INTEGER,
    completeness_score INTEGER,
    accuracy_score INTEGER,

    -- Status
    status VARCHAR(20),  -- healthy, degraded, unhealthy

    -- Details
    issues JSONB DEFAULT '[]',

    UNIQUE(tenant_id, date, platform)
);
```

### FactActionsQueue

Pending autopilot actions.

```sql
CREATE TABLE fact_actions_queue (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id),

    -- Action
    action_type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id INTEGER NOT NULL,

    -- Details
    payload JSONB NOT NULL,
    reason TEXT,

    -- Status
    status VARCHAR(20) DEFAULT 'pending',  -- pending, approved, rejected, executed

    -- Audit
    created_by_id INTEGER,
    approved_by_id INTEGER,
    approved_at TIMESTAMP WITH TIME ZONE,
    executed_at TIMESTAMP WITH TIME ZONE,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

## Campaign Builder Models

### TenantPlatformConnection

OAuth connections to ad platforms.

```sql
CREATE TABLE tenant_platform_connections (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id),

    -- Platform
    platform ad_platform NOT NULL,

    -- OAuth Tokens (encrypted)
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at TIMESTAMP WITH TIME ZONE,

    -- Status
    is_connected BOOLEAN DEFAULT FALSE,
    last_verified_at TIMESTAMP WITH TIME ZONE,
    connection_error TEXT,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(tenant_id, platform)
);
```

### CampaignDraft

Campaign drafts before publishing.

```sql
CREATE TABLE campaign_drafts (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id),
    created_by_id INTEGER REFERENCES users(id),

    -- Draft Info
    name VARCHAR(500) NOT NULL,
    platforms JSONB NOT NULL,  -- Array of platforms to publish to

    -- Campaign Data
    data JSONB NOT NULL,

    -- Status
    status VARCHAR(50) DEFAULT 'draft',

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

## Automation Models

### Rule

Automation rules.

```sql
CREATE TABLE rules (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id),

    -- Rule Info
    name VARCHAR(255) NOT NULL,
    description TEXT,

    -- Definition
    conditions JSONB NOT NULL,
    actions JSONB NOT NULL,

    -- Schedule
    schedule VARCHAR(50),  -- cron expression or interval

    -- Status
    status rule_status DEFAULT 'draft',
    is_enabled BOOLEAN DEFAULT TRUE,

    -- Metrics
    executions_count INTEGER DEFAULT 0,
    last_executed_at TIMESTAMP WITH TIME ZONE,
    last_execution_result JSONB,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE
);
```

---

## Audit & Logging

### AuditLog

Compliance audit trail.

```sql
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER REFERENCES tenants(id),
    user_id INTEGER REFERENCES users(id),

    -- Action
    action audit_action NOT NULL,
    resource_type VARCHAR(100) NOT NULL,
    resource_id VARCHAR(255),

    -- Details
    old_values JSONB,
    new_values JSONB,
    metadata JSONB DEFAULT '{}',

    -- Request Context
    ip_address INET,
    user_agent TEXT,
    request_id VARCHAR(100),

    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX ix_audit_logs_tenant ON audit_logs(tenant_id);
CREATE INDEX ix_audit_logs_user ON audit_logs(user_id);
CREATE INDEX ix_audit_logs_resource ON audit_logs(resource_type, resource_id);
CREATE INDEX ix_audit_logs_created ON audit_logs(created_at);
```

---

## Indexes Strategy

### Multi-Column Indexes

Used for common query patterns:

```sql
-- Tenant + Status (most common filter)
CREATE INDEX ix_campaigns_tenant_status ON campaigns(tenant_id, status);

-- Tenant + Date Range (analytics queries)
CREATE INDEX ix_campaigns_date_range ON campaigns(tenant_id, start_date, end_date);

-- Email hash lookups (authentication)
CREATE INDEX ix_users_email_hash ON users(email_hash);
```

### Partial Indexes

Used for filtered queries:

```sql
-- Active campaigns only
CREATE INDEX ix_campaigns_active
ON campaigns(tenant_id, created_at)
WHERE status = 'active' AND is_deleted = FALSE;
```

### JSONB Indexes

Used for JSON column queries:

```sql
-- GIN index for JSONB containment queries
CREATE INDEX ix_profiles_traits ON cdp_profiles USING GIN (traits);
```

---

## Migrations

### Running Migrations

```bash
# Apply all pending migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View current revision
alembic current

# View history
alembic history
```

### Creating Migrations

```bash
# Auto-generate from model changes
alembic revision --autogenerate -m "Add new_table"

# Create empty migration for manual changes
alembic revision -m "Manual data migration"
```
