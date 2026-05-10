# Stratum AI - System Architecture

## High-Level Architecture

```mermaid
graph TB
    subgraph "Client Layer"
        WEB[React SPA]
        MOBILE[Mobile Apps]
        API_CLIENT[API Clients]
    end

    subgraph "Edge Layer"
        CDN[CloudFront CDN]
        LB[Application Load Balancer]
    end

    subgraph "Application Layer"
        API[FastAPI Backend]
        WS[WebSocket Server]
        SSE[SSE Server]
    end

    subgraph "Processing Layer"
        WORKER[Celery Workers]
        SCHEDULER[Celery Beat]
        FLOWER[Flower Monitor]
    end

    subgraph "Data Layer"
        PG[(PostgreSQL 16)]
        REDIS[(Redis 7)]
    end

    subgraph "External Services"
        META[Meta API]
        GOOGLE[Google Ads API]
        TIKTOK[TikTok API]
        SNAP[Snapchat API]
        SENTRY[Sentry]
        SMTP[SMTP Server]
    end

    WEB --> CDN --> LB
    MOBILE --> LB
    API_CLIENT --> LB

    LB --> API
    LB --> WS
    LB --> SSE

    API --> PG
    API --> REDIS
    API --> WORKER

    WORKER --> PG
    WORKER --> REDIS
    WORKER --> META
    WORKER --> GOOGLE
    WORKER --> TIKTOK
    WORKER --> SNAP

    SCHEDULER --> REDIS
    FLOWER --> REDIS

    API --> SENTRY
    API --> SMTP
```

## Technology Stack

### Backend
| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Framework | FastAPI | Latest | REST API, async support |
| Language | Python | 3.11+ | Type hints, performance |
| ORM | SQLAlchemy | 2.x | Database operations |
| Validation | Pydantic | 2.x | Request/response schemas |
| Task Queue | Celery | 5.x | Background jobs |
| Scheduler | Celery Beat | 5.x | Scheduled tasks |

### Frontend
| Component | Technology | Version | Purpose |
|-----------|------------|---------|---------|
| Framework | React | 18.x | UI components |
| Language | TypeScript | 5.x | Type safety |
| Styling | Tailwind CSS | 3.x | Utility-first CSS |
| State | Zustand | Latest | Global state management |
| Data Fetching | TanStack Query | 5.x | Server state management |
| Build Tool | Vite | 5.x | Fast bundling |

### Infrastructure
| Component | Technology | Purpose |
|-----------|------------|---------|
| Database | PostgreSQL 16 | Primary data store |
| Cache | Redis 7 | Caching, message broker |
| Container | Docker | Containerization |
| Orchestration | Docker Compose | Local development |
| Cloud | AWS (ECS, RDS, ElastiCache) | Production hosting |

### Observability
| Component | Technology | Purpose |
|-----------|------------|---------|
| Metrics | Prometheus | Metric collection |
| Visualization | Grafana | Dashboards |
| Error Tracking | Sentry | Error monitoring |
| Logging | Structlog | Structured logging |

---

## Backend Architecture

### Project Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI application entry point
│   ├── core/
│   │   ├── config.py        # Settings management (Pydantic)
│   │   ├── logging.py       # Structured logging setup
│   │   ├── metrics.py       # Prometheus metrics
│   │   └── websocket.py     # WebSocket manager
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py  # API router aggregation
│   │       └── endpoints/   # 51+ endpoint modules
│   ├── auth/
│   │   ├── jwt.py           # JWT token handling
│   │   ├── mfa.py           # Multi-factor authentication
│   │   └── permissions.py   # RBAC implementation
│   ├── db/
│   │   ├── session.py       # Database connection
│   │   └── base.py          # SQLAlchemy base
│   ├── models/              # SQLAlchemy models
│   ├── schemas/             # Pydantic schemas
│   ├── services/            # Business logic
│   │   ├── cdp/             # Customer Data Platform
│   │   ├── trust_engine/    # Trust gate logic
│   │   └── integrations/    # External APIs
│   ├── workers/
│   │   ├── celery_app.py    # Celery configuration
│   │   └── tasks/           # Background tasks
│   └── middleware/
│       ├── audit.py         # Audit logging
│       ├── tenant.py        # Tenant extraction
│       └── rate_limit.py    # Rate limiting
├── alembic/                 # Database migrations
├── tests/                   # Test suite
└── Dockerfile               # Container definition
```

### Request Flow

```mermaid
sequenceDiagram
    participant Client
    participant LB as Load Balancer
    participant API as FastAPI
    participant MW as Middleware
    participant EP as Endpoint
    participant SVC as Service
    participant DB as PostgreSQL
    participant Cache as Redis

    Client->>LB: HTTPS Request
    LB->>API: Forward Request
    API->>MW: Rate Limit Check
    MW->>MW: Tenant Extraction
    MW->>MW: Auth Validation
    MW->>EP: Route to Endpoint
    EP->>Cache: Check Cache
    alt Cache Hit
        Cache-->>EP: Cached Data
    else Cache Miss
        EP->>SVC: Business Logic
        SVC->>DB: Query Data
        DB-->>SVC: Result
        SVC-->>EP: Processed Data
        EP->>Cache: Store in Cache
    end
    EP-->>API: Response
    API->>MW: Audit Log
    API-->>Client: JSON Response
```

### Middleware Stack

Middleware executes in reverse order (last added = first executed):

1. **Request Timing** - Adds timing headers and request ID
2. **Audit Middleware** - Logs state-changing requests
3. **Tenant Middleware** - Extracts tenant context
4. **Rate Limit Middleware** - Request throttling
5. **GZip Middleware** - Response compression
6. **CORS Middleware** - Cross-origin handling

### Database Schema

```mermaid
erDiagram
    TENANT ||--o{ USER : has
    TENANT ||--o{ CAMPAIGN : owns
    TENANT ||--o{ CDP_PROFILE : contains
    TENANT ||--o{ SEGMENT : defines

    USER ||--o{ AUDIT_LOG : generates
    USER }o--|| ROLE : has

    CAMPAIGN ||--o{ AD_SET : contains
    CAMPAIGN ||--o{ PERFORMANCE_DATA : tracks

    CDP_PROFILE ||--o{ EVENT : has
    CDP_PROFILE }o--o{ SEGMENT : belongs_to
    CDP_PROFILE ||--o{ IDENTITY : has

    SEGMENT ||--o{ AUDIENCE_SYNC : syncs_to

    TRUST_GATE ||--o{ SIGNAL : evaluates
    TRUST_GATE ||--o{ AUTOMATION_LOG : triggers
```

---

## Frontend Architecture

### Project Structure

```
frontend/
├── src/
│   ├── App.tsx              # Root component with routing
│   ├── main.tsx             # Application entry point
│   ├── api/                 # API hooks (30+ files)
│   │   ├── auth.ts          # Authentication
│   │   ├── campaigns.ts     # Campaign management
│   │   ├── cdp.ts           # CDP operations (60+ hooks)
│   │   └── ...
│   ├── components/          # Reusable components
│   │   ├── ui/              # Base UI components
│   │   ├── common/          # Shared components
│   │   ├── cdp/             # CDP-specific components
│   │   └── charts/          # Visualization components
│   ├── views/               # Page components
│   │   ├── dashboard/       # Dashboard views
│   │   ├── cdp/             # CDP views
│   │   ├── tenant/          # Tenant-scoped views
│   │   └── superadmin/      # Admin views
│   ├── contexts/            # React contexts
│   │   ├── AuthContext.tsx  # Authentication state
│   │   ├── ThemeContext.tsx # Theme management
│   │   └── DemoContext.tsx  # Demo mode
│   ├── hooks/               # Custom hooks
│   ├── lib/                 # Utilities
│   └── stores/              # Zustand stores
├── public/                  # Static assets
├── index.html               # HTML template
├── vite.config.ts           # Vite configuration
├── tailwind.config.js       # Tailwind configuration
└── package.json             # Dependencies
```

### Component Architecture

```mermaid
graph TB
    subgraph "Provider Layer"
        HELMET[HelmetProvider]
        THEME[ThemeProvider]
        AUTH[AuthProvider]
        DEMO[DemoProvider]
        TOOLTIP[TooltipProvider]
        JOYRIDE[JoyrideProvider]
    end

    subgraph "Routing Layer"
        ROUTES[React Router]
        PROTECTED[ProtectedRoute]
        ONBOARDING[OnboardingGuard]
    end

    subgraph "Layout Layer"
        DASHBOARD[DashboardLayout]
        TENANT[TenantLayout]
        CMS[CMSLayout]
    end

    subgraph "View Layer"
        VIEWS[Page Components]
    end

    subgraph "Data Layer"
        QUERY[TanStack Query]
        ZUSTAND[Zustand Stores]
    end

    HELMET --> THEME --> AUTH --> DEMO --> TOOLTIP --> JOYRIDE
    JOYRIDE --> ROUTES
    ROUTES --> PROTECTED --> ONBOARDING
    ONBOARDING --> DASHBOARD
    ONBOARDING --> TENANT
    ROUTES --> CMS
    DASHBOARD --> VIEWS
    TENANT --> VIEWS
    CMS --> VIEWS
    VIEWS --> QUERY
    VIEWS --> ZUSTAND
```

### State Management

| Type | Technology | Use Case |
|------|------------|----------|
| Server State | TanStack Query | API data caching |
| Global State | Zustand | User preferences, UI state |
| Context State | React Context | Auth, Theme, Demo mode |
| Local State | useState/useReducer | Component-specific state |

---

## Trust Engine Architecture

```mermaid
flowchart TB
    subgraph "Signal Collection"
        S1[Meta Signals]
        S2[Google Signals]
        S3[TikTok Signals]
        S4[Snapchat Signals]
        S5[CDP Events]
    end

    subgraph "Health Calculation"
        HC[Health Calculator]
        EMQ[EMQ Score]
        DATA[Data Freshness]
        COMP[Completeness]
    end

    subgraph "Trust Gate"
        TG{Trust Gate}
        PASS[PASS]
        HOLD[HOLD]
        BLOCK[BLOCK]
    end

    subgraph "Automation"
        AUTO[Autopilot Engine]
        ALERT[Alert System]
        MANUAL[Manual Queue]
    end

    S1 & S2 & S3 & S4 & S5 --> HC
    HC --> EMQ & DATA & COMP
    EMQ & DATA & COMP --> TG

    TG -->|"≥70"| PASS --> AUTO
    TG -->|"40-69"| HOLD --> ALERT
    TG -->|"<40"| BLOCK --> MANUAL
```

### Trust Thresholds

```python
# From config
HEALTHY_THRESHOLD = 70      # Green - autopilot enabled
DEGRADED_THRESHOLD = 40     # Yellow - alert + hold
# Below 40 = Red - manual required
```

---

## Data Flow Architecture

### Real-Time Updates

```mermaid
sequenceDiagram
    participant Worker as Celery Worker
    participant Redis
    participant API as FastAPI
    participant WS as WebSocket
    participant Client

    Worker->>Redis: Publish Event
    Redis->>API: PubSub Notification
    API->>WS: Forward to WebSocket
    WS->>Client: Push Update

    Note over Client: UI Updates Automatically
```

### Background Job Processing

```mermaid
flowchart LR
    subgraph "Job Producers"
        API[API Endpoints]
        SCHEDULE[Celery Beat]
        WEBHOOK[Webhooks]
    end

    subgraph "Message Queue"
        REDIS[(Redis)]
    end

    subgraph "Job Consumers"
        W1[Worker 1]
        W2[Worker 2]
        W3[Worker 3]
        W4[Worker 4]
    end

    subgraph "Results"
        DB[(PostgreSQL)]
        NOTIFY[Notifications]
    end

    API & SCHEDULE & WEBHOOK --> REDIS
    REDIS --> W1 & W2 & W3 & W4
    W1 & W2 & W3 & W4 --> DB & NOTIFY
```

---

## Security Architecture

### Authentication Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant DB

    User->>Frontend: Login (email, password)
    Frontend->>API: POST /auth/login
    API->>DB: Verify credentials
    DB-->>API: User record

    alt MFA Enabled
        API-->>Frontend: MFA required
        Frontend->>User: Enter TOTP code
        User->>Frontend: TOTP code
        Frontend->>API: POST /auth/mfa/verify
        API->>API: Verify TOTP
    end

    API->>API: Generate JWT
    API-->>Frontend: Access + Refresh tokens
    Frontend->>Frontend: Store tokens
    Frontend-->>User: Redirect to dashboard
```

### Authorization Model

```mermaid
graph TB
    subgraph "Roles"
        SA[SuperAdmin]
        ADMIN[Admin]
        MB[Media Buyer]
        VIEWER[Viewer]
    end

    subgraph "Permissions"
        P1[Read Analytics]
        P2[Write Campaigns]
        P3[Manage Users]
        P4[System Config]
        P5[Billing]
    end

    SA --> P1 & P2 & P3 & P4 & P5
    ADMIN --> P1 & P2 & P3
    MB --> P1 & P2
    VIEWER --> P1
```

---

## Deployment Architecture

### AWS Production

```mermaid
graph TB
    subgraph "Internet"
        USERS[Users]
    end

    subgraph "AWS Edge"
        CF[CloudFront]
        WAF[WAF]
    end

    subgraph "VPC"
        subgraph "Public Subnet"
            ALB[Application Load Balancer]
        end

        subgraph "Private Subnet - Compute"
            ECS[ECS Fargate Cluster]
            API1[API Container 1]
            API2[API Container 2]
            W1[Worker Container]
            W2[Worker Container]
        end

        subgraph "Private Subnet - Data"
            RDS[(RDS PostgreSQL)]
            CACHE[(ElastiCache Redis)]
        end
    end

    USERS --> CF --> WAF --> ALB
    ALB --> ECS
    ECS --> API1 & API2 & W1 & W2
    API1 & API2 --> RDS & CACHE
    W1 & W2 --> RDS & CACHE
```

### Docker Compose (Development)

| Service | Port | Purpose |
|---------|------|---------|
| api | 8000 | FastAPI backend |
| frontend | 5173 | Vite dev server |
| db | 5432 | PostgreSQL |
| redis | 6379 | Cache & broker |
| worker | - | Celery worker |
| scheduler | - | Celery beat |
| flower | 5555 | Celery monitoring |
