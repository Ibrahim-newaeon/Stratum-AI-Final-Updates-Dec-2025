# Stratum AI Platform - Complete Feature Documentation v1.0.0

**Release Date:** January 13, 2026
**Version:** 1.0.0
**Production Status:** 100% Validated

---

## Table of Contents

1. [Platform Overview](#platform-overview)
2. [Core Architecture](#core-architecture)
3. [Trust Engine](#trust-engine)
4. [Autopilot System](#autopilot-system)
5. [Campaign Management](#campaign-management)
6. [Platform Integrations](#platform-integrations)
7. [CRM Integration](#crm-integration)
8. [Analytics & Reporting](#analytics--reporting)
9. [Attribution Modeling](#attribution-modeling)
10. [Pacing & Forecasting](#pacing--forecasting)
11. [Profit & ROAS Analysis](#profit--roas-analysis)
12. [A/B Testing](#ab-testing)
13. [User Management](#user-management)
14. [API Reference](#api-reference)
15. [Technical Stack](#technical-stack)

---

## Platform Overview

Stratum AI is a **Revenue Operating System** with **Trust-Gated Autopilot Architecture**. The platform enables marketing teams to automate campaign management while ensuring data quality through intelligent safety mechanisms.

### Core Concept

```
Signal Health Check → Trust Gate → Automation Decision
       ↓                  ↓              ↓
   [HEALTHY]         [PASS]         [EXECUTE]
   [DEGRADED]        [HOLD]         [ALERT ONLY]
   [UNHEALTHY]       [BLOCK]        [MANUAL REQUIRED]
```

### Key Value Propositions

- **Trust-Gated Automation**: Automation only executes when signal health passes safety thresholds
- **Multi-Platform Support**: Meta, Google, TikTok, Snapchat ad platform integrations
- **Real-Time Signal Monitoring**: Continuous EMQ (Event Match Quality) tracking
- **Intelligent Budget Management**: AI-powered budget allocation and pacing
- **Comprehensive Attribution**: Multi-touch attribution with multiple models
- **CRM Integration**: HubSpot integration with bidirectional sync

---

## Core Architecture

### Multi-Tenant Design

The platform operates on a multi-tenant architecture where each organization (tenant) has isolated data and configurations.

| Component | Description |
|-----------|-------------|
| Tenant Isolation | Complete data separation between organizations |
| Role-Based Access | Admin, Manager, Analyst, Viewer roles |
| Feature Flags | Per-tenant feature enablement |
| Subscription Plans | Tiered access to features |

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        STRATUM AI PLATFORM                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Frontend   │  │   Backend    │  │   Workers    │          │
│  │   React 18   │  │   FastAPI    │  │   Celery     │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                 │                 │                   │
│         └────────────────┼─────────────────┘                   │
│                          │                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  PostgreSQL  │  │    Redis     │  │  Prometheus  │          │
│  │   Database   │  │    Cache     │  │  Monitoring  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

---

## Trust Engine

The Trust Engine is the core decision-making component that evaluates signal health before allowing automation execution.

### Signal Health Calculator

Calculates a composite health score (0-100) from four weighted components:

| Component | Weight | Description |
|-----------|--------|-------------|
| EMQ Score | 40% | Event Match Quality from platform data |
| Freshness Score | 25% | Data recency (fresh <24h, stale >48h) |
| Variance Score | 20% | Attribution consistency (platform vs GA4) |
| Anomaly Score | 15% | Z-score based pattern detection |

### Health Status Levels

| Status | Score Range | Behavior |
|--------|-------------|----------|
| HEALTHY | ≥70 | Full autopilot enabled |
| DEGRADED | 40-69 | Limited actions, alert only |
| CRITICAL | <40 | Manual intervention required |

### Trust Gate Decision Flow

```
[Signal Sources] → [Collectors] → [Health Calculator]
                                         ↓
                                   [Trust Gate]
                                    ↙      ↘
                              [PASS]      [HOLD/BLOCK]
                                ↓              ↓
                          [Execute]      [Alert/Manual]
```

### EMQ (Event Match Quality) Drivers

The 5-driver model for EMQ scoring:

1. **Event Match Rate** - Percentage of events successfully matched
2. **Pixel Coverage** - Coverage of tracking pixels across properties
3. **Conversion Latency** - Time delay in conversion reporting
4. **Attribution Accuracy** - Accuracy of attribution data
5. **Data Freshness** - Recency of incoming data

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/tenant/{id}/signal-health` | GET | Get signal health status |
| `/tenant/{id}/signal-health/history` | GET | Get historical signal health |
| `/tenant/{id}/attribution-variance` | GET | Get attribution variance |
| `/tenant/{id}/trust-status` | GET | Get combined trust status |

---

## Autopilot System

The Autopilot System manages automated campaign actions with configurable enforcement rules.

### Enforcement Modes

| Mode | Description |
|------|-------------|
| ADVISORY | Warn only, no blocking |
| SOFT_BLOCK | Warn + require confirmation |
| HARD_BLOCK | Prevent via API, log override attempts |

### Violation Types

| Type | Description |
|------|-------------|
| BUDGET_EXCEEDED | Daily/campaign budget limits exceeded |
| ROAS_BELOW_THRESHOLD | Revenue/spend ratio below target |
| DAILY_SPEND_LIMIT | Daily spending cap reached |
| CAMPAIGN_PAUSE_REQUIRED | Performance triggers pause |
| FREQUENCY_CAP_EXCEEDED | Ad frequency limits exceeded |

### Enforcement Settings

```json
{
  "enforcement_enabled": true,
  "default_mode": "SOFT_BLOCK",
  "max_daily_budget_increase_pct": 20,
  "max_campaign_budget": 10000,
  "roas_threshold": 2.0,
  "roas_lookback_days": 7,
  "max_changes_per_day": 10,
  "min_hours_between_changes": 4
}
```

### Action Lifecycle

```
QUEUED → APPROVED → APPLIED
           ↓
        FAILED

QUEUED → DISMISSED (cancelled)
```

### Action Types

| Category | Actions |
|----------|---------|
| Budget | increase, decrease |
| Status | pause, enable (campaign/adset/creative) |
| Bid | increase, decrease |

### Kill Switch

Emergency feature to disable all autopilot actions for a tenant:

```
POST /tenant/{id}/autopilot/enforcement/kill-switch
Body: { "enabled": false }
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/tenant/{id}/autopilot/status` | GET | Get autopilot status |
| `/tenant/{id}/autopilot/actions` | GET | Get queued actions |
| `/tenant/{id}/autopilot/actions` | POST | Queue new action |
| `/tenant/{id}/autopilot/actions/{id}/approve` | POST | Approve action |
| `/tenant/{id}/autopilot/actions/{id}/dismiss` | POST | Dismiss action |
| `/tenant/{id}/autopilot/enforcement/settings` | GET/PUT | Get/update settings |
| `/tenant/{id}/autopilot/enforcement/check` | POST | Check action validity |
| `/tenant/{id}/autopilot/enforcement/audit-log` | GET | Get audit log |

---

## Campaign Management

### Campaign Builder

Multi-step wizard for creating campaigns across platforms:

| Step | Description |
|------|-------------|
| 1. Platform Selection | Choose ad platform and ad account |
| 2. Campaign Basics | Name, objective configuration |
| 3. Budget & Schedule | Daily/lifetime budget, date range |
| 4. Targeting | Locations, demographics, interests |
| 5. Ad Creatives | Upload images/videos, set copy |
| 6. Review & Submit | Final review before submission |

### Campaign Workflow

```
DRAFT → SUBMITTED → APPROVED → PUBLISHING → PUBLISHED
                       ↓
                   REJECTED → DRAFT (revise)

PUBLISHING → FAILED (retry available)
```

### Supported Platforms

| Platform | Features |
|----------|----------|
| Meta (Facebook/Instagram) | Full campaign management, CAPI |
| Google Ads | Campaign creation, conversion tracking |
| TikTok | Campaign management, events API |
| Snapchat | Campaign management, conversions |

### Campaign Draft Fields

```json
{
  "name": "Summer Sale 2026",
  "platform": "META",
  "objective": "CONVERSIONS",
  "budget_type": "DAILY",
  "budget_amount_cents": 10000,
  "start_date": "2026-01-15",
  "end_date": "2026-02-15",
  "targeting": {
    "locations": ["US", "CA"],
    "age_min": 25,
    "age_max": 54,
    "genders": ["male", "female"]
  },
  "creatives": [...]
}
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/tenant/{id}/campaign-drafts` | GET/POST | List/create drafts |
| `/tenant/{id}/campaign-drafts/{id}` | GET/PUT | Get/update draft |
| `/tenant/{id}/campaign-drafts/{id}/submit` | POST | Submit for approval |
| `/tenant/{id}/campaign-drafts/{id}/approve` | POST | Approve draft |
| `/tenant/{id}/campaign-drafts/{id}/reject` | POST | Reject draft |
| `/tenant/{id}/campaign-drafts/{id}/publish` | POST | Publish to platform |
| `/tenant/{id}/ad-accounts/{platform}` | GET | List ad accounts |

---

## Platform Integrations

### OAuth Connection Flow

```
1. POST /oauth/{platform}/start → Returns authorization URL
2. User authorizes on platform
3. GET /oauth/{platform}/callback → Exchanges code for tokens
4. POST /oauth/{platform}/connect → Connects selected ad account
```

### Connection Status

| Status | Description |
|--------|-------------|
| CONNECTED | Active, working connection |
| EXPIRED | Token expired, needs refresh |
| ERROR | Connection error |
| DISCONNECTED | User disconnected |

### CAPI (Conversion API) Integration

Server-side conversion tracking for improved attribution:

| Feature | Description |
|---------|-------------|
| Event Delivery | Real-time event transmission to platforms |
| PII Hashing | Privacy-compliant data handling |
| Retry Logic | Automatic retry with exponential backoff |
| Circuit Breaker | Prevents cascading failures |
| Rate Limiting | Token bucket rate control |

### Supported CAPI Events

- Purchase
- Lead
- Add to Cart
- View Content
- Initiate Checkout
- Subscribe
- Custom Events

### Offline Conversions

Upload offline conversions from:
- CRM systems (HubSpot, Salesforce)
- Point of Sale (POS)
- Call centers
- Manual CSV uploads

---

## CRM Integration

### HubSpot Integration

Full bidirectional sync with HubSpot CRM:

| Feature | Description |
|---------|-------------|
| Contact Sync | Import contacts with identity matching |
| Deal Tracking | Sync deals and revenue data |
| Writeback | Push attribution data back to HubSpot |
| Webhooks | Real-time event notifications |

### Identity Matching

Cross-platform user identification:

| Method | Description |
|--------|-------------|
| Email Hash | SHA256 hashed email matching |
| Phone Hash | SHA256 hashed phone matching |
| Click IDs | gclid, fbclid, ttclid, sclid matching |
| External IDs | Custom identifier matching |

### Pipeline Metrics

Track CRM pipeline with ad performance:

```json
{
  "leads": 150,
  "mqls": 75,
  "sqls": 45,
  "opportunities": 20,
  "deals_won": 8,
  "ad_spend_cents": 500000,
  "pipeline_value_cents": 15000000,
  "won_revenue_cents": 4000000,
  "pipeline_roas": 30.0,
  "won_roas": 8.0
}
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/integrations/hubspot/connect` | POST | Start OAuth flow |
| `/integrations/hubspot/status` | GET | Get connection status |
| `/integrations/hubspot/sync` | POST | Trigger manual sync |
| `/integrations/pipeline/summary` | GET | Get pipeline summary |
| `/integrations/pipeline/roas` | GET | Get pipeline ROAS |
| `/integrations/contacts` | GET | List synced contacts |
| `/integrations/deals` | GET | List synced deals |

---

## Analytics & Reporting

### Dashboard KPIs

| Metric | Description |
|--------|-------------|
| Spend | Total ad spend across platforms |
| Revenue | Attributed revenue |
| ROAS | Return on ad spend |
| Conversions | Total conversion count |
| CTR | Click-through rate |
| CPC | Cost per click |
| CPA | Cost per acquisition |

### Analytics Dimensions

- Platform breakdown (Meta, Google, TikTok, Snapchat)
- Campaign performance
- Demographics (age, gender, location)
- Time trends (daily, weekly, monthly)

### Report Types

| Type | Description |
|------|-------------|
| CAMPAIGN_PERFORMANCE | Campaign metrics and trends |
| ATTRIBUTION_SUMMARY | Attribution model comparison |
| PACING_STATUS | Budget pacing and forecasts |
| PROFIT_ROAS | Profit-based ROAS analysis |
| PIPELINE_METRICS | CRM pipeline performance |
| EXECUTIVE_SUMMARY | High-level overview |
| CUSTOM | User-defined metrics |

### Report Formats

- PDF
- CSV
- Excel
- JSON
- HTML

### Scheduled Reports

```json
{
  "frequency": "WEEKLY",
  "day_of_week": 1,
  "time_of_day": "09:00",
  "delivery_channels": ["EMAIL", "SLACK"],
  "recipients": ["team@company.com"]
}
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/analytics/kpis` | GET | Get KPI tiles |
| `/analytics/demographics` | GET | Get demographic data |
| `/analytics/platform-breakdown` | GET | Platform performance |
| `/analytics/trends` | GET | Performance trends |
| `/reporting/templates` | GET/POST | Report templates |
| `/reporting/schedules` | GET/POST | Report schedules |
| `/reporting/generate` | POST | Generate report |

---

## Attribution Modeling

### Supported Models

| Model | Description |
|-------|-------------|
| LAST_TOUCH | 100% credit to last touchpoint |
| FIRST_TOUCH | 100% credit to first touchpoint |
| LINEAR | Equal credit across all touchpoints |
| POSITION_BASED | 40% first, 40% last, 20% middle |
| TIME_DECAY | More credit to recent touchpoints |
| DATA_DRIVEN | ML-based attribution |

### Data-Driven Models

| Algorithm | Description |
|-----------|-------------|
| MARKOV_CHAIN | Probability-based state transitions |
| SHAPLEY_VALUE | Game theory fair credit allocation |

### Attribution Metrics

```json
{
  "model": "TIME_DECAY",
  "dimension": "campaign",
  "attributed_revenue_cents": 5000000,
  "attributed_conversions": 150,
  "attributed_roas": 4.5,
  "touchpoints": {
    "first_touch_count": 200,
    "last_touch_count": 150,
    "assisted_count": 450
  }
}
```

### Conversion Path Analysis

Track customer journeys across touchpoints:

```
Meta Ad → Google Search → Direct → Conversion
   ↓           ↓           ↓
  20%        50%        30% (time decay)
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/attribution/daily` | GET | Daily attributed revenue |
| `/attribution/paths` | GET | Conversion paths |
| `/attribution/models` | GET | Trained models |
| `/attribution/compare` | GET | Model comparison |

---

## Pacing & Forecasting

### Target Management

Set and track performance targets:

| Metric Type | Description |
|-------------|-------------|
| SPEND | Ad spend targets |
| REVENUE | Revenue targets |
| ROAS | Return on ad spend targets |
| CONVERSIONS | Conversion targets |
| LEADS | Lead generation targets |
| CPA | Cost per acquisition targets |

### Target Configuration

```json
{
  "metric_type": "SPEND",
  "target_value_cents": 5000000,
  "period": "MONTHLY",
  "start_date": "2026-01-01",
  "end_date": "2026-01-31",
  "warning_threshold_pct": 80,
  "critical_threshold_pct": 95
}
```

### Pacing Status

| Status | Description |
|--------|-------------|
| ON_TRACK | Within expected range |
| AHEAD | Above expected pace |
| BEHIND | Below expected pace |
| AT_RISK | May miss target |
| MISSED | Target will not be met |

### Pacing Alerts

| Alert Type | Description |
|------------|-------------|
| UNDERPACING_SPEND | Spending below pace |
| OVERPACING_SPEND | Spending above pace |
| ROAS_BELOW_TARGET | ROAS trending below target |
| PACING_CLIFF | Sudden pace change |
| BUDGET_EXHAUSTION | Budget running out early |

### Forecasting

Predict end-of-period performance:

```json
{
  "forecast_type": "EOM",
  "model_type": "EWMA",
  "forecasted_value_cents": 4800000,
  "confidence_lower_cents": 4500000,
  "confidence_upper_cents": 5100000,
  "confidence_level": 0.95
}
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/pacing/targets` | GET/POST | Manage targets |
| `/pacing/status` | GET | Get pacing status |
| `/pacing/alerts` | GET | Get pacing alerts |
| `/pacing/forecast` | GET | Get forecasts |

---

## Profit & ROAS Analysis

### Profit Calculation

Track true profitability beyond revenue ROAS:

| Metric | Formula |
|--------|---------|
| Gross Profit | Revenue - COGS |
| Contribution Margin | Gross Profit - Variable Costs |
| Net Profit | Contribution Margin - Fixed Costs |
| Profit ROAS | Net Profit / Ad Spend |

### Cost Components

| Cost Type | Description |
|-----------|-------------|
| COGS | Cost of goods sold |
| Shipping | Shipping/fulfillment costs |
| Platform Fees | Marketplace fees |
| Payment Processing | Payment gateway fees |
| Returns | Return/refund costs |

### Margin Configuration

```json
{
  "product_id": "SKU-12345",
  "cogs_cents": 2500,
  "margin_type": "PERCENTAGE",
  "margin_value": 0.35,
  "shipping_cost_cents": 500,
  "platform_fee_pct": 0.15,
  "payment_fee_pct": 0.029
}
```

### Profit Reports

- Product-level profitability
- Category-level analysis
- Platform comparison
- Breakeven analysis

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/profit/products` | GET/POST | Product catalog |
| `/profit/margins` | GET/POST | Margin configuration |
| `/profit/daily` | GET | Daily profit metrics |
| `/profit/reports` | GET | Profit reports |

---

## A/B Testing

### Test Types

| Type | Description |
|------|-------------|
| CAMPAIGN | Test campaign variations |
| CREATIVE | Test ad creative variations |
| AUDIENCE | Test audience segments |
| LANDING_PAGE | Test landing page variations |
| BID_STRATEGY | Test bidding strategies |

### Test Configuration

```json
{
  "name": "Creative Test Q1",
  "test_type": "CREATIVE",
  "variants": [
    {"name": "Control", "traffic_split": 50},
    {"name": "Variant A", "traffic_split": 50}
  ],
  "primary_metric": "CONVERSION_RATE",
  "minimum_sample_size": 1000,
  "confidence_level": 0.95
}
```

### Test Lifecycle

```
DRAFT → RUNNING → COMPLETED
           ↓
        PAUSED → RUNNING
           ↓
        STOPPED
```

### Statistical Analysis

| Metric | Description |
|--------|-------------|
| p_value | Statistical significance |
| effect_size | Magnitude of difference |
| confidence_interval | Range of likely values |
| power | Probability of detecting effect |

### Power Analysis

Calculate required sample size:

```json
{
  "baseline_conversion_rate": 0.05,
  "minimum_detectable_effect": 0.10,
  "confidence_level": 0.95,
  "power": 0.80,
  "required_sample_size": 3842
}
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/experiments` | GET/POST | List/create experiments |
| `/experiments/{id}` | GET/PUT | Get/update experiment |
| `/experiments/{id}/start` | POST | Start experiment |
| `/experiments/{id}/stop` | POST | Stop experiment |
| `/experiments/{id}/results` | GET | Get statistical results |

---

## User Management

### User Roles

| Role | Permissions |
|------|-------------|
| ADMIN | Full access, user management |
| MANAGER | Campaign management, approvals |
| ANALYST | View analytics, create reports |
| VIEWER | Read-only access |

### Authentication Features

| Feature | Description |
|---------|-------------|
| Email/Password | Standard authentication |
| WhatsApp OTP | Two-factor via WhatsApp |
| JWT Tokens | Access and refresh tokens |
| Email Verification | Verify email ownership |
| Password Reset | Self-service password recovery |

### User Management

```json
{
  "email": "user@company.com",
  "full_name": "John Doe",
  "role": "MANAGER",
  "is_active": true,
  "tenant_id": "uuid",
  "preferences": {
    "timezone": "America/New_York",
    "notifications": ["email", "slack"]
  }
}
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/login` | POST | User login |
| `/auth/register` | POST | User registration |
| `/auth/refresh` | POST | Refresh tokens |
| `/auth/me` | GET | Get current user |
| `/users` | GET | List users |
| `/users/invite` | POST | Invite user |
| `/users/{id}` | PATCH/DELETE | Update/delete user |

---

## API Reference

### Base URL

```
Production: https://api.stratum.ai/v1
Development: http://localhost:8000/api/v1
```

### Authentication

All API requests require a Bearer token:

```
Authorization: Bearer <access_token>
```

### Rate Limiting

| Tier | Requests/Minute |
|------|-----------------|
| Standard | 100 |
| Professional | 500 |
| Enterprise | 2000 |

### Response Format

```json
{
  "data": {...},
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 100
  }
}
```

### Error Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request",
    "details": [...]
  }
}
```

### Complete Endpoint Summary

| Module | Endpoints |
|--------|-----------|
| Authentication | 13 |
| Users | 6 |
| Tenants | 9 |
| Trust Layer | 4 |
| Autopilot | 8 |
| Autopilot Enforcement | 8 |
| Campaign Builder | 17 |
| Integrations | 17 |
| Campaigns | 7 |
| Analytics | 7 |
| Dashboard | 8 |
| Reporting | 25+ |
| OAuth | 7 |
| Predictions | 3 |
| SuperAdmin | 5+ |
| **Total** | **150+** |

---

## Technical Stack

### Backend

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11+ | Runtime |
| FastAPI | Latest | Web framework |
| PostgreSQL | 15 | Database |
| Redis | Latest | Caching/queues |
| Celery | Latest | Task queue |
| SQLAlchemy | 2.x | ORM |
| Pydantic | 2.x | Validation |
| Alembic | Latest | Migrations |

### Frontend

| Technology | Version | Purpose |
|------------|---------|---------|
| React | 18 | UI framework |
| TypeScript | 5.x | Type safety |
| Tailwind CSS | 3.x | Styling |
| Vite | Latest | Build tool |
| React Router | 6.x | Routing |
| TanStack Query | Latest | Data fetching |
| Zustand | Latest | State management |

### Infrastructure

| Technology | Purpose |
|------------|---------|
| Docker | Containerization |
| Docker Compose | Local orchestration |
| AWS ECS | Production deployment |
| AWS RDS | Managed PostgreSQL |
| AWS ElastiCache | Managed Redis |
| Prometheus | Metrics collection |
| Grafana | Monitoring dashboards |
| Sentry | Error tracking |

### Testing

| Tool | Purpose |
|------|---------|
| Pytest | Unit/integration tests |
| K6 | Load testing |
| Vitest | Frontend testing |

---

## Production Validation

### Test Results

| Category | Result |
|----------|--------|
| Unit Tests | 179/179 passed |
| Integration Tests | 52/52 passed |
| Load Tests | 100% checks passed |
| Security Audit | No vulnerabilities |
| Frontend Build | Successful |

### Load Test Performance

| Endpoint | p95 Response Time |
|----------|-------------------|
| GET /settings | 95ms |
| PUT /settings | 136ms |
| POST /check | 67ms |
| GET /audit-log | 43ms |

### Monitoring

Prometheus alerts configured for:
- High error rate (>5%)
- High latency (p95 > 500ms)
- API/Worker down
- Database connection issues
- Signal health degradation
- Autopilot frozen state

---

## Quick Start Commands

```bash
# Start the full stack
docker compose up -d

# Run all tests
docker compose exec api pytest tests/ -v

# Run load tests
docker run --rm -i --network stratum_network \
  grafana/k6 run - < tests/load/autopilot-enforcement-load-test.js

# View logs
docker compose logs -f api

# Access API docs
open http://localhost:8000/docs
```

---

## Support & Resources

- **Documentation**: `/docs` directory
- **API Reference**: `http://localhost:8000/docs` (Swagger UI)
- **Issues**: GitHub Issues
- **Architecture**: `/docs/architecture/`

---

**Stratum AI v1.0.0** - Revenue Operating System with Trust-Gated Autopilot

*Built with precision. Deployed with confidence.*
