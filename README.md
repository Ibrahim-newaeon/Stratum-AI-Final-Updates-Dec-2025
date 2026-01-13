# Stratum AI Platform

**Revenue Operating System with Trust-Gated Autopilot Architecture**

[![Version](https://img.shields.io/badge/version-1.1.0-purple.svg)](https://github.com/Ibrahim-newaeon/Stratum-AI-Final-Updates-Dec-2025/releases/tag/v1.1.0)
[![Tests](https://img.shields.io/badge/tests-231%20passed-brightgreen.svg)](#production-validation)
[![License](https://img.shields.io/badge/license-Proprietary-blue.svg)](#)

## Documentation

**[View Full Documentation](https://ibrahim-newaeon.github.io/Stratum-AI-Final-Updates-Dec-2025/)**

Interactive documentation including:
- First-time user journey flow diagrams
- Complete 60+ screen directory
- All feature specifications
- API reference (150+ endpoints)

---

## Overview

Stratum AI enables marketing teams to automate campaign management while ensuring data quality through intelligent safety mechanisms. Automation executes **only when signal health passes safety thresholds**.

```
Signal Health Check → Trust Gate → Automation Decision
       ↓                  ↓              ↓
   [HEALTHY]         [PASS]         [EXECUTE]
   [DEGRADED]        [HOLD]         [ALERT ONLY]
   [UNHEALTHY]       [BLOCK]        [MANUAL REQUIRED]
```

## Key Features

| Feature | Description |
|---------|-------------|
| **Trust Engine** | Signal health monitoring with 5-component weighted scoring (now includes CDP EMQ) |
| **Autopilot** | Configurable enforcement (Advisory/Soft-Block/Hard-Block) |
| **Campaign Builder** | Multi-step wizard with approval workflow |
| **CDP (NEW)** | First-party data platform with identity resolution & consent management |
| **Multi-Platform** | Meta, Google, TikTok, Snapchat integrations |
| **CRM Integration** | HubSpot bidirectional sync with identity matching |
| **Attribution** | 6 models including Markov Chain & Shapley Value |
| **Pacing** | Budget forecasting with EWMA predictions |
| **A/B Testing** | Statistical analysis with power calculations |

## CDP (Customer Data Platform) v1.1.0

Stratum CDP provides first-party data infrastructure for privacy-compliant customer data management:

```
Event Ingestion → Profile Unification → Trust Engine Integration
       ↓                  ↓                      ↓
   [EMQ Score]     [Identity Graph]      [Signal Health + CDP]
```

### CDP Features

| Feature | Description |
|---------|-------------|
| **Event Ingestion** | Real-time event collection with batch support (up to 1000/request) |
| **Identity Resolution** | PII hashing, profile unification, multi-identifier matching |
| **EMQ Scoring** | Event Match Quality scoring based on identifier quality, completeness, timeliness |
| **Consent Management** | GDPR/PDPL compliant consent tracking per profile |
| **Source Authentication** | API key-based source authentication for secure ingestion |
| **Trust Engine Integration** | CDP EMQ contributes 10% to overall signal health score |

### CDP Endpoints

```bash
# Event Ingestion
POST /api/v1/cdp/events         # Ingest events (single or batch)

# Profile Management
GET /api/v1/cdp/profiles/{id}   # Get profile by UUID
GET /api/v1/cdp/profiles        # Lookup profile by identifier

# Source Management
GET /api/v1/cdp/sources         # List data sources
POST /api/v1/cdp/sources        # Create new source

# Health Check
GET /api/v1/cdp/health          # CDP module health status
```

### Rate Limits

| Operation | Limit |
|-----------|-------|
| Event Ingestion | 100 requests/minute |
| Profile Lookups | 300 requests/minute |
| Source Operations | 30 requests/minute |

### ROI Calculator

Interactive calculator at `/calculator` estimates the business impact of improved identity resolution.

## Tech Stack

### Backend
- Python 3.11+, FastAPI, PostgreSQL 15, Redis, Celery
- SQLAlchemy 2.x, Pydantic 2.x, Alembic

### Frontend
- React 18, TypeScript, Tailwind CSS, Vite
- React Router 6, TanStack Query, Zustand

### Infrastructure
- Docker, AWS-ready (ECS, RDS, ElastiCache)
- Prometheus, Grafana, Sentry

## Quick Start

```bash
# Start the full stack
docker compose up -d

# Run all tests
docker compose exec api pytest tests/ -v

# Access the application
open http://localhost:5173

# API documentation
open http://localhost:8000/docs
```

## Production Validation

| Check | Result |
|-------|--------|
| Unit Tests | 179/179 passed |
| Integration Tests | 52/52 passed |
| Load Tests | 100% checks, 0% errors |
| Security Audit | No hardcoded credentials |
| Frontend Build | Successful |

## Project Structure

```
stratum-ai/
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/    # API routes
│   │   ├── core/                # Business logic
│   │   ├── models/              # SQLAlchemy models
│   │   ├── schemas/             # Pydantic schemas
│   │   └── services/            # External integrations
│   └── tests/
├── frontend/
│   ├── src/
│   │   ├── components/          # React components
│   │   ├── views/               # Page views
│   │   ├── api/                 # API clients
│   │   └── stores/              # State management
│   └── public/
├── docs/                        # Documentation
├── infrastructure/              # Docker, monitoring
└── tests/load/                  # K6 load tests
```

## Links

- [Full Documentation](https://ibrahim-newaeon.github.io/Stratum-AI-Final-Updates-Dec-2025/)
- [Release v1.0.0](https://github.com/Ibrahim-newaeon/Stratum-AI-Final-Updates-Dec-2025/releases/tag/v1.0.0)
- [API Reference](http://localhost:8000/docs) (when running locally)

---

**Stratum AI v1.1.0** - Built with precision. Deployed with confidence.
