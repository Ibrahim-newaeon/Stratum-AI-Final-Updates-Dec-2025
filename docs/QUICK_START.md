# Stratum AI - Quick Start Guide

Get up and running with Stratum AI in under 10 minutes.

---

## Prerequisites

- Docker 24.0+ and Docker Compose 2.20+
- Git
- 4GB RAM minimum

---

## 1. Clone & Configure

```bash
# Clone repository
git clone https://github.com/your-org/stratum-ai.git
cd stratum-ai

# Copy environment template
cp .env.example .env

# Edit configuration (set your passwords and keys)
nano .env
```

### Minimum .env Configuration

```bash
# Required settings
POSTGRES_USER=stratum
POSTGRES_PASSWORD=your-secure-password
POSTGRES_DB=stratum_db
SECRET_KEY=your-256-bit-secret-key
JWT_SECRET_KEY=your-jwt-secret-key

# Generate keys with:
# openssl rand -hex 32
```

---

## 2. Start Services

```bash
# Build and start all services
docker compose up -d

# Wait for services to be healthy (about 30 seconds)
docker compose ps
```

Expected output:
```
NAME                STATUS              PORTS
stratum-api         running (healthy)   0.0.0.0:8000->8000/tcp
stratum-db          running (healthy)   0.0.0.0:5432->5432/tcp
stratum-frontend    running             0.0.0.0:5173->5173/tcp
stratum-redis       running (healthy)   0.0.0.0:6379->6379/tcp
```

---

## 3. Run Migrations

```bash
# Apply database migrations
docker compose exec api alembic upgrade head
```

---

## 4. Create Admin User

```bash
# Create superadmin account
docker compose exec api python -m app.scripts.seed_demo_users
```

Default demo credentials:
- **Email**: `demo@stratum.ai`
- **Password**: `demo1234`

---

## 5. Access the Application

Open your browser:

| Service | URL |
|---------|-----|
| **Frontend** | http://localhost:5173 |
| **API Docs** | http://localhost:8000/docs |
| **Health Check** | http://localhost:8000/health |

---

## 6. First Login

1. Go to http://localhost:5173
2. Click **Sign In**
3. Enter demo credentials
4. Explore the dashboard

---

## Quick Commands Reference

```bash
# Start services
docker compose up -d

# Stop services
docker compose down

# View logs
docker compose logs -f

# View specific service logs
docker compose logs -f api

# Restart a service
docker compose restart api

# Rebuild after code changes
docker compose up -d --build

# Check service health
docker compose ps

# Access API shell
docker compose exec api bash

# Access database
docker compose exec db psql -U stratum stratum_db
```

---

## Common Issues

### Port Already in Use

```bash
# Check what's using the port
netstat -tulpn | grep 5173

# Or change ports in docker-compose.yml
```

### Database Connection Failed

```bash
# Check if database is ready
docker compose exec db pg_isready

# Check database logs
docker compose logs db
```

### API Won't Start

```bash
# Check API logs
docker compose logs api

# Verify migrations
docker compose exec api alembic current
```

---

## Next Steps

1. **Read the User Guide**: [USER_GUIDE.md](./USER_GUIDE.md)
2. **Configure Integrations**: Connect Google, Meta, TikTok
3. **Set Up Trust Engine**: Configure automation thresholds
4. **Build CDP Segments**: Create customer audiences

---

## Development Mode

For local development with hot reload:

```bash
# Backend (separate terminal)
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

---

## Getting Help

- **Full Documentation**: [API_REFERENCE.md](./API_REFERENCE.md)
- **Deployment Guide**: [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)
- **GitHub Issues**: https://github.com/your-org/stratum-ai/issues
