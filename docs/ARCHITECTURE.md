# Stratum AI - System Architecture

## Overview

Stratum AI is an enterprise marketing intelligence platform that unifies advertising analytics across Meta, Google, TikTok, Snapchat, and LinkedIn. The system provides AI-powered ROAS optimization, automation rules, competitor intelligence, and GDPR-compliant data handling.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              STRATUM AI PLATFORM                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐    ┌─────────────┐  │
│  │   React     │    │   FastAPI   │    │  PostgreSQL │    │    Redis    │  │
│  │  Frontend   │◄──►│   Backend   │◄──►│  Database   │    │   Cache     │  │
│  │  (Vite)     │    │   (Async)   │◄──►│             │    │   + Queue   │  │
│  └─────────────┘    └──────┬──────┘    └─────────────┘    └──────┬──────┘  │
│                            │                                      │         │
│                            ▼                                      ▼         │
│                     ┌─────────────┐                        ┌─────────────┐  │
│                     │   Celery    │◄───────────────────────│   Redis     │  │
│                     │   Workers   │                        │   Broker    │  │
│                     └──────┬──────┘                        └─────────────┘  │
│                            │                                                │
│           ┌────────────────┼────────────────┐                              │
│           ▼                ▼                ▼                              │
│    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                      │
│    │  ML Models  │  │  Ad APIs    │  │  WhatsApp   │                      │
│    │  (sklearn)  │  │  (5 Plat.)  │  │  Business   │                      │
│    └─────────────┘  └─────────────┘  └─────────────┘                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
stratum-ai/
├── backend/                      # Python FastAPI backend
│   ├── app/
│   │   ├── main.py              # Application entry point
│   │   ├── models.py            # SQLAlchemy ORM models
│   │   ├── schemas.py           # Pydantic schemas
│   │   ├── api/v1/              # API endpoints
│   │   ├── core/                # Config, security, logging
│   │   ├── db/                  # Database session management
│   │   ├── middleware/          # HTTP middleware
│   │   ├── services/            # Business logic
│   │   ├── ml/                  # Machine learning
│   │   └── workers/             # Celery tasks
│   ├── migrations/              # Alembic migrations
│   └── tests/                   # pytest test suite
│
├── frontend/                    # React TypeScript frontend
│   ├── src/
│   │   ├── components/          # React components
│   │   ├── views/               # Page components
│   │   ├── services/            # API clients
│   │   ├── contexts/            # React contexts
│   │   ├── types/               # TypeScript types
│   │   └── i18n/                # Internationalization
│   └── public/                  # Static assets
│
├── ml_service/                  # ML model storage
│   └── models/                  # Trained model files
│
├── scripts/                     # Utility scripts
│   └── init-db.sql             # Database initialization
│
├── docs/                        # Documentation
├── docker-compose.yml           # Container orchestration
└── .env                         # Environment configuration
```

---

## Core Components

### 1. Backend (FastAPI)

The backend is built with FastAPI, providing async HTTP handling with automatic OpenAPI documentation.

**Key Features:**
- Async database operations with SQLAlchemy 2.0
- JWT-based authentication
- Multi-tenant data isolation
- Rate limiting and audit logging
- Server-Sent Events for real-time updates

**Application Factory Pattern:**
```python
# backend/app/main.py
def create_application() -> FastAPI:
    app = FastAPI(
        title="Stratum AI",
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    # Middleware stack (executed in reverse order)
    app.add_middleware(CORSMiddleware, ...)
    app.add_middleware(GZipMiddleware, ...)
    app.add_middleware(RateLimitMiddleware, ...)
    app.add_middleware(TenantMiddleware)
    app.add_middleware(AuditMiddleware)

    # Include API routes
    app.include_router(api_router, prefix="/api/v1")

    return app
```

### 2. Frontend (React + Vite)

Single-page application built with React 18, TypeScript, and Tailwind CSS.

**Key Features:**
- TypeScript for type safety
- Tailwind CSS for styling
- React Query for data fetching
- i18next for internationalization (EN, AR, UK)
- Recharts for data visualization

**Component Hierarchy:**
```
App.tsx
├── AuthProvider
│   └── ProtectedRoute
│       └── DashboardLayout
│           ├── Sidebar
│           ├── Header
│           └── [Page Views]
│               ├── Overview
│               ├── Campaigns
│               ├── Rules
│               ├── Assets
│               └── ...
```

### 3. Database (PostgreSQL)

Multi-tenant relational database with row-level security.

**Key Design Decisions:**
- All tables include `tenant_id` for isolation
- Soft delete via `is_deleted` flag
- JSONB for flexible configuration storage
- Monetary values stored as cents (integers)
- Comprehensive indexing strategy

### 4. Cache & Queue (Redis)

Redis serves multiple purposes:
- **Caching**: API response caching, session data
- **Message Broker**: Celery task queue
- **Pub/Sub**: Real-time event distribution
- **Rate Limiting**: Token bucket storage

### 5. Background Workers (Celery)

Async task processing for long-running operations.

**Worker Queues:**
| Queue | Purpose | Tasks |
|-------|---------|-------|
| sync | Data synchronization | Campaign sync, competitor refresh |
| rules | Automation | Rule evaluation, action execution |
| ml | Machine learning | Predictions, model training |
| intel | Intelligence | Competitor analysis |
| default | General | Email, notifications |

---

## Data Flow

### Request Lifecycle

```
Client Request
      │
      ▼
┌─────────────────┐
│  Nginx/LB       │  SSL termination, static files
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Rate Limiter   │  Token bucket algorithm
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Auth Middleware│  JWT validation, user extraction
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Tenant Middleware│  Tenant context injection
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Audit Middleware│  Request logging (async)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  API Endpoint   │  Business logic execution
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Database       │  PostgreSQL with tenant filter
└─────────────────┘
```

### Campaign Data Sync Flow

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│  Ad Platform│    │   Celery    │    │  PostgreSQL │
│     APIs    │◄───│   Worker    │───►│   Database  │
└─────────────┘    └──────┬──────┘    └─────────────┘
                         │
                         ▼
                  ┌─────────────┐
                  │    Redis    │  Publish sync_complete
                  │   Pub/Sub   │
                  └──────┬──────┘
                         │
                         ▼
                  ┌─────────────┐
                  │   Frontend  │  SSE receives update
                  │   (React)   │
                  └─────────────┘
```

### ML Prediction Flow

```
Campaign Data ──► Feature Extraction ──► Model Inference ──► Predictions
      │                   │                    │                  │
      │                   │                    │                  │
      ▼                   ▼                    ▼                  ▼
┌──────────┐       ┌──────────┐        ┌──────────┐       ┌──────────┐
│PostgreSQL│       │ Pandas   │        │ sklearn  │       │  Cache   │
│ Database │       │ DataFrame│        │ XGBoost  │       │ (Redis)  │
└──────────┘       └──────────┘        └──────────┘       └──────────┘
```

---

## Security Architecture

### Authentication Flow

```
┌─────────────┐         ┌─────────────┐         ┌─────────────┐
│   Client    │         │   Backend   │         │  Database   │
└──────┬──────┘         └──────┬──────┘         └──────┬──────┘
       │                       │                       │
       │  POST /auth/login     │                       │
       │  {email, password}    │                       │
       │──────────────────────►│                       │
       │                       │  Query user by email  │
       │                       │──────────────────────►│
       │                       │◄──────────────────────│
       │                       │  Verify bcrypt hash   │
       │                       │                       │
       │  {access_token,       │                       │
       │   refresh_token}      │                       │
       │◄──────────────────────│                       │
       │                       │                       │
       │  GET /api/v1/campaigns│                       │
       │  Authorization: Bearer│                       │
       │──────────────────────►│                       │
       │                       │  Validate JWT         │
       │                       │  Extract tenant_id    │
       │                       │  Query with filter    │
       │                       │──────────────────────►│
       │                       │◄──────────────────────│
       │  {campaigns}          │                       │
       │◄──────────────────────│                       │
```

### Security Layers

| Layer | Implementation | Purpose |
|-------|---------------|---------|
| Transport | HTTPS/TLS | Encryption in transit |
| Authentication | JWT (HS256) | Identity verification |
| Authorization | Role-based (RBAC) | Access control |
| Data Isolation | Tenant middleware | Multi-tenancy |
| Input Validation | Pydantic schemas | Injection prevention |
| Rate Limiting | Token bucket | DoS protection |
| Audit Logging | Middleware + Redis | Compliance |
| PII Encryption | Fernet (AES-128) | Data at rest |

### Role Permissions

```python
class UserRole(str, Enum):
    ADMIN = "admin"       # Full system access
    MANAGER = "manager"   # Team + campaign management
    ANALYST = "analyst"   # View + create reports
    VIEWER = "viewer"     # Read-only access
```

---

## Multi-Tenancy

### Tenant Isolation Strategy

All database queries are automatically filtered by `tenant_id`:

```python
# Middleware injects tenant context
@app.middleware("http")
async def tenant_middleware(request: Request, call_next):
    token_data = decode_jwt(request.headers.get("Authorization"))
    request.state.tenant_id = token_data.get("tenant_id")
    return await call_next(request)

# Service layer uses tenant filter
async def get_campaigns(db: AsyncSession, tenant_id: int):
    query = select(Campaign).where(
        Campaign.tenant_id == tenant_id,
        Campaign.is_deleted == False
    )
    return await db.execute(query)
```

### Tenant Hierarchy

```
Tenant (Organization)
├── Users (team members)
├── Campaigns (across platforms)
│   ├── CampaignMetrics (daily data)
│   └── CreativeAssets (media files)
├── Rules (automation)
├── Competitors (benchmarking)
├── WhatsAppContacts (messaging)
└── AuditLogs (compliance)
```

---

## Scalability Considerations

### Horizontal Scaling

```
                    ┌─────────────┐
                    │   Load      │
                    │  Balancer   │
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
   ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
   │  API Node 1 │  │  API Node 2 │  │  API Node 3 │
   └─────────────┘  └─────────────┘  └─────────────┘
          │                │                │
          └────────────────┼────────────────┘
                           ▼
                    ┌─────────────┐
                    │  PostgreSQL │  Primary + Replicas
                    │   Cluster   │
                    └─────────────┘
```

### Caching Strategy

| Data Type | TTL | Cache Key Pattern |
|-----------|-----|-------------------|
| Campaign list | 5 min | `tenant:{id}:campaigns` |
| KPI metrics | 15 min | `tenant:{id}:kpis:{date}` |
| ML predictions | 30 min | `prediction:{campaign_id}:{model}` |
| User session | 24 hr | `session:{user_id}` |

---

## External Integrations

### Ad Platform Connectors

```
┌─────────────────────────────────────────────────────────────┐
│                    Platform Connector Layer                  │
├─────────────┬─────────────┬─────────────┬─────────────┬─────┤
│    Meta     │   Google    │   TikTok    │  Snapchat   │ LI  │
│  (Graph API)│ (Ads API)   │ (Marketing) │  (Marketing)│     │
└──────┬──────┴──────┬──────┴──────┬──────┴──────┬──────┴──┬──┘
       │             │             │             │         │
       └─────────────┴─────────────┴─────────────┴─────────┘
                                   │
                            ┌──────▼──────┐
                            │   Unified   │
                            │   Campaign  │
                            │    Model    │
                            └─────────────┘
```

### Conversion API (CAPI) Flow

```
Website Event ──► Event Mapper ──► Data Quality ──► Platform CAPI
     │                │                 │                │
     │                │                 │                │
     ▼                ▼                 ▼                ▼
┌──────────┐   ┌──────────┐     ┌──────────┐     ┌──────────┐
│ Raw JSON │   │ Standard │     │ EMQ Score│     │Meta/Google│
│  Event   │   │  Event   │     │ + Hashing│     │  TikTok   │
└──────────┘   └──────────┘     └──────────┘     └──────────┘
```

---

## Monitoring & Observability

### Health Check Endpoints

| Endpoint | Purpose | Response |
|----------|---------|----------|
| `/health` | Full health check | DB + Redis status |
| `/health/ready` | Readiness probe | 200 if ready |
| `/health/live` | Liveness probe | 200 if alive |
| `/metrics` | Application metrics | CPU, memory, threads |

### Logging Strategy

```python
# Structured logging with structlog
logger.info(
    "campaign_synced",
    tenant_id=tenant_id,
    platform="meta",
    campaign_count=42,
    duration_ms=1234.56
)
```

Output:
```json
{
  "event": "campaign_synced",
  "tenant_id": 1,
  "platform": "meta",
  "campaign_count": 42,
  "duration_ms": 1234.56,
  "timestamp": "2024-12-20T10:30:00Z",
  "level": "info"
}
```

---

## Deployment Architecture

### Production Setup

```
┌──────────────────────────────────────────────────────────────┐
│                         PRODUCTION                            │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐                                            │
│  │   Vercel    │  Frontend (React)                          │
│  │   CDN       │  - Global edge caching                     │
│  └─────────────┘  - Automatic HTTPS                         │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                 Docker Swarm / K8s                   │    │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐│    │
│  │  │   API   │  │   API   │  │ Worker  │  │ Worker  ││    │
│  │  │  Node 1 │  │  Node 2 │  │  Node 1 │  │  Node 2 ││    │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘│    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ PostgreSQL  │  │    Redis    │  │   Sentry    │         │
│  │  (Primary)  │  │   Cluster   │  │   (Errors)  │         │
│  │  + Replica  │  │             │  │             │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Technology Stack Summary

| Layer | Technology | Version |
|-------|------------|---------|
| **Frontend** | React + TypeScript | 18.x |
| **Build Tool** | Vite | 5.x |
| **Styling** | Tailwind CSS | 3.x |
| **Backend** | FastAPI | 0.109.x |
| **ORM** | SQLAlchemy | 2.0.x |
| **Database** | PostgreSQL | 16.x |
| **Cache** | Redis | 7.x |
| **Task Queue** | Celery | 5.3.x |
| **ML** | scikit-learn + XGBoost | 1.4.x |
| **Container** | Docker | 24.x |

---

## Next Steps

- [API Documentation](./API.md)
- [Database Schema](./DATABASE.md)
- [Frontend Components](./FRONTEND.md)
- [ML Models](./ML.md)
- [Deployment Guide](./DEPLOYMENT.md)
