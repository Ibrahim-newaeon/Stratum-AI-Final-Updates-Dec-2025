# Stratum AI Documentation

Welcome to the Stratum AI technical documentation. This documentation covers the code architecture, logic, and operational aspects of the platform.

---

## Documentation Index

| Document | Description |
|----------|-------------|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | System overview, component architecture, data flow |
| [API.md](./API.md) | Complete REST API reference with examples |
| [DATABASE.md](./DATABASE.md) | Database schema, models, and query patterns |
| [FRONTEND.md](./FRONTEND.md) | React components, state management, styling |
| [ML.md](./ML.md) | Machine learning models, training, inference |
| [DEPLOYMENT.md](./DEPLOYMENT.md) | Deployment procedures, operations, troubleshooting |
| [EMQ_FIXES.md](./EMQ_FIXES.md) | EMQ One-Click Fix System - detection, remediation, ROAS impact |
| [META_INTEGRATION_TESTING.md](./META_INTEGRATION_TESTING.md) | Meta CAPI integration testing guide |

---

## Quick Reference

### Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | React 18 + TypeScript + Vite + Tailwind |
| Backend | FastAPI + SQLAlchemy + Celery |
| Database | PostgreSQL 16 |
| Cache | Redis 7 |
| ML | scikit-learn + XGBoost |

### Key Concepts

**Multi-Tenancy**
- All data isolated by `tenant_id`
- Row-level security via middleware
- Tenant context injected from JWT

**Authentication**
- JWT tokens (access + refresh)
- bcrypt password hashing
- Role-based access control (RBAC)

**Real-Time Updates**
- Server-Sent Events (SSE)
- Redis pub/sub for event distribution
- Tenant-scoped channels

---

## Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   React     │────►│   FastAPI   │────►│  PostgreSQL │
│  Frontend   │     │   Backend   │     │  Database   │
└─────────────┘     └──────┬──────┘     └─────────────┘
                          │
                          ▼
                   ┌─────────────┐
                   │   Celery    │────► ML Models
                   │   Workers   │────► Ad Platform APIs
                   └─────────────┘────► Email/WhatsApp
```

---

## Getting Started

### For Developers

1. Read [ARCHITECTURE.md](./ARCHITECTURE.md) for system overview
2. Review [API.md](./API.md) for endpoint reference
3. Check [DATABASE.md](./DATABASE.md) for data models
4. See [FRONTEND.md](./FRONTEND.md) for UI components

### For DevOps

1. Read [DEPLOYMENT.md](./DEPLOYMENT.md) for deployment procedures
2. Review Docker Compose configuration
3. Set up monitoring and alerting

### For Data Scientists

1. Read [ML.md](./ML.md) for model documentation
2. Review training pipeline
3. Understand feature engineering

---

## Code Structure

```
stratum-ai/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/   # REST endpoints
│   │   ├── core/               # Config, security
│   │   ├── db/                 # Database session
│   │   ├── middleware/         # HTTP middleware
│   │   ├── ml/                 # ML models
│   │   ├── services/           # Business logic
│   │   └── workers/            # Celery tasks
│   ├── migrations/             # Alembic
│   └── tests/                  # pytest
│
├── frontend/
│   └── src/
│       ├── components/         # React components
│       ├── views/              # Page components
│       ├── services/           # API clients
│       └── contexts/           # React contexts
│
├── docs/                       # This documentation
├── scripts/                    # Utility scripts
└── docker-compose.yml          # Container orchestration
```

---

## API Quick Reference

### Authentication
```
POST /api/v1/auth/login          # Login
POST /api/v1/auth/register       # Register
POST /api/v1/auth/refresh        # Refresh token
POST /api/v1/auth/forgot-password # Request reset
POST /api/v1/auth/reset-password  # Reset password
```

### Campaigns
```
GET    /api/v1/campaigns         # List campaigns
POST   /api/v1/campaigns         # Create campaign
GET    /api/v1/campaigns/{id}    # Get campaign
PUT    /api/v1/campaigns/{id}    # Update campaign
DELETE /api/v1/campaigns/{id}    # Delete campaign
```

### Analytics
```
GET  /api/v1/analytics/kpis      # Get KPIs
GET  /api/v1/analytics/platforms # Platform breakdown
POST /api/v1/analytics/export    # Export data
```

### ML/Predictions
```
GET  /api/v1/predictions/roas    # ROAS predictions
POST /api/v1/predictions/budget-optimize # Budget optimization
POST /api/v1/simulate            # What-if simulation
```

### EMQ One-Click Fixes
```
GET  /api/v1/qa/fixes/suggestions    # Get fix suggestions with ROAS impact
POST /api/v1/qa/fixes/apply          # Apply a fix
GET  /api/v1/qa/fixes/run/{id}       # Get fix run status
GET  /api/v1/qa/fixes/history        # Get fix history
```

---

## Database Models

| Model | Purpose |
|-------|---------|
| Tenant | Organization (multi-tenancy root) |
| User | User accounts with roles |
| Campaign | Unified campaign across platforms |
| CampaignMetric | Daily performance metrics |
| CreativeAsset | Digital assets (images, videos) |
| Rule | Automation rules |
| CompetitorBenchmark | Competitor intelligence |
| AuditLog | Security audit trail |
| WhatsAppContact | WhatsApp contacts |
| WhatsAppMessage | Message tracking |
| CapiQaLog | CAPI event quality logs |
| FixRun | EMQ fix audit trail |
| TenantTrackingConfig | Per-platform tracking configuration |

---

## Environment Variables

### Required
```
SECRET_KEY          # Application secret
JWT_SECRET_KEY      # JWT signing key
DATABASE_URL        # PostgreSQL connection
REDIS_URL           # Redis connection
PII_ENCRYPTION_KEY  # Fernet encryption key
```

### Optional
```
SMTP_HOST/PASSWORD  # Email configuration
SENTRY_DSN          # Error tracking
ML_PROVIDER         # 'local' or 'vertex'
```

---

## Support

- GitHub Issues: Report bugs and feature requests
- Documentation: This docs folder
- API Docs: `/docs` endpoint (development only)
