# Stratum AI — Feature Reference

> **Complete technical reference for all 14 platform features.**  
> For user-facing guides, see `docs/04-features/{feature}/user-flows.md`.  
> For API contracts, see `docs/04-features/{feature}/api-contracts.md`.

---

## Feature Index

| # | Feature | Status | Module Path |
|---|---------|--------|-------------|
| 01 | [Trust Engine](#01-trust-engine) | Production | `backend/app/services/trust/` |
| 02 | [CDP](#02-customer-data-platform) | Production | `backend/app/services/cdp/` |
| 03 | [Audience Sync](#03-audience-sync) | Production | `backend/app/services/audience_sync/` |
| 04 | [CMS](#04-content-management-system) | Production | `backend/app/api/v1/endpoints/cms.py` |
| 05 | [Authentication](#05-authentication) | Production | `backend/app/core/security.py` |
| 06 | [Campaigns](#06-campaigns) | Production | `backend/app/api/v1/endpoints/campaigns.py` |
| 07 | [Autopilot](#07-autopilot) | Production | `backend/app/services/autopilot/` |
| 08 | [Rules Engine](#08-rules-engine) | Production | `backend/app/api/v1/endpoints/rules.py` |
| 09 | [Analytics](#09-analytics) | Production | `backend/app/api/v1/endpoints/analytics.py` |
| 10 | [Integrations](#10-integrations) | Production | `backend/app/api/v1/endpoints/integrations.py` |
| 11 | [Onboarding](#11-onboarding) | Production | `frontend/src/views/Onboarding.tsx` |
| 12 | [WhatsApp](#12-whatsapp) | Production | `backend/app/api/v1/endpoints/whatsapp.py` |
| 13 | [Payments](#13-payments) | Production | `backend/app/api/v1/endpoints/stripe_webhook.py` |
| 14 | [Superadmin](#14-superadmin) | Internal | `backend/app/api/v1/endpoints/superadmin.py` |

---

## 01. Trust Engine

### Purpose
Calculates a 0-100 Trust Score by evaluating 5 data quality components. Prevents automation from executing on unreliable data.

### Core Algorithm

```python
COMPONENT_WEIGHTS = {
    "capi_health": 0.25,
    "pixel_firing": 0.20,
    "event_match_quality": 0.20,
    "attribution_variance": 0.20,
    "autopilot_history": 0.15,
}

def calculate_trust_score(components: dict) -> int:
    score = sum(
        components[name] * weight 
        for name, weight in COMPONENT_WEIGHTS.items()
    )
    return min(100, max(0, int(score)))
```

### Key Models

```python
class TrustScore(Base):
    tenant_id: int
    date: date
    overall_score: int
    capi_health: int
    pixel_firing: int
    event_match_quality: int
    attribution_variance: int
    autopilot_history: int
```

### Gate Verdicts

| Score Range | Verdict | Autopilot Mode |
|-------------|---------|----------------|
| 90-100 | PASS | Automatic |
| 70-89 | PASS | Supervised |
| 50-69 | HOLD | Approval Required |
| 0-49 | BLOCK | Manual Only |

### Frontend Components
- `components/SignalHealthPanel.tsx` — Real-time signal cards
- `views/Trust.tsx` — Full trust dashboard
- `components/widgets/TrustGateStatus.tsx` — Mini status widget

---

## 02. Customer Data Platform

### Purpose
First-party data infrastructure with identity resolution, consent management, and audience segmentation.

### Core Concepts

| Concept | Description |
|---------|-------------|
| **Event** | Any tracked action (page_view, purchase, signup) |
| **Profile** | Unified user record with resolved identities |
| **Trait** | Computed attribute (LTV, churn_risk, segment) |
| **Audience** | Segment definition (SQL-like query on traits) |
| **Consent** | GDPR/CCPA compliance flags per profile |

### Identity Resolution

```python
# Example: Merge anonymous web user with identified CRM record
profile = IdentityGraph.resolve(
    external_ids=[
        {"type": "email", "value": "user@example.com"},
        {"type": "phone", "value": "+1234567890"},
        {"type": "meta_fbid", "value": "123456789"},
    ]
)
```

### Key Models

```python
class CDPEvent(Base):
    tenant_id: int
    profile_id: Optional[int]
    event_type: str          # "purchase", "page_view", etc.
    properties: JSONB
    timestamp: datetime

class CDPProfile(Base):
    tenant_id: int
    external_ids: JSONB      # [{"type": "email", "value": "..."}]
    traits: JSONB
    consent: JSONB
    merged_into_id: Optional[int]
```

### Frontend Components
- `views/cdp/CDPProfiles.tsx` — Profile browser
- `views/cdp/CDPSegments.tsx` — Segment builder
- `views/cdp/CDPIdentityGraph.tsx` — Identity resolution visualizer

---

## 03. Audience Sync

### Purpose
Push CDP segments to ad platforms for targeting and exclusion.

### Supported Platforms

| Platform | Sync Type | API |
|----------|-----------|-----|
| Meta | Custom Audience | Marketing API |
| Google | Customer Match | Google Ads API |
| TikTok | Custom Audience | TikTok for Business API |
| Snapchat | Snap Audience | Snapchat Marketing API |

### Sync Workflow

```
CDP Segment (e.g., "High LTV Customers")
    → AudienceSyncService.create_or_update_audience()
        → Hash PII (SHA-256) for privacy
            → Upload to platform API
                → Poll for match rate
                    → Store platform_audience_id
```

### Key Models

```python
class AudienceSync(Base):
    tenant_id: int
    segment_id: int          # CDP segment
    platform: str            # "meta", "google", etc.
    platform_audience_id: str
    status: str              # "syncing", "active", "error"
    last_sync_at: datetime
    match_rate: Optional[float]
```

---

## 04. Content Management System

### Purpose
Manage marketing content: blog posts, landing pages, authors, categories, and contacts.

### Content Types

| Type | Description | URL Pattern |
|------|-------------|-------------|
| **Post** | Blog article | `/blog/{slug}` |
| **Page** | Static landing page | `/{slug}` |
| **Author** | Writer profile | `/author/{slug}` |
| **Category** | Content taxonomy | `/category/{slug}` |
| **Contact** | Lead/subscriber | Internal only |

### Editor
- **Rich Text**: Tiptap editor with custom extensions
- **SEO**: Meta title, description, OpenGraph tags
- **Publishing**: Draft → Scheduled → Published → Archived
- **Multilingual**: i18n support with locale switching

### Key Models

```python
class CMSPost(Base):
    tenant_id: Optional[int]   # Null = global (landing site)
    title: str
    slug: str
    content: str               # HTML from Tiptap
    excerpt: str
    status: str                # "draft", "scheduled", "published", "archived"
    published_at: Optional[datetime]
    author_id: int
    category_id: int
    seo_meta: JSONB
```

### Frontend Components
- `components/cms/RichTextEditor.tsx` — Tiptap-based editor
- `views/cms/CMSPosts.tsx` — Post management
- `views/cms/CMSPages.tsx` — Page management
- `views/cms/CMSAuthors.tsx` — Author directory

---

## 05. Authentication

### Purpose
Secure user access with multiple authentication methods and role-based authorization.

### Auth Methods

| Method | Flow | Use Case |
|--------|------|----------|
| **Email/Password** | Register → Verify Email → Login | Standard |
| **WhatsApp OTP** | Phone → OTP → Token | Passwordless, MFA |
| **Social OAuth** | Google/Meta OAuth → Account Link | Quick signup |
| **API Key** | HMAC-signed request headers | Integrations |

### JWT Token Structure

```json
{
  "sub": "user_id",
  "tenant_id": 42,
  "role": "tenant_admin",
  "permissions": ["campaigns", "analytics", "users"],
  "iat": 1714123456,
  "exp": 1714124356
}
```

### RBAC Roles

| Role | Campaigns | Analytics | Users | Billing | Settings |
|------|-----------|-----------|-------|---------|----------|
| Superadmin | ✅ | ✅ | ✅ | ✅ | ✅ |
| Tenant Admin | ✅ | ✅ | ✅ | ✅ | ✅ |
| Manager | ✅ | ✅ | ✅ | ❌ | ❌ |
| Analyst | ✅ | ✅ | ❌ | ❌ | ❌ |
| Viewer | ✅ (own) | ❌ | ❌ | ❌ | ❌ |

### Security Features
- Rate limiting: 5 login attempts / 15 min per IP
- Account lockout: 30 min after 5 failed attempts
- Session timeout: 30 min idle, 12 hours max
- Password requirements: 8+ chars, mixed case, number, symbol
- PII encryption: AES-256 for emails/phones at rest

---

## 06. Campaigns

### Purpose
Create, manage, and monitor ad campaigns across multiple platforms from a single interface.

### Campaign Lifecycle

```
DRAFT → SUBMITTED → APPROVED → ACTIVE → PAUSED → COMPLETED
   ↓        ↓           ↓          ↓        ↓
  Edit   Review     Publish     Monitor  Resume/Stop
```

### Builder Wizard Steps

1. **Basics**: Name, objective, platforms, budget, schedule
2. **Targeting**: Audiences, locations, demographics, placements
3. **Creative**: Images, videos, headlines, primary text, CTA
4. **Review**: Pre-flight trust check, preview, publish/save draft

### Key Models

```python
class Campaign(Base):
    tenant_id: int
    name: str
    status: str              # "draft", "active", "paused", "completed"
    objective: str           # "conversions", "traffic", "leads"
    platforms: list[str]     # ["meta", "google"]
    budget_cents: int        # BigInteger for safety
    spent_cents: int
    start_date: date
    end_date: Optional[date]
    targeting: JSONB
    creative: JSONB
    platform_campaign_ids: JSONB  # { "meta": "12345", "google": "abc" }
```

### Frontend Components
- `views/tenant/CampaignBuilder.tsx` — Multi-step wizard
- `views/Campaigns.tsx` — Campaign list and management
- `views/CampaignDetail.tsx` — Single campaign analytics
- `components/dashboard/CampaignTable.tsx` — Reusable campaign table

---

## 07. Autopilot

### Purpose
Automated campaign management that executes only when Trust Score permits.

### Enforcement Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| **Advisory** | Suggests only, never executes | Learning the system |
| **Supervised** | Suggests, executes after approval | Recommended default |
| **Hard Block** | Auto-blocks risky, executes safe | Experienced users |

### Action Types

```python
class AutopilotAction(Enum):
    BUDGET_INCREASE = "increase_budget"
    BUDGET_DECREASE = "decrease_budget"
    PAUSE = "pause_campaign"
    RESUME = "resume_campaign"
    APPLY_LABEL = "apply_label"
    NOTIFY_SLACK = "notify_slack"
```

### Decision Engine

```python
class AutopilotEvaluator:
    def evaluate_campaign(self, campaign: Campaign) -> List[Action]:
        actions = []
        
        if campaign.roas > 3.5 and campaign.days_active >= 3:
            actions.append(Action.budget_increase(percent=15))
        
        if campaign.roas < 1.0 and campaign.days_active >= 3:
            actions.append(Action.budget_decrease(percent=20))
        
        if campaign.cpa > 2 * campaign.target_cpa:
            actions.append(Action.pause())
        
        return actions
```

### Frontend Components
- `views/Autopilot.tsx` — Settings and configuration
- `components/AutopilotPanel.tsx` — Pending actions panel
- `components/dashboard/SignalRecoveryCard.tsx` — Recovery suggestions

---

## 08. Rules Engine

### Purpose
User-defined business rules that trigger actions when conditions are met.

### Rule Structure

```json
{
  "name": "High ROAS Scaler",
  "conditions": {
    "logic": "AND",
    "groups": [
      {
        "logic": "AND",
        "conditions": [
          { "field": "roas", "operator": ">", "value": "3.5" },
          { "field": "status", "operator": "equals", "value": "active" }
        ]
      }
    ]
  },
  "action": {
    "type": "scale_budget",
    "config": { "direction": "increase", "amount": 15 }
  },
  "schedule": {
    "enabled": true,
    "frequency": "daily",
    "hoursOfDay": [9, 15]
  }
}
```

### Supported Operators

| Type | Operators |
|------|-----------|
| Number | `=`, `!=`, `>`, `<`, `>=`, `<=` |
| String | `equals`, `not_equals`, `contains`, `starts_with` |
| Enum | `is`, `is_not`, `in`, `not_in` |
| Date | `before`, `after`, `within_last`, `within_next` |

### Frontend Components
- `views/CustomAutopilotRules.tsx` — Rule list and management
- `components/autopilot/CustomAutopilotRulesBuilder.tsx` — Visual rule builder
- `views/Rules.tsx` — Legacy rules management

---

## 09. Analytics

### Purpose
Unified reporting across all platforms with attribution modeling and forecasting.

### Attribution Models

| Model | Description | Use Case |
|-------|-------------|----------|
| **Last Click** | 100% to last touchpoint | Simple |
| **First Click** | 100% to first touchpoint | Brand awareness |
| **Linear** | Equal split across all touchpoints | Balanced |
| **Time Decay** | More credit to recent touchpoints | Short cycles |
| **Position-Based** | 40% first, 40% last, 20% middle | Full funnel |
| **Markov Chain** | Probabilistic path analysis | Complex journeys |
| **Shapley Value** | Game-theoretic fair allocation | Enterprise |

### Forecasting Models

| Model | Output | Accuracy |
|-------|--------|----------|
| **EWMA** | Next 7-day spend/revenue | ~85% |
| **Prophet** | Seasonal trends | ~88% |
| **XGBoost** | ROAS prediction | ~91% |

### Key Endpoints

```
GET /api/v1/tenants/{tenant_id}/overview          # KPI summary
GET /api/v1/tenants/{tenant_id}/analytics/daily   # Time-series
GET /api/v1/tenants/{tenant_id}/attribution       # Attribution report
GET /api/v1/tenants/{tenant_id}/predictions       # Forecasts
```

### Frontend Components
- `views/Overview.tsx` — Main dashboard
- `views/tenant/Attribution.tsx` — Attribution explorer
- `views/tenant/Pacing.tsx` — Budget pacing and forecasting
- `components/charts/*.tsx` — Recharts wrappers

---

## 10. Integrations

### Purpose
Connect external platforms for data ingestion and action execution.

### Platform Support Matrix

| Platform | Data In | Actions Out | Auth |
|----------|---------|-------------|------|
| **Meta Ads** | Campaigns, insights, events | Budget, status, creative | OAuth 2.0 |
| **Google Ads** | Campaigns, conversions | Budget, status | OAuth 2.0 |
| **TikTok Ads** | Campaigns, insights | Budget, status | OAuth 2.0 |
| **Snapchat** | Campaigns, insights | Budget, status | OAuth 2.0 |
| **LinkedIn** | Campaigns, insights | Budget, status | OAuth 2.0 |
| **HubSpot** | Contacts, deals, companies | Contacts, deals | OAuth 2.0 |
| **Pipedrive** | Deals, persons, organizations | Deals | OAuth 2.0 |
| **Slack** | — | Notifications | OAuth 2.0 |
| **Stripe** | Subscriptions, invoices | Billing | Webhook |
| **WhatsApp** | Messages, contacts | Broadcasts, OTP | Twilio API |

### Connection Flow

```
User clicks "Connect"
    → Redirect to platform OAuth
        → User grants permissions
            → Platform redirects with auth code
                → Backend exchanges code for tokens
                    → Stores encrypted tokens
                        → Triggers initial sync
```

### Frontend Components
- `views/Settings.tsx` — Integration management
- `components/integrations/PlatformSetupModal.tsx` — OAuth setup wizard
- `views/pages/ConnectPlatforms.tsx` — Public integration directory

---

## 11. Onboarding

### Purpose
Guide new users from signup to first campaign with contextual help.

### Onboarding Steps

| Step | Action | Help Context |
|------|--------|--------------|
| 1 | Create tenant | Tooltips on name/slug |
| 2 | Connect first platform | Platform-specific guides |
| 3 | Review dashboard | Interactive tour (`data-tour` attributes) |
| 4 | Understand Trust Score | Animated explanation |
| 5 | Create first campaign | Wizard with inline help |
| 6 | Configure Autopilot | Mode selector with risk explanation |
| 7 | Invite team | Role descriptions |

### Tour System

```tsx
// Components marked with data-tour are highlighted
<div data-tour="sidebar">...</div>
<div data-tour="kpi-strip">...</div>
<div data-tour="insights-panel">...</div>
```

### Frontend Components
- `views/Onboarding.tsx` — Main onboarding wizard
- `components/onboarding/OnboardingChecklist.tsx` — Progress tracker
- `components/onboarding/OnboardingChat.tsx` — Help chatbot
- `components/guide/JoyrideWrapper.tsx` — Interactive tour engine

---

## 12. WhatsApp

### Purpose
Customer communication via WhatsApp Business API: contacts, templates, broadcasts, and OTP.

### Features

| Feature | Description |
|---------|-------------|
| **Contacts** | Import, manage, and segment WhatsApp contacts |
| **Templates** | Create and manage message templates (requires Meta approval) |
| **Broadcasts** | Send templated messages to segments |
| **Conversations** | Two-way messaging with contact history |
| **OTP** | Secure verification codes for login |
| **Opt-in/Opt-out** | Compliance management |

### Message Types

| Type | Requires Template | Use Case |
|------|-------------------|----------|
| **Text** | No (if 24h window) | Conversations |
| **Template** | Yes | Broadcasts, OTP |
| **Media** | Yes (header) | Promotional |
| **Interactive** | Yes | CTAs, quick replies |

### Key Models

```python
class WhatsAppContact(Base):
    tenant_id: int
    phone_number: str
    name: str
    opt_in_status: str       # "opted_in", "pending", "opted_out"
    labels: list[str]
    last_interaction: datetime

class WhatsAppTemplate(Base):
    tenant_id: int
    name: str
    category: str            # "MARKETING", "UTILITY", "AUTHENTICATION"
    language: str
    status: str              # "PENDING", "APPROVED", "REJECTED"
    components: JSONB        # Header, body, footer, buttons
```

### Frontend Components
- `views/whatsapp/WhatsAppManager.tsx` — Main hub
- `views/whatsapp/WhatsAppContacts.tsx` — Contact management
- `views/whatsapp/WhatsAppTemplates.tsx` — Template editor
- `views/whatsapp/WhatsAppBroadcast.tsx` — Broadcast composer
- `views/whatsapp/WhatsAppMessages.tsx` — Conversation view

---

## 13. Payments

### Purpose
Subscription billing via Stripe with plan management and invoicing.

### Plans

| Plan | Price | Users | Campaigns | Features |
|------|-------|-------|-----------|----------|
| **Starter** | $99/mo | 3 | 10 | Core dashboard, 2 platforms |
| **Professional** | $299/mo | 10 | 50 | +CDP, +Autopilot, +CRM |
| **Enterprise** | Custom | Unlimited | Unlimited | +SLA, +Dedicated support, +Custom ML |

### Billing Events

| Event | Stripe Webhook | Action |
|-------|----------------|--------|
| Subscription created | `customer.subscription.created` | Activate tenant |
| Payment succeeded | `invoice.payment_succeeded` | Update MRR metrics |
| Payment failed | `invoice.payment_failed` | Alert + grace period |
| Subscription cancelled | `customer.subscription.deleted` | Schedule tenant deactivation |

### Key Models

```python
class Subscription(Base):
    tenant_id: int
    stripe_subscription_id: str
    plan: str                    # "starter", "professional", "enterprise"
    status: str                  # "active", "past_due", "canceled"
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
```

### Frontend Components
- `views/Settings.tsx` — Billing tab
- `views/pages/Pricing.tsx` — Public pricing page
- `views/superadmin/Billing.tsx` — Superadmin billing management

---

## 14. Superadmin

### Purpose
Internal dashboard for system-wide monitoring, tenant management, and operational tasks.

### Access Control

| Feature | Route | Required Role |
|---------|-------|---------------|
| Portfolio overview | `/superadmin` | superadmin |
| Tenant management | `/superadmin/tenants` | superadmin |
| Billing oversight | `/superadmin/billing` | superadmin |
| System health | `/superadmin/system` | superadmin |
| CMS management | `/superadmin/cms` | superadmin |
| Audit logs | `/superadmin/audit` | superadmin |

### Portfolio Metrics

| Metric | Source |
|--------|--------|
| MRR | Stripe subscriptions |
| ARR | MRR × 12 |
| Churn Rate | Canceled / Total subscriptions |
| ARPA | Total MRR / Active tenants |
| NRR | (Starting MRR + Expansion - Churn) / Starting MRR |

### System Health Dashboard

| Component | Metric |
|-----------|--------|
| Pipeline | Success rate, jobs failed (24h) |
| API | Requests, error rate, P50/P99 latency |
| Platforms | Per-platform sync success rate |
| Resources | CPU, memory, disk usage |

### Frontend Components
- `views/SuperadminDashboard.tsx` — Main dashboard
- `views/superadmin/TenantsList.tsx` — Tenant directory
- `views/superadmin/Billing.tsx` — Billing management
- `views/superadmin/System.tsx` — System health
- `views/superadmin/CMS.tsx` — Global CMS management
- `views/superadmin/Audit.tsx` — Audit log viewer

---

## Cross-Cutting Concerns

### Audit Logging

Every state-mutating operation is logged:

```python
class AuditLogEntry(Base):
    tenant_id: Optional[int]
    user_id: int
    action: str              # "create", "update", "delete", "execute"
    resource_type: str       # "campaign", "user", "rule"
    resource_id: int
    changes: JSONB           # { "before": {}, "after": {} }
    ip_address: str
    user_agent: str
    success: bool
    timestamp: datetime
```

### Rate Limiting

| Endpoint Type | Limit | Window |
|---------------|-------|--------|
| Auth (login) | 5 | 15 minutes |
| Auth (register) | 3 | 15 minutes |
| API (general) | 100 | 1 minute |
| API (heavy) | 20 | 1 minute |
| Webhooks | 1000 | 1 minute |

### Error Handling

| Code | Meaning | User Action |
|------|---------|-------------|
| 400 | Bad Request | Check input validation |
| 401 | Unauthorized | Log in again |
| 403 | Forbidden | Contact admin for permissions |
| 404 | Not Found | Check URL or ID |
| 409 | Conflict | Resource already exists |
| 422 | Validation Error | Fix form errors |
| 429 | Too Many Requests | Wait and retry |
| 500 | Server Error | Contact support |

---

## Related Documentation

- [Feature User Flows](../04-features/) — Step-by-step user journeys per feature
- [API Contracts](../04-features/) — Request/response schemas per feature
- [System Architecture](../architecture/system-architecture.md) — Full-stack architecture
- [Setup Guide](../01-setup/local-setup.md) — Development environment setup
