# Stratum AI - Deployment Plan

## Current State

### Codebase Status: READY FOR DEPLOYMENT
All frontend polishing is complete. The codebase is production-ready.

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
- **GitHub Pages Branch**: `gh-pages` (OUTDATED - needs re-sync, see Action Items)

---

## IMMEDIATE ACTION ITEMS

### 1. Re-sync GitHub Pages Landing Page
The `gh-pages` branch is behind `main` and missing all recent fixes (buttons, logos, KG alignment).

```bash
# Switch to gh-pages branch
git checkout gh-pages

# Copy latest landing.html as index.html
git checkout main -- frontend/public/landing.html
cp frontend/public/landing.html index.html

# Commit and push
git add index.html
git commit -m "sync: update landing page with latest fixes"
git push origin gh-pages

# Switch back to main
git checkout main
```

### 2. Enable GitHub Pages (if not already done)
- Go to: https://github.com/Ibrahim-newaeon/Stratum-AI-Final-Updates-Dec-2025/settings/pages
- Source: Deploy from a branch
- Branch: `gh-pages` / `/ (root)`
- Save

---

## Deployment Options

### Option 1: Railway (Full Stack) - RECOMMENDED

**Best for:** Complete production deployment with all services.

**What gets deployed:**
- Frontend (React + Vite, served via Nginx)
- Backend (FastAPI + Python 3.14)
- PostgreSQL 16 Database
- Redis 7 Cache/Broker
- Celery Worker + Beat Scheduler

**Steps:**
1. Go to https://railway.app and sign in with GitHub
2. New Project > Deploy from GitHub Repo
3. Select: `Ibrahim-newaeon/Stratum-AI-Final-Updates-Dec-2025`
4. Railway detects `docker-compose.yml` - add services:
   - **PostgreSQL** - Add from Railway marketplace
   - **Redis** - Add from Railway marketplace
   - **API** - From `backend/` directory
   - **Frontend** - From `frontend/` directory
5. Set environment variables (see Environment Variables section below)
6. Deploy all services

**Post-Deploy:**
```bash
# Run database migrations
railway run --service api alembic upgrade head

# Create superadmin user
railway run --service api python scripts/seed_superadmin.py
```

**Cost:** $5-20/month (usage-based)
**Time:** 10-15 minutes

---

### Option 2: Vercel (Frontend) + Render (Backend)

**Best for:** Free-tier frontend hosting with separated backend.

**Frontend on Vercel:**
```bash
cd frontend
npx vercel
```
- Project name: `stratum-ai`
- Framework: Vite
- Build command: `npm run build`
- Output directory: `dist`
- Environment variable: `VITE_API_URL=https://stratum-api.onrender.com/api/v1`
- Deploy: `npx vercel --prod`

**Backend on Render:**
1. Go to https://render.com > New > Web Service
2. Connect GitHub repo
3. Settings:
   - Root Directory: `backend`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. Add PostgreSQL (Render Starter: $7/month)
5. Add Redis (Render Starter: $0-7/month)
6. Set environment variables (see below)

**Cost:** Vercel FREE + Render $14-21/month
**Time:** 15-20 minutes

---

### Option 3: GitHub Pages (Landing Page Only) - DONE

**Status:** Deployed (needs re-sync with latest fixes)
**URL:** https://ibrahim-newaeon.github.io/Stratum-AI-Final-Updates-Dec-2025/
**Branch:** `gh-pages`
**What's deployed:** Static landing page only (no React app, no backend)
**Cost:** FREE

---

## Environment Variables

### Required for Production
```env
# Application
APP_ENV=production
DEBUG=false
SECRET_KEY=<openssl rand -hex 32>
JWT_SECRET_KEY=<openssl rand -hex 32>
PII_ENCRYPTION_KEY=<openssl rand -base64 32>
CORS_ORIGINS=https://your-frontend-domain.com

# Database (provided by Railway/Render)
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/stratum_ai
DATABASE_URL_SYNC=postgresql://user:pass@host:5432/stratum_ai

# Redis (provided by Railway/Render)
REDIS_URL=redis://host:6379/0
CELERY_BROKER_URL=redis://host:6379/1

# ML / Mock Data (start with mock, switch to real later)
ML_PROVIDER=local
USE_MOCK_AD_DATA=true
MARKET_INTEL_PROVIDER=mock

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
```

### Optional Integrations (add when ready)
```env
# Stripe Payments
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Email (SendGrid)
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=<sendgrid-api-key>
SMTP_FROM_EMAIL=noreply@stratum.ai

# Ad Platform OAuth (for production audience sync)
META_APP_ID=<your-app-id>
META_APP_SECRET=<your-app-secret>
GOOGLE_CLIENT_ID=<your-client-id>
GOOGLE_CLIENT_SECRET=<your-client-secret>
TIKTOK_APP_ID=<your-app-id>
TIKTOK_APP_SECRET=<your-app-secret>

# Error Tracking
SENTRY_DSN=<your-sentry-dsn>

# Slack Alerts
SLACK_WEBHOOK_URL=<your-webhook-url>
SLACK_CHANNEL=#stratum-alerts
```

### Frontend Environment Variable
```env
# Set this on Vercel or in frontend/.env.production
VITE_API_URL=https://your-api-domain.com/api/v1
```

---

## Docker Architecture

```
                    Load Balancer / Nginx
                         |
              +----------+----------+
              |                     |
        Frontend:80          API:8000
        (Nginx+React)       (FastAPI)
                                |
              +---------+-------+---------+
              |         |                 |
         PostgreSQL   Redis      Celery Worker
           :5432      :6379      + Beat Scheduler
```

**Docker files available:**
- `docker-compose.yml` - Development (all services)
- `docker-compose.prod.yml` - Production (resource limits, replicas)
- `docker-compose.dev.yml` - Dev overrides
- `docker-compose.monitoring.yml` - Prometheus + Grafana
- `backend/Dockerfile` - Python 3.14, non-root user, healthcheck
- `frontend/Dockerfile` - Multi-stage build (dev/build/production), ~25MB final image

---

## Post-Deployment Checklist

### Verify Services
- [ ] Frontend loads at the public URL
- [ ] Landing page (iframe) displays correctly
- [ ] API health check passes: `GET /health`
- [ ] Login/signup works
- [ ] Dashboard loads after login

### Verify Features
- [ ] CDP profiles, segments, events pages load
- [ ] Knowledge Graph visualization renders
- [ ] Audience Sync shows platform connections
- [ ] Trust Engine dashboard shows signal health
- [ ] Campaign management works

### Security
- [ ] HTTPS/SSL configured
- [ ] CORS restricted to frontend domain only
- [ ] No credentials in version control
- [ ] Rate limiting active on auth endpoints
- [ ] PII encryption key set

---

## Recommended Strategy

| Goal | Option | Cost | Time |
|------|--------|------|------|
| Quick demo / portfolio | GitHub Pages (landing) | FREE | Done |
| Full app demo | Railway (all-in-one) | $5-20/mo | 15 min |
| Production split | Vercel + Render | $14-21/mo | 20 min |
| Enterprise | Docker + AWS/GCP | $50+/mo | 1-2 hrs |

**Recommended path:**
1. Re-sync GitHub Pages landing (5 min)
2. Deploy full stack on Railway for live demo (15 min)
3. Migrate to Vercel + Render when ready for custom domain

---

## URLs

| Environment | URL | Status |
|-------------|-----|--------|
| Landing (GitHub Pages) | https://ibrahim-newaeon.github.io/Stratum-AI-Final-Updates-Dec-2025/ | Deployed (needs re-sync) |
| Full Stack (Railway) | TBD | Not yet deployed |
| Frontend (Vercel) | TBD | Not yet deployed |
| Backend (Render) | TBD | Not yet deployed |

---

**Last Updated:** 2026-02-12
**Status:** Landing page deployed (outdated), full stack pending deployment
