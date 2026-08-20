# Phase 8 — Infrastructure & DevOps

## 1. Compose Variants

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Local dev (bind mounts, mock data default true) |
| `docker-compose.prod.yml` | Production overrides (`USE_MOCK_AD_DATA=false`) |
| `docker-compose.staging.yml` | Staging |
| `docker-compose.hetzner.yml` | Hetzner-specific |
| `docker-compose.observability.yml` | Observability stack |
| `docker-compose.monitoring.yml` | Monitoring profile |

CI validates: `docker-compose.yml + docker-compose.prod.yml` and `+ hetzner.yml` (`ci.yml:710-716`).

## 2. Container Hardening (dev compose)

```80:82:docker-compose.yml
    user: "1000:1000"
    security_opt:
      - no-new-privileges:true
```

Resource limits on all services (e.g. api 1 CPU / 1G `docker-compose.yml:188-191`).

Redis requires password (`docker-compose.yml:48`).

## 3. CI/CD Pipeline

Release gate jobs (`ci.yml:732-755`):
- backend-quality, backend-tests, backend-security, frontend, security, secrets, deploy-config

**Not gated:** e2e (`ci.yml:479-517` vs `732` needs list)

Node version split:
- CI: `NODE_VERSION: "24"` (`ci.yml:42`)
- Dockerfile: `node:26-alpine` (`frontend/Dockerfile:6,28`)

Documented in CI comments as intentional until storage regression resolved (`ci.yml:18-41`).

Python: CI 3.12 matches backend Dockerfile (assumed — verify in `backend/Dockerfile`).

## 4. Deployment Targets

| Target | Evidence |
|--------|----------|
| Docker / Hetzner | `docker-compose.hetzner.yml`, nginx configs |
| Railway | Comments in compose + config (DB URL, asset paths) |
| Vercel | `vercel.json` at repo root |

**UNKNOWN — not present in available evidence:** active production URL, deploy frequency, blue/green strategy.

## 5. Backup & DR

**Search:** `glob scripts/backup/*.sh` — referenced in CI shell syntax (`ci.yml:722-724`).

Backup scripts exist but **no scheduled backup service** in default `docker-compose.yml`.

**UNKNOWN — not present in available evidence:** RPO/RTO targets, restore drill results.

## 6. Infra Findings

| ID | Sev | Title |
|----|-----|-------|
| F-004 | P1 | Dev compose USE_MOCK_AD_DATA=true default |
| F-005 | P2 | Node 24 (CI) vs 26 (Dockerfile) mismatch |
| F-006 | P2 | E2E excluded from release gate |
| F-012 | P2 | Local asset storage default; bind mounts in dev |

## 7. Deploy Config Validation (Positive)

CI runs:
- `nginx -t` with throwaway TLS certs (`ci.yml:660-692`)
- Cloudflare IP range freshness check (`ci.yml:698-700`, continue-on-error)
- `docker compose config` with `.env.hetzner.template` placeholders (`ci.yml:702-717`)
- Shell syntax all `scripts/*.sh` (`ci.yml:719-724`)

## 8. Docker Publish

`.github/workflows/docker.yml` — separate workflow (not fully read; present in repo).

Dependabot: `.github/dependabot.yml`.

## 9. Proposed Fixes (DO NOT APPLY)

1. Add `e2e` to release gate `needs:` once stable against built artifact
2. Align Node 24 across Dockerfile or fix Node 26 jsdom storage issue per CI comments
3. Add backup cron sidecar or document managed-DB PITR for production

## 10. Searches Run

```
glob docker-compose*.yml           → 11 files
glob scripts/backup/*              → present (CI reference)
read docker-compose.prod.yml USE_MOCK lines 75,136,188
read ci.yml gate job 729-755
read frontend/Dockerfile line 6
```
