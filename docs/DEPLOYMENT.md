# Stratum AI - Deployment & Operations Guide

## Overview

This guide covers deployment procedures, infrastructure setup, monitoring, and operational best practices for Stratum AI.

---

## Deployment Options

### 1. Docker Compose (Development/Staging)

Recommended for development and small-scale deployments.

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

### 2. Kubernetes (Production)

Recommended for production with high availability requirements.

### 3. Hybrid (Vercel + Docker)

Frontend on Vercel CDN, backend on Docker/K8s.

---

## Quick Start

### Prerequisites

- Docker 24.x+
- Docker Compose 2.x+
- Node.js 20.x+ (for local frontend development)
- Python 3.11+ (for local backend development)

### 1. Clone and Configure

```bash
# Clone repository
git clone <repository-url>
cd Stratum-AI-Final-Updates-Dec-2025-main

# Copy environment template
cp .env.example .env

# Generate secure credentials
python -c "import secrets; print('SECRET_KEY=' + secrets.token_urlsafe(48))"
python -c "import secrets; print('JWT_SECRET_KEY=' + secrets.token_urlsafe(48))"
python -c "import secrets, base64; print('PII_ENCRYPTION_KEY=' + base64.urlsafe_b64encode(secrets.token_bytes(32)).decode())"
python -c "import secrets; print('POSTGRES_PASSWORD=' + secrets.token_urlsafe(24))"

# Update .env with generated credentials
```

### 2. Start Services

```bash
# Start all services
docker-compose up -d

# Wait for services to be healthy
docker-compose ps

# Run database migrations
docker-compose exec api alembic upgrade head
```

### 3. Verify Deployment

```bash
# Check API health
curl http://localhost:8000/health

# Check frontend
curl http://localhost:5173
```

---

## Environment Configuration

### Required Variables

```env
# =============================================================================
# REQUIRED FOR ALL ENVIRONMENTS
# =============================================================================

# Application
APP_NAME=StratumAI
APP_ENV=production              # development, staging, production
DEBUG=false                     # NEVER true in production
SECRET_KEY=<64-char-random>     # Generate with secrets.token_urlsafe(48)

# Database
POSTGRES_USER=stratum
POSTGRES_PASSWORD=<secure-password>
POSTGRES_DB=stratum_ai
DATABASE_URL=postgresql+asyncpg://stratum:<password>@db:5432/stratum_ai

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1

# JWT
JWT_SECRET_KEY=<64-char-random>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Encryption
PII_ENCRYPTION_KEY=<32-byte-base64>
```

### Optional Variables

```env
# =============================================================================
# OPTIONAL / FEATURE-SPECIFIC
# =============================================================================

# Email (SendGrid)
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=SG.xxxx
FROM_EMAIL=noreply@yourdomain.com
FRONTEND_URL=https://app.yourdomain.com

# ML Configuration
ML_PROVIDER=local               # 'local' or 'vertex'
ML_MODELS_PATH=/app/ml_service/models

# Google Vertex AI (if ML_PROVIDER=vertex)
GOOGLE_CLOUD_PROJECT=your-project
GOOGLE_APPLICATION_CREDENTIALS=/secrets/gcp-key.json

# Ad Platforms (set USE_MOCK_AD_DATA=false for real APIs)
USE_MOCK_AD_DATA=true
META_APP_ID=xxx
META_APP_SECRET=xxx
GOOGLE_ADS_DEVELOPER_TOKEN=xxx

# Monitoring
SENTRY_DSN=https://xxx@sentry.io/xxx
LOG_LEVEL=INFO
LOG_FORMAT=json

# Rate Limiting
RATE_LIMIT_PER_MINUTE=100
RATE_LIMIT_BURST=20

# CORS
CORS_ORIGINS=https://app.yourdomain.com
```

---

## Docker Compose Services

### Service Overview

| Service | Image | Port | Purpose |
|---------|-------|------|---------|
| db | postgres:16-alpine | 5432 | Primary database |
| redis | redis:7-alpine | 6379 | Cache + message broker |
| api | custom | 8000 | FastAPI backend |
| worker | custom | - | Celery workers |
| scheduler | custom | - | Celery beat |
| frontend | custom | 5173 | React frontend |
| flower | custom | 5555 | Celery monitoring (optional) |

### Starting Specific Services

```bash
# Start only database and redis
docker-compose up -d db redis

# Start API without frontend
docker-compose up -d db redis api worker

# Start monitoring
docker-compose --profile monitoring up -d flower
```

### Scaling Workers

```bash
# Scale Celery workers
docker-compose up -d --scale worker=4
```

---

## Database Operations

### Migrations

```bash
# Run migrations
docker-compose exec api alembic upgrade head

# Create new migration
docker-compose exec api alembic revision --autogenerate -m "Description"

# Rollback one version
docker-compose exec api alembic downgrade -1

# View migration history
docker-compose exec api alembic history
```

### Backup & Restore

```bash
# Create backup
docker-compose exec db pg_dump -U stratum stratum_ai > backup_$(date +%Y%m%d).sql

# Compressed backup
docker-compose exec db pg_dump -U stratum stratum_ai | gzip > backup_$(date +%Y%m%d).sql.gz

# Restore from backup
cat backup.sql | docker-compose exec -T db psql -U stratum stratum_ai

# Restore from compressed backup
gunzip -c backup.sql.gz | docker-compose exec -T db psql -U stratum stratum_ai
```

### Database Maintenance

```bash
# Connect to database
docker-compose exec db psql -U stratum stratum_ai

# Vacuum and analyze
docker-compose exec db psql -U stratum -c "VACUUM ANALYZE;" stratum_ai

# Check table sizes
docker-compose exec db psql -U stratum stratum_ai -c "
SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC
LIMIT 10;"
```

---

## Production Deployment

### Production Checklist

- [ ] Generate new credentials (SECRET_KEY, JWT_SECRET_KEY, etc.)
- [ ] Set APP_ENV=production and DEBUG=false
- [ ] Configure CORS_ORIGINS for your domain
- [ ] Set up SSL/TLS certificates
- [ ] Configure email (SMTP/SendGrid)
- [ ] Set up Sentry for error tracking
- [ ] Configure database backups
- [ ] Set up monitoring and alerting
- [ ] Review rate limiting settings
- [ ] Test health check endpoints
- [ ] Disable OpenAPI docs (automatic in production)

### Nginx Configuration (Reverse Proxy)

```nginx
# /etc/nginx/sites-available/stratum

upstream api_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # Gzip
    gzip on;
    gzip_types application/json text/plain;

    location / {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # SSE endpoint
    location /api/v1/events/stream {
        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_buffering off;
        proxy_cache off;
        proxy_read_timeout 86400s;
    }
}
```

### SSL Certificate (Let's Encrypt)

```bash
# Install certbot
apt install certbot python3-certbot-nginx

# Generate certificate
certbot --nginx -d api.yourdomain.com

# Auto-renewal (cron)
0 0 1 * * certbot renew --quiet
```

---

## Monitoring

### Health Checks

```bash
# Full health check
curl https://api.yourdomain.com/health

# Readiness probe (K8s)
curl https://api.yourdomain.com/health/ready

# Liveness probe (K8s)
curl https://api.yourdomain.com/health/live

# Application metrics
curl https://api.yourdomain.com/metrics
```

### Log Aggregation

Logs are output in JSON format for easy parsing:

```json
{
  "event": "request_completed",
  "method": "GET",
  "path": "/api/v1/campaigns",
  "status_code": 200,
  "duration_ms": 45.23,
  "timestamp": "2024-12-20T10:30:00Z",
  "request_id": "abc-123-xyz"
}
```

### Sentry Integration

```python
# Automatic in production when SENTRY_DSN is set
if settings.sentry_dsn and settings.is_production:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.app_env,
        traces_sample_rate=0.1,
    )
```

### Celery Monitoring (Flower)

```bash
# Start Flower
docker-compose --profile monitoring up -d flower

# Access at http://localhost:5555
```

---

## Scaling

### Horizontal Scaling

```yaml
# docker-compose.override.yml for production
services:
  api:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 2G

  worker:
    deploy:
      replicas: 4
      resources:
        limits:
          cpus: '1'
          memory: 1G
```

### Database Connection Pooling

```python
# Configured in backend/app/db/session.py
engine = create_async_engine(
    settings.database_url,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
)
```

### Redis Caching

```python
# Cache KPIs for 5 minutes
@cache(ttl=300)
async def get_kpis(tenant_id: int):
    ...
```

---

## Troubleshooting

### Common Issues

#### 1. Database Connection Failed

```bash
# Check database is running
docker-compose ps db

# Check connection
docker-compose exec api python -c "
from app.db.session import check_database_health
import asyncio
print(asyncio.run(check_database_health()))
"

# Check logs
docker-compose logs db
```

#### 2. Redis Connection Failed

```bash
# Check Redis is running
docker-compose exec redis redis-cli ping

# Check connection from API
docker-compose exec api python -c "
import redis
r = redis.from_url('redis://redis:6379/0')
print(r.ping())
"
```

#### 3. Celery Workers Not Processing

```bash
# Check worker status
docker-compose exec worker celery -A app.workers.celery_app inspect active

# Check queues
docker-compose exec worker celery -A app.workers.celery_app inspect reserved

# Restart workers
docker-compose restart worker
```

#### 4. API Returns 500 Errors

```bash
# Check API logs
docker-compose logs -f api

# Enable debug mode temporarily
docker-compose exec api env DEBUG=true python -m uvicorn app.main:app --reload
```

### Debug Mode

For development debugging:

```bash
# Run API in debug mode
docker-compose exec api python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Run with Python debugger
docker-compose exec api python -m pdb -m uvicorn app.main:app
```

---

## Security

### Credential Rotation

```bash
# 1. Generate new credentials
NEW_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(48))")

# 2. Update .env file
sed -i "s/SECRET_KEY=.*/SECRET_KEY=$NEW_SECRET/" .env

# 3. Restart services
docker-compose restart api worker

# 4. Verify
curl http://localhost:8000/health
```

### Database User Permissions

```sql
-- Create read-only user for analytics
CREATE USER analytics_user WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE stratum_ai TO analytics_user;
GRANT USAGE ON SCHEMA public TO analytics_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO analytics_user;
```

### Network Security

```yaml
# docker-compose.override.yml
services:
  db:
    ports: []  # Remove external port access

  redis:
    ports: []  # Remove external port access
```

---

## Backup Strategy

### Automated Backups

```bash
#!/bin/bash
# backup.sh - Run daily via cron

BACKUP_DIR=/backups
DATE=$(date +%Y%m%d_%H%M%S)

# Database backup
docker-compose exec -T db pg_dump -U stratum stratum_ai | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Redis backup
docker-compose exec -T redis redis-cli BGSAVE
docker cp stratum_redis:/data/dump.rdb $BACKUP_DIR/redis_$DATE.rdb

# Cleanup old backups (keep 30 days)
find $BACKUP_DIR -name "*.sql.gz" -mtime +30 -delete
find $BACKUP_DIR -name "*.rdb" -mtime +30 -delete

# Upload to S3 (optional)
aws s3 sync $BACKUP_DIR s3://your-bucket/backups/
```

### Cron Configuration

```bash
# Edit crontab
crontab -e

# Add daily backup at 2 AM
0 2 * * * /opt/stratum/backup.sh >> /var/log/backup.log 2>&1
```

---

## Vercel Deployment (Frontend)

### Setup

```bash
cd frontend

# Install Vercel CLI
npm install -g vercel

# Login
vercel login

# Deploy
vercel --prod
```

### Environment Variables

Set in Vercel dashboard:
- `VITE_API_BASE_URL`: https://api.yourdomain.com
- `VITE_WS_URL`: wss://api.yourdomain.com
- `VITE_DEFAULT_LOCALE`: en

### Build Configuration

```json
// vercel.json
{
  "buildCommand": "npm run build",
  "outputDirectory": "dist",
  "framework": "vite",
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

---

## Runbook

### Service Restart Procedure

```bash
# 1. Notify users of maintenance
# 2. Scale down workers
docker-compose scale worker=0

# 3. Restart API (zero-downtime with multiple replicas)
docker-compose restart api

# 4. Verify health
curl http://localhost:8000/health

# 5. Scale up workers
docker-compose scale worker=4

# 6. Verify task processing
docker-compose exec worker celery -A app.workers.celery_app inspect active
```

### Database Migration Procedure

```bash
# 1. Create backup
./backup.sh

# 2. Test migration on copy
docker-compose exec db createdb stratum_ai_test -T stratum_ai
docker-compose exec api alembic upgrade head --sql > migration.sql
# Review migration.sql

# 3. Apply migration
docker-compose exec api alembic upgrade head

# 4. Verify
docker-compose exec db psql -U stratum stratum_ai -c "\dt"
```

### Incident Response

1. **Identify** - Check health endpoints, logs, metrics
2. **Contain** - Scale down affected services
3. **Diagnose** - Review logs, check recent changes
4. **Fix** - Apply hotfix or rollback
5. **Recover** - Restart services, verify health
6. **Document** - Write post-mortem

---

## Support

For issues:
1. Check this documentation
2. Review application logs
3. Check GitHub issues
4. Contact development team
