# Stratum AI - Production Deployment Guide

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Server Requirements](#server-requirements)
3. [Architecture Overview](#architecture-overview)
4. [Docker Production Setup](#docker-production-setup)
5. [Environment Configuration](#environment-configuration)
6. [Database Setup](#database-setup)
7. [SSL/HTTPS Configuration](#sslhttps-configuration)
8. [Reverse Proxy Setup](#reverse-proxy-setup)
9. [Monitoring & Logging](#monitoring--logging)
10. [Backup & Recovery](#backup--recovery)
11. [Scaling Strategies](#scaling-strategies)
12. [Security Hardening](#security-hardening)
13. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

| Software | Minimum Version | Recommended |
|----------|-----------------|-------------|
| Docker | 24.0+ | Latest |
| Docker Compose | 2.20+ | Latest |
| Git | 2.40+ | Latest |
| Node.js | 18.x | 20.x LTS |
| Python | 3.11+ | 3.11.x |

### Required Accounts & Services

- **Domain Name**: Registered domain with DNS access
- **SSL Certificate**: Let's Encrypt (free) or commercial certificate
- **SMTP Service**: SendGrid, AWS SES, or similar
- **Cloud Provider** (optional): AWS, GCP, Azure, or DigitalOcean

---

## Server Requirements

### Minimum Production Configuration

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| CPU | 4 vCPUs | 8 vCPUs |
| RAM | 8 GB | 16 GB |
| Storage | 50 GB SSD | 100 GB SSD |
| Network | 1 Gbps | 1 Gbps |

### Service Resource Allocation

```yaml
# Recommended resource limits per service
api:
  memory: 2GB
  cpu: 2

frontend:
  memory: 512MB
  cpu: 0.5

postgres:
  memory: 4GB
  cpu: 2

redis:
  memory: 1GB
  cpu: 1

celery-worker:
  memory: 2GB
  cpu: 2

celery-beat:
  memory: 512MB
  cpu: 0.5
```

---

## Architecture Overview

```
                    ┌─────────────────────────────────────────┐
                    │              Load Balancer               │
                    │         (Nginx / AWS ALB / etc)          │
                    └────────────────┬────────────────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │                      │                      │
              ▼                      ▼                      ▼
    ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
    │    Frontend     │   │    Backend      │   │   WebSocket     │
    │  (Nginx/React)  │   │   (FastAPI)     │   │   (Optional)    │
    │    Port 80      │   │   Port 8000     │   │   Port 8001     │
    └─────────────────┘   └────────┬────────┘   └─────────────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
              ▼                    ▼                    ▼
    ┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
    │   PostgreSQL    │   │     Redis       │   │  Celery Worker  │
    │   Port 5432     │   │   Port 6379     │   │   (Background)  │
    └─────────────────┘   └─────────────────┘   └─────────────────┘
```

---

## Docker Production Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-org/stratum-ai.git
cd stratum-ai
```

### 2. Create Production Docker Compose

Create `docker-compose.prod.yml`:

```yaml
version: '3.8'

services:
  # =============================================================================
  # PostgreSQL Database
  # =============================================================================
  db:
    image: postgres:15-alpine
    container_name: stratum-db
    restart: always
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backups:/backups
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - stratum-network
    deploy:
      resources:
        limits:
          memory: 4G

  # =============================================================================
  # Redis Cache & Message Broker
  # =============================================================================
  redis:
    image: redis:7-alpine
    container_name: stratum-redis
    restart: always
    command: redis-server --appendonly yes --maxmemory 1gb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - stratum-network
    deploy:
      resources:
        limits:
          memory: 1G

  # =============================================================================
  # Backend API
  # =============================================================================
  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: production
    container_name: stratum-api
    restart: always
    environment:
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      - REDIS_URL=redis://redis:6379/0
      - SECRET_KEY=${SECRET_KEY}
      - ENVIRONMENT=production
      - DEBUG=false
    env_file:
      - .env.production
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - stratum-network
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '2'
      replicas: 2

  # =============================================================================
  # Celery Worker
  # =============================================================================
  worker:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: production
    container_name: stratum-worker
    restart: always
    command: celery -A app.workers.celery_app worker --loglevel=info --concurrency=4
    environment:
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
      - CELERY_RESULT_BACKEND=redis://redis:6379/2
    env_file:
      - .env.production
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - stratum-network
    deploy:
      resources:
        limits:
          memory: 2G

  # =============================================================================
  # Celery Beat Scheduler
  # =============================================================================
  scheduler:
    build:
      context: ./backend
      dockerfile: Dockerfile
      target: production
    container_name: stratum-scheduler
    restart: always
    command: celery -A app.workers.celery_app beat --loglevel=info
    environment:
      - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
    env_file:
      - .env.production
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - stratum-network
    deploy:
      resources:
        limits:
          memory: 512M

  # =============================================================================
  # Frontend (Nginx serving static files)
  # =============================================================================
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      target: production
    container_name: stratum-frontend
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
      - ./certbot/www:/var/www/certbot:ro
    depends_on:
      - api
    networks:
      - stratum-network
    deploy:
      resources:
        limits:
          memory: 512M

volumes:
  postgres_data:
  redis_data:

networks:
  stratum-network:
    driver: bridge
```

### 3. Build and Start Services

```bash
# Build production images
docker compose -f docker-compose.prod.yml build

# Start all services
docker compose -f docker-compose.prod.yml up -d

# Check status
docker compose -f docker-compose.prod.yml ps

# View logs
docker compose -f docker-compose.prod.yml logs -f
```

---

## Environment Configuration

### Create Production Environment File

Create `.env.production`:

```bash
# =============================================================================
# Application Settings
# =============================================================================
ENVIRONMENT=production
DEBUG=false
APP_NAME=Stratum AI
APP_URL=https://your-domain.com
API_URL=https://api.your-domain.com

# =============================================================================
# Security Keys (Generate unique values!)
# =============================================================================
# Generate with: openssl rand -hex 32
SECRET_KEY=your-256-bit-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here
ENCRYPTION_KEY=your-encryption-key-here

# JWT Settings
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# =============================================================================
# Database Configuration
# =============================================================================
POSTGRES_USER=stratum_prod
POSTGRES_PASSWORD=your-strong-password-here
POSTGRES_DB=stratum_production
DATABASE_URL=postgresql+asyncpg://stratum_prod:your-strong-password-here@db:5432/stratum_production

# =============================================================================
# Redis Configuration
# =============================================================================
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# =============================================================================
# Email Configuration (SendGrid Example)
# =============================================================================
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=your-sendgrid-api-key
SMTP_FROM_EMAIL=noreply@your-domain.com
SMTP_FROM_NAME=Stratum AI

# =============================================================================
# Stripe Payment Processing
# =============================================================================
STRIPE_SECRET_KEY=sk_live_your-stripe-secret-key
STRIPE_PUBLISHABLE_KEY=pk_live_your-stripe-publishable-key
STRIPE_WEBHOOK_SECRET=whsec_your-webhook-secret

# =============================================================================
# External Integrations
# =============================================================================
# Google Ads
GOOGLE_ADS_DEVELOPER_TOKEN=your-developer-token
GOOGLE_ADS_CLIENT_ID=your-client-id
GOOGLE_ADS_CLIENT_SECRET=your-client-secret

# Meta (Facebook)
META_APP_ID=your-app-id
META_APP_SECRET=your-app-secret

# TikTok
TIKTOK_APP_ID=your-app-id
TIKTOK_APP_SECRET=your-app-secret

# =============================================================================
# Monitoring & Logging
# =============================================================================
SENTRY_DSN=https://your-sentry-dsn
LOG_LEVEL=INFO

# =============================================================================
# CORS Settings
# =============================================================================
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com
```

### Generate Secure Keys

```bash
# Generate SECRET_KEY
openssl rand -hex 32

# Generate JWT_SECRET_KEY
openssl rand -hex 32

# Generate ENCRYPTION_KEY
openssl rand -hex 32

# Generate strong database password
openssl rand -base64 24
```

---

## Database Setup

### 1. Run Migrations

```bash
# Access the API container
docker compose -f docker-compose.prod.yml exec api bash

# Run migrations
alembic upgrade head

# Verify migration status
alembic current
```

### 2. Create Superadmin User

```bash
# Inside the API container
python -c "
from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash
import asyncio

async def create_superadmin():
    async with SessionLocal() as db:
        user = User(
            email='admin@your-domain.com',
            hashed_password=get_password_hash('your-secure-password'),
            full_name='System Administrator',
            is_active=True,
            is_superuser=True,
            email_verified=True
        )
        db.add(user)
        await db.commit()
        print('Superadmin created successfully')

asyncio.run(create_superadmin())
"
```

### 3. Seed Initial Data (Optional)

```bash
# Run seed scripts
python -m app.scripts.seed_data
```

---

## SSL/HTTPS Configuration

### Option 1: Let's Encrypt with Certbot

```bash
# Install Certbot
apt-get update
apt-get install certbot python3-certbot-nginx

# Obtain certificate
certbot --nginx -d your-domain.com -d www.your-domain.com -d api.your-domain.com

# Auto-renewal (add to crontab)
echo "0 0,12 * * * root certbot renew --quiet" >> /etc/crontab
```

### Option 2: Manual SSL Certificate

```bash
# Create SSL directory
mkdir -p nginx/ssl

# Copy your certificates
cp your-certificate.crt nginx/ssl/certificate.crt
cp your-private-key.key nginx/ssl/private.key
cp your-ca-bundle.crt nginx/ssl/ca-bundle.crt

# Set permissions
chmod 600 nginx/ssl/private.key
```

---

## Reverse Proxy Setup

### Nginx Configuration

Create `nginx/nginx.conf`:

```nginx
upstream api_backend {
    server api:8000;
    keepalive 32;
}

# Rate limiting
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=5r/m;

server {
    listen 80;
    server_name your-domain.com www.your-domain.com api.your-domain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

# Main application
server {
    listen 443 ssl http2;
    server_name your-domain.com www.your-domain.com;

    # SSL Configuration
    ssl_certificate /etc/nginx/ssl/certificate.crt;
    ssl_certificate_key /etc/nginx/ssl/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    # Security Headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 1024;
    gzip_types text/plain text/css text/xml text/javascript application/javascript application/json;

    # Frontend static files
    root /usr/share/nginx/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # API proxy
    location /api {
        limit_req zone=api_limit burst=20 nodelay;

        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        proxy_read_timeout 90s;
    }

    # Auth endpoints (stricter rate limit)
    location /api/v1/auth {
        limit_req zone=auth_limit burst=5 nodelay;

        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Health check
    location /health {
        proxy_pass http://api_backend/health;
        proxy_http_version 1.1;
    }
}

# API subdomain (optional)
server {
    listen 443 ssl http2;
    server_name api.your-domain.com;

    ssl_certificate /etc/nginx/ssl/certificate.crt;
    ssl_certificate_key /etc/nginx/ssl/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;

    location / {
        limit_req zone=api_limit burst=20 nodelay;

        proxy_pass http://api_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Monitoring & Logging

### 1. Prometheus Metrics

The API exposes metrics at `/metrics`. Configure Prometheus:

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'stratum-api'
    static_configs:
      - targets: ['api:8000']
    metrics_path: /metrics
```

### 2. Grafana Dashboard

Import the provided dashboard from `monitoring/grafana/dashboards/stratum.json`.

### 3. Log Aggregation

Configure log drivers in Docker:

```yaml
# In docker-compose.prod.yml
services:
  api:
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "5"
```

### 4. Sentry Error Tracking

Set `SENTRY_DSN` in environment variables for automatic error reporting.

---

## Backup & Recovery

### Automated Database Backups

Create `scripts/backup.sh`:

```bash
#!/bin/bash
set -e

BACKUP_DIR="/backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/stratum_${TIMESTAMP}.sql.gz"

# Create backup
docker compose -f docker-compose.prod.yml exec -T db \
  pg_dump -U ${POSTGRES_USER} ${POSTGRES_DB} | gzip > ${BACKUP_FILE}

# Keep only last 7 days of backups
find ${BACKUP_DIR} -name "stratum_*.sql.gz" -mtime +7 -delete

echo "Backup completed: ${BACKUP_FILE}"
```

### Schedule Daily Backups

```bash
# Add to crontab
0 2 * * * /path/to/scripts/backup.sh >> /var/log/stratum-backup.log 2>&1
```

### Restore from Backup

```bash
# Stop API to prevent writes
docker compose -f docker-compose.prod.yml stop api worker scheduler

# Restore database
gunzip -c /backups/stratum_20260121_020000.sql.gz | \
  docker compose -f docker-compose.prod.yml exec -T db \
  psql -U ${POSTGRES_USER} ${POSTGRES_DB}

# Restart services
docker compose -f docker-compose.prod.yml start api worker scheduler
```

---

## Scaling Strategies

### Horizontal Scaling (Multiple API Instances)

```yaml
# docker-compose.prod.yml
services:
  api:
    deploy:
      replicas: 4
      resources:
        limits:
          memory: 2G
          cpus: '2'
```

### Vertical Scaling (Increase Resources)

```yaml
services:
  db:
    deploy:
      resources:
        limits:
          memory: 8G
          cpus: '4'
```

### External Database

For high-traffic deployments, use managed PostgreSQL:

```bash
# .env.production
DATABASE_URL=postgresql+asyncpg://user:pass@rds-endpoint.amazonaws.com:5432/stratum
```

### Redis Cluster

For high-availability caching:

```bash
REDIS_URL=redis://redis-cluster.amazonaws.com:6379
```

---

## Security Hardening

### 1. Firewall Rules

```bash
# Allow only necessary ports
ufw default deny incoming
ufw default allow outgoing
ufw allow 22/tcp   # SSH
ufw allow 80/tcp   # HTTP (redirect to HTTPS)
ufw allow 443/tcp  # HTTPS
ufw enable
```

### 2. Docker Security

```yaml
# docker-compose.prod.yml security options
services:
  api:
    security_opt:
      - no-new-privileges:true
    read_only: true
    tmpfs:
      - /tmp
```

### 3. Environment Variable Security

- Never commit `.env.production` to version control
- Use secrets management (AWS Secrets Manager, HashiCorp Vault)
- Rotate secrets regularly

### 4. Regular Updates

```bash
# Update base images monthly
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --build
```

---

## Troubleshooting

### Common Issues

#### Container Won't Start

```bash
# Check logs
docker compose -f docker-compose.prod.yml logs api

# Check container status
docker compose -f docker-compose.prod.yml ps
```

#### Database Connection Failed

```bash
# Verify database is running
docker compose -f docker-compose.prod.yml exec db pg_isready

# Check connection from API container
docker compose -f docker-compose.prod.yml exec api \
  python -c "from app.db.session import engine; print('Connected!')"
```

#### High Memory Usage

```bash
# Check container stats
docker stats

# Restart specific service
docker compose -f docker-compose.prod.yml restart api
```

#### Migration Errors

```bash
# Check migration status
docker compose -f docker-compose.prod.yml exec api alembic current

# Downgrade if needed
docker compose -f docker-compose.prod.yml exec api alembic downgrade -1

# Re-run migration
docker compose -f docker-compose.prod.yml exec api alembic upgrade head
```

### Health Checks

```bash
# API health
curl https://your-domain.com/health

# Database health
docker compose -f docker-compose.prod.yml exec db pg_isready

# Redis health
docker compose -f docker-compose.prod.yml exec redis redis-cli ping
```

### Logs Location

| Service | Log Location |
|---------|--------------|
| API | `docker logs stratum-api` |
| Worker | `docker logs stratum-worker` |
| Nginx | `/var/log/nginx/` |
| PostgreSQL | `docker logs stratum-db` |

---

## Deployment Checklist

Before going live, verify:

- [ ] All environment variables configured
- [ ] SSL certificates installed and valid
- [ ] Database migrations completed
- [ ] Superadmin account created
- [ ] CORS origins configured correctly
- [ ] Email sending tested
- [ ] Payment processing tested (Stripe)
- [ ] Backups configured and tested
- [ ] Monitoring dashboards accessible
- [ ] Rate limiting configured
- [ ] Security headers enabled
- [ ] DNS records pointing to server
- [ ] Health checks passing
- [ ] Log rotation configured

---

## Support

For deployment assistance:
- GitHub Issues: https://github.com/your-org/stratum-ai/issues
- Documentation: https://docs.stratum.ai
- Email: support@stratum.ai
