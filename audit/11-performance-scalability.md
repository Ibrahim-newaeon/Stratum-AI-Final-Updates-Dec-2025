# Phase 11 — Performance & Scalability

## 1. Stated Resource Limits (dev compose)

| Service | CPU | Memory |
|---------|-----|--------|
| api | 1.0 | 1G |
| worker | 2.0 | 2G |
| db | 1.0 | 1G |
| redis | 0.5 | 512M |
| frontend | 0.5 | 512M |

Evidence: `docker-compose.yml:188-383`.

## 2. Database Pool

Default 10 + 20 overflow per process (`config.py:64-65`).

**Cannot compute total DB connections without:**
- API worker count (uvicorn `--workers N`)
- Celery concurrency (4 in compose `docker-compose.yml:292`)
- Beat/scheduler processes

**Missing data:** production replica counts — **UNKNOWN**.

## 3. Caching

- Redis: sessions, rate limits, token blacklist, Celery broker
- Redis maxmemory 256mb LRU in compose (`docker-compose.yml:48`)

## 4. ML Inference

- Local scikit-learn models baked in image (`docker-compose.yml:169-173` comments)
- `ML_AUTO_TRAIN=true` default can block startup / OOM on 1G limit if models missing (`docker-compose.yml:172-173`, `config.py:108-114`)
- Load tests set `ML_AUTO_TRAIN=false` (`ci.yml:827`)

## 5. Compression & Payload

GZip middleware min 1000 bytes (`main.py:399`).

## 6. Horizontal Scaling Considerations

| Component | Scale notes |
|-----------|-------------|
| API | Stateless; WebSocket/SSE need sticky sessions or Redis pub/sub (already used for SSE `main.py:835-842`) |
| Celery | Worker count independent; beat must be singleton |
| Postgres | RLS + connection pool budgeting critical |
| Redis | Single instance in compose; prod needs HA for revocation/idempotency |

## 7. Performance Findings

| ID | Sev | Title |
|----|-----|-------|
| — | P2 | ML auto-train on startup risks health-check timeout under 1G memory |
| — | P2 | No CDN/caching strategy documented for API (only asset_s3 config) |

No P0/P1 performance blockers identified from static analysis alone.

## 8. Load Test Evidence

k6 smoke on main (`ci.yml:849-854`) — **pass criteria thresholds in JS file not read in this phase**.

**Search:** file exists at `tests/load/autopilot-enforcement-load-test.js`.

## 9. Positive Controls

- Pool timeout prevents indefinite hang (`config.py:67-69`)
- Redis memory cap with LRU eviction
- GZip for large JSON responses
- Resource limits in compose template
- k6 load smoke on main merges

## 10. Searches Run

```
grep "pool_size|max_overflow" backend/app/core/config.py  → 64-65
grep "ML_AUTO_TRAIN" docker-compose.yml ci.yml            → multiple
grep "GZipMiddleware" backend/app/main.py                 → 399
glob tests/load/*                                         → autopilot-enforcement-load-test.js
```

## 11. Missing Data for Capacity Planning

- Expected RPS, concurrent tenants, CDP event ingest volume: **UNKNOWN**
- p95/p99 latency SLOs: **UNKNOWN**

Without these, cannot recommend instance sizes or validate 1G API limit for production.
