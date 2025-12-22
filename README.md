# Stratum AI

**Enterprise Marketing Intelligence Platform**

Unified analytics across Meta, Google, TikTok, Snapchat, and LinkedIn with AI-powered insights, automation rules, and GDPR compliance.

---

## Features

- **Cross-Platform Campaign Analytics** - Unified view of Meta, Google, TikTok, Snapchat, and LinkedIn ads
- **AI-Powered ROAS Optimization** - Machine learning predictions and budget recommendations
- **Automation Rules Engine** - If-then workflows with Slack/WhatsApp notifications
- **Competitor Intelligence** - Market benchmarking and competitive analysis
- **What-If Simulator** - Predict campaign outcomes before making changes
- **WhatsApp Business Integration** - Template messaging and broadcasts
- **GDPR Compliance** - PII encryption, data export, and right-to-be-forgotten
- **Multi-Tenant Architecture** - Isolated data for multiple organizations
- **Multi-Language Support** - English, Arabic, and Ukrainian

---

## Tech Stack

### Backend
- **Framework:** FastAPI 0.109+ (Python 3.11+)
- **Database:** PostgreSQL 16 with async SQLAlchemy
- **Cache/Queue:** Redis 7 with Celery
- **ML:** scikit-learn, XGBoost (optional: Google Vertex AI)
- **Auth:** JWT with bcrypt password hashing
- **Encryption:** Fernet symmetric encryption for PII

### Frontend
- **Framework:** React 18 with TypeScript
- **Build:** Vite 5
- **Styling:** Tailwind CSS
- **State:** Zustand + React Query
- **Charts:** Recharts, Tremor

### Infrastructure
- **Containers:** Docker Compose
- **Deployment:** Vercel (frontend), Docker (backend)

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 20+ (for local frontend development)
- Python 3.11+ (for local backend development)

### 1. Clone and Configure

```bash
# Clone the repository
git clone <repository-url>
cd Stratum-AI-Final-Updates-Dec-2025-main

# Copy environment template
cp .env.example .env

# Generate secure credentials (IMPORTANT!)
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(48))"
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(48))"
python -c "import secrets, base64; print('PII_ENCRYPTION_KEY=' + base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
python -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(24))"

# Update .env with generated credentials
```

### 2. Start with Docker Compose

```bash
# Start all services
docker-compose up -d

# Check logs
docker-compose logs -f api

# Run database migrations
docker-compose exec api alembic upgrade head
```

### 3. Access the Application

- **Frontend:** http://localhost:5173
- **Backend API:** http://localhost:8000
- **API Docs:** http://localhost:8000/docs (development only)
- **Flower (Celery monitor):** http://localhost:5555

---

## Development Setup

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Build for production
npm run build
```

### Running Tests

```bash
# Backend tests
cd backend
pytest -v

# With coverage
pytest --cov=app --cov-report=html

# Frontend tests
cd frontend
npm run test
npm run test:coverage
```

---

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/v1/endpoints/    # API route handlers
│   │   ├── core/                # Config, security, logging
│   │   ├── db/                  # Database session, base models
│   │   ├── middleware/          # Audit, tenant, rate limiting
│   │   ├── ml/                  # Machine learning modules
│   │   ├── services/            # Business logic, external APIs
│   │   ├── workers/             # Celery tasks
│   │   ├── models.py            # SQLAlchemy ORM models
│   │   ├── schemas.py           # Pydantic request/response schemas
│   │   └── main.py              # FastAPI application factory
│   ├── migrations/              # Alembic database migrations
│   ├── tests/                   # pytest test suite
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/          # React components
│   │   ├── views/               # Page components
│   │   ├── services/            # API client
│   │   ├── contexts/            # React contexts
│   │   ├── types/               # TypeScript types
│   │   └── i18n/                # Translations
│   ├── package.json
│   └── vite.config.ts
│
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/login` | User login |
| POST | `/api/v1/auth/register` | User registration |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| POST | `/api/v1/auth/logout` | User logout |
| POST | `/api/v1/auth/forgot-password` | Request password reset |
| POST | `/api/v1/auth/reset-password` | Reset password with token |

### Campaigns
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/campaigns` | List campaigns |
| POST | `/api/v1/campaigns` | Create campaign |
| GET | `/api/v1/campaigns/{id}` | Get campaign details |
| PUT | `/api/v1/campaigns/{id}` | Update campaign |
| DELETE | `/api/v1/campaigns/{id}` | Delete campaign |
| GET | `/api/v1/campaigns/{id}/metrics` | Get campaign metrics |

### Analytics
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/analytics/kpis` | Dashboard KPIs |
| GET | `/api/v1/analytics/platforms` | Platform breakdown |
| POST | `/api/v1/analytics/export` | Export data |

### Health Checks
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Full health check |
| GET | `/health/ready` | Readiness probe |
| GET | `/health/live` | Liveness probe |
| GET | `/metrics` | Application metrics |

---

## Environment Variables

### Required for Production

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Application secret (min 32 chars) |
| `JWT_SECRET_KEY` | JWT signing key |
| `PII_ENCRYPTION_KEY` | 32-byte base64 encryption key |
| `POSTGRES_PASSWORD` | Database password |
| `DATABASE_URL` | PostgreSQL connection string |
| `REDIS_URL` | Redis connection string |

### Email Configuration

| Variable | Description |
|----------|-------------|
| `SMTP_HOST` | SMTP server hostname |
| `SMTP_PORT` | SMTP port (default: 587) |
| `SMTP_USER` | SMTP username |
| `SMTP_PASSWORD` | SMTP password |
| `FROM_EMAIL` | Sender email address |
| `FRONTEND_URL` | Frontend URL for email links |

### Ad Platform APIs (Optional)

| Platform | Variables |
|----------|-----------|
| Meta | `META_APP_ID`, `META_APP_SECRET`, `META_ACCESS_TOKEN` |
| Google | `GOOGLE_ADS_DEVELOPER_TOKEN`, `GOOGLE_ADS_CLIENT_ID`, etc. |
| TikTok | `TIKTOK_APP_ID`, `TIKTOK_SECRET`, `TIKTOK_ACCESS_TOKEN` |
| Snapchat | `SNAPCHAT_CLIENT_ID`, `SNAPCHAT_CLIENT_SECRET`, etc. |
| LinkedIn | `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET`, etc. |

See `.env.example` for the complete list.

---

## Deployment

### Production Checklist

- [ ] Generate new secure credentials (never use defaults)
- [ ] Set `DEBUG=false` and `APP_ENV=production`
- [ ] Configure CORS origins for your domain
- [ ] Set up SMTP for transactional emails
- [ ] Configure Sentry DSN for error tracking
- [ ] Enable HTTPS/SSL
- [ ] Set up database backups
- [ ] Configure rate limiting appropriately
- [ ] Review and restrict API keys

### Docker Production Build

```bash
# Build production images
docker-compose -f docker-compose.yml build

# Deploy with production settings
APP_ENV=production docker-compose up -d
```

### Vercel Deployment (Frontend)

The frontend is configured for Vercel deployment:

```bash
cd frontend
vercel --prod
```

---

## Security

- **Authentication:** JWT tokens with configurable expiration
- **Password Storage:** bcrypt with automatic salting
- **PII Encryption:** Fernet symmetric encryption (AES-128-CBC)
- **Rate Limiting:** Configurable per-minute and burst limits
- **CORS:** Configurable allowed origins
- **Audit Logging:** All state changes are logged
- **Multi-Tenancy:** Data isolation at database level

### Reporting Security Issues

Please report security vulnerabilities privately. Do not create public issues.

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

Proprietary - All rights reserved.

---

## Support

For support, please contact the development team or open an issue in the repository.
