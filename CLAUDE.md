# Stratum AI Platform

## Overview
Revenue Operating System with Trust-Gated Autopilot architecture.
Automation executes ONLY when signal health passes safety thresholds.

## Core Concept
```
Signal Health Check → Trust Gate → Automation Decision
       ↓                  ↓              ↓
   [HEALTHY]         [PASS]         [EXECUTE]
   [DEGRADED]        [HOLD]         [ALERT ONLY]
   [UNHEALTHY]       [BLOCK]        [MANUAL REQUIRED]
```

## Tech Stack
- **Backend**: Python 3.11+, FastAPI, Pydantic
- **Database**: PostgreSQL 15, Redis (caching/queues)
- **Queue**: Celery + Redis
- **Frontend**: React 18, TypeScript, Tailwind CSS
- **Infra**: Docker, AWS (ECS, RDS, ElastiCache)
- **Monitoring**: Prometheus, Grafana, Sentry

## Project Structure
```
/stratum-ai/
├── api/              # FastAPI routes
├── core/             # Business logic, trust engine
│   ├── signals/      # Signal collectors & processors
│   ├── gates/        # Trust gate evaluators
│   └── automations/  # Automation executors
├── models/           # SQLAlchemy models
├── schemas/          # Pydantic schemas
├── services/         # External integrations
├── workers/          # Celery tasks
└── tests/
```

## Key Commands
```bash
make dev              # Start local env
make test             # Run pytest
make lint             # Ruff + mypy
make migrate          # Alembic migrations
docker compose up -d  # Full stack
```

## Code Standards
- Type hints REQUIRED on all functions
- Pydantic models for all API I/O
- Async/await for all I/O operations
- 90%+ test coverage for core/
- Docstrings on public functions

## Domain Terminology
| Term | Definition |
|------|------------|
| Signal | Input data point (metric, event, webhook) |
| Signal Health | Composite score (0-100) of signal reliability |
| Trust Gate | Decision checkpoint before automation |
| Autopilot | Automated action when trust passes |

## Trust Engine Rules
```python
HEALTHY_THRESHOLD = 70      # Green - autopilot enabled
DEGRADED_THRESHOLD = 40     # Yellow - alert + hold
# Never auto-execute when signal_health < 70
```

## Do NOT
- Skip trust gate checks for "quick fixes"
- Hardcode thresholds (use config)
- Execute automations without audit logging
- Merge without passing CI

## Git Workflow
- Branch: `feature/STRAT-123-description`
- Commit: `feat(signals): add anomaly detection [STRAT-123]`

## CDP (Customer Data Platform) Frontend

### Views & Routes
| Route | Component | Description |
|-------|-----------|-------------|
| `/dashboard/cdp` | CDPDashboard | Main overview with stats, lifecycle distribution, event volume charts |
| `/dashboard/cdp/profiles` | CDPProfiles | Profile viewer with search, filters, pagination, detail modal |
| `/dashboard/cdp/segments` | CDPSegments | Segment builder with condition builder, preview, CRUD |
| `/dashboard/cdp/events` | CDPEvents | Event timeline with volume charts, anomaly detection |
| `/dashboard/cdp/identity` | CDPIdentityGraph | SVG-based identity graph visualization |

### Key Files
- `frontend/src/views/cdp/` - All CDP view components
- `frontend/src/api/cdp.ts` - React Query hooks for CDP API (60+ hooks)
- `frontend/src/views/DashboardLayout.tsx` - CDP navigation added here

### CDP API Hooks (from `@/api/cdp`)
- `useCDPHealth`, `useProfileStatistics`, `useEventStatistics`
- `useSegments`, `useCreateSegment`, `useUpdateSegment`, `useDeleteSegment`
- `useSearchProfiles`, `useCDPProfile`, `useExportAudience`
- `useEventTrends`, `useAnomalySummary`, `useEventAnomalies`
- `useIdentityGraph`, `useMergeHistory`

### Navigation
CDP section is in sidebar with collapsible submenu (6 items including Audience Sync).
State managed via `cdpExpanded` in DashboardLayout.

### CDP Audience Sync (New Feature)
Push CDP segments directly to ad platforms for targeting.

**Routes:**
- `/dashboard/cdp/audience-sync` - Main audience sync management

**Key Files:**
- `frontend/src/components/cdp/AudienceSync.tsx` - Full UI component
- `frontend/src/views/cdp/CDPAudienceSync.tsx` - View wrapper
- `backend/app/services/cdp/audience_sync/` - Platform connectors
- `backend/app/api/v1/endpoints/audience_sync.py` - REST API

**Supported Platforms:**
- Meta (Custom Audiences API)
- Google (Customer Match API)
- TikTok (DMP Custom Audience API)
- Snapchat (Audience Match SAM API)

**Features:**
- Create platform audiences linked to CDP segments
- Auto-sync with configurable intervals (1h - 1 week)
- Manual sync trigger
- Sync history with metrics (profiles sent, added, match rate)
- Manual export to CSV/JSON with traits and events

---

## Update Landing Content with CDP Unique Selling Points

### CDP Core Value Propositions

**1. Unified Customer Profiles**
- Single customer view across all touchpoints
- Identity resolution merging anonymous → known → customer
- Real-time profile enrichment from events

**2. Multi-Platform Audience Sync**
- Push segments to Meta, Google, TikTok, Snapchat with one click
- Hashed identifier matching (email, phone, MAID)
- Auto-sync keeps audiences fresh (configurable intervals)
- Match rate tracking and optimization

**3. Advanced Segmentation**
- Dynamic segments with behavioral conditions
- RFM analysis (Recency, Frequency, Monetary)
- Lifecycle stage targeting (anonymous → churned)
- Computed traits for complex attributes

**4. Event Intelligence**
- Real-time event ingestion and processing
- Anomaly detection with alerting
- EMQ (Event Match Quality) scoring
- Conversion funnel analysis

**5. Identity Graph**
- Visual identity resolution
- Cross-device tracking
- Profile merge history and audit trail
- Canonical identity management

**6. Privacy-First Design**
- Consent management per data type
- GDPR/CCPA compliant exports
- Hashed PII for platform sync
- Audit logging for all operations

### Landing Page Feature Highlights

```
CDP FEATURES FOR LANDING PAGE:

Hero Section:
"Turn Customer Data Into Revenue"
- Unify profiles across every touchpoint
- Sync audiences to all ad platforms instantly
- Automate targeting with smart segmentation

Feature Cards:
┌─────────────────────────────────────────────────────────────┐
│ 🎯 One-Click Audience Sync                                  │
│ Push segments to Meta, Google, TikTok & Snapchat instantly. │
│ Auto-sync keeps your audiences fresh 24/7.                  │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 👤 360° Customer Profiles                                   │
│ Unified view from anonymous visitor to loyal customer.      │
│ Real-time enrichment from every interaction.                │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 📊 Smart Segmentation                                       │
│ Build segments with behavioral rules, RFM scores,           │
│ and lifecycle stages. Preview before you publish.           │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 🔗 Identity Resolution                                      │
│ Connect the dots across devices and channels.               │
│ Visual identity graph shows every connection.               │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│ 📤 Flexible Export                                          │
│ Export audiences as CSV or JSON anytime.                    │
│ Include traits, events, and custom attributes.              │
└─────────────────────────────────────────────────────────────┘

Comparison Table:
| Feature              | Stratum CDP | Segment | mParticle |
|----------------------|-------------|---------|-----------|
| Multi-platform sync  | ✅ 4 platforms | ✅ | ✅ |
| Real-time segments   | ✅ | ✅ | ✅ |
| Identity graph viz   | ✅ | ❌ | ❌ |
| RFM analysis         | ✅ Built-in | ❌ | ❌ |
| Trust-gated actions  | ✅ Unique | ❌ | ❌ |
| Manual CSV export    | ✅ | ✅ | ✅ |
| Anomaly detection    | ✅ | ❌ | ✅ |
```

### API Endpoints Summary (for docs)
```
CDP Audience Sync API:
GET    /cdp/audience-sync/platforms           - Connected platforms
GET    /cdp/audience-sync/audiences           - List audiences
POST   /cdp/audience-sync/audiences           - Create audience
POST   /cdp/audience-sync/audiences/{id}/sync - Trigger sync
GET    /cdp/audience-sync/audiences/{id}/history - Sync history
DELETE /cdp/audience-sync/audiences/{id}      - Delete audience
POST   /cdp/audiences/export                  - Export CSV/JSON
```

## Imports
@docs/architecture/trust-engine.md
@docs/integrations/README.md
