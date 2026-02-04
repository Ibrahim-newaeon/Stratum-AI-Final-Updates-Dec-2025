# Stratum AI - Complete Feature Documentation

**Version:** 2.0.0
**Last Updated:** January 2, 2026
**Platform:** Multi-Tenant SaaS Marketing Intelligence Platform

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Architecture Overview](#architecture-overview)
3. [Core Platform Features](#core-platform-features)
4. [Data Layer](#data-layer)
5. [Trust Layer (USP)](#trust-layer-usp)
6. [Intelligence Layer](#intelligence-layer)
7. [Autopilot System](#autopilot-system)
8. [Campaign Builder](#campaign-builder)
9. [Meta CAPI Integration](#meta-capi-integration)
10. [EMQ Fix System](#emq-fix-system)
11. [Landing Page CMS](#landing-page-cms)
12. [Admin & Superadmin Features](#admin--superadmin-features)
13. [Security & Access Control](#security--access-control)
14. [API Reference](#api-reference)
15. [Deployment Guide](#deployment-guide)

---

## Executive Summary

Stratum AI is an enterprise-grade marketing intelligence platform designed for agencies and brands managing multi-platform advertising campaigns. The platform provides:

- **Unified Campaign Management** across Meta, Google, TikTok, and Snapchat
- **AI-Powered Recommendations** with confidence scoring and guardrails
- **Signal Health Monitoring** ensuring data quality for automation
- **Autopilot Actions** with approval workflows and budget caps
- **Attribution Variance Tracking** comparing platform vs GA4 data
- **Multi-Tenant Architecture** with plan-based feature gating

---

## Architecture Overview

### Technology Stack

| Component | Technology |
|-----------|------------|
| Backend API | FastAPI (Python 3.11+) |
| Database | PostgreSQL 15+ with TimescaleDB |
| Cache | Redis 7+ |
| Task Queue | Celery with Redis broker |
| Frontend | React 18 + TypeScript + Vite |
| State Management | Zustand + React Query |
| Authentication | JWT with refresh tokens |
| Container | Docker + Docker Compose |

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        STRATUM AI PLATFORM                       │
├─────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │   React     │  │   FastAPI   │  │   Celery    │              │
│  │   Frontend  │──│   Backend   │──│   Workers   │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
│         │                │                │                      │
│         └────────────────┼────────────────┘                      │
│                          │                                       │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  PostgreSQL │  │    Redis    │  │  Platform   │              │
│  │  Database   │  │    Cache    │  │    APIs     │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

---

## Core Platform Features

### 1. Multi-Tenant System

- **Tenant Isolation**: Complete data separation between tenants
- **Plan-Based Tiers**: Starter, Growth, Professional, Enterprise
- **Feature Flags**: Per-tenant feature gating
- **White-Label Ready**: Customizable branding per tenant

### 2. User Management

- **Role-Based Access Control (RBAC)**:
  - `superadmin`: Platform-wide access
  - `admin`: Tenant management
  - `analyst`: Read + limited write
  - `viewer`: Read-only access

- **Permissions System**:
  - `campaigns:read`, `campaigns:write`
  - `analytics:read`, `analytics:export`
  - `settings:manage`, `users:manage`
  - `autopilot:approve`, `autopilot:execute`

### 3. Dashboard & Analytics

- **Command Center**: Real-time campaign performance
- **KPI Widgets**: Spend, Revenue, ROAS, CPA, Conversions
- **Trend Analysis**: Day-over-day, week-over-week comparisons
- **Platform Breakdown**: Per-platform metrics aggregation

---

## Data Layer

### Database Schema

#### Core Tables

| Table | Description |
|-------|-------------|
| `tenant` | Tenant organizations |
| `user` | User accounts with roles |
| `tenant_platform_connection` | Platform OAuth connections |
| `fact_daily_metrics` | Daily campaign performance |
| `dim_campaign` | Campaign dimension table |
| `dim_adset` | Ad set dimension table |
| `dim_creative` | Creative dimension table |

#### Trust Layer Tables

| Table | Description |
|-------|-------------|
| `fact_signal_health_daily` | Daily signal health metrics |
| `fact_attribution_variance_daily` | Platform vs GA4 variance |
| `fact_actions_queue` | Autopilot action queue |

### Data Ingestion

- **Platform Connectors**: OAuth-based connections
- **Hourly Sync**: Metrics pulled every hour
- **Daily Rollups**: Aggregated fact tables
- **Historical Backfill**: Up to 90 days on connection

---

## Trust Layer (USP)

The Trust Layer ensures data quality before enabling automation.

### Signal Health Monitoring

**Metrics Tracked:**
- EMQ Score (Event Match Quality)
- Event Loss Percentage
- Data Freshness (minutes since last sync)
- API Error Rate

**Health Statuses:**
| Status | Description | Automation |
|--------|-------------|------------|
| `ok` | All metrics healthy | Enabled |
| `risk` | Minor issues detected | Enabled with warnings |
| `degraded` | Significant problems | Blocked |
| `critical` | System failure | Blocked |

**Thresholds:**
```
EMQ Score:
  - ok: >= 8.0
  - risk: >= 6.0
  - degraded: >= 4.0
  - critical: < 4.0

Event Loss:
  - ok: < 5%
  - risk: < 10%
  - degraded: < 25%
  - critical: >= 25%

Freshness:
  - ok: < 60 minutes
  - risk: < 120 minutes
  - degraded: < 360 minutes
  - critical: >= 360 minutes
```

### Attribution Variance

Compares platform-reported conversions with GA4 data:

| Variance | Status | Color |
|----------|--------|-------|
| < 5% | Healthy | Green |
| 5-15% | Minor | Yellow |
| 15-30% | Moderate | Orange |
| > 30% | High | Red |

**Confidence Scoring:**
- Based on data volume
- Conversion count validation
- AOV (Average Order Value) consistency

---

## Intelligence Layer

### AI Recommendations Engine

**Recommendation Types:**
1. **Budget Shift**: Reallocate spend to high-performing entities
2. **Creative Refresh**: Flag fatigued creatives
3. **Fix Campaign**: Address underperforming campaigns
4. **Scaling Opportunity**: Identify scale candidates
5. **Anomaly Investigation**: Alert on unusual patterns

**Priority Levels:**
- `critical`: Immediate action required
- `high`: Action within 24 hours
- `medium`: Action within 3 days
- `low`: Optimization opportunity
- `info`: Informational insight

**Confidence Scoring:**
- 0.0 - 0.3: Low confidence
- 0.3 - 0.6: Medium confidence
- 0.6 - 0.8: High confidence
- 0.8 - 1.0: Very high confidence

### Anomaly Detection

**Metrics Monitored:**
- Spend spikes/drops
- ROAS changes
- CPA anomalies
- Conversion rate shifts
- CTR fluctuations

**Detection Method:**
- Z-score analysis against 14-day baseline
- Configurable sensitivity thresholds
- Severity classification

### Scaling Score

Entities classified into:
- **Scale Candidates**: High ROAS, consistent performance
- **Fix Candidates**: Below target, fixable issues
- **Watch Candidates**: New or volatile entities

---

## Autopilot System

### Autopilot Levels

| Level | Name | Description |
|-------|------|-------------|
| 0 | Suggest Only | Recommendations shown, manual action |
| 1 | Guarded Auto | Safe actions auto-execute |
| 2 | Approval Required | All actions need approval |

### Action Types

**Safe Actions (Level 1 auto-execute):**
- `budget_increase` (within caps)
- `budget_decrease` (within caps)
- `pause_creative` (fatigue detected)

**Approval Required:**
- `pause_campaign`
- `pause_adset`
- `enable_campaign`
- `enable_adset`
- `bid_adjustment`

### Guardrails & Caps

```
Budget Caps:
  - max_budget_pct_change: 30%
  - max_daily_budget_change: $500
  - min_budget_floor: $10

Safety Rules:
  - No action if signal_health = degraded/critical
  - Daily spend limit per tenant
  - Cooldown period between same-entity actions
```

### Action Queue Workflow

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│  Queued  │───>│ Approved │───>│ Applied  │    │ Dismissed│
└──────────┘    └──────────┘    └──────────┘    └──────────┘
     │                                               ^
     └───────────────────────────────────────────────┘
```

---

## Campaign Builder

### Multi-Platform Campaign Creation

**Supported Platforms:**
- Meta (Facebook/Instagram)
- Google Ads
- TikTok Ads
- Snapchat Ads

### Campaign Structure

```
Campaign
├── Ad Sets (targeting, budget, schedule)
│   ├── Creatives (images, videos, copy)
│   └── Audience targeting
└── Settings (objective, optimization)
```

### Draft System

- Save campaigns as drafts
- Clone existing campaigns
- Bulk editing capabilities
- Approval workflow for publishing

---

## Meta CAPI Integration

### Conversions API (CAPI)

**Features:**
- Server-side event tracking
- Event deduplication
- EMQ score optimization
- Real-time event streaming

### Event Types Supported

| Event | Description |
|-------|-------------|
| `Purchase` | Completed transactions |
| `AddToCart` | Cart additions |
| `InitiateCheckout` | Checkout starts |
| `Lead` | Lead form submissions |
| `ViewContent` | Page/product views |
| `Search` | Search queries |
| `CompleteRegistration` | Account signups |

### QA Dashboard

- Event delivery status
- EMQ score monitoring
- Error tracking and alerts
- Match rate analytics

---

## EMQ Fix System

### One-Click Fixes

**EMQ Improvement Actions:**
1. **Add Customer Information Parameters**
   - Email hash enhancement
   - Phone number normalization
   - External ID mapping

2. **Fix Event Timestamp Issues**
   - Timezone correction
   - Deduplication window adjustment

3. **Improve Match Keys**
   - FBC (Facebook Click ID) capture
   - FBP (Facebook Pixel) enhancement

### ROAS Impact Predictions

Each fix shows predicted ROAS improvement:
```
Fix: Add email hash
Predicted ROAS Improvement: +12-18%
Confidence: High
Implementation Time: < 1 hour
```

---

## Landing Page CMS

### Multi-Language Support

- Primary language configuration
- Translation management
- RTL language support
- Language-specific SEO

### Page Builder

**Components:**
- Hero sections
- Feature grids
- Testimonials
- Pricing tables
- FAQ accordions
- Contact forms
- CTA buttons

### SEO Management

- Meta title/description
- OpenGraph tags
- Schema markup
- Sitemap generation
- Robots.txt configuration

---

## Admin & Superadmin Features

### Tenant Admin Dashboard

- User management
- Platform connections
- Billing overview
- Feature flag status
- Activity logs

### Superadmin Dashboard

**Platform Overview:**
- Total MRR/ARR
- Active tenants count
- System health status
- API request volumes

**Tenant Management:**
- Create/edit tenants
- Adjust feature flags
- View tenant metrics
- Impersonation mode

**Analytics:**
- Platform-wide metrics
- Churn risk analysis
- Revenue forecasting
- Usage patterns

**Audit Logs:**
- User actions tracking
- Permission changes
- System events
- Security alerts

---

## Security & Access Control

### Authentication

- JWT-based authentication
- Refresh token rotation
- Session management
- MFA support (optional)

### Authorization

- Role-based access control
- Permission-based actions
- Tenant isolation
- API key management

### Data Security

- Encryption at rest (AES-256)
- Encryption in transit (TLS 1.3)
- PII handling compliance
- Data retention policies

### Audit Trail

All sensitive actions logged:
- Login/logout events
- Permission changes
- Data exports
- Configuration changes
- Autopilot actions

---

## API Reference

### Base URL
```
Production: https://api.stratum.ai/api/v1
Development: http://localhost:8000/api/v1
```

### Authentication
```
Header: Authorization: Bearer <jwt_token>
```

### Key Endpoints

#### Insights API
```
GET /insights/tenant/{tenant_id}/insights
GET /insights/tenant/{tenant_id}/recommendations
GET /insights/tenant/{tenant_id}/anomalies
GET /insights/tenant/{tenant_id}/kpis
```

#### Trust Layer API
```
GET /trust-layer/tenant/{tenant_id}/signal-health
GET /trust-layer/tenant/{tenant_id}/attribution-variance
GET /trust-layer/tenant/{tenant_id}/status
```

#### Autopilot API
```
GET  /autopilot/tenant/{tenant_id}/status
GET  /autopilot/tenant/{tenant_id}/actions
POST /autopilot/tenant/{tenant_id}/actions/{id}/approve
POST /autopilot/tenant/{tenant_id}/actions/{id}/dismiss
```

#### Campaign API
```
GET    /campaigns/tenant/{tenant_id}/campaigns
POST   /campaigns/tenant/{tenant_id}/campaigns
GET    /campaigns/tenant/{tenant_id}/campaigns/{id}
PUT    /campaigns/tenant/{tenant_id}/campaigns/{id}
DELETE /campaigns/tenant/{tenant_id}/campaigns/{id}
```

#### CAPI API
```
POST /capi/events/stream
POST /capi/events/batch
GET  /capi/platforms/connect
```

### Response Format
```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "meta": {
    "timestamp": "2026-01-02T12:00:00Z",
    "request_id": "uuid"
  }
}
```

---

## Deployment Guide

### Prerequisites

- Docker 24+
- Docker Compose 2.20+
- PostgreSQL 15+ (or use Docker)
- Redis 7+ (or use Docker)

### Environment Variables

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/stratum

# Redis
REDIS_URL=redis://localhost:6379/0

# JWT
JWT_SECRET_KEY=your-secret-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Platform APIs
META_APP_ID=your-meta-app-id
META_APP_SECRET=your-meta-app-secret
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Feature Flags
ENABLE_AUTOPILOT=true
ENABLE_AI_RECOMMENDATIONS=true
```

### Docker Deployment

```bash
# Build and start all services
docker-compose up -d --build

# View logs
docker-compose logs -f

# Scale workers
docker-compose up -d --scale celery-worker=3
```

### Database Migrations

```bash
# Run migrations
alembic upgrade head

# Create new migration
alembic revision --autogenerate -m "description"
```

---

## Support & Resources

- **Documentation**: https://docs.stratum.ai
- **API Reference**: https://api.stratum.ai/docs
- **Support Email**: support@stratum.ai
- **Status Page**: https://status.stratum.ai

---

**Copyright 2026 Stratum AI. All Rights Reserved.**
