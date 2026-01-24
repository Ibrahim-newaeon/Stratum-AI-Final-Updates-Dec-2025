# Environment Variables Reference

Complete reference for all environment variables used in Stratum AI.

---

## Application Settings

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `APP_NAME` | string | "Stratum AI" | Application name displayed in UI |
| `APP_ENV` | enum | "development" | Environment: `development`, `staging`, `production` |
| `DEBUG` | bool | true | Enable debug mode (detailed errors, docs) |
| `API_V1_PREFIX` | string | "/api/v1" | API route prefix |

### Example
```env
APP_NAME=Stratum AI
APP_ENV=development
DEBUG=true
API_V1_PREFIX=/api/v1
```

---

## Security Settings

### Core Security Keys

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `SECRET_KEY` | string | **Yes** | Main application secret (min 32 chars) |
| `JWT_SECRET_KEY` | string | **Yes** | JWT token signing key (min 32 chars) |
| `PII_ENCRYPTION_KEY` | string | **Yes** | AES key for PII encryption (min 32 chars) |

**Generate Secure Keys:**
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

### JWT Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `JWT_ALGORITHM` | string | "HS256" | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | int | 30 | Access token expiry |
| `REFRESH_TOKEN_EXPIRE_DAYS` | int | 7 | Refresh token expiry |

### Token Expiry

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `EMAIL_VERIFICATION_EXPIRE_HOURS` | int | 24 | Email verification link expiry |
| `PASSWORD_RESET_EXPIRE_HOURS` | int | 1 | Password reset link expiry |

### Example
```env
SECRET_KEY=super-secret-key-at-least-32-characters-long
JWT_SECRET_KEY=jwt-secret-key-at-least-32-characters-long
PII_ENCRYPTION_KEY=pii-encryption-key-32-characters!!
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

---

## Database Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `DATABASE_URL` | string | - | Async PostgreSQL URL (asyncpg) |
| `DATABASE_URL_SYNC` | string | - | Sync PostgreSQL URL (for Alembic) |
| `DB_POOL_SIZE` | int | 10 | Connection pool size |
| `DB_MAX_OVERFLOW` | int | 20 | Max connections above pool |
| `DB_POOL_RECYCLE` | int | 3600 | Connection recycle time (seconds) |

### URL Format
```
postgresql+asyncpg://username:password@host:port/database
postgresql://username:password@host:port/database  # sync version
```

### Example
```env
DATABASE_URL=postgresql+asyncpg://stratum:password@localhost:5432/stratum_ai
DATABASE_URL_SYNC=postgresql://stratum:password@localhost:5432/stratum_ai
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
DB_POOL_RECYCLE=3600
```

---

## Redis Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `REDIS_URL` | string | redis://localhost:6379/0 | Redis connection URL |
| `CELERY_BROKER_URL` | string | redis://localhost:6379/1 | Celery message broker |
| `CELERY_RESULT_BACKEND` | string | redis://localhost:6379/2 | Celery result storage |

### Example
```env
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

---

## Ad Platform Integrations

### Meta (Facebook) Ads

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `META_APP_ID` | string | No | Meta App ID |
| `META_APP_SECRET` | string | No | Meta App Secret |
| `META_ACCESS_TOKEN` | string | No | Long-lived access token |
| `META_API_VERSION` | string | "v19.0" | Graph API version |

### Google Ads

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `GOOGLE_ADS_DEVELOPER_TOKEN` | string | No | Developer token |
| `GOOGLE_ADS_CLIENT_ID` | string | No | OAuth Client ID |
| `GOOGLE_ADS_CLIENT_SECRET` | string | No | OAuth Client Secret |
| `GOOGLE_ADS_REFRESH_TOKEN` | string | No | OAuth refresh token |
| `GOOGLE_ADS_CUSTOMER_ID` | string | No | Manager account ID |

### TikTok Ads

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `TIKTOK_APP_ID` | string | No | TikTok App ID |
| `TIKTOK_APP_SECRET` | string | No | TikTok App Secret |
| `TIKTOK_ACCESS_TOKEN` | string | No | Access token |

### Snapchat Ads

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `SNAPCHAT_CLIENT_ID` | string | No | Snapchat Client ID |
| `SNAPCHAT_CLIENT_SECRET` | string | No | Snapchat Client Secret |
| `SNAPCHAT_ACCESS_TOKEN` | string | No | Access token |

### OAuth Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `OAUTH_REDIRECT_BASE_URL` | string | http://localhost:8000 | Base URL for OAuth callbacks |

### Example
```env
# Meta
META_APP_ID=123456789
META_APP_SECRET=your-app-secret
META_API_VERSION=v19.0

# Google Ads
GOOGLE_ADS_DEVELOPER_TOKEN=your-developer-token
GOOGLE_ADS_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_ADS_CLIENT_SECRET=your-client-secret

# TikTok
TIKTOK_APP_ID=your-app-id
TIKTOK_APP_SECRET=your-app-secret

# OAuth
OAUTH_REDIRECT_BASE_URL=https://api.yourdomain.com
```

---

## WhatsApp Business API

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `WHATSAPP_PHONE_NUMBER_ID` | string | No | WhatsApp Business Phone ID |
| `WHATSAPP_ACCESS_TOKEN` | string | No | API access token |
| `WHATSAPP_BUSINESS_ACCOUNT_ID` | string | No | Business Account ID |
| `WHATSAPP_VERIFY_TOKEN` | string | "stratum-whatsapp-verify-token" | Webhook verification token |
| `WHATSAPP_APP_SECRET` | string | No | App Secret for signature verification |
| `WHATSAPP_API_VERSION` | string | "v18.0" | Meta Graph API version |

### Example
```env
WHATSAPP_PHONE_NUMBER_ID=123456789012345
WHATSAPP_ACCESS_TOKEN=EAABs...long-token
WHATSAPP_BUSINESS_ACCOUNT_ID=987654321012345
WHATSAPP_VERIFY_TOKEN=my-secure-verify-token
WHATSAPP_APP_SECRET=abcd1234...
```

---

## CRM Integrations

### HubSpot

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `HUBSPOT_CLIENT_ID` | string | No | OAuth App Client ID |
| `HUBSPOT_CLIENT_SECRET` | string | No | OAuth App Client Secret |
| `HUBSPOT_API_KEY` | string | No | API Key (legacy) |

### Zoho

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `ZOHO_CLIENT_ID` | string | No | OAuth App Client ID |
| `ZOHO_CLIENT_SECRET` | string | No | OAuth App Client Secret |
| `ZOHO_REGION` | string | "com" | Data center: com, eu, in, com.au, jp, com.cn |

---

## ML & Analytics

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `ML_PROVIDER` | enum | "local" | ML provider: `local`, `vertex` |
| `ML_MODELS_PATH` | string | "./ml_models" | Local models directory |
| `GOOGLE_CLOUD_PROJECT` | string | - | GCP project for Vertex AI |
| `VERTEX_AI_ENDPOINT` | string | - | Vertex AI endpoint URL |
| `GOOGLE_APPLICATION_CREDENTIALS` | string | - | Path to GCP credentials JSON |

### Market Intelligence

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `MARKET_INTEL_PROVIDER` | enum | "mock" | Provider: `mock`, `serpapi`, `dataforseo` |
| `SERPAPI_KEY` | string | - | SerpAPI key |
| `DATAFORSEO_LOGIN` | string | - | DataForSEO login |
| `DATAFORSEO_PASSWORD` | string | - | DataForSEO password |

### Example
```env
ML_PROVIDER=local
ML_MODELS_PATH=./ml_models
MARKET_INTEL_PROVIDER=mock
```

---

## Email Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SMTP_HOST` | string | "smtp.gmail.com" | SMTP server host |
| `SMTP_PORT` | int | 587 | SMTP server port |
| `SMTP_USER` | string | - | SMTP username |
| `SMTP_PASSWORD` | string | - | SMTP password |
| `SMTP_TLS` | bool | true | Use TLS |
| `SMTP_SSL` | bool | false | Use SSL |
| `EMAIL_FROM_NAME` | string | "Stratum AI" | Sender name |
| `EMAIL_FROM_ADDRESS` | string | "noreply@stratum.ai" | Sender email |

### Example
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_TLS=true
EMAIL_FROM_NAME=Stratum AI
EMAIL_FROM_ADDRESS=noreply@yourdomain.com
```

---

## CORS Configuration

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `CORS_ORIGINS` | string | "http://localhost:3000,http://localhost:5173" | Comma-separated allowed origins |
| `CORS_ALLOW_CREDENTIALS` | bool | true | Allow credentials in requests |

### Example
```env
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,https://app.yourdomain.com
CORS_ALLOW_CREDENTIALS=true
```

---

## Stripe Payments

| Variable | Type | Required | Description |
|----------|------|----------|-------------|
| `STRIPE_SECRET_KEY` | string | No | Stripe Secret Key (sk_...) |
| `STRIPE_PUBLISHABLE_KEY` | string | No | Stripe Publishable Key (pk_...) |
| `STRIPE_WEBHOOK_SECRET` | string | No | Webhook signing secret (whsec_...) |
| `STRIPE_STARTER_PRICE_ID` | string | No | Starter tier Price ID |
| `STRIPE_PROFESSIONAL_PRICE_ID` | string | No | Professional tier Price ID |
| `STRIPE_ENTERPRISE_PRICE_ID` | string | No | Enterprise tier Price ID |

### Example
```env
STRIPE_SECRET_KEY=sk_test_your_test_key
STRIPE_PUBLISHABLE_KEY=pk_test_your_publishable_key
STRIPE_WEBHOOK_SECRET=whsec_your_webhook_secret
STRIPE_STARTER_PRICE_ID=price_starter_id
STRIPE_PROFESSIONAL_PRICE_ID=price_professional_id
STRIPE_ENTERPRISE_PRICE_ID=price_enterprise_id
```

---

## Observability

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `LOG_LEVEL` | enum | "INFO" | Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL |
| `LOG_FORMAT` | enum | "json" | Format: `json`, `console` |
| `SENTRY_DSN` | string | - | Sentry DSN for error tracking |

### Example
```env
LOG_LEVEL=INFO
LOG_FORMAT=json
SENTRY_DSN=https://key@sentry.io/project
```

---

## Rate Limiting

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `RATE_LIMIT_PER_MINUTE` | int | 100 | Requests per minute per IP |
| `RATE_LIMIT_BURST` | int | 20 | Burst limit above rate |

---

## Feature Flags

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `FEATURE_COMPETITOR_INTEL` | bool | true | Enable competitor intelligence |
| `FEATURE_WHAT_IF_SIMULATOR` | bool | true | Enable what-if simulator |
| `FEATURE_AUTOMATION_RULES` | bool | true | Enable automation rules |
| `FEATURE_GDPR_COMPLIANCE` | bool | true | Enable GDPR features |

---

## Subscription

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `SUBSCRIPTION_TIER` | enum | "enterprise" | Default tier: `starter`, `professional`, `enterprise` |

---

## Frontend Environment Variables

Frontend uses `VITE_` prefix for environment variables.

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `VITE_API_BASE_URL` | string | http://localhost:8000 | Backend API URL |
| `VITE_WS_URL` | string | ws://localhost:8000 | WebSocket URL |
| `VITE_DEFAULT_LOCALE` | string | "en" | Default language |
| `VITE_SENTRY_DSN` | string | - | Frontend Sentry DSN |

### Example (.env in frontend/)
```env
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_DEFAULT_LOCALE=en
VITE_SENTRY_DSN=https://key@sentry.io/frontend-project
```

---

## Development Defaults

In development mode (`APP_ENV=development`), these fallback values are used if not set:

```python
SECRET_KEY="dev-only-secret-key-do-not-use-in-production-32chars"
JWT_SECRET_KEY="dev-only-jwt-secret-do-not-use-in-production-32"
PII_ENCRYPTION_KEY="dev-only-pii-key-do-not-use-in-prod-32ch"
```

**Warning**: These defaults are NOT secure for production use.

---

## Production Checklist

Before deploying to production, ensure:

- [ ] `APP_ENV=production`
- [ ] `DEBUG=false`
- [ ] All `SECRET_KEY`, `JWT_SECRET_KEY`, `PII_ENCRYPTION_KEY` are unique, random, 32+ characters
- [ ] `DATABASE_URL` uses strong password, not `changeme`
- [ ] `CORS_ORIGINS` only includes your actual domains
- [ ] `SENTRY_DSN` is configured for error tracking
- [ ] All Stripe keys are live keys (not test)
- [ ] SMTP is configured for real email delivery
- [ ] Rate limits are appropriate for expected traffic
