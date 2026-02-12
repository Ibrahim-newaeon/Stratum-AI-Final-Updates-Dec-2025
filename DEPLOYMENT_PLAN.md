# Stratum AI - Deployment Plan

## Current State

### Codebase Status: READY FOR DEPLOYMENT
All frontend polishing is complete. The codebase is production-ready.

### Domain: `stratumai.app` (owned)
- `stratumai.app` → Frontend (React app)
- `api.stratumai.app` → Backend (FastAPI)

### Recent Updates (Feb 2026)
- Landing page CSS bugs, dead JS, and broken links fixed
- CDP section width tightened
- Environment variables standardized, keyframe names fixed, dead API client removed
- All buttons standardized to `rounded-lg` (8px) with hover color changes
- Platform logos now show native brand colors (removed grayscale override)
- Knowledge Graph section aligned (graph stretches full height alongside features)
- CDP Carousel (5 interactive slides) with autoplay
- Login & Signup pages themed to match landing page
- WhatsNew modal centered on all screen sizes
- Main index.html with HoloGlass theme

### Repository
- **GitHub**: https://github.com/Ibrahim-newaeon/Stratum-AI-Final-Updates-Dec-2025
- **Main Branch**: `main` (all latest code)
- **GitHub Pages Branch**: `gh-pages` (synced Feb 12, 2026)

---

## COMPLETED

### GitHub Pages (Landing Page)
- **Status**: LIVE
- **URL**: https://ibrahim-newaeon.github.io/Stratum-AI-Final-Updates-Dec-2025/
- **Branch**: `gh-pages` (synced with latest main)
- **Cost**: FREE

---

## Railway Full Stack Deployment (FASTEST)

### Step 1: Create Project on Railway (2 min)
1. Go to https://railway.app and sign in with GitHub
2. Click **New Project** > **Deploy from GitHub Repo**
3. Select: `Ibrahim-newaeon/Stratum-AI-Final-Updates-Dec-2025`

### Step 2: Add Database & Cache (2 min)
1. Click **+ New** > **Database** > **PostgreSQL** (add to project)
2. Click **+ New** > **Database** > **Redis** (add to project)
3. Railway auto-provisions both and provides connection URLs

### Step 3: Configure Backend Service (3 min)
1. Add a service from the repo, set **Root Directory**: `backend`
2. Railway will use `backend/Dockerfile` automatically
3. Add these environment variables:

```env
# App Settings
APP_ENV=production
APP_NAME=stratum-ai
APP_VERSION=1.0.0
DEBUG=false

# Security Keys (from your stratum-ai.env file)
SECRET_KEY=<copy from stratum-ai.env>
JWT_SECRET_KEY=<copy from stratum-ai.env>
PII_ENCRYPTION_KEY=<copy from stratum-ai.env>

# Database (use Railway reference variables)
DATABASE_URL=${{Postgres.DATABASE_URL}}
DATABASE_URL_SYNC=${{Postgres.DATABASE_URL}}
POSTGRES_USER=${{Postgres.PGUSER}}
POSTGRES_PASSWORD=${{Postgres.PGPASSWORD}}
POSTGRES_DB=${{Postgres.PGDATABASE}}

# Redis (use Railway reference variables)
REDIS_URL=${{Redis.REDIS_URL}}
CELERY_BROKER_URL=${{Redis.REDIS_URL}}
CELERY_RESULT_BACKEND=${{Redis.REDIS_URL}}

# CORS & Frontend
CORS_ORIGINS=https://stratumai.app

# Ad Platforms - Meta
USE_MOCK_AD_DATA=false
META_APP_ID=<copy from stratum-ai.env>
META_APP_SECRET=<copy from stratum-ai.env>
META_ACCESS_TOKEN=<copy from stratum-ai.env>
META_AD_ACCOUNT_IDS=<copy from stratum-ai.env>
META_CAPI_ACCESS_TOKEN=<copy from stratum-ai.env>
META_PIXEL_ID=<copy from stratum-ai.env>

# Ad Platforms - Google
GOOGLE_ADS_DEVELOPER_TOKEN=<copy from stratum-ai.env>
GOOGLE_ADS_CLIENT_ID=<copy from stratum-ai.env>
GOOGLE_ADS_CLIENT_SECRET=<copy from stratum-ai.env>
GOOGLE_ADS_REFRESH_TOKEN=<copy from stratum-ai.env>
GOOGLE_ADS_ACCESS_TOKEN=<copy from stratum-ai.env>
GOOGLE_ADS_CUSTOMER_ID=<copy from stratum-ai.env>
GOOGLE_ADS_MCC_ID=<copy from stratum-ai.env>

# Ad Platforms - TikTok
TIKTOK_APP_ID=<copy from stratum-ai.env>
TIKTOK_ACCESS_TOKEN=<copy from stratum-ai.env>
TIKTOK_AD_ACCOUNT_ID=<copy from stratum-ai.env>
TIKTOK_ADVERTISER_ID=<copy from stratum-ai.env>
TIKTOK_PIXEL_ID=<copy from stratum-ai.env>
TIKTOK_CAPI_TOKEN=<copy from stratum-ai.env>

# Ad Platforms - Snapchat
SNAPCHAT_APP_ID=<copy from stratum-ai.env>
SNAPCHAT_SECRET=<copy from stratum-ai.env>
SNAPCHAT_CAPI_TOKEN=<copy from stratum-ai.env>
SNAPCHAT_AD_ACCOUNT_ID=<copy from stratum-ai.env>
SNAPCHAT_PIXEL_ID=<copy from stratum-ai.env>

# Google Analytics / GTM
MIDAS_GTM_SERVER_CONTAINER=<copy from stratum-ai.env>
MIDAS_GTM_WEB_CONTAINER=<copy from stratum-ai.env>
MIDAS_GA4_MEASUREMENT_ID=<copy from stratum-ai.env>
MIDAS_GA4_TAG_ID=<copy from stratum-ai.env>
MIDAS_GOOGLE_ADS_ID=<copy from stratum-ai.env>

# Subscription & Gateway
SUBSCRIPTION_TIER=starter
GATEWAY_API_KEY=<copy from stratum-ai.env>

# ML
ML_PROVIDER=local
MARKET_INTEL_PROVIDER=mock

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

**Note:** Railway reference variables like `${{Postgres.DATABASE_URL}}` auto-fill from the PostgreSQL service you added. No need to hardcode DB credentials.

### Step 4: Configure Frontend Service (2 min)
1. Add another service from the same repo, set **Root Directory**: `frontend`
2. Railway will use `frontend/Dockerfile` automatically
3. Add this environment variable:

```env
VITE_API_BASE_URL=https://api.stratumai.app/api/v1
```

### Step 5: Add Custom Domain (3 min)
1. In Railway, click on the **Frontend** service > **Settings** > **Networking** > **Custom Domain**
   - Add: `stratumai.app`
   - Railway gives you a CNAME target (e.g., `xxx.up.railway.app`)

2. Click on the **Backend** service > **Settings** > **Networking** > **Custom Domain**
   - Add: `api.stratumai.app`
   - Railway gives you a CNAME target

3. Go to your domain registrar (where you bought stratumai.app) and add DNS records:

```
Type    Name    Value                           TTL
CNAME   @       <railway-frontend-target>       300
CNAME   api     <railway-backend-target>        300
```

If your registrar doesn't support CNAME on root (`@`), use:
```
Type    Name    Value                           TTL
A       @       <railway-provided-IP>           300
CNAME   api     <railway-backend-target>        300
```

Railway provides SSL/HTTPS automatically once DNS propagates.

### Step 6: Run Database Migrations (2 min)
Open the **Backend** service terminal in Railway dashboard:

```bash
alembic upgrade head
python scripts/seed_superadmin.py
```

### Step 7: Verify (2 min)
```
https://api.stratumai.app/health        → Should return OK
https://stratumai.app                    → Should load the React app
https://stratumai.app/login              → Should show login page
```

---

## Total Time: ~15 minutes

| Step | Action | Time |
|------|--------|------|
| 1 | Create Railway project | 2 min |
| 2 | Add PostgreSQL + Redis | 2 min |
| 3 | Configure backend + env vars | 3 min |
| 4 | Configure frontend | 2 min |
| 5 | Custom domain + DNS | 3 min |
| 6 | Run migrations | 2 min |
| 7 | Verify everything works | 1 min |
| **Total** | | **~15 min** |

**Cost:** $5-20/month (Railway usage-based pricing)

---

## Environment File Reference

All production values are stored in:
```
C:\Users\Vip\OneDrive\Desktop\stratum-ai.env
```
This file contains all real API keys and credentials. Copy values from there into Railway's environment variable settings. **Never commit this file to git.**

---

## Docker Architecture on Railway

```
        stratumai.app              api.stratumai.app
             |                            |
      +------+------+             +------+------+
      |  Frontend   |             |   Backend   |
      | (Nginx+React|             |  (FastAPI)  |
      |  Port 80)   |             |  Port 8000) |
      +-------------+             +------+------+
                                         |
                          +--------------++--------------+
                          |               |              |
                   +------+------+ +------+------+ +-----+-------+
                   | PostgreSQL  | |    Redis    | |   Celery    |
                   |   (Railway) | |  (Railway)  | |   Worker    |
                   +-------------+ +-------------+ +-------------+
```

---

## Post-Deployment Checklist

### Services
- [ ] `https://api.stratumai.app/health` returns OK
- [ ] `https://stratumai.app` loads React app
- [ ] Landing page (iframe) displays correctly
- [ ] Login/signup works
- [ ] Dashboard loads after login

### Features
- [ ] CDP profiles, segments, events pages load
- [ ] Knowledge Graph visualization renders
- [ ] Audience Sync shows platform connections
- [ ] Trust Engine dashboard shows signal health
- [ ] Campaign management works
- [ ] Ad platform data pulls from Meta, Google, TikTok, Snapchat

### Security
- [ ] HTTPS/SSL active (Railway auto-provisions)
- [ ] CORS restricted to `https://stratumai.app` only
- [ ] No credentials in version control
- [ ] Rate limiting active on auth endpoints
- [ ] PII encryption key set

---

## URLs

| Environment | URL | Status |
|-------------|-----|--------|
| Landing (GitHub Pages) | https://ibrahim-newaeon.github.io/Stratum-AI-Final-Updates-Dec-2025/ | LIVE |
| Frontend (Production) | https://stratumai.app | Pending Railway deploy |
| Backend API (Production) | https://api.stratumai.app | Pending Railway deploy |
| API Health Check | https://api.stratumai.app/health | Pending Railway deploy |

---

**Last Updated:** 2026-02-12
**Status:** Landing page LIVE, full stack ready to deploy on Railway
