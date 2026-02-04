# Local Development Setup

This guide walks you through setting up Stratum AI for local development.

## Prerequisites

### Required Software

| Software | Version | Purpose |
|----------|---------|---------|
| Python | 3.11+ | Backend runtime |
| Node.js | 18+ | Frontend runtime |
| Docker | 24+ | Container runtime |
| Docker Compose | 2.x | Multi-container orchestration |
| Git | 2.x | Version control |

### Optional Tools

| Tool | Purpose |
|------|---------|
| pgAdmin | PostgreSQL GUI |
| Redis Insight | Redis GUI |
| Postman | API testing |

---

## Quick Start (Docker)

The fastest way to get started is using Docker Compose:

```bash
# 1. Clone the repository
git clone <repository-url>
cd stratum-ai

# 2. Copy environment file
cp .env.example .env

# 3. Start all services
docker compose up -d

# 4. View logs
docker compose logs -f
```

### Service URLs

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend | http://localhost:5173 | React application |
| Backend API | http://localhost:8000 | FastAPI server |
| API Docs | http://localhost:8000/docs | Swagger UI |
| Flower | http://localhost:5555 | Celery monitoring |
| PostgreSQL | localhost:5432 | Database |
| Redis | localhost:6379 | Cache/Broker |

---

## Manual Setup (Without Docker)

### 1. Database Setup

```bash
# Start PostgreSQL (macOS with Homebrew)
brew services start postgresql@16

# Create database
createdb stratum_ai

# Or using psql
psql -c "CREATE DATABASE stratum_ai;"
psql -c "CREATE USER stratum WITH PASSWORD 'your_password';"
psql -c "GRANT ALL PRIVILEGES ON DATABASE stratum_ai TO stratum;"
```

### 2. Redis Setup

```bash
# macOS
brew services start redis

# Linux
sudo systemctl start redis

# Verify
redis-cli ping  # Should return PONG
```

### 3. Backend Setup

```bash
# Navigate to backend
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# or: .\venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export DATABASE_URL="postgresql+asyncpg://stratum:password@localhost:5432/stratum_ai"
export DATABASE_URL_SYNC="postgresql://stratum:password@localhost:5432/stratum_ai"
export REDIS_URL="redis://localhost:6379/0"
export SECRET_KEY="your-32-char-secret-key-here!!"
export JWT_SECRET_KEY="your-32-char-jwt-secret-here!!"
export PII_ENCRYPTION_KEY="your-32-char-encryption-key!!"

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Celery Workers

Open a new terminal:

```bash
cd backend
source venv/bin/activate

# Start Celery worker
celery -A app.workers.celery_app worker --loglevel=info --concurrency=4
```

Open another terminal for the scheduler:

```bash
cd backend
source venv/bin/activate

# Start Celery Beat (scheduler)
celery -A app.workers.celery_app beat --loglevel=info
```

### 5. Frontend Setup

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Set environment variables (or create .env)
export VITE_API_BASE_URL="http://localhost:8000"
export VITE_WS_URL="ws://localhost:8000"

# Start development server
npm run dev
```

---

## Environment Configuration

### Backend Environment Variables

Create a `.env` file in the project root:

```env
# Application
APP_ENV=development
DEBUG=true
SECRET_KEY=dev-only-secret-key-do-not-use-in-production-32chars

# Database
DATABASE_URL=postgresql+asyncpg://stratum:password@localhost:5432/stratum_ai
DATABASE_URL_SYNC=postgresql://stratum:password@localhost:5432/stratum_ai

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Security
JWT_SECRET_KEY=dev-only-jwt-secret-do-not-use-in-production-32
PII_ENCRYPTION_KEY=dev-only-pii-key-do-not-use-in-prod-32ch

# CORS
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Mock Mode (for development without real API credentials)
USE_MOCK_AD_DATA=true
MARKET_INTEL_PROVIDER=mock
ML_PROVIDER=local
```

### Frontend Environment Variables

Create `.env` in the frontend directory:

```env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_DEFAULT_LOCALE=en
```

---

## Database Migrations

### Running Migrations

```bash
cd backend

# Apply all pending migrations
alembic upgrade head

# Check current migration
alembic current

# View migration history
alembic history
```

### Creating New Migrations

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Add new_feature table"

# Create empty migration
alembic revision -m "Manual migration for data update"
```

### Rolling Back

```bash
# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>

# Rollback all migrations
alembic downgrade base
```

---

## Seed Data

### Creating a Superadmin User

```bash
cd backend

# Using the CLI tool
python -m app.cli.create_superadmin \
  --email admin@stratum.ai \
  --password YourSecurePassword123!

# Or via API (development only)
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@stratum.ai",
    "password": "YourSecurePassword123!",
    "full_name": "Admin User"
  }'
```

### Loading Demo Data

```bash
# Load demo tenant with sample data
python -m app.cli.seed_demo_data

# This creates:
# - Demo tenant
# - Sample campaigns
# - Mock analytics data
# - CDP profiles and segments
```

---

## Verifying Installation

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# Expected response:
# {
#   "status": "healthy",
#   "version": "1.0.0",
#   "environment": "development",
#   "database": "healthy",
#   "redis": "healthy"
# }

# Frontend (should load React app)
curl http://localhost:5173
```

### Running Tests

```bash
# Backend tests
cd backend
pytest

# With coverage
pytest --cov=app --cov-report=html

# Frontend tests
cd frontend
npm run test

# E2E tests
npm run test:e2e
```

---

## Docker Commands Reference

### Starting Services

```bash
# Start all services
docker compose up -d

# Start specific service
docker compose up -d api

# Start with logs
docker compose up

# Rebuild and start
docker compose up -d --build
```

### Viewing Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api
docker compose logs -f worker
```

### Stopping Services

```bash
# Stop all services
docker compose down

# Stop and remove volumes
docker compose down -v

# Stop specific service
docker compose stop api
```

### Executing Commands

```bash
# Run migrations in container
docker compose exec api alembic upgrade head

# Access database
docker compose exec db psql -U stratum -d stratum_ai

# Access Redis
docker compose exec redis redis-cli

# Run backend tests
docker compose exec api pytest
```

### Monitoring

```bash
# View running containers
docker compose ps

# View resource usage
docker stats

# Access Flower (Celery monitoring)
open http://localhost:5555
```

---

## IDE Setup

### VS Code Extensions

Recommended extensions for development:

```json
{
  "recommendations": [
    "ms-python.python",
    "ms-python.vscode-pylance",
    "bradlc.vscode-tailwindcss",
    "dsznajder.es7-react-js-snippets",
    "dbaeumer.vscode-eslint",
    "esbenp.prettier-vscode",
    "ms-azuretools.vscode-docker"
  ]
}
```

### VS Code Settings

```json
{
  "python.defaultInterpreterPath": "./backend/venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.mypyEnabled": true,
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "[python]": {
    "editor.defaultFormatter": "ms-python.python"
  }
}
```

---

## Troubleshooting

### Port Already in Use

```bash
# Find process using port
lsof -i :8000
lsof -i :5173

# Kill process
kill -9 <PID>
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Check database exists
psql -l | grep stratum_ai

# Reset database
dropdb stratum_ai
createdb stratum_ai
alembic upgrade head
```

### Redis Connection Issues

```bash
# Check Redis is running
redis-cli ping

# Check Redis memory
redis-cli info memory
```

### Celery Worker Not Processing

```bash
# Check Celery is connected
celery -A app.workers.celery_app inspect ping

# Check active tasks
celery -A app.workers.celery_app inspect active

# Purge all tasks (use with caution)
celery -A app.workers.celery_app purge
```

### Frontend Build Issues

```bash
# Clear node_modules and reinstall
rm -rf node_modules package-lock.json
npm install

# Clear Vite cache
rm -rf node_modules/.vite
npm run dev
```
