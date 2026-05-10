# Stratum AI - Architectural Decision Records (ADR)

This document captures key architectural decisions made during the development of Stratum AI.

---

## ADR-001: Trust-Gated Automation Architecture

**Date**: 2024-Q1
**Status**: Accepted
**Context**: Marketing automation platforms often execute actions blindly based on rules, leading to poor decisions when data quality is compromised.

**Decision**: Implement a Trust Gate system that evaluates signal health before allowing automation to execute.

**Consequences**:
- (+) Prevents automation errors from bad data
- (+) Provides auditability for all decisions
- (+) Builds user confidence in automation
- (-) Adds latency to automation execution
- (-) Requires signal health infrastructure

**Thresholds**:
```python
HEALTHY_THRESHOLD = 70      # Autopilot enabled
DEGRADED_THRESHOLD = 40     # Alert only
# Below 40 = Manual required
```

---

## ADR-002: FastAPI + Async/Await Pattern

**Date**: 2024-Q1
**Status**: Accepted
**Context**: Need high-performance API handling many concurrent connections to ad platform APIs.

**Decision**: Use FastAPI with async/await for all I/O operations.

**Alternatives Considered**:
- Django REST Framework: More mature but synchronous
- Flask: Lightweight but requires extensions for async
- Node.js/Express: Would split tech stack

**Consequences**:
- (+) Excellent performance for I/O-bound workloads
- (+) Native async database drivers (asyncpg)
- (+) OpenAPI documentation auto-generated
- (+) Pydantic integration for validation
- (-) Team needs async Python expertise
- (-) Some libraries lack async support

---

## ADR-003: Multi-Tenant Architecture with Schema Isolation

**Date**: 2024-Q1
**Status**: Accepted
**Context**: SaaS platform serving multiple customers requires data isolation.

**Decision**: Use tenant_id column on all tenant-scoped tables with middleware-based tenant context.

**Alternatives Considered**:
- Separate databases per tenant: Maximum isolation but operational overhead
- Schema-per-tenant: Good isolation but migration complexity
- Row-level security: What we chose - balance of isolation and simplicity

**Consequences**:
- (+) Single database for operational simplicity
- (+) Shared schema reduces migration complexity
- (+) Tenant context via middleware is clean
- (-) Must ensure all queries include tenant_id
- (-) Less isolation than separate databases

**Implementation**:
```python
# Middleware extracts tenant from JWT
@app.middleware("http")
async def tenant_middleware(request: Request, call_next):
    tenant_id = extract_tenant_from_token(request)
    request.state.tenant_id = tenant_id
    return await call_next(request)
```

---

## ADR-004: Celery for Background Task Processing

**Date**: 2024-Q1
**Status**: Accepted
**Context**: Need reliable background job processing for data sync, report generation, and scheduled tasks.

**Decision**: Use Celery with Redis as message broker.

**Alternatives Considered**:
- AWS SQS + Lambda: Vendor lock-in
- Dramatiq: Less ecosystem support
- RQ (Redis Queue): Simpler but fewer features
- Built-in BackgroundTasks: Not suitable for long-running tasks

**Consequences**:
- (+) Mature, battle-tested solution
- (+) Built-in scheduling with Celery Beat
- (+) Monitoring via Flower
- (+) Retries and error handling
- (-) Additional infrastructure (Redis)
- (-) Worker deployment complexity

**Task Categories**:
| Queue | Priority | Use Case |
|-------|----------|----------|
| default | Normal | General tasks |
| high | High | Real-time sync |
| low | Low | Report generation |
| scheduled | - | Celery Beat tasks |

---

## ADR-005: React + TypeScript + TanStack Query

**Date**: 2024-Q1
**Status**: Accepted
**Context**: Need modern frontend with type safety and efficient data fetching.

**Decision**: Use React 18, TypeScript, and TanStack Query (React Query) for data management.

**Alternatives Considered**:
- Vue.js: Less TypeScript integration at the time
- Angular: Heavier framework, steeper learning curve
- SWR: Lighter but fewer features than TanStack Query

**Consequences**:
- (+) TypeScript catches errors at compile time
- (+) TanStack Query handles caching, deduplication, background updates
- (+) Large ecosystem and community
- (+) Vite provides fast development experience
- (-) React ecosystem fragmentation (state management choices)

**State Management Strategy**:
| Type | Technology |
|------|------------|
| Server State | TanStack Query |
| Global UI State | Zustand |
| Auth/Theme | React Context |
| Local State | useState |

---

## ADR-006: Tailwind CSS for Styling

**Date**: 2024-Q1
**Status**: Accepted
**Context**: Need consistent, maintainable styling system.

**Decision**: Use Tailwind CSS with custom design tokens.

**Alternatives Considered**:
- CSS Modules: Good isolation but verbose
- Styled Components: Runtime overhead
- Chakra UI: Opinionated component library

**Consequences**:
- (+) Utility-first reduces CSS file size
- (+) Consistent design system via config
- (+) Works well with component libraries
- (+) Dark mode support built-in
- (-) HTML can look cluttered
- (-) Learning curve for utility classes

**Design Tokens** (from tailwind.config.js):
- Colors: Primary, success, warning, error palette
- Typography: System font stack with fallbacks
- Spacing: 4px base unit (0.25rem)
- Breakpoints: sm, md, lg, xl, 2xl

---

## ADR-007: JWT + MFA Authentication

**Date**: 2024-Q1
**Status**: Accepted
**Context**: Secure authentication for SaaS platform with optional MFA.

**Decision**: JWT tokens with access/refresh pattern, optional TOTP-based MFA.

**Token Strategy**:
- Access token: 30 minutes expiry
- Refresh token: 7 days expiry
- Stored in httpOnly cookies (web) or secure storage (mobile)

**MFA Implementation**:
- TOTP (Time-based One-Time Password)
- QR code for authenticator app setup
- Backup codes for recovery

**Consequences**:
- (+) Stateless authentication scales well
- (+) MFA significantly improves security
- (+) Refresh tokens reduce login friction
- (-) Token revocation requires blacklist
- (-) MFA adds user friction

---

## ADR-008: PostgreSQL with asyncpg

**Date**: 2024-Q1
**Status**: Accepted
**Context**: Need robust relational database with JSON support and async driver.

**Decision**: PostgreSQL 16 with asyncpg driver for async operations.

**Alternatives Considered**:
- MySQL: Less JSON support, different ACID guarantees
- MongoDB: Would lose relational integrity
- CockroachDB: Distributed complexity not needed

**Consequences**:
- (+) Excellent JSON support for flexible schemas
- (+) asyncpg provides true async I/O
- (+) JSONB for CDP event storage
- (+) Full-text search capabilities
- (-) Operational complexity vs managed services

**Connection Pooling**:
```python
db_pool_size: int = 10
db_max_overflow: int = 20
db_pool_recycle: int = 3600  # seconds
```

---

## ADR-009: Customer Data Platform (CDP) as Core Feature

**Date**: 2024-Q2
**Status**: Accepted
**Context**: Marketing intelligence requires unified customer view beyond ad platform data.

**Decision**: Build native CDP with profile unification, segmentation, and audience sync.

**Key Features**:
- Identity resolution across devices/channels
- Event tracking and computed traits
- Dynamic segmentation
- Multi-platform audience sync (Meta, Google, TikTok, Snapchat)

**Consequences**:
- (+) Differentiating feature vs competitors
- (+) Enables advanced personalization
- (+) One-click audience sync to ad platforms
- (-) Significant engineering investment
- (-) Data storage costs

**Data Model**:
```
Profile → Events
       → Traits (computed)
       → Identities
       → Segments
```

---

## ADR-010: Server-Side Event Tracking (CAPI)

**Date**: 2024-Q2
**Status**: Accepted
**Context**: Browser-side tracking increasingly blocked; platforms prefer server-side events.

**Decision**: Implement server-side event forwarding to ad platform Conversions APIs.

**Platforms Supported**:
- Meta Conversions API
- Google Ads Enhanced Conversions
- TikTok Events API
- Snapchat Conversions API

**Consequences**:
- (+) Bypasses ad blockers and ITP
- (+) Better attribution accuracy
- (+) EMQ scoring for quality monitoring
- (-) Implementation complexity per platform
- (-) Server infrastructure for event processing

---

## ADR-011: Prometheus + Grafana for Observability

**Date**: 2024-Q1
**Status**: Accepted
**Context**: Need metrics collection and visualization for production monitoring.

**Decision**: Use Prometheus for metrics collection, Grafana for dashboards.

**Metrics Collected**:
- Request latency (p50, p95, p99)
- Error rates by endpoint
- Celery queue depth
- Database connection pool
- Cache hit rates

**Consequences**:
- (+) Industry standard, well-supported
- (+) Rich alerting capabilities
- (+) Integration with AWS/Kubernetes
- (-) Additional infrastructure to maintain
- (-) Cardinality management required

---

## ADR-012: Stripe for Payment Processing

**Date**: 2024-Q3
**Status**: Accepted
**Context**: Need subscription billing for SaaS tiers.

**Decision**: Use Stripe for all payment processing with webhook integration.

**Subscription Tiers**:
- Starter: $X/month
- Professional: $Y/month
- Enterprise: Custom pricing

**Consequences**:
- (+) Industry-leading payment platform
- (+) Built-in subscription management
- (+) Webhook events for billing lifecycle
- (+) PCI compliance handled by Stripe
- (-) Transaction fees
- (-) Webhook reliability requires idempotency

---

## ADR-013: Feature Flag System

**Date**: 2024-Q2
**Status**: Accepted
**Context**: Need ability to enable/disable features per tenant or globally.

**Decision**: Configuration-based feature flags with tier-based defaults.

**Current Flags**:
```python
feature_competitor_intel: bool = True
feature_what_if_simulator: bool = True
feature_automation_rules: bool = True
feature_gdpr_compliance: bool = True
```

**Consequences**:
- (+) Gradual feature rollout
- (+) Tier-based feature gating
- (+) Quick disable for broken features
- (-) Code complexity with flag checks
- (-) Technical debt if flags not cleaned up

---

## ADR-014: WebSocket + SSE for Real-Time Updates

**Date**: 2024-Q2
**Status**: Accepted
**Context**: Dashboard needs real-time updates for metrics and alerts.

**Decision**: Support both WebSocket and Server-Sent Events.

**Use Cases**:
- WebSocket: Bidirectional (chat, interactive features)
- SSE: Server-to-client only (dashboard updates)

**Message Types**:
- `emq_update`: EMQ score changes
- `incident_opened/closed`: Incident notifications
- `autopilot_mode_change`: Autopilot status
- `action_status_update`: Action queue changes
- `platform_status`: Platform health

**Consequences**:
- (+) Real-time user experience
- (+) Reduced polling load
- (+) Event-driven architecture
- (-) Connection management complexity
- (-) Scale considerations for WebSocket state

---

## Template for New ADRs

```markdown
## ADR-XXX: [Title]

**Date**: YYYY-MM
**Status**: Proposed | Accepted | Deprecated | Superseded
**Context**: [Problem description]

**Decision**: [What was decided]

**Alternatives Considered**:
- Option A: [Why not chosen]
- Option B: [Why not chosen]

**Consequences**:
- (+) [Positive outcome]
- (-) [Negative outcome / tradeoff]
```
