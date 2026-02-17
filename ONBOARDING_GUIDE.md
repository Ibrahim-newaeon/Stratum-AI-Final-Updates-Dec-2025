# Stratum AI - Platform Onboarding Guide

## Table of Contents

1. [Platform Overview](#1-platform-overview)
2. [User Roles & Permissions](#2-user-roles--permissions)
3. [Getting Started](#3-getting-started)
4. [Dashboard Navigation Map](#4-dashboard-navigation-map)
5. [Core Features Walkthrough](#5-core-features-walkthrough)
6. [CDP (Customer Data Platform)](#6-cdp-customer-data-platform)
7. [Campaign Management](#7-campaign-management)
8. [Analytics & Intelligence](#8-analytics--intelligence)
9. [Automation & Rules](#9-automation--rules)
10. [Advanced Features](#10-advanced-features)
11. [Superadmin Panel](#11-superadmin-panel)
12. [CMS Portal](#12-cms-portal)
13. [Account Manager Portal](#13-account-manager-portal)
14. [Integrations](#14-integrations)
15. [API Reference](#15-api-reference)
16. [Feature Matrix by Plan](#16-feature-matrix-by-plan)

---

## 1. Platform Overview

Stratum AI is a **Revenue Operating System** with a Trust-Gated Autopilot architecture. It combines campaign management, customer data, analytics, and intelligent automation into a single platform.

### Core Concept: Trust-Gated Automation

```
Signal Health Check  -->  Trust Gate  -->  Automation Decision
       |                     |                    |
  [HEALTHY 70+]         [PASS]            [EXECUTE automatically]
  [DEGRADED 40-69]      [HOLD]            [ALERT ONLY - review needed]
  [UNHEALTHY <40]       [BLOCK]           [MANUAL REQUIRED]
```

The platform monitors signal health (data quality) and only allows automated actions when trust thresholds are met. This protects budgets from executing on unreliable data.

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Tailwind CSS |
| Backend | Python 3.11+, FastAPI, Pydantic |
| Database | PostgreSQL 16 |
| Cache/Queue | Redis 7 |
| Background Jobs | Celery + Redis |
| Infrastructure | Docker, AWS/DigitalOcean |

---

## 2. User Roles & Permissions

| Role | Access Level | Typical User |
|------|-------------|--------------|
| **Superadmin** | Full platform access, cross-tenant | Platform operator |
| **Admin** | Full tenant access, team management | Agency owner, Marketing Director |
| **Manager** | Campaign CRUD, analytics, reports | Campaign Manager, Media Buyer |
| **Analyst** | Read-only dashboards and reports | Data Analyst |
| **Viewer** | Read-only dashboards | Client stakeholder |
| **Account Manager** | Portfolio of tenants, narrative views | AM / CSM |

### Permission Matrix

| Capability | Superadmin | Admin | Manager | Analyst | Viewer |
|-----------|-----------|-------|---------|---------|--------|
| View dashboards | Yes | Yes | Yes | Yes | Yes |
| Create campaigns | Yes | Yes | Yes | No | No |
| Manage rules | Yes | Yes | Yes | No | No |
| Run reports | Yes | Yes | Yes | Yes | No |
| Manage team | Yes | Yes | No | No | No |
| Tenant settings | Yes | Yes | No | No | No |
| System admin | Yes | No | No | No | No |
| Manage billing | Yes | No | No | No | No |
| CMS access | Yes | Yes (limited) | No | No | No |

---

## 3. Getting Started

### For New Users (Self-Service)

1. **Sign Up** at `/signup`
   - Enter company name, email, password
   - Password requires: 8+ chars, uppercase, lowercase, digit

2. **Verify Email**
   - Check inbox for verification link (expires in 5 minutes)
   - Click to verify at `/verify-email`

3. **Complete Onboarding Wizard** at `/onboarding`
   - Select your industry
   - Enter ad spend range
   - Set team size
   - Choose automation mode (full autopilot vs. approval-based)
   - Select primary KPI focus

4. **Access Dashboard**
   - You'll land on `/dashboard/overview`
   - The sidebar contains all navigation sections

### For Invited Users

1. Accept the team invitation email
2. Set your password
3. Log in at `/login`
4. You'll have access based on your assigned role

### First Steps After Login

| Step | Action | Where |
|------|--------|-------|
| 1 | Connect ad platforms | `/app/:tenantId/campaigns/connect` |
| 2 | Review dashboard overview | `/dashboard/overview` |
| 3 | Set up automation rules | `/dashboard/rules` |
| 4 | Configure notifications | `/dashboard/settings` |
| 5 | Invite team members | `/app/:tenantId/team` |

---

## 4. Dashboard Navigation Map

### Main Sidebar Structure

```
MAIN DASHBOARD (/dashboard)
|
+-- Core Navigation
|   +-- Overview              Dashboard home with KPIs
|   +-- Dashboard             Custom dashboard builder
|   +-- Campaigns             Campaign listing & performance
|   +-- Stratum               Signal intelligence & anomalies
|   +-- Benchmarks            Industry benchmarks
|   +-- Competitor Intel      Competitor tracking & analysis
|   +-- Assets                Creative asset management (DAM)
|   +-- Rules                 Automation rules engine
|   +-- Custom Autopilot      Enterprise custom automation
|   +-- Custom Reports        Report builder
|   +-- WhatsApp              WhatsApp messaging
|
+-- CDP (Customer Data Platform) [Collapsible]
|   +-- CDP Overview          Health & stats
|   +-- Profiles              Customer profiles
|   +-- Segments              Audience segmentation
|   +-- Events                Event timeline
|   +-- Identity Graph        Identity resolution
|   +-- RFM Analysis          Recency/Frequency/Monetary
|   +-- Funnels               Conversion funnels
|   +-- Computed Traits       Custom attributes
|   +-- Consent               GDPR/CCPA consent
|   +-- Predictive Churn      Churn prediction
|   +-- Audience Sync         Push to ad platforms
|
+-- Knowledge Graph [Collapsible]
|   +-- Insights              Business insights
|   +-- Problem Detection     Anomaly detection
|   +-- Revenue Attribution   Revenue paths
|   +-- Journey Explorer      Customer journeys
|
+-- Admin/System
|   +-- Tenants               Multi-tenant management
|   +-- ML Training           Model training
|   +-- CAPI Setup            Conversion API config
|   +-- Data Quality          Data validation
|   +-- EMQ Dashboard         Event Match Quality
|   +-- Settings              Account settings
|
+-- Superadmin [Role-restricted]
    +-- Dashboard             Revenue metrics (MRR/ARR)
    +-- Control Tower         Platform operations
    +-- Tenants               Tenant management
    +-- Benchmarks            Cross-tenant benchmarks
    +-- Audit                 Audit trail
    +-- Billing               Subscription management
    +-- System                System health
    +-- CMS                   Content management
    +-- Users                 User administration
```

### Tenant-Scoped Navigation (`/app/:tenantId`)

```
TENANT WORKSPACE
|
+-- Overview                  Tenant dashboard & KPIs
+-- Campaigns                 Campaign management
|   +-- Connect               OAuth platform connections
|   +-- Ad Accounts           Account selection
|   +-- New Campaign          Campaign builder wizard
|   +-- Drafts                Draft management
|   +-- Publish Logs          Publish history
|
+-- Analytics
|   +-- Attribution           Multi-touch attribution
|   +-- Profit ROAS           Profitability analysis
|   +-- Pacing                Budget pacing & forecasts
|   +-- Reporting             Automated reports
|   +-- Integrations          CRM & data connectors
|
+-- Advanced
|   +-- A/B Testing           Experiment framework
|   +-- Dead Letter Queue     Failed event recovery
|   +-- Model Explainability  ML model interpretation
|   +-- Embed Widgets         Embeddable components
|
+-- Admin
    +-- Settings              Tenant configuration
    +-- Team                  Team member management
    +-- Competitors           Competitor tracking
    +-- Benchmarks            Performance benchmarks
```

---

## 5. Core Features Walkthrough

### Dashboard Overview (`/dashboard/overview`)

The main dashboard displays:
- **KPI Cards** - Spend, Revenue, ROAS, Conversions with trends
- **Campaign Performance Table** - Top campaigns by performance
- **Interactive Charts** - Daily trends, platform breakdown, regional analysis
- **Anomaly Alerts** - Automated anomaly detection
- **Quick Actions** - Common tasks shortcuts

**Actions available:**
- Click any KPI card to drill down into campaign details
- Set metric alerts from KPI cards
- Export dashboard data (CSV)
- Filter by date range, platform, region

### Signal Intelligence (`/dashboard/stratum`)

The Stratum view shows:
- **Anomaly Detection** - AI-detected anomalies across metrics
- **Signal Health** - Data quality scoring per platform
- **Alert Rules** - Create/edit rules for metric thresholds
- **Insight Cards** - Actionable recommendations

---

## 6. CDP (Customer Data Platform)

### CDP Overview (`/dashboard/cdp`)

Displays CDP health metrics:
- Total profiles, events ingested, active segments
- Lifecycle distribution (anonymous, known, customer, churned)
- Event volume charts with trends

### Profiles (`/dashboard/cdp/profiles`)

- **Search** customers by name, email, or attributes
- **View Profile Detail** - Unified customer view with:
  - Identity information
  - Event history
  - Segment membership
  - Computed traits
  - Consent status

### Segments (`/dashboard/cdp/segments`)

Build dynamic audience segments:
1. Click "Create Segment"
2. Add conditions (behavioral rules, properties, events)
3. Preview audience size
4. Save and activate

**Condition types:**
- Profile attributes (age, location, plan)
- Event-based (purchased in last 30 days)
- RFM scoring (high-value customers)
- Lifecycle stage (new, active, at-risk, churned)

### Audience Sync (`/dashboard/cdp/audience-sync`)

Push CDP segments to ad platforms for targeting:

**Supported Platforms:**
| Platform | API | Match Types |
|----------|-----|-------------|
| Meta | Custom Audiences | Email, Phone, MAID |
| Google | Customer Match | Email, Phone, MAID |
| TikTok | DMP Audiences | Email, Phone, MAID |
| Snapchat | SAM Audiences | Email, Phone, MAID |

**How to sync:**
1. Connect platform (OAuth) via Campaigns > Connect
2. Go to Audience Sync
3. Create audience linked to a CDP segment
4. Set sync interval (1 hour to 1 week)
5. Monitor match rates and sync history

**Manual Export:**
- Export audiences as CSV or JSON
- Include traits, events, and custom attributes

### Identity Graph (`/dashboard/cdp/identity`)

Visual SVG-based graph showing:
- How anonymous visitors become known customers
- Cross-device connections
- Profile merge history
- Canonical identity resolution

### Other CDP Features

| Feature | Path | Description |
|---------|------|-------------|
| RFM Analysis | `/dashboard/cdp/rfm` | Recency/Frequency/Monetary customer scoring |
| Funnels | `/dashboard/cdp/funnels` | Conversion funnel analysis |
| Computed Traits | `/dashboard/cdp/computed-traits` | Custom calculated attributes |
| Consent Manager | `/dashboard/cdp/consent` | GDPR/CCPA consent management |
| Predictive Churn | `/dashboard/cdp/predictive-churn` | ML-powered churn prediction |

---

## 7. Campaign Management

### Connecting Ad Platforms (`/app/:tenantId/campaigns/connect`)

1. Navigate to Campaigns > Connect Platforms
2. Click "Connect" next to the platform
3. Complete OAuth authorization
4. Select ad accounts to sync

**Supported platforms:** Meta Ads, Google Ads, TikTok Ads, Snapchat Ads

### Creating Campaigns (`/app/:tenantId/campaigns/new`)

The Campaign Builder wizard guides you through:
1. **Platform Selection** - Choose target platform
2. **Campaign Setup** - Name, objective, budget
3. **Audience Targeting** - Use CDP segments or platform audiences
4. **Creative Selection** - Choose from DAM assets
5. **Review & Publish** - Verify settings before launch

**Save as Draft** - Save progress without publishing

### Campaign Lifecycle

```
Draft --> Active --> Paused --> Completed
                      |
                   Archived
```

### Campaign Performance (`/app/:tenantId/campaigns`)

View all campaigns with:
- Status, spend, revenue, ROAS, CPA
- Sorting and filtering by platform, status
- Pause/resume/delete actions
- Bulk status updates

### Creative Assets (`/dashboard/assets`)

Digital Asset Management (DAM):
- Upload images, videos, HTML5 creatives
- Tag and organize assets
- Track creative fatigue scores
- Asset performance metrics

---

## 8. Analytics & Intelligence

### Attribution (`/app/:tenantId/attribution`)

Multi-touch attribution modeling:
- **Models:** First-touch, Last-touch, Linear, Time-decay, Data-driven
- **Channel Contribution** - See how each channel contributes to conversions
- **Conversion Paths** - Visualize customer journey paths
- **Revenue Attribution** - Attribute revenue to channels/campaigns

### Profit ROAS (`/app/:tenantId/profit`)

Go beyond ROAS to actual profitability:
- Upload product margins and COGS
- Calculate true profit per channel/campaign
- Identify campaigns that drive revenue but lose money
- Margin rules for dynamic cost calculations

### Pacing (`/app/:tenantId/pacing`)

Budget pacing and forecasting:
- **Set Targets** - Budget and KPI targets by period
- **Track Pace** - Daily actual vs. expected spend
- **Pace Alerts** - Get notified when pacing deviates
- **Forecasts** - ML-powered spend and performance forecasts

### Automated Reporting (`/app/:tenantId/reporting`)

Create and schedule automated reports:

1. **Create Template** - Define report structure
   - Choose report type (performance, attribution, executive, etc.)
   - Select sections and metrics
   - Set default format (PDF, Excel, CSV, etc.)

2. **Schedule Delivery** - Set up recurring reports
   - Frequency: daily, weekly, biweekly, monthly, quarterly
   - Delivery channels: email, Slack, Teams, webhook, S3
   - Configure recipients per channel

3. **Generate On-Demand** - Run reports with custom date range

4. **View History** - Track all generated reports with download links

### Benchmarks (`/dashboard/benchmarks`)

Industry and competitive benchmarks:
- Compare your metrics against industry averages
- Platform-specific benchmarks (CTR, CPC, ROAS by industry)
- Tenant-to-tenant comparison (anonymized)

### Competitor Intelligence (`/dashboard/competitors`)

Track and analyze competitors:
- Ad spend estimation
- Creative monitoring
- Share of voice
- Competitive positioning

---

## 9. Automation & Rules

### Rules Engine (`/dashboard/rules`)

Create IF-THEN automation rules:

**Condition Fields:** ROAS, CTR, CPC, CPA, Spend, Impressions, Clicks, Conversions, Fatigue Score

**Operators:** =, !=, >, <, >=, <=

**Actions:**
| Action | Description |
|--------|-------------|
| Pause Campaign | Automatically pause underperforming campaigns |
| Adjust Budget | Increase/decrease budget by percentage |
| Apply Label | Tag campaigns for organization |
| Send Alert | Email notification |
| Notify Slack | Slack channel notification |
| Notify WhatsApp | WhatsApp message alert |

**Example Rules:**
- IF ROAS < 2.0 THEN Pause Campaign (cooldown: 24h)
- IF Spend > $800 THEN Notify WhatsApp (cooldown: 12h)
- IF CTR > 3% THEN Adjust Budget +20% (cooldown: 48h)

### Custom Autopilot (`/dashboard/custom-autopilot-rules`)

Enterprise-grade trust-gated automation:
- Complex condition groups (AND/OR logic)
- Multi-action sequences
- Trust gate integration - actions only execute when signal health passes
- Full audit trail of all automated actions

---

## 10. Advanced Features

### A/B Testing (`/app/:tenantId/ab-testing`)

Run statistically rigorous experiments:

1. **Create Test** - Name, hypothesis, test type, primary metric
2. **Configure Variants** - Control + variants with traffic allocation
3. **Set Confidence Level** - 90%, 95%, or 99%
4. **Power Analysis** - Calculate required sample size before launch
5. **Monitor Results** - Real-time statistical significance
6. **LTV Impact** - Projected revenue lift from winning variant

**Test Types:** Campaign, Creative, Audience, Landing Page, Bid Strategy

### Dead Letter Queue (`/app/:tenantId/dead-letter-queue`)

Manage failed Conversion API (CAPI) events:
- View failed events with error details
- Retry individual or bulk events
- Resolve events manually
- Filter by platform and status
- Track recovery metrics

### Model Explainability (`/app/:tenantId/explainability`)

Understand ML model decisions:
- **SHAP Analysis** - Feature importance visualization
- **LIME Explanations** - Local model interpretation
- **LTV Predictions** - Customer lifetime value forecasting
- **Feature Impact** - Which factors drive predictions

### WhatsApp Integration (`/dashboard/whatsapp`)

Business messaging capabilities:
- Contact management with opt-in tracking
- Conversation threading
- Template-based messaging
- OTP verification for authentication
- Scheduled message delivery

---

## 11. Superadmin Panel

Access: `/dashboard/superadmin` (superadmin role only)

### Dashboard
- **Revenue Metrics** - MRR, ARR, NRR, churn rate
- **Tenant Portfolio** - All tenants at a glance
- **System Health** - Infrastructure status

### Tenant Management (`/dashboard/superadmin/tenants`)
- Create/edit/suspend tenants
- View tenant health profiles
- Manage feature flags per tenant
- Override autopilot settings

### System Health (`/dashboard/superadmin/system`)
- Service status (API, DB, Redis, Workers)
- Queue monitoring (pause, resume, retry failed jobs)
- Resource usage metrics
- Pipeline health checks

### Audit Trail (`/dashboard/superadmin/audit`)
- Browse all user actions
- Filter by user, action type, date range
- Export for compliance reporting

### Billing (`/dashboard/superadmin/billing`)
- Subscription management
- Plan changes and invoicing
- Usage metrics per tenant

### User Management (`/dashboard/superadmin/users`)
- Platform-wide user administration
- Role assignment
- Account status management

---

## 12. CMS Portal

Access: `/cms` (admin/superadmin only, separate login at `/cms-login`)

### Features

| Section | Path | Description |
|---------|------|-------------|
| Dashboard | `/cms` | CMS overview and stats |
| Posts | `/cms/posts` | Blog post management |
| Post Editor | `/cms/posts/new` | Rich text editor with media |
| Categories | `/cms/categories` | Category hierarchy |
| Authors | `/cms/authors` | Author profiles |
| Contacts | `/cms/contacts` | Contact form submissions |
| Pages | `/cms/pages` | Static page management |
| Landing Features | `/cms/landing/features` | Edit landing page features |
| Landing FAQ | `/cms/landing/faq` | Edit FAQ section |
| Landing Pricing | `/cms/landing/pricing` | Edit pricing section |
| Settings | `/cms/settings` | CMS configuration |

### Post Editor Features
- Rich text editing with TipTap
- Media upload and embedding
- SEO metadata (title, description)
- Category and tag assignment
- Draft/publish workflow
- Scheduled publishing

---

## 13. Account Manager Portal

Access: `/dashboard/am/portfolio` (AM role)

### Portfolio View (`/dashboard/am/portfolio`)
- Overview of all assigned tenants
- Health indicators per tenant (EMQ score, autopilot mode)
- Quick action buttons

### Tenant Narrative (`/dashboard/am/tenant/:tenantId`)

Client-facing account review with 4 tabs:

1. **Client Summary** - EMQ score card, timeline overview
2. **What Changed** - 30-day event timeline with incidents
3. **What We Blocked** - Actions blocked by trust gate + budget protected
4. **Fix Playbook** - Prioritized action items with owners and impact estimates

**Actions:**
- Export narrative report (text download)
- Schedule client call (opens email template)
- Assign playbook items to team members

---

## 14. Integrations

### Ad Platforms (OAuth)

| Platform | Features |
|----------|----------|
| Meta Ads | Campaign sync, CAPI, audience sync |
| Google Ads | Campaign sync, audience sync |
| TikTok Ads | Campaign sync, audience sync |
| Snapchat Ads | Campaign sync, audience sync |

### CRM Systems

| CRM | Features |
|-----|----------|
| HubSpot | Contact sync, deal tracking, writeback |
| Salesforce | Contact sync, deal tracking, writeback |
| Pipedrive | Contact sync, deal tracking |
| Zoho | Contact sync, deal tracking |

### Communication

| Channel | Features |
|---------|----------|
| Slack | Notifications, report delivery, alerts |
| Email (SendGrid) | Transactional, reports, alerts |
| WhatsApp | Messaging, OTP, alerts |
| Webhooks | Custom event notifications |

### Data & Analytics

| Tool | Features |
|------|----------|
| Sentry | Error tracking and monitoring |
| Prometheus | Metrics collection |
| Grafana | Dashboard visualization |
| Stripe | Payment processing |

---

## 15. API Reference

### Authentication

```
POST /api/v1/auth/signup          Sign up (creates tenant)
POST /api/v1/auth/login           Login
POST /api/v1/auth/refresh-token   Refresh JWT
POST /api/v1/auth/logout          Logout
POST /api/v1/auth/forgot-password Password reset request
POST /api/v1/auth/reset-password  Password reset
POST /api/v1/auth/verify-email    Email verification
```

### Campaigns

```
GET    /api/v1/campaigns              List campaigns
POST   /api/v1/campaigns              Create campaign
GET    /api/v1/campaigns/:id          Get campaign
PATCH  /api/v1/campaigns/:id          Update campaign
DELETE /api/v1/campaigns/:id          Delete campaign
POST   /api/v1/campaigns/:id/pause    Pause campaign
POST   /api/v1/campaigns/:id/activate Resume campaign
```

### CDP

```
GET    /api/v1/cdp/health             CDP health metrics
GET    /api/v1/cdp/profiles           Search profiles
GET    /api/v1/cdp/profiles/:id       Get profile
GET    /api/v1/cdp/segments           List segments
POST   /api/v1/cdp/segments           Create segment
GET    /api/v1/cdp/events             List events
POST   /api/v1/cdp/events/ingest      Ingest events
GET    /api/v1/cdp/identity-graph     Identity graph
```

### Audience Sync

```
GET    /api/v1/cdp/audience-sync/platforms          Connected platforms
GET    /api/v1/cdp/audience-sync/audiences          List audiences
POST   /api/v1/cdp/audience-sync/audiences          Create audience
POST   /api/v1/cdp/audience-sync/audiences/:id/sync Trigger sync
GET    /api/v1/cdp/audience-sync/audiences/:id/history Sync history
DELETE /api/v1/cdp/audience-sync/audiences/:id      Delete audience
POST   /api/v1/cdp/audiences/export                 Export CSV/JSON
```

### Rules

```
GET    /api/v1/rules        List rules
POST   /api/v1/rules        Create rule
PATCH  /api/v1/rules/:id    Update rule
DELETE /api/v1/rules/:id    Delete rule
```

### Reporting

```
GET    /api/v1/reporting/templates    Report templates
POST   /api/v1/reporting/schedules   Schedule report
GET    /api/v1/reporting/executions   Report history
POST   /api/v1/reporting/execute     Generate report
POST   /api/v1/reporting/export      Export report
```

Full interactive API docs available at: `http://your-domain:8000/docs` (Swagger UI)

---

## 16. Feature Matrix by Plan

| Feature | Starter | Professional | Enterprise |
|---------|---------|-------------|------------|
| Dashboard & KPIs | Yes | Yes | Yes |
| Campaign Management | 5 campaigns | 50 campaigns | Unlimited |
| Ad Platform Sync | 1 platform | 4 platforms | 4 platforms |
| Rules Engine | 3 rules | 20 rules | Unlimited |
| Custom Autopilot | No | No | Yes |
| CDP Profiles | 10K | 100K | Unlimited |
| Audience Sync | No | 2 platforms | 4 platforms |
| Segments | 5 | 25 | Unlimited |
| A/B Testing | No | Yes | Yes |
| Attribution Modeling | Basic | Advanced | Data-driven |
| Profit ROAS | No | Yes | Yes |
| Pacing & Forecasting | Basic | Advanced | Advanced |
| Automated Reporting | Basic | Full | Full + Custom |
| Custom Reports | No | No | Yes |
| CRM Integration | No | HubSpot | All CRMs |
| WhatsApp | No | Yes | Yes |
| Team Members | 2 | 10 | Unlimited |
| API Access | No | Yes | Yes |
| Dedicated Support | Email | Priority | Dedicated CSM |
| SLA | None | 99.5% | 99.9% |

---

## Quick Reference Card

| Task | Where to Go |
|------|-------------|
| Log in | `/login` |
| View dashboard | `/dashboard/overview` |
| Create a campaign | `/app/:tenantId/campaigns/new` |
| Connect ad platform | `/app/:tenantId/campaigns/connect` |
| Build an audience | `/dashboard/cdp/segments` |
| Sync to ad platform | `/dashboard/cdp/audience-sync` |
| Set automation rule | `/dashboard/rules` |
| Create A/B test | `/app/:tenantId/ab-testing` |
| Generate report | `/app/:tenantId/reporting` |
| Manage team | `/app/:tenantId/team` |
| View system health | `/dashboard/superadmin/system` |
| Edit landing page | `/cms/landing/features` |
| API documentation | `http://your-domain:8000/docs` |

---

## Support & Resources

- **Public Website:** Landing page at `/`
- **API Docs:** Swagger UI at `/docs` on your API server
- **Status Page:** `/status`
- **Changelog:** `/changelog`
- **FAQ:** `/faq`
- **Documentation:** `/docs`
- **Contact:** `/contact`

---

*Last updated: February 2026*
