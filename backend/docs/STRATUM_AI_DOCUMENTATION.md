# Stratum AI - Platform Documentation

---

## 1. Executive Summary

Stratum AI is a **Revenue Operating System** built on a **Trust-Gated Autopilot** architecture. It is designed for marketing and advertising teams who need to automate campaign management, budget optimization, and performance analysis across multiple ad platforms -- while maintaining confidence that automation decisions are backed by reliable data.

The platform's core differentiator is its Trust Engine: before any automated action executes (budget changes, campaign pauses, bid adjustments), the system evaluates the health of incoming data signals. If signal quality falls below configurable thresholds, automation is held or blocked, and human operators are alerted. This prevents the costly errors that arise when automation acts on degraded or unreliable data.

```
Signal Health Check --> Trust Gate --> Automation Decision
       |                   |                |
   [HEALTHY]          [PASS]          [EXECUTE]
   [DEGRADED]         [HOLD]          [ALERT ONLY]
   [UNHEALTHY]        [BLOCK]         [MANUAL REQUIRED]
```

Stratum AI consolidates advertising data from Meta, Google, TikTok, Snapchat, and LinkedIn into a unified analytics layer, pairs it with a built-in Customer Data Platform (CDP), and delivers actionable recommendations through its analytics engine. The platform serves multiple tenants with complete data isolation, role-based access control, and enterprise-grade security.

---

## 2. Platform Architecture

### 2.1 High-Level Architecture

```
+---------------------+       +---------------------+       +----------------------+
|   React Frontend    |       |   FastAPI Backend    |       |   Background Workers |
|   (Vite + TS)       |<----->|   (Async Python)     |<----->|   (Celery + Beat)    |
|   Port 5173         |       |   Port 8000          |       |                      |
+---------------------+       +---------------------+       +----------------------+
                                      |   |                          |
                              +-------+   +--------+                |
                              |                    |                |
                     +--------v------+    +--------v------+   +----v---------+
                     |  PostgreSQL   |    |    Redis      |   |  Ad Platform |
                     |  16           |    |    7          |   |  APIs        |
                     |  Port 5432    |    |  Port 6379    |   |  (Meta,      |
                     +---------------+    +---------------+   |   Google,    |
                                                              |   TikTok,    |
                                                              |   Snapchat,  |
                                                              |   LinkedIn)  |
                                                              +--------------+
```

### 2.2 Tech Stack Summary

| Layer | Technology | Version |
|-------|-----------|---------|
| **Backend** | Python, FastAPI, Pydantic | 3.11+, 0.109, 2.x |
| **Database** | PostgreSQL (asyncpg driver) | 16 |
| **Cache/Queue** | Redis | 7 |
| **Task Queue** | Celery + Celery Beat | 5.3 |
| **ORM** | SQLAlchemy (async) | 2.x |
| **Auth** | JWT + OAuth2 + MFA (TOTP) | -- |
| **Frontend** | React, TypeScript, Vite | 18, 5.3, 5.1 |
| **UI Framework** | Tailwind CSS, shadcn/ui, Radix UI | 3.4 |
| **State Management** | Zustand + TanStack React Query | -- |
| **Charting** | Recharts, Tremor | -- |
| **Animation** | Framer Motion | -- |
| **Migrations** | Alembic | -- |
| **Monitoring** | Prometheus, Grafana, Sentry | -- |
| **Logging** | structlog (JSON) | -- |
| **Containerization** | Docker Compose (8 services) | -- |

### 2.3 System Components

| Component | Description |
|-----------|-------------|
| **API Server** | FastAPI application with 50+ REST endpoints, async I/O, automatic OpenAPI docs |
| **Celery Worker** | Background task processor (4 concurrency) for data sync, report generation, audience sync |
| **Celery Beat** | Scheduled task runner for periodic data pulls, health checks, pacing alerts |
| **Frontend** | Single-page React application with real-time WebSocket updates |
| **PostgreSQL** | Primary data store with tenant-isolated schemas and 41+ Alembic migrations |
| **Redis** | Multi-purpose: API caching (db 0), Celery broker (db 1), Celery results (db 2), rate limiting |
| **Flower** | Optional Celery monitoring dashboard (port 5555) |

---

## 3. Core Features

### 3.1 Trust Engine & Signal Health

The Trust Engine is the platform's decision-making core. It evaluates the reliability of incoming data signals before allowing any automation to execute. Signal health is a composite score (0-100) computed from five weighted drivers: EMQ score (35%), API health (25%), event loss rate (20%), platform stability (10%), and data quality (10%). When signal health drops below the configurable healthy threshold (default 70), the Trust Gate holds automation and alerts operators. The system supports four health states: Healthy, Risk, Degraded, and Critical.

**Key files:** `analytics/logic/signal_health.py`, `stratum/core/trust_gate.py`

### 3.2 Customer Data Platform (CDP)

The CDP provides a unified customer data layer that collects events from multiple sources, resolves identities across devices and channels, and builds enriched customer profiles. It supports batch and single-event ingestion with source key authentication, identity resolution with canonical identity graphs, lifecycle stage tracking (Anonymous through Churned), RFM analysis, computed traits, dynamic segment building, funnel analysis, and consent management. All PII is encrypted at rest using Fernet encryption.

**Key files:** `models/cdp.py`, `api/v1/endpoints/cdp.py`, `schemas/cdp.py`

### 3.3 Autopilot Enforcement Engine

The Autopilot system manages automated campaign actions through a trust-gated approval workflow. Actions flow through three enforcement modes: Advisory (warn only), Soft-Block (warn + require confirmation), and Hard-Block (prevent action, log override attempts). The engine supports action types including budget increases/decreases, campaign/adset/creative pause/enable, and bid adjustments. Safe actions (budget decreases, pauses, bid decreases) can auto-execute at Guarded Auto level, while all other actions require explicit approval. Every action is audit-logged with before/after values and platform responses.

**Key files:** `autopilot/enforcer.py`, `autopilot/service.py`

### 3.4 Campaign Builder

The Campaign Builder provides a complete workflow for creating, drafting, and publishing campaigns across connected ad platforms. It manages platform connectors (OAuth connections), ad account sync and enable/disable, campaign draft CRUD with approval workflows, and publish logs for audit trails. Drafts progress through a lifecycle (draft, review, approved, published) with RBAC-enforced permissions at each stage. All routes enforce tenant isolation.

**Key files:** `models/campaign_builder.py`, `api/v1/endpoints/campaign_builder.py`

### 3.5 Audience Sync

Audience Sync pushes CDP segments to advertising platforms as custom audiences for targeting. It supports Meta Custom Audiences, Google Customer Match, TikTok Custom Audiences, and Snapchat Audience Match. Each sync is configurable with auto-sync intervals (1-168 hours), and sync history is tracked for audit purposes. PII is SHA-256 hashed before transmission to ad platforms. Platform availability is gated by subscription tier: Professional gets 2 platforms, Enterprise gets all 4.

**Key files:** `services/cdp/audience_sync/`, `api/v1/endpoints/audience_sync.py`

### 3.6 Authentication & Security (JWT + MFA + OAuth2)

Authentication uses a multi-layered approach combining JWT access/refresh tokens, optional TOTP-based MFA, and WhatsApp OTP verification. Access tokens expire after 30 minutes (configurable), refresh tokens after 7 days. Password hashing uses bcrypt. The system includes login rate limiting with Redis-backed attempt tracking, token blacklisting for logout, email verification flows, and password reset with time-limited tokens. PII fields are encrypted with Fernet (AES) before storage, and constant-time comparisons (`hmac.compare_digest`) are used for sensitive operations.

**Key files:** `auth/`, `core/security.py`, `services/mfa_service.py`, `api/v1/endpoints/auth.py`

### 3.7 Analytics Engine (EMQ, Attribution, Anomaly Detection)

The analytics engine comprises eight interconnected modules:

- **EMQ Calculation:** Computes Event Measurement Quality from five drivers -- Event Match Rate (30%), Pixel Coverage (25%), Conversion Latency (20%), Attribution Accuracy (15%), and Data Freshness (10%). Scores determine autopilot mode: normal (80+), limited (60-79), cuts-only (40-59), or frozen (<40).
- **Scaling Score:** Ranks campaigns/adsets for "scale vs fix" using ROAS, CPA, CVR, and CTR deltas against baselines, with frequency, EMQ, and volume penalties. EMA smoothing reduces noise.
- **Creative Fatigue:** Detects overexposed creatives by measuring CTR drops, ROAS drops, CPA rises, and frequency increases against baselines. States: Healthy (<0.45), Watch (0.45-0.65), Refresh (>0.65).
- **Anomaly Detection:** Z-score based detection across spend, ROAS, CPA, and other metrics with configurable windows and thresholds. Severity levels: Low, Medium, High, Critical.
- **Attribution Variance:** Quantifies divergence between platform-reported and GA4 data for revenue and conversions. Flags significant variance (>30%) with actionable warnings.
- **Budget Reallocation:** Daily optimization that shifts budget from underperformers to winners with guardrails (max 15% total daily spend movement, per-entity caps).
- **Recommendations Engine:** Central orchestrator that combines all analytics into prioritized, actionable daily recommendations.
- **Data-Driven Attribution:** ML-based credit distribution across marketing touchpoints.

**Key files:** `analytics/logic/` (8 modules)

### 3.8 Ad Platform Integrations (Meta, Google, TikTok, Snapchat, LinkedIn)

Stratum AI integrates with five major advertising platforms through a unified OAuth factory pattern. Each platform integration supports OAuth authorization flows with token refresh, ad account discovery and selection, campaign/adset/creative data sync, spend and performance metrics ingestion, and Conversions API (CAPI) for server-side event tracking. The platform supports both live API connections and mock data mode for development. LinkedIn integration adds B2B-specific campaign management including objective types like Lead Generation and Job Applicants.

**Key files:** `services/oauth/` (factory.py, meta.py, google.py, tiktok.py, snapchat.py), `services/linkedin_client.py`

### 3.9 CMS (Content Management)

The CMS module provides a full-featured content management system for blog posts, pages, and contact form handling. It includes public endpoints (no auth) for listing published posts, fetching by slug, browsing categories and tags, and submitting contact forms. Admin endpoints provide full CRUD for posts, pages, categories, tags, and authors with a versioned workflow system (draft, review, published). The CMS supports SEO metadata, rich text content, and editorial workflows with audit logging.

**Key files:** `models/cms.py`, `api/v1/endpoints/cms.py`

### 3.10 WhatsApp Business Integration

The WhatsApp module integrates with the WhatsApp Business API for customer communication. It supports contact management with opt-in status tracking, message template management (Marketing, Utility, Authentication categories), conversation tracking, webhook handling for inbound messages and delivery status updates, and OTP verification for authentication flows. Webhook signatures are verified using HMAC SHA-256. The module supports template creation, message sending, and delivery analytics.

**Key files:** `services/whatsapp_service.py`, `services/whatsapp_client.py`, `api/v1/endpoints/whatsapp.py`

### 3.11 Subscription & Billing Management

The subscription system manages three tiers (Starter, Professional, Enterprise) with configurable feature gates, usage limits, and lifecycle states. Subscription status flows through Active, Expiring Soon (within 14 days), Grace Period (7 days after expiry), and Expired states. Feature access is enforced through a dependency injection system (`SubscriptionRequired`, `SubscriptionWarning`) that can be applied to any endpoint. The system supports grace periods to prevent abrupt service disruption. See Section 10 for payment gateway details.

**Key files:** `core/tiers.py`, `core/subscription.py`, `core/feature_gate.py`, `api/v1/endpoints/subscription.py`

### 3.12 Multi-Tenancy & Row-Level Security

Every request passes through the TenantMiddleware which extracts tenant context from JWT claims, X-Tenant-ID headers, or subdomain. Tenant ID is set on `request.state.tenant_id` and enforced on all database queries. The middleware allows public endpoints (health checks, auth, docs) to bypass tenant resolution. All data models include a `tenant_id` foreign key for row-level isolation. The architecture ensures complete data separation between customers while sharing a single application instance.

**Key files:** `middleware/tenant.py`, models with `tenant_id` columns

### 3.13 Reporting Engine (PDF, Slack, Email)

The reporting engine provides automated report generation with template-based configuration. It supports multiple report types (campaign performance, EMQ health, budget pacing), output formats (PDF, CSV), and delivery channels (email, Slack, in-app). Reports can be scheduled at various frequencies and include chart visualizations. The system tracks execution history with status logging and supports retry for failed deliveries. Templates are customizable with HTML and chart configuration options.

**Key files:** `services/reporting/` (report_generator.py, pdf_generator.py, delivery.py, scheduler.py), `api/v1/endpoints/reporting.py`

### 3.14 SuperAdmin Dashboard

The SuperAdmin dashboard provides platform-level oversight for Stratum AI operators. It surfaces revenue metrics (MRR, ARR, NRR, ARPA, churn rate), a tenant portfolio view with health indicators (signal health status, open alerts, churn risk, data freshness), system health monitoring (pipeline success rates, API error rates, latency percentiles, queue depth), and per-platform health breakdowns. This view is restricted to users with superadmin privileges and operates across all tenants.

**Key files:** `api/v1/endpoints/superadmin.py`, `api/v1/endpoints/superadmin_analytics.py`

### 3.15 Market Intelligence & Competitor Analysis

The competitor intelligence module allows tenants to track competitors and benchmark performance. Features include competitor tracking with share-of-voice analysis, estimated traffic comparisons, primary competitor designation, and market positioning insights. The module supports multiple data providers (SerpAPI, DataForSEO) with a mock provider for development. Competitor benchmarks are stored per-tenant and sortable by share of voice.

**Key files:** `api/v1/endpoints/competitors.py`, `services/competitor_benchmarking_service.py`, `services/competitor_scraper.py`

### 3.16 CRM Integrations (HubSpot, Zoho, Salesforce, Pipedrive)

Stratum AI integrates with four CRM platforms through a consistent pattern of client, sync, and writeback modules. Each integration supports OAuth-based authentication, contact and company data synchronization, identity matching between CDP profiles and CRM records, and bidirectional writeback of computed traits and segment memberships. HubSpot and Pipedrive are available at the Professional tier; Salesforce and Zoho require Enterprise. All CRM integrations support both API key and OAuth authentication methods.

**Key files:** `services/crm/` (hubspot_client.py, zoho_client.py, salesforce_client.py, pipedrive_client.py, *_sync.py, *_writeback.py)

### 3.17 Pacing & Budget Forecasting

The pacing module tracks spend velocity against targets and forecasts end-of-period outcomes. It supports target creation at multiple granularities (campaign, account, platform) for metrics including spend, revenue, ROAS, CPA, and conversions. The system uses EWMA-based forecasting for metric projection, real-time pacing calculations with on-track/over-pace/under-pace indicators, and configurable alerts with severity levels. Targets can be set for daily, weekly, monthly, or quarterly periods.

**Key files:** `services/pacing/` (PacingService, TargetService, ForecastingService, PacingAlertService), `api/v1/endpoints/pacing.py`

### 3.18 Profit & COGS Tracking

The profit module calculates true Profit ROAS by incorporating Cost of Goods Sold (COGS) data. It includes a product catalog with SKU-level management, COGS data ingestion from multiple sources (manual entry, CSV upload), margin rules with fixed and percentage margin types, and profit ROAS calculations that subtract COGS from platform-reported revenue. This provides advertisers with an accurate picture of advertising profitability beyond top-line revenue metrics.

**Key files:** `services/profit/` (ProfitCalculationService, COGSService, COGSIngestionService, ProductCatalogService), `api/v1/endpoints/profit.py`

---

## 4. API Reference Summary

### 4.1 API Endpoint Groups

All API endpoints are prefixed with `/api/v1/` and return standardized `APIResponse` wrappers.

| Endpoint Group | Prefix | Description |
|---------------|--------|-------------|
| **Auth** | `/auth` | Login, register, token refresh, password reset, email verification, WhatsApp OTP |
| **MFA** | `/mfa` | TOTP setup, verification, disable |
| **Users** | `/users` | User profile CRUD, role management |
| **Tenants** | `/tenants` | Tenant management, settings, member invitations |
| **OAuth** | `/oauth` | Platform OAuth flows (Meta, Google, TikTok, Snapchat) |
| **LinkedIn** | `/linkedin` | LinkedIn Ads OAuth, campaign management, analytics |
| **Campaign Builder** | `/tenant/{id}/...` | Platform connectors, ad accounts, campaign drafts, publish logs |
| **Campaigns** | `/campaigns` | Campaign data retrieval and management |
| **Dashboard** | `/dashboard` | Overview metrics, charts, summary data |
| **Analytics** | `/analytics` | Performance analytics, trends, breakdowns |
| **Analytics AI** | `/analytics/ai` | AI-powered insights and recommendations |
| **EMQ v2** | `/emq` | EMQ score calculation and driver breakdown |
| **Signal Health / Trust** | `/trust` | Signal health checks, trust gate status |
| **Autopilot** | `/autopilot` | Autopilot mode, action queue, approvals |
| **Autopilot Enforcement** | `/enforcement` | Enforcement rules, audit logs, confirmation tokens |
| **CDP** | `/cdp` | Profiles, events, segments, identity resolution, funnels, computed traits |
| **Audience Sync** | `/cdp/audience-sync` | Platform audience creation, sync triggers, sync history |
| **Pacing** | `/pacing` | Targets, pacing calculations, forecasts, alerts |
| **Profit** | `/profit` | Products, COGS, profit ROAS, margin rules |
| **Reporting** | `/reporting` | Report templates, schedules, executions, delivery |
| **Competitors** | `/competitors` | Competitor tracking, share of voice, benchmarks |
| **Rules** | `/rules` | Custom automation rules engine |
| **Simulator** | `/simulator` | What-if budget/bid simulation |
| **Predictions** | `/predictions` | ML-based performance predictions |
| **ML Training** | `/ml` | Model training triggers and status |
| **Notifications** | `/notifications` | In-app notification management |
| **Slack** | `/slack` | Slack integration and notification delivery |
| **WhatsApp** | `/whatsapp` | Contacts, templates, conversations, webhooks |
| **CMS** | `/cms` | Blog posts, pages, categories, tags, contact forms |
| **GDPR** | `/gdpr` | Data export, right to erasure, audit logs |
| **Feature Flags** | `/features` | Feature flag status for current tenant |
| **Subscription** | `/subscription` | Subscription status, tier info, plan management |
| **Tier** | `/tier` | Tier details, feature access, limits |
| **Payments** | `/payments` | Payment intents, checkout sessions |
| **Stripe Webhooks** | `/webhooks/stripe` | Stripe event processing |
| **API Keys** | `/api-keys` | API key generation and management |
| **Webhooks** | `/webhooks` | Webhook endpoint management |
| **Onboarding** | `/onboarding` | 5-step onboarding wizard |
| **Assets** | `/assets` | Creative asset management |
| **Insights** | `/insights` | AI-generated performance insights |
| **Knowledge Graph** | `/knowledge-graph` | Entity relationship exploration |
| **Embed Widgets** | `/embed` | Embeddable analytics widgets |
| **Changelog** | `/changelog` | Platform changelog entries |
| **SuperAdmin** | `/superadmin` | Platform-wide management (restricted) |
| **SuperAdmin Analytics** | `/superadmin/analytics` | Cross-tenant analytics (restricted) |
| **CAPI** | `/capi` | Conversions API configuration |
| **Meta CAPI** | `/meta-capi` | Meta-specific CAPI setup |
| **Attribution** | `/attribution` | Attribution model configuration |
| **DDA** | `/dda` | Data-driven attribution |
| **Newsletter** | `/newsletter` | Newsletter subscription management |
| **Landing CMS** | `/landing` | Landing page CMS |

### 4.2 Authentication Flow

```
1. POST /api/v1/auth/register       --> Create account (returns user, sends verification email)
2. GET  /api/v1/auth/verify-email    --> Verify email with token
3. POST /api/v1/auth/login           --> Authenticate (returns access + refresh tokens)
4. POST /api/v1/auth/mfa/verify      --> If MFA enabled, verify TOTP code
5. All subsequent requests include:   Authorization: Bearer <access_token>
6. POST /api/v1/auth/refresh          --> Exchange refresh token for new access token
7. POST /api/v1/auth/logout           --> Blacklist current token
```

### 4.3 Key Request/Response Patterns

All API responses follow a standardized wrapper format:

```json
{
  "success": true,
  "data": { ... },
  "message": "Optional message",
  "errors": null
}
```

Paginated responses include:

```json
{
  "success": true,
  "data": [ ... ],
  "total": 150,
  "page": 1,
  "page_size": 20,
  "pages": 8
}
```

Error responses:

```json
{
  "success": false,
  "data": null,
  "message": "Error description",
  "errors": [{"field": "email", "message": "Already registered"}]
}
```

---

## 5. Subscription Tiers

### 5.1 Tier Overview

| Aspect | Starter ($499/mo) | Professional ($999/mo) | Enterprise (Custom) |
|--------|-------------------|----------------------|-------------------|
| **Ad Accounts** | Up to 5 | Up to 15 | Unlimited |
| **Users** | Up to 3 | Up to 10 | Unlimited |
| **Segments** | Up to 10 | Up to 50 | Unlimited |
| **Automations** | Up to 5 | Up to 25 | Unlimited |
| **API Rate Limit** | 60/min | 300/min | 1,000/min |
| **Data Retention** | 90 days | 365 days | 730 days (2 years) |
| **API Keys** | 3 | 10 | Unlimited |
| **Webhooks** | 5 | 20 | Unlimited |
| **Embed Widgets** | 3 (with branding) | 10 (minimal branding) | Unlimited (white-label) |
| **Ad Spend Limit** | $100,000/mo | $500,000/mo | Unlimited |

### 5.2 Feature Comparison

| Feature | Starter | Professional | Enterprise |
|---------|:-------:|:------------:|:----------:|
| Signal Health Monitoring | Yes | Yes | Yes |
| Anomaly Detection | Yes | Yes | Yes |
| CDP Profiles & Events | Yes | Yes | Yes |
| RFM Analysis | Yes | Yes | Yes |
| Dashboard Exports | Yes | Yes | Yes |
| Slack/Email/In-App Notifications | Yes | Yes | Yes |
| API Access & Webhooks | Yes | Yes | Yes |
| Changelog Access | Yes | Yes | Yes |
| Funnel Builder | -- | Yes | Yes |
| Computed Traits | -- | Yes | Yes |
| Segment Builder | -- | Yes | Yes |
| Trust Gate Audit Logs | -- | Yes | Yes |
| Action Dry Run | -- | Yes | Yes |
| Pipedrive Integration | -- | Yes | Yes |
| HubSpot Integration | -- | Yes | Yes |
| Audience Sync (2 platforms) | -- | Yes | Yes |
| Predictive Churn | -- | -- | Yes |
| Custom Autopilot Rules | -- | -- | Yes |
| Custom Report Builder | -- | -- | Yes |
| What-If Simulator | -- | -- | Yes |
| Salesforce Integration | -- | -- | Yes |
| Zoho Integration | -- | -- | Yes |
| CRM Writeback | -- | -- | Yes |
| Consent Management | -- | -- | Yes |
| GDPR Tools | -- | -- | Yes |
| Audit Export | -- | -- | Yes |
| Audience Sync (all 4 platforms) | -- | -- | Yes |
| Identity Graph | -- | -- | Yes |
| White-Label Embed Widgets | -- | -- | Yes |

### 5.3 Subscription Lifecycle

```
Active --> Expiring Soon (14 days before expiry)
                |
                v
         Grace Period (7 days after expiry -- full access continues)
                |
                v
           Expired (access restricted, HTTP 402 returned)
```

**NOTE:** Payment gateway (Stripe) is optional for this phase. Subscriptions are managed via the `Tenant.plan` and `Tenant.plan_expires_at` database fields. When Stripe is not configured, all subscription features work normally -- plans are assigned and managed directly through the admin interface or API.

---

## 6. Client Onboarding Guide

The onboarding flow is a structured 5-step wizard that guides new tenants from initial setup to a fully operational platform. Each step is independently saveable, and progress is tracked so users can resume at any point.

### Step 1: Tenant Creation

1. A SuperAdmin or automated provisioning system creates a new tenant record via `POST /api/v1/tenants`.
2. The tenant is assigned a unique `slug` (used for subdomain routing, e.g., `acme.stratum.ai`), a subscription plan (`starter`, `professional`, or `enterprise`), and a `plan_expires_at` date.
3. The system initializes the tenant's configuration with default settings: enforcement mode (advisory), autopilot level (suggest-only), and Trust Engine thresholds.
4. The tenant receives a unique `tenant_id` that isolates all subsequent data.

### Step 2: Admin User Setup

1. The first user registers via `POST /api/v1/auth/register` with the tenant context.
2. An email verification link is sent. The user verifies their email via the link (or `GET /api/v1/auth/verify-email?token=...`).
3. The first user is automatically assigned the Admin role for the tenant.
4. The admin can optionally enable MFA via `POST /api/v1/mfa/setup` (generates a TOTP secret and QR code).
5. Additional team members are invited by the admin. Each receives an invitation email and registers through the accept-invite flow.
6. Roles are assigned: Admin, Manager, Analyst, or Viewer, each with different permission levels.

### Step 3: Ad Platform Connection (OAuth Flows)

1. Navigate to the Platform Selection step in the onboarding wizard (`PUT /api/v1/onboarding/step/2`).
2. Select which platforms to connect: Meta, Google, TikTok, Snapchat, and/or LinkedIn.
3. For each platform, initiate the OAuth flow:
   - `POST /api/v1/oauth/{platform}/start` -- returns an authorization URL.
   - The user is redirected to the platform's consent screen.
   - After granting access, the callback is handled at `GET /api/v1/oauth/{platform}/callback`.
   - Tokens are securely stored (encrypted) in the `TenantPlatformConnection` table.
4. Once connected, discover available ad accounts: `GET /api/v1/oauth/{platform}/accounts`.
5. Select and enable the accounts to track: `POST /api/v1/oauth/{platform}/accounts/connect`.
6. The system begins syncing historical data for enabled accounts.

### Step 4: Signal Health Verification

1. After platform connections are established, the system runs an initial data sync (triggered automatically or via Celery tasks).
2. Check signal health: `GET /api/v1/trust/signal-health`. This returns the current EMQ score, event loss percentage, API health status, and the composite signal health status.
3. Review the EMQ driver breakdown: `GET /api/v1/emq/score`. This shows the five driver scores:
   - **Event Match Rate** -- verify pixel and CAPI are both sending events.
   - **Pixel Coverage** -- confirm tracking is installed on key pages.
   - **Conversion Latency** -- ensure events are arriving promptly.
   - **Attribution Accuracy** -- compare platform vs GA4 numbers.
   - **Data Freshness** -- confirm recent data is flowing.
4. If any driver shows "critical" status, follow the recommended actions (e.g., check pixel installation, verify CAPI credentials, review event mapping).
5. Target: achieve an EMQ score of 80+ ("reliable" confidence band) before enabling automation.

### Step 5: CDP Setup (Customer Profiles & Events)

1. Create a data source: `POST /api/v1/cdp/sources` with source name and type (website, app, server, CRM).
2. Each source receives a unique `source_key` for authentication.
3. Begin ingesting events:
   - Single event: `POST /api/v1/cdp/events` with source key in headers.
   - Batch events: `POST /api/v1/cdp/events/batch` for high-volume ingestion.
4. Events automatically create or update profiles through identity resolution.
5. Configure segments: use the segment builder (Professional+ tier) to create dynamic audience groups based on behavioral and demographic criteria.
6. Set up computed traits to derive metrics like total purchases, average order value, and days since last activity.
7. If CRM integration is needed, connect via the CRM settings and configure sync schedules.

### Step 6: Autopilot Configuration

1. Navigate to the Automation Preferences step: `PUT /api/v1/onboarding/step/4`.
2. Select the autopilot mode:
   - **Manual** (Suggest Only) -- platform generates recommendations, human takes all actions.
   - **Assisted** (Approval Required) -- platform queues recommended actions, human approves.
   - **Semi-Auto** (Guarded Auto) -- safe actions (budget decreases, pauses) auto-execute within caps; others require approval.
3. Configure Trust Gate thresholds via `PUT /api/v1/onboarding/step/5`:
   - Budget change caps (daily maximum, percentage limits).
   - ROAS floor thresholds.
   - Enforcement mode (advisory, soft-block, hard-block).
4. Review the enforcement rules: `GET /api/v1/enforcement/rules`.
5. Test with a dry run: use the Action Dry Run feature (Professional+ tier) to simulate what autopilot would do without executing.

### Step 7: Dashboard Walkthrough

1. Navigate to the main dashboard at `GET /api/v1/dashboard/overview`.
2. Key dashboard sections:
   - **Signal Health Widget** -- real-time EMQ score with trend indicators.
   - **Campaign Performance** -- ROAS, spend, revenue, conversions by platform.
   - **Autopilot Queue** -- pending actions awaiting approval.
   - **Anomaly Alerts** -- any detected anomalies in spend, ROAS, or CPA.
   - **Recommendations** -- AI-generated daily insights.
   - **Budget Pacing** -- spend velocity against monthly targets.
3. Configure notification preferences: `POST /api/v1/notifications/preferences` (Slack, email, in-app).
4. Explore the CDP dashboard for customer insights, segments, and lifecycle analytics.
5. If competitor tracking is relevant, add competitors via `POST /api/v1/competitors`.

### Step 8: Reporting Setup

1. Browse available report templates: `GET /api/v1/reporting/templates`.
2. Create a custom template if needed: `POST /api/v1/reporting/templates` with report type, format (PDF/CSV), and chart configuration.
3. Schedule recurring reports: `POST /api/v1/reporting/schedules` with:
   - Template selection.
   - Frequency (daily, weekly, monthly).
   - Delivery channel (email address, Slack channel, or in-app).
   - Date range parameters.
4. Generate an on-demand report: `POST /api/v1/reporting/executions`.
5. Review delivery history: `GET /api/v1/reporting/deliveries`.
6. Failed deliveries can be retried via `POST /api/v1/reporting/deliveries/{id}/retry`.

---

## 7. Deployment Guide

### 7.1 Environment Variables Reference

| Variable | Required | Default | Description |
|----------|:--------:|---------|-------------|
| `APP_ENV` | Yes | `development` | Environment: `development`, `staging`, `production` |
| `SECRET_KEY` | **Yes** | -- | Application signing key (min 32 chars) |
| `JWT_SECRET_KEY` | **Yes** | -- | JWT token signing key (min 32 chars) |
| `PII_ENCRYPTION_KEY` | **Yes** | -- | Fernet encryption key for PII fields (min 32 chars) |
| `DATABASE_URL` | Yes | `postgresql+asyncpg://stratum:password@localhost:5432/stratum_ai` | Async PostgreSQL connection string |
| `DATABASE_URL_SYNC` | No | Derived from DATABASE_URL | Sync PostgreSQL connection (for Alembic) |
| `REDIS_URL` | Yes | `redis://localhost:6379/0` | Redis connection for caching |
| `CELERY_BROKER_URL` | Yes | `redis://localhost:6379/1` | Celery message broker |
| `CELERY_RESULT_BACKEND` | No | `redis://localhost:6379/2` | Celery result storage |
| `CORS_ORIGINS` | No | `http://localhost:3000,http://localhost:5173` | Comma-separated allowed origins |
| `FRONTEND_URL` | No | `http://localhost:5173` | Frontend base URL (for email links) |
| `LOG_LEVEL` | No | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `LOG_FORMAT` | No | `json` | Log format: `json` or `console` |
| `SENTRY_DSN` | No | -- | Sentry error tracking DSN |
| `ML_PROVIDER` | No | `local` | ML provider: `local` or `vertex` |
| `USE_MOCK_AD_DATA` | No | `false` | Use mock data (dev only, blocked in production) |
| `MARKET_INTEL_PROVIDER` | No | `mock` | Market intel: `mock`, `serpapi`, `dataforseo` |
| **Ad Platforms** | | | |
| `META_APP_ID` / `META_APP_SECRET` | No | -- | Meta/Facebook OAuth credentials |
| `GOOGLE_ADS_CLIENT_ID` / `GOOGLE_ADS_CLIENT_SECRET` | No | -- | Google Ads OAuth credentials |
| `TIKTOK_APP_ID` / `TIKTOK_SECRET` | No | -- | TikTok Ads OAuth credentials |
| `SNAPCHAT_CLIENT_ID` / `SNAPCHAT_CLIENT_SECRET` | No | -- | Snapchat OAuth credentials |
| `LINKEDIN_CLIENT_ID` / `LINKEDIN_CLIENT_SECRET` | No | -- | LinkedIn OAuth credentials |
| **WhatsApp** | | | |
| `WHATSAPP_PHONE_NUMBER_ID` | No | -- | WhatsApp Business phone number ID |
| `WHATSAPP_ACCESS_TOKEN` | No | -- | WhatsApp API access token |
| `WHATSAPP_BUSINESS_ACCOUNT_ID` | No | -- | WhatsApp Business account ID |
| `WHATSAPP_APP_SECRET` | No | -- | Webhook signature verification secret |
| **Email (SMTP)** | | | |
| `SMTP_HOST` / `SMTP_PORT` | No | -- / `587` | SMTP server configuration |
| `SMTP_USER` / `SMTP_PASSWORD` | No | -- | SMTP authentication |
| `EMAIL_FROM_ADDRESS` | No | `noreply@stratumhq.com` | Sender email address |
| **Stripe (Optional)** | | | |
| `STRIPE_SECRET_KEY` | No | -- | Stripe API secret key |
| `STRIPE_PUBLISHABLE_KEY` | No | -- | Stripe publishable key |
| `STRIPE_WEBHOOK_SECRET` | No | -- | Stripe webhook signing secret |
| **CRM** | | | |
| `HUBSPOT_CLIENT_ID` / `HUBSPOT_CLIENT_SECRET` | No | -- | HubSpot OAuth credentials |

### 7.2 Docker Deployment

**Quick start (full stack):**

```bash
# Set required environment variables
export SECRET_KEY=$(openssl rand -hex 32)
export JWT_SECRET_KEY=$(openssl rand -hex 32)
export PII_ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
export FLOWER_PASSWORD=$(openssl rand -hex 16)

# Start all 7 core services (db, redis, api, worker, scheduler, frontend, flower)
docker compose up -d

# Include optional monitoring (Flower)
docker compose --profile monitoring up -d
```

**Services launched:**

| Service | Container | Port | Health Check |
|---------|-----------|------|-------------|
| PostgreSQL 16 | `stratum_db` | 5432 | `pg_isready` |
| Redis 7 | `stratum_redis` | 6379 | `redis-cli ping` |
| FastAPI API | `stratum_api` | 8000 | `curl /health` |
| Celery Worker | `stratum_worker` | -- | `celery inspect ping` |
| Celery Beat | `stratum_scheduler` | -- | `celery inspect ping` |
| React Frontend | `stratum_frontend` | 5173 | -- |
| Flower (optional) | `stratum_flower` | 5555 | -- |

### 7.3 Database Setup

```bash
# PostgreSQL is automatically provisioned by Docker Compose.
# Alembic migrations run automatically on API container start:
#   alembic upgrade head

# To run migrations manually:
docker compose exec api alembic upgrade head

# To create a new migration:
docker compose exec api alembic revision --autogenerate -m "description"

# To check migration status:
docker compose exec api alembic current
```

### 7.4 Production Checklist

- [ ] Set `APP_ENV=production` (enforces security validations)
- [ ] Generate strong, unique values for `SECRET_KEY`, `JWT_SECRET_KEY`, `PII_ENCRYPTION_KEY` (min 32 chars each)
- [ ] Set `USE_MOCK_AD_DATA=false` (production rejects mock mode)
- [ ] Configure a strong PostgreSQL password (not `password` or `changeme`)
- [ ] Set `CORS_ORIGINS` to your actual frontend domain
- [ ] Configure `SENTRY_DSN` for error tracking
- [ ] Set up SMTP credentials for transactional emails
- [ ] Configure ad platform OAuth credentials for live integrations
- [ ] Set `WHATSAPP_VERIFY_TOKEN` to a unique value if WhatsApp is enabled
- [ ] Enable TLS/SSL for all external-facing services
- [ ] Configure resource limits appropriate for expected load
- [ ] Set up database backups (PostgreSQL pg_dump or continuous archiving)
- [ ] Set up Redis persistence or a managed Redis service
- [ ] Configure log aggregation for structlog JSON output
- [ ] Set up Prometheus scraping for the `/metrics` endpoint
- [ ] Review and configure rate limiting (`RATE_LIMIT_PER_MINUTE`, `RATE_LIMIT_BURST`)
- [ ] Set `DEBUG=false`
- [ ] Configure `FLOWER_PASSWORD` if using Flower monitoring

---

## 8. Security Features

### 8.1 Authentication

| Feature | Implementation |
|---------|---------------|
| **Password Hashing** | bcrypt via passlib |
| **JWT Access Tokens** | HS256 signed, 30-minute expiry (configurable) |
| **JWT Refresh Tokens** | 7-day expiry (configurable) |
| **Token Blacklisting** | Redis-backed for logout invalidation |
| **MFA (TOTP)** | RFC 6238 time-based one-time passwords |
| **WhatsApp OTP** | 5-minute expiry, Redis-stored |
| **Login Rate Limiting** | Redis-backed attempt tracking with lockout |
| **Email Verification** | Token-based, 24-hour expiry |
| **Password Reset** | Token-based, 1-hour expiry |

### 8.2 Data Protection

| Feature | Implementation |
|---------|---------------|
| **PII Encryption** | Fernet (AES-128-CBC) encryption for all PII fields before database storage |
| **PII Hashing** | SHA-256 hash columns for PII lookup without decryption |
| **Constant-Time Comparison** | `hmac.compare_digest()` for all sensitive value comparisons |
| **Token Generation** | `secrets` module (cryptographically secure) for all tokens and keys |
| **Audience Data** | SHA-256 hashing of emails/phones before platform sync |

### 8.3 Tenant Isolation

| Feature | Implementation |
|---------|---------------|
| **Row-Level Security** | All models include `tenant_id` FK; all queries filter by tenant |
| **Middleware Enforcement** | `TenantMiddleware` extracts and validates tenant context on every request |
| **JWT Claims** | `tenant_id` embedded in JWT; cross-tenant requests rejected |
| **API Key Scoping** | API keys are tenant-scoped with `X-Tenant-ID` header validation |

### 8.4 GDPR Compliance

| Feature | Endpoint |
|---------|----------|
| **Data Export** | `POST /api/v1/gdpr/export` -- exports all user data as JSON (Data Portability) |
| **Right to Erasure** | `POST /api/v1/gdpr/anonymize` -- anonymizes PII fields irreversibly |
| **Consent Management** | CDP consent tracking per profile (Enterprise tier) |
| **Audit Logging** | All data access and modifications logged with user, action, and timestamp |
| **Audit Export** | Audit logs exportable for compliance review (Enterprise tier) |

### 8.5 Rate Limiting

- Global rate limiting: configurable per-minute and burst limits.
- Tier-based rate limiting: Starter (60/min), Professional (300/min), Enterprise (1,000/min).
- Login-specific rate limiting with progressive lockout.
- CDP event ingestion rate limiting per source key.

### 8.6 Security Validations in Production

The application enforces the following in `staging` and `production` environments:

- `SECRET_KEY` must not be the default value.
- `JWT_SECRET_KEY` must not be the default value.
- `PII_ENCRYPTION_KEY` must not be the default value.
- `USE_MOCK_AD_DATA` must be `false`.
- Database password must not be in the insecure defaults list.
- All security keys must be at least 32 characters.

---

## 9. Monitoring & Observability

### 9.1 Structured Logging

All application logs are emitted in JSON format via `structlog` with consistent fields:

```json
{
  "timestamp": "2025-12-15T10:30:00Z",
  "level": "info",
  "event": "request_completed",
  "request_id": "abc-123",
  "tenant_id": 42,
  "user_id": 7,
  "method": "GET",
  "path": "/api/v1/dashboard",
  "status_code": 200,
  "duration_ms": 45
}
```

Log level is configurable via the `LOG_LEVEL` environment variable. Format toggles between `json` (production) and `console` (development) via `LOG_FORMAT`.

### 9.2 Sentry Integration

- Error tracking with automatic exception capture.
- Performance tracing with configurable sample rates (`SENTRY_TRACES_SAMPLE_RATE`, default 10%).
- Profiling with configurable sample rates (`SENTRY_PROFILES_SAMPLE_RATE`, default 10%).
- Release tracking via `SENTRY_RELEASE` tag (typically git SHA or version number).
- Tenant context attached to all Sentry events for filtering.

### 9.3 Prometheus Metrics

The application exposes metrics at the `/metrics` endpoint for Prometheus scraping:

- **Request metrics:** latency histograms, request counts by path/method/status.
- **Queue metrics:** Celery queue depth, task execution times, failure rates.
- **Business metrics:** active tenants, signal health distribution, autopilot action counts.
- **System metrics:** database connection pool usage, Redis connection counts.

### 9.4 Health Check Endpoints

| Endpoint | Purpose | Checks |
|----------|---------|--------|
| `GET /health` | Basic liveness | Application is running |
| `GET /health/live` | Kubernetes liveness | Process is alive |
| `GET /health/ready` | Kubernetes readiness | Database and Redis are reachable |

### 9.5 Celery Monitoring

- **Flower Dashboard** (optional, port 5555): Real-time view of worker status, task queues, active/completed/failed tasks.
- Password-protected access via `FLOWER_BASIC_AUTH`.
- Worker health checks via `celery inspect ping` with 10-second timeout.

---

## 10. Payment Gateway Note

For this phase, no payment gateway is required. The subscription system operates independently using database-managed plan assignments (`Tenant.plan`). When Stripe is configured in the future, it will sync automatically with the existing subscription infrastructure. All billing UI gracefully handles the unconfigured state.

Specifically:

- **Plan Assignment:** Tenant plans are set via the `Tenant.plan` field (`starter`, `professional`, `enterprise`) and `Tenant.plan_expires_at` for expiry tracking.
- **Feature Gating:** The `core/tiers.py` module enforces feature access based on the plan field directly, independent of any payment processor.
- **Subscription Status:** The `core/subscription.py` module calculates Active/Expiring/Grace/Expired status from the database fields alone.
- **Stripe Preparation:** Environment variables (`STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`, Stripe Price IDs per tier) are defined but all default to `None`. The `stripe_service.py` and webhook endpoints are implemented and ready for activation.
- **Graceful Degradation:** When Stripe keys are not configured, the payment endpoints return appropriate responses indicating the payment system is not active, and all other platform features continue to function normally.

---

*Document generated for Stratum AI Platform. For questions, refer to the codebase documentation in the `/docs` directory or contact the engineering team.*
