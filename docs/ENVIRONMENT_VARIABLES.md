# Stratum AI - Environment Variables Reference

Complete reference for all environment variables used by Stratum AI.

---

## Table of Contents

1. [Core Application](#core-application)
2. [Database](#database)
3. [Redis & Caching](#redis--caching)
4. [Authentication & Security](#authentication--security)
5. [Email Configuration](#email-configuration)
6. [Payment Processing](#payment-processing)
7. [External Integrations](#external-integrations)
8. [Monitoring & Logging](#monitoring--logging)
9. [Feature Flags](#feature-flags)
10. [Example Files](#example-files)

---

## Core Application

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ENVIRONMENT` | Yes | `development` | Environment mode: `development`, `staging`, `production` |
| `DEBUG` | No | `true` | Enable debug mode (set `false` in production) |
| `APP_NAME` | No | `Stratum AI` | Application display name |
| `APP_URL` | Yes | - | Base URL of the application (e.g., `https://app.stratum.ai`) |
| `API_URL` | Yes | - | Base URL of the API (e.g., `https://api.stratum.ai`) |
| `API_V1_PREFIX` | No | `/api/v1` | API version prefix |
| `WORKERS` | No | `4` | Number of Uvicorn workers |
| `HOST` | No | `0.0.0.0` | Server bind host |
| `PORT` | No | `8000` | Server bind port |

### Example

```bash
ENVIRONMENT=production
DEBUG=false
APP_NAME=Stratum AI
APP_URL=https://app.stratum.ai
API_URL=https://api.stratum.ai
API_V1_PREFIX=/api/v1
WORKERS=4
```

---

## Database

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | - | Full PostgreSQL connection string |
| `POSTGRES_USER` | Yes | - | PostgreSQL username |
| `POSTGRES_PASSWORD` | Yes | - | PostgreSQL password |
| `POSTGRES_DB` | Yes | - | PostgreSQL database name |
| `POSTGRES_HOST` | No | `db` | PostgreSQL host |
| `POSTGRES_PORT` | No | `5432` | PostgreSQL port |
| `DB_POOL_SIZE` | No | `20` | Connection pool size |
| `DB_MAX_OVERFLOW` | No | `10` | Max overflow connections |
| `DB_POOL_RECYCLE` | No | `3600` | Connection recycle time (seconds) |

### Connection String Format

```bash
# Async (recommended)
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/database

# Sync (for migrations)
DATABASE_URL_SYNC=postgresql://user:password@host:5432/database
```

### Example

```bash
POSTGRES_USER=stratum_prod
POSTGRES_PASSWORD=super-secure-password-123
POSTGRES_DB=stratum_production
POSTGRES_HOST=db
POSTGRES_PORT=5432
DATABASE_URL=postgresql+asyncpg://stratum_prod:super-secure-password-123@db:5432/stratum_production
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
```

---

## Redis & Caching

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | Yes | - | Redis connection URL |
| `REDIS_HOST` | No | `redis` | Redis host |
| `REDIS_PORT` | No | `6379` | Redis port |
| `REDIS_PASSWORD` | No | - | Redis password (if auth enabled) |
| `REDIS_DB` | No | `0` | Redis database number |
| `CELERY_BROKER_URL` | Yes | - | Celery message broker URL |
| `CELERY_RESULT_BACKEND` | Yes | - | Celery result backend URL |
| `CACHE_TTL` | No | `3600` | Default cache TTL (seconds) |

### Example

```bash
REDIS_URL=redis://redis:6379/0
REDIS_HOST=redis
REDIS_PORT=6379
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
CACHE_TTL=3600
```

### With Authentication

```bash
REDIS_URL=redis://:your-redis-password@redis:6379/0
REDIS_PASSWORD=your-redis-password
```

---

## Authentication & Security

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes | - | Application secret key (256-bit) |
| `JWT_SECRET_KEY` | Yes | - | JWT signing secret |
| `JWT_ALGORITHM` | No | `HS256` | JWT algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `30` | Access token lifetime |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `7` | Refresh token lifetime |
| `ENCRYPTION_KEY` | Yes | - | Data encryption key |
| `CORS_ORIGINS` | Yes | - | Allowed CORS origins (comma-separated) |
| `ALLOWED_HOSTS` | No | `*` | Allowed host headers |

### Generating Secure Keys

```bash
# Generate SECRET_KEY (256-bit hex)
openssl rand -hex 32

# Generate JWT_SECRET_KEY
openssl rand -hex 32

# Generate ENCRYPTION_KEY (for Fernet)
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

### Example

```bash
SECRET_KEY=a1b2c3d4e5f6789012345678901234567890abcdef1234567890abcdef123456
JWT_SECRET_KEY=f6e5d4c3b2a1098765432109876543210987654321fedcba0987654321fedcba
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
ENCRYPTION_KEY=your-fernet-encryption-key
CORS_ORIGINS=https://app.stratum.ai,https://www.stratum.ai
ALLOWED_HOSTS=app.stratum.ai,api.stratum.ai
```

---

## Email Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SMTP_HOST` | Yes | - | SMTP server hostname |
| `SMTP_PORT` | No | `587` | SMTP server port |
| `SMTP_USER` | Yes | - | SMTP username |
| `SMTP_PASSWORD` | Yes | - | SMTP password or API key |
| `SMTP_FROM_EMAIL` | Yes | - | Default sender email |
| `SMTP_FROM_NAME` | No | `Stratum AI` | Default sender name |
| `SMTP_TLS` | No | `true` | Enable TLS |
| `SMTP_SSL` | No | `false` | Enable SSL |

### SendGrid Configuration

```bash
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=SG.your-sendgrid-api-key
SMTP_FROM_EMAIL=noreply@stratum.ai
SMTP_FROM_NAME=Stratum AI
SMTP_TLS=true
```

### AWS SES Configuration

```bash
SMTP_HOST=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USER=your-ses-smtp-username
SMTP_PASSWORD=your-ses-smtp-password
SMTP_FROM_EMAIL=noreply@stratum.ai
SMTP_FROM_NAME=Stratum AI
SMTP_TLS=true
```

### Gmail Configuration (Development Only)

```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_TLS=true
```

---

## Payment Processing

### Stripe

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `STRIPE_SECRET_KEY` | Yes | - | Stripe secret API key |
| `STRIPE_PUBLISHABLE_KEY` | Yes | - | Stripe publishable key |
| `STRIPE_WEBHOOK_SECRET` | Yes | - | Stripe webhook signing secret |
| `STRIPE_PRICE_STARTER` | No | - | Stripe Price ID for Starter plan |
| `STRIPE_PRICE_PROFESSIONAL` | No | - | Stripe Price ID for Professional plan |
| `STRIPE_PRICE_ENTERPRISE` | No | - | Stripe Price ID for Enterprise plan |

### Example

```bash
# Test keys (development)
STRIPE_SECRET_KEY=sk_test_your-test-secret-key
STRIPE_PUBLISHABLE_KEY=pk_test_your-test-publishable-key
STRIPE_WEBHOOK_SECRET=whsec_your-test-webhook-secret

# Live keys (production)
STRIPE_SECRET_KEY=sk_live_your-live-secret-key
STRIPE_PUBLISHABLE_KEY=pk_live_your-live-publishable-key
STRIPE_WEBHOOK_SECRET=whsec_your-live-webhook-secret

# Price IDs
STRIPE_PRICE_STARTER=price_1234567890abcdef
STRIPE_PRICE_PROFESSIONAL=price_0987654321fedcba
STRIPE_PRICE_ENTERPRISE=price_abcdef1234567890
```

---

## External Integrations

### Google Ads

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_ADS_DEVELOPER_TOKEN` | Yes | - | Google Ads developer token |
| `GOOGLE_ADS_CLIENT_ID` | Yes | - | OAuth client ID |
| `GOOGLE_ADS_CLIENT_SECRET` | Yes | - | OAuth client secret |
| `GOOGLE_ADS_REFRESH_TOKEN` | No | - | OAuth refresh token |
| `GOOGLE_ADS_LOGIN_CUSTOMER_ID` | No | - | Manager account ID |

### Meta (Facebook/Instagram)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `META_APP_ID` | Yes | - | Meta app ID |
| `META_APP_SECRET` | Yes | - | Meta app secret |
| `META_ACCESS_TOKEN` | No | - | System user access token |
| `META_PIXEL_ID` | No | - | Default Pixel ID |

### TikTok Ads

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TIKTOK_APP_ID` | Yes | - | TikTok app ID |
| `TIKTOK_APP_SECRET` | Yes | - | TikTok app secret |
| `TIKTOK_ACCESS_TOKEN` | No | - | Long-lived access token |

### Snapchat Ads

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SNAPCHAT_CLIENT_ID` | Yes | - | Snapchat OAuth client ID |
| `SNAPCHAT_CLIENT_SECRET` | Yes | - | Snapchat OAuth client secret |
| `SNAPCHAT_REDIRECT_URI` | Yes | - | OAuth redirect URI |

### Example

```bash
# Google Ads
GOOGLE_ADS_DEVELOPER_TOKEN=your-developer-token
GOOGLE_ADS_CLIENT_ID=123456789.apps.googleusercontent.com
GOOGLE_ADS_CLIENT_SECRET=your-client-secret

# Meta
META_APP_ID=1234567890123456
META_APP_SECRET=abcdef123456789abcdef123456789ab

# TikTok
TIKTOK_APP_ID=7123456789012345678
TIKTOK_APP_SECRET=abcdef123456789abcdef123456789ab

# Snapchat
SNAPCHAT_CLIENT_ID=your-client-id
SNAPCHAT_CLIENT_SECRET=your-client-secret
SNAPCHAT_REDIRECT_URI=https://app.stratum.ai/auth/snapchat/callback
```

---

## Monitoring & Logging

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LOG_LEVEL` | No | `INFO` | Logging level: DEBUG, INFO, WARNING, ERROR |
| `LOG_FORMAT` | No | `json` | Log format: `json` or `text` |
| `SENTRY_DSN` | No | - | Sentry DSN for error tracking |
| `SENTRY_ENVIRONMENT` | No | - | Sentry environment tag |
| `PROMETHEUS_ENABLED` | No | `true` | Enable Prometheus metrics |
| `PROMETHEUS_PORT` | No | `9090` | Prometheus metrics port |

### Example

```bash
LOG_LEVEL=INFO
LOG_FORMAT=json
SENTRY_DSN=https://abc123@o123456.ingest.sentry.io/1234567
SENTRY_ENVIRONMENT=production
PROMETHEUS_ENABLED=true
```

---

## Feature Flags

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `FEATURE_CDP_ENABLED` | No | `true` | Enable CDP features |
| `FEATURE_AUDIENCE_SYNC_ENABLED` | No | `true` | Enable audience sync |
| `FEATURE_MFA_ENABLED` | No | `true` | Enable two-factor auth |
| `FEATURE_WEBHOOKS_ENABLED` | No | `true` | Enable webhook system |
| `FEATURE_API_RATE_LIMITING` | No | `true` | Enable API rate limiting |

### Example

```bash
FEATURE_CDP_ENABLED=true
FEATURE_AUDIENCE_SYNC_ENABLED=true
FEATURE_MFA_ENABLED=true
FEATURE_WEBHOOKS_ENABLED=true
FEATURE_API_RATE_LIMITING=true
```

---

## Example Files

### Development (.env.development)

```bash
# =============================================================================
# Stratum AI - Development Environment
# =============================================================================

# Application
ENVIRONMENT=development
DEBUG=true
APP_NAME=Stratum AI (Dev)
APP_URL=http://localhost:5173
API_URL=http://localhost:8000

# Database
POSTGRES_USER=stratum_dev
POSTGRES_PASSWORD=devpassword123
POSTGRES_DB=stratum_dev
DATABASE_URL=postgresql+asyncpg://stratum_dev:devpassword123@localhost:5432/stratum_dev

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# Security (development keys - DO NOT use in production)
SECRET_KEY=dev-secret-key-not-for-production-use-only-for-development
JWT_SECRET_KEY=dev-jwt-secret-key-not-for-production-use-only-for-dev
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30
CORS_ORIGINS=http://localhost:5173,http://localhost:3000

# Email (use Mailhog for development)
SMTP_HOST=localhost
SMTP_PORT=1025
SMTP_USER=
SMTP_PASSWORD=
SMTP_FROM_EMAIL=dev@localhost
SMTP_TLS=false

# Stripe (test keys)
STRIPE_SECRET_KEY=sk_test_your-test-key
STRIPE_PUBLISHABLE_KEY=pk_test_your-test-key
STRIPE_WEBHOOK_SECRET=whsec_test-webhook-secret

# Logging
LOG_LEVEL=DEBUG
LOG_FORMAT=text
```

### Production (.env.production)

```bash
# =============================================================================
# Stratum AI - Production Environment
# =============================================================================

# Application
ENVIRONMENT=production
DEBUG=false
APP_NAME=Stratum AI
APP_URL=https://app.stratum.ai
API_URL=https://api.stratum.ai

# Database
POSTGRES_USER=stratum_prod
POSTGRES_PASSWORD=CHANGE_THIS_TO_SECURE_PASSWORD
POSTGRES_DB=stratum_production
DATABASE_URL=postgresql+asyncpg://stratum_prod:CHANGE_THIS_TO_SECURE_PASSWORD@db:5432/stratum_production
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# Security (generate with: openssl rand -hex 32)
SECRET_KEY=GENERATE_NEW_256_BIT_KEY
JWT_SECRET_KEY=GENERATE_NEW_256_BIT_KEY
ENCRYPTION_KEY=GENERATE_FERNET_KEY
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
CORS_ORIGINS=https://app.stratum.ai,https://www.stratum.ai

# Email
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=SENDGRID_API_KEY
SMTP_FROM_EMAIL=noreply@stratum.ai
SMTP_FROM_NAME=Stratum AI
SMTP_TLS=true

# Stripe (live keys)
STRIPE_SECRET_KEY=sk_live_YOUR_LIVE_KEY
STRIPE_PUBLISHABLE_KEY=pk_live_YOUR_LIVE_KEY
STRIPE_WEBHOOK_SECRET=whsec_YOUR_WEBHOOK_SECRET

# External Integrations
GOOGLE_ADS_DEVELOPER_TOKEN=YOUR_TOKEN
GOOGLE_ADS_CLIENT_ID=YOUR_CLIENT_ID
GOOGLE_ADS_CLIENT_SECRET=YOUR_CLIENT_SECRET
META_APP_ID=YOUR_APP_ID
META_APP_SECRET=YOUR_APP_SECRET
TIKTOK_APP_ID=YOUR_APP_ID
TIKTOK_APP_SECRET=YOUR_APP_SECRET

# Monitoring
LOG_LEVEL=INFO
LOG_FORMAT=json
SENTRY_DSN=https://your-sentry-dsn
SENTRY_ENVIRONMENT=production
PROMETHEUS_ENABLED=true

# Feature Flags
FEATURE_CDP_ENABLED=true
FEATURE_AUDIENCE_SYNC_ENABLED=true
FEATURE_MFA_ENABLED=true
FEATURE_WEBHOOKS_ENABLED=true
FEATURE_API_RATE_LIMITING=true
```

---

## Security Best Practices

1. **Never commit `.env` files** to version control
2. **Use secrets management** (AWS Secrets Manager, HashiCorp Vault) in production
3. **Rotate secrets regularly** (at least quarterly)
4. **Use different keys** for each environment
5. **Restrict access** to environment files
6. **Audit access** to secrets
7. **Use strong passwords** (minimum 24 characters for databases)
