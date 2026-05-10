# Campaign Builder Specification

## Overview

The Campaign Builder enables creating, managing, and publishing advertising campaigns across multiple platforms (Meta, Google, TikTok, Snapchat). Campaigns are drafted in a platform-agnostic format and converted at publish time.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  CAMPAIGN BUILDER ARCHITECTURE                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   PLATFORM CONNECTIONS                    │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │  │
│  │  │   Meta   │ │  Google  │ │  TikTok  │ │ Snapchat │   │  │
│  │  │  OAuth   │ │  OAuth   │ │  OAuth   │ │  OAuth   │   │  │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘   │  │
│  └───────┼────────────┼────────────┼────────────┼─────────┘  │
│          │            │            │            │             │
│          └────────────┴────────────┴────────────┘             │
│                            │                                   │
│                            ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    AD ACCOUNTS                            │  │
│  │  • Synced from platforms after OAuth                     │  │
│  │  • Enable/disable per tenant                             │  │
│  │  • Budget caps per account                               │  │
│  └──────────────────────────┬───────────────────────────────┘  │
│                            │                                   │
│                            ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  CAMPAIGN DRAFTS                          │  │
│  │                                                          │  │
│  │  draft → submitted → approved → publishing → published   │  │
│  │             ↓           ↓                                │  │
│  │         rejected      failed                             │  │
│  └──────────────────────────┬───────────────────────────────┘  │
│                            │                                   │
│                            ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  PLATFORM PUBLISH                         │  │
│  │  • Convert canonical JSON to platform format             │  │
│  │  • Call platform API to create campaign                  │  │
│  │  • Log request/response for audit                        │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Supported Platforms

| Platform | API | OAuth Version |
|----------|-----|---------------|
| **Meta** | Marketing API v18.0 | OAuth 2.0 |
| **Google** | Google Ads API v15 | OAuth 2.0 |
| **TikTok** | Marketing API v1.3 | OAuth 2.0 |
| **Snapchat** | Marketing API v1 | OAuth 2.0 |

---

## Data Models

### TenantPlatformConnection

Stores OAuth tokens and connection metadata per tenant.

```python
class TenantPlatformConnection:
    id: UUID
    tenant_id: int
    platform: AdPlatform            # meta, google, tiktok, snapchat

    # Status
    status: ConnectionStatus        # connected, expired, error, disconnected

    # Token storage (encrypted)
    token_ref: str | None           # Reference to secrets manager
    access_token_encrypted: str | None
    refresh_token_encrypted: str | None
    token_expires_at: datetime | None

    # OAuth metadata
    scopes: list[str]               # Granted permissions
    granted_by_user_id: int | None

    # Timestamps
    connected_at: datetime | None
    last_refreshed_at: datetime | None

    # Error tracking
    last_error: str | None
    error_count: int = 0
```

### TenantAdAccount

Ad accounts enabled for use by tenant.

```python
class TenantAdAccount:
    id: UUID
    tenant_id: int
    connection_id: UUID
    platform: AdPlatform

    # Platform identifiers
    platform_account_id: str        # e.g., act_123456789
    name: str
    business_name: str | None

    # Configuration
    currency: str = "USD"
    timezone: str = "UTC"
    is_enabled: bool = False

    # Budget controls
    daily_budget_cap: Decimal | None
    monthly_budget_cap: Decimal | None

    # Platform metadata
    permissions_json: dict
    account_status: str | None      # active, disabled, etc.

    # Sync tracking
    last_synced_at: datetime | None
    sync_error: str | None
```

### CampaignDraft

Campaign drafts with approval workflow.

```python
class CampaignDraft:
    id: UUID
    tenant_id: int
    ad_account_id: UUID | None
    platform: AdPlatform

    # Draft identification
    name: str
    description: str | None
    status: DraftStatus

    # Campaign configuration (canonical JSON)
    draft_json: dict                # Platform-agnostic format

    # Workflow tracking
    created_by_user_id: int | None
    submitted_by_user_id: int | None
    approved_by_user_id: int | None
    rejected_by_user_id: int | None

    submitted_at: datetime | None
    approved_at: datetime | None
    rejected_at: datetime | None
    rejection_reason: str | None

    # Published campaign reference
    platform_campaign_id: str | None
    published_at: datetime | None
```

### CampaignPublishLog

Audit trail for publish attempts.

```python
class CampaignPublishLog:
    id: UUID
    tenant_id: int
    draft_id: UUID | None
    platform: AdPlatform
    platform_account_id: str

    # Actor
    published_by_user_id: int | None

    # Event timing
    event_time: datetime

    # Request/Response (for debugging)
    request_json: dict | None
    response_json: dict | None

    # Result
    result_status: PublishResult    # success, failure
    platform_campaign_id: str | None

    # Error details
    error_code: str | None
    error_message: str | None

    # Retry tracking
    retry_count: int = 0
    last_retry_at: datetime | None
```

---

## Enums

### AdPlatform

```python
class AdPlatform(str, Enum):
    META = "meta"
    GOOGLE = "google"
    TIKTOK = "tiktok"
    SNAPCHAT = "snapchat"
```

### ConnectionStatus

```python
class ConnectionStatus(str, Enum):
    CONNECTED = "connected"
    EXPIRED = "expired"
    ERROR = "error"
    DISCONNECTED = "disconnected"
```

### DraftStatus

```python
class DraftStatus(str, Enum):
    DRAFT = "draft"                 # Initial state, being edited
    SUBMITTED = "submitted"         # Sent for approval
    APPROVED = "approved"           # Ready to publish
    REJECTED = "rejected"           # Needs revision
    PUBLISHING = "publishing"       # In progress
    PUBLISHED = "published"         # Live on platform
    FAILED = "failed"               # Publish failed
```

---

## Draft JSON Format

Campaign drafts use a canonical JSON format that's converted to platform-specific format at publish time.

### Structure

```json
{
  "campaign": {
    "name": "Summer Sale 2024",
    "objective": "CONVERSIONS",
    "budget": {
      "amount": 1000.00,
      "currency": "USD",
      "type": "daily"
    },
    "schedule": {
      "start_date": "2024-06-01",
      "end_date": "2024-08-31"
    }
  },
  "ad_sets": [
    {
      "name": "US - 25-54",
      "targeting": {
        "locations": ["US"],
        "age_min": 25,
        "age_max": 54,
        "genders": ["all"],
        "interests": ["fashion", "shopping"]
      },
      "budget": {
        "amount": 500.00,
        "type": "daily"
      },
      "optimization_goal": "CONVERSIONS",
      "billing_event": "IMPRESSIONS"
    }
  ],
  "ads": [
    {
      "name": "Summer Sale - Image Ad",
      "ad_set_index": 0,
      "creative": {
        "type": "image",
        "image_url": "https://...",
        "headline": "Summer Sale - Up to 50% Off!",
        "description": "Shop now for the best deals",
        "call_to_action": "SHOP_NOW",
        "link_url": "https://..."
      }
    }
  ]
}
```

---

## Workflow State Machine

```
┌─────────┐  submit   ┌───────────┐  approve  ┌──────────┐
│  DRAFT  │──────────►│ SUBMITTED │──────────►│ APPROVED │
└─────────┘           └─────┬─────┘           └────┬─────┘
     ▲                      │                      │
     │                      │ reject               │ publish
     │                      ▼                      ▼
     │               ┌───────────┐         ┌────────────┐
     └───────────────│ REJECTED  │         │ PUBLISHING │
         revise      └───────────┘         └──────┬─────┘
                                                  │
                                     ┌────────────┼────────────┐
                                     │            │            │
                                     ▼            ▼            ▼
                              ┌───────────┐ ┌──────────┐ (retry)
                              │ PUBLISHED │ │  FAILED  │───┘
                              └───────────┘ └──────────┘
```

---

## Platform Integration

### Meta (Facebook/Instagram)

**Objectives Mapping**:
| Canonical | Meta API |
|-----------|----------|
| AWARENESS | BRAND_AWARENESS |
| TRAFFIC | LINK_CLICKS |
| ENGAGEMENT | POST_ENGAGEMENT |
| LEADS | LEAD_GENERATION |
| CONVERSIONS | CONVERSIONS |
| SALES | PRODUCT_CATALOG_SALES |

### Google Ads

**Campaign Types**:
| Canonical | Google API |
|-----------|------------|
| SEARCH | SEARCH |
| DISPLAY | DISPLAY |
| VIDEO | VIDEO |
| SHOPPING | SHOPPING |
| PERFORMANCE_MAX | PERFORMANCE_MAX |

### TikTok

**Objectives**:
| Canonical | TikTok API |
|-----------|------------|
| AWARENESS | REACH |
| TRAFFIC | TRAFFIC |
| CONVERSIONS | CONVERSIONS |
| APP_INSTALL | APP_INSTALL |

### Snapchat

**Objectives**:
| Canonical | Snapchat API |
|-----------|--------------|
| AWARENESS | AWARENESS |
| TRAFFIC | WEBSITE_TRAFFIC |
| CONVERSIONS | WEBSITE_CONVERSIONS |
| APP_INSTALL | APP_INSTALLS |

---

## Budget Controls

### Ad Account Caps

```python
class BudgetCap:
    daily_budget_cap: Decimal | None
    monthly_budget_cap: Decimal | None
```

Enforced before publishing any campaign.

### Campaign Budget Types

| Type | Description |
|------|-------------|
| `daily` | Budget resets daily |
| `lifetime` | Total budget for campaign duration |

---

## Database Schema

```sql
-- Platform connections
CREATE TABLE tenant_platform_connection (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'disconnected',

    token_ref TEXT,
    access_token_encrypted TEXT,
    refresh_token_encrypted TEXT,
    token_expires_at TIMESTAMPTZ,

    scopes JSONB DEFAULT '[]',
    granted_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,

    connected_at TIMESTAMPTZ,
    last_refreshed_at TIMESTAMPTZ,
    last_error TEXT,
    error_count INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(tenant_id, platform)
);

-- Ad accounts
CREATE TABLE tenant_ad_account (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    connection_id UUID NOT NULL REFERENCES tenant_platform_connection(id) ON DELETE CASCADE,
    platform VARCHAR(50) NOT NULL,

    platform_account_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    business_name VARCHAR(255),

    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    timezone VARCHAR(100) NOT NULL DEFAULT 'UTC',
    is_enabled BOOLEAN NOT NULL DEFAULT FALSE,

    daily_budget_cap NUMERIC(12, 2),
    monthly_budget_cap NUMERIC(12, 2),

    permissions_json JSONB DEFAULT '{}',
    account_status VARCHAR(50),

    last_synced_at TIMESTAMPTZ,
    sync_error TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(tenant_id, platform, platform_account_id)
);

-- Campaign drafts
CREATE TABLE campaign_draft (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    ad_account_id UUID REFERENCES tenant_ad_account(id) ON DELETE SET NULL,
    platform VARCHAR(50) NOT NULL,

    name VARCHAR(255) NOT NULL,
    description TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'draft',

    draft_json JSONB NOT NULL DEFAULT '{}',

    created_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    submitted_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    approved_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    rejected_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,

    submitted_at TIMESTAMPTZ,
    approved_at TIMESTAMPTZ,
    rejected_at TIMESTAMPTZ,
    rejection_reason TEXT,

    platform_campaign_id VARCHAR(255),
    published_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Publish logs
CREATE TABLE campaign_publish_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id INTEGER NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    draft_id UUID REFERENCES campaign_draft(id) ON DELETE SET NULL,
    platform VARCHAR(50) NOT NULL,
    platform_account_id VARCHAR(255) NOT NULL,

    published_by_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,

    event_time TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    request_json JSONB,
    response_json JSONB,

    result_status VARCHAR(50) NOT NULL,
    platform_campaign_id VARCHAR(255),

    error_code VARCHAR(100),
    error_message TEXT,

    retry_count INTEGER DEFAULT 0,
    last_retry_at TIMESTAMPTZ
);
```

---

## Configuration

### Environment Variables

```bash
# OAuth Client IDs/Secrets (per platform)
META_CLIENT_ID=xxx
META_CLIENT_SECRET=xxx
GOOGLE_CLIENT_ID=xxx
GOOGLE_CLIENT_SECRET=xxx
TIKTOK_CLIENT_ID=xxx
TIKTOK_CLIENT_SECRET=xxx
SNAPCHAT_CLIENT_ID=xxx
SNAPCHAT_CLIENT_SECRET=xxx

# OAuth Redirect URI
OAUTH_REDIRECT_URI=https://app.stratum.ai/oauth/callback
```

### Feature Flags

| Flag | Description |
|------|-------------|
| `campaign_builder` | Enable campaign builder |
| `campaign_builder_meta` | Enable Meta platform |
| `campaign_builder_google` | Enable Google platform |
| `campaign_builder_tiktok` | Enable TikTok platform |
| `campaign_builder_snapchat` | Enable Snapchat platform |

---

## Related Documentation

- [User Flows](./user-flows.md) - Step-by-step user journeys
- [API Contracts](./api-contracts.md) - API endpoints and schemas
- [Edge Cases](./edge-cases.md) - Error handling and edge cases
