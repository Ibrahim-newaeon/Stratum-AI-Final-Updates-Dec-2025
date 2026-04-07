# Available Scripts & Commands

Reference for all available scripts and commands in Stratum AI.

---

## Docker Compose Commands

### Starting Services

```bash
# Start all services in detached mode
docker compose up -d

# Start with build (rebuild images)
docker compose up -d --build

# Start specific services
docker compose up -d api frontend

# Start with logs (foreground)
docker compose up

# Start with monitoring profile (includes Flower)
docker compose --profile monitoring up -d
```

### Stopping Services

```bash
# Stop all services
docker compose down

# Stop and remove volumes (data loss!)
docker compose down -v

# Stop specific service
docker compose stop api
```

### Viewing Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api
docker compose logs -f worker
docker compose logs -f frontend

# Last 100 lines
docker compose logs -f --tail=100 api
```

### Executing Commands

```bash
# Run command in running container
docker compose exec api <command>
docker compose exec frontend <command>
docker compose exec db <command>

# Run in new container (starts if not running)
docker compose run --rm api <command>

# Examples
docker compose exec api alembic upgrade head
docker compose exec db psql -U stratum -d stratum_ai
docker compose exec redis redis-cli
```

### Container Management

```bash
# List running containers
docker compose ps

# View resource usage
docker stats

# Restart service
docker compose restart api

# Rebuild single service
docker compose build api
```

---

## Backend Commands

### Python/FastAPI

```bash
# Navigate to backend
cd backend

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
.\venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Dev dependencies

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start with specific workers
uvicorn app.main:app --workers 4 --host 0.0.0.0 --port 8000
```

### Alembic (Database Migrations)

```bash
# Apply all pending migrations
alembic upgrade head

# Apply specific migration
alembic upgrade <revision_id>

# Create new migration (auto-generate)
alembic revision --autogenerate -m "Add new_table"

# Create empty migration
alembic revision -m "Manual migration"

# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade <revision_id>

# Rollback all migrations
alembic downgrade base

# Show current revision
alembic current

# Show migration history
alembic history

# Show migration history with details
alembic history --verbose
```

### Celery (Background Tasks)

```bash
# Start Celery worker
celery -A app.workers.celery_app worker --loglevel=info

# Start with concurrency
celery -A app.workers.celery_app worker --loglevel=info --concurrency=4

# Start specific queues
celery -A app.workers.celery_app worker --loglevel=info -Q high,default

# Start Celery Beat (scheduler)
celery -A app.workers.celery_app beat --loglevel=info

# Start Flower (monitoring)
celery -A app.workers.celery_app flower --port=5555

# Inspect workers
celery -A app.workers.celery_app inspect ping
celery -A app.workers.celery_app inspect active
celery -A app.workers.celery_app inspect reserved

# Purge all tasks (use with caution!)
celery -A app.workers.celery_app purge
```

### Testing

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_auth.py

# Run specific test function
pytest tests/test_auth.py::test_login

# Run with coverage
pytest --cov=app

# Generate HTML coverage report
pytest --cov=app --cov-report=html
open htmlcov/index.html  # View report

# Run with specific markers
pytest -m "not slow"
pytest -m integration

# Run in parallel
pytest -n auto
```

### Code Quality

```bash
# Run Ruff linter
ruff check .

# Run Ruff with auto-fix
ruff check . --fix

# Run mypy type checker
mypy app

# Format code with black
black app tests

# Sort imports
isort app tests
```

### CLI Tools

```bash
# Create superadmin user
python -m app.cli.create_superadmin --email admin@example.com --password SecurePass123!

# Seed demo data
python -m app.cli.seed_demo_data

# Clear cache
python -m app.cli.clear_cache

# Generate API key
python -m app.cli.generate_api_key --tenant-id 1 --name "Integration Key"
```

---

## Frontend Commands

### npm Scripts

```bash
# Navigate to frontend
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev

# Start dev server on specific host/port
npm run dev -- --host 0.0.0.0 --port 3000

# Build for production
npm run build

# Preview production build
npm run preview

# Run linter
npm run lint

# Run linter with auto-fix
npm run lint -- --fix
```

### Testing

```bash
# Run unit tests
npm run test

# Run tests in watch mode
npm run test -- --watch

# Run tests with coverage
npm run test:coverage

# Run E2E tests (Playwright)
npm run test:e2e

# Run E2E tests with UI
npm run test:e2e:ui

# Run E2E tests headed (visible browser)
npm run test:e2e:headed

# Show E2E test report
npm run test:e2e:report
```

### Type Checking

```bash
# Check TypeScript types
npx tsc --noEmit

# Check specific file
npx tsc --noEmit src/App.tsx
```

### Dependency Management

```bash
# Check for outdated packages
npm outdated

# Update packages
npm update

# Audit for vulnerabilities
npm audit

# Fix vulnerabilities
npm audit fix
```

---

## Database Commands

### PostgreSQL (psql)

```bash
# Connect to database
psql -U stratum -d stratum_ai

# Connect via Docker
docker compose exec db psql -U stratum -d stratum_ai

# Common psql commands
\l         # List databases
\dt        # List tables
\d table   # Describe table
\q         # Quit
```

### Useful SQL Commands

```sql
-- List all tables with row counts
SELECT schemaname, tablename, n_live_tup
FROM pg_stat_user_tables
ORDER BY n_live_tup DESC;

-- Check table sizes
SELECT tablename, pg_size_pretty(pg_total_relation_size(tablename::regclass))
FROM pg_tables WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(tablename::regclass) DESC;

-- List active connections
SELECT * FROM pg_stat_activity WHERE datname = 'stratum_ai';

-- Kill a specific connection
SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE pid = <pid>;
```

### Backup & Restore

```bash
# Backup database
pg_dump -U stratum -d stratum_ai > backup.sql

# Backup via Docker
docker compose exec db pg_dump -U stratum stratum_ai > backup.sql

# Restore database
psql -U stratum -d stratum_ai < backup.sql

# Restore via Docker
docker compose exec -T db psql -U stratum stratum_ai < backup.sql
```

---

## Redis Commands

### redis-cli

```bash
# Connect to Redis
redis-cli

# Connect via Docker
docker compose exec redis redis-cli

# Common commands
PING           # Check connection
KEYS *         # List all keys (use sparingly)
GET key        # Get value
SET key value  # Set value
DEL key        # Delete key
FLUSHALL       # Clear all data (dangerous!)

# Check memory
INFO memory

# List Celery tasks
KEYS celery*
```

---

## Git Workflow

### Branch Naming

```bash
# Feature branch
git checkout -b feature/STRAT-123-add-new-feature

# Bug fix branch
git checkout -b fix/STRAT-456-fix-login-issue

# Hotfix branch
git checkout -b hotfix/STRAT-789-critical-fix
```

### Commit Format

```bash
# Format: type(scope): message [TICKET]
git commit -m "feat(signals): add anomaly detection [STRAT-123]"
git commit -m "fix(auth): resolve token refresh issue [STRAT-456]"
git commit -m "docs(readme): update setup instructions"
git commit -m "refactor(cdp): simplify segment builder logic"
git commit -m "test(api): add integration tests for campaigns"
```

### Common Workflow

```bash
# Start new feature
git checkout main
git pull origin main
git checkout -b feature/STRAT-123-new-feature

# Make changes and commit
git add .
git commit -m "feat(module): add feature [STRAT-123]"

# Push and create PR
git push -u origin feature/STRAT-123-new-feature

# After PR approved, merge to main
git checkout main
git pull origin main
git branch -d feature/STRAT-123-new-feature
```

---

## Quick Reference

### Development Startup

```bash
# Full stack with Docker
docker compose up -d

# Manual startup (3 terminals)
# Terminal 1: Backend
cd backend && source venv/bin/activate && uvicorn app.main:app --reload

# Terminal 2: Celery
cd backend && source venv/bin/activate && celery -A app.workers.celery_app worker --loglevel=info

# Terminal 3: Frontend
cd frontend && npm run dev
```

### Health Checks

```bash
# Backend health
curl http://localhost:8000/health

# Database
pg_isready -h localhost -p 5432

# Redis
redis-cli ping

# Celery
celery -A app.workers.celery_app inspect ping
```

### Common Tasks

| Task | Command |
|------|---------|
| Reset database | `alembic downgrade base && alembic upgrade head` |
| Clear Redis cache | `redis-cli FLUSHALL` |
| Rebuild Docker | `docker compose down && docker compose up -d --build` |
| View API logs | `docker compose logs -f api` |
| Run migrations | `docker compose exec api alembic upgrade head` |
| Create user | `python -m app.cli.create_superadmin` |
