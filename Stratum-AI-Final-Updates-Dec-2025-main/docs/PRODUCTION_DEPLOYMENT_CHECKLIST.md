# Stratum AI - Production Deployment Checklist

## Pre-Deployment Validation

### 1. Security Configuration
- [ ] `APP_ENV=production` is set
- [ ] `SECRET_KEY` is a strong 32+ character random string
- [ ] `JWT_SECRET_KEY` is a strong 32+ character random string
- [ ] `PII_ENCRYPTION_KEY` is a valid 32-byte base64-encoded key
- [ ] `DATABASE_URL` uses SSL (`?sslmode=require`)
- [ ] No hardcoded credentials in codebase
- [ ] CORS origins are properly restricted
- [ ] Rate limiting is enabled and configured

### 2. Database
- [ ] PostgreSQL 15+ is running with SSL enabled
- [ ] Database user has minimum required permissions
- [ ] Connection pooling is configured (PgBouncer recommended)
- [ ] All migrations have been applied (`alembic upgrade head`)
- [ ] Database backups are configured
- [ ] Point-in-time recovery is enabled

### 3. Redis
- [ ] Redis 7+ is running
- [ ] Authentication is enabled (`requirepass`)
- [ ] TLS is configured for production
- [ ] Memory limits are set
- [ ] Persistence is configured (RDB or AOF)

### 4. Infrastructure
- [ ] Load balancer is configured with SSL termination
- [ ] Health checks are configured (`/health` endpoint)
- [ ] Auto-scaling rules are defined
- [ ] Container resources (CPU/memory) are set appropriately
- [ ] Network security groups restrict access

### 5. Monitoring & Observability
- [ ] Prometheus is scraping metrics from `/metrics`
- [ ] Grafana dashboards are configured
- [ ] Alert rules are active (see `infrastructure/prometheus/alerts.yml`)
- [ ] Log aggregation is set up (CloudWatch, ELK, etc.)
- [ ] Sentry or error tracking is configured
- [ ] APM is enabled for tracing

### 6. CI/CD
- [ ] All tests pass in CI pipeline
- [ ] Load tests pass smoke scenario
- [ ] Security scan shows no critical vulnerabilities
- [ ] Docker images are built and pushed
- [ ] Deployment pipeline is ready

## Deployment Steps

### Step 1: Database Migration
```bash
# Connect to production and run migrations
alembic upgrade head
```

### Step 2: Deploy API
```bash
# Pull latest image
docker pull your-registry/stratum-api:latest

# Deploy with orchestrator (ECS, K8s, etc.)
# Ensure blue-green or rolling deployment
```

### Step 3: Deploy Workers
```bash
# Deploy Celery workers
docker pull your-registry/stratum-worker:latest
```

### Step 4: Verify Deployment
```bash
# Check API health
curl https://api.your-domain.com/health

# Check metrics endpoint
curl https://api.your-domain.com/metrics

# Run smoke test
k6 run -e SCENARIO=smoke -e BASE_URL=https://api.your-domain.com tests/load/autopilot-enforcement-load-test.js
```

### Step 5: DNS Cutover
- [ ] Update DNS records to point to new deployment
- [ ] Verify SSL certificate is valid
- [ ] Test from multiple regions

## Post-Deployment Validation

### Functional Tests
- [ ] Login/authentication works
- [ ] Platform OAuth connections work
- [ ] Campaign operations work
- [ ] Trust layer endpoints return data
- [ ] EMQ score calculation works
- [ ] Autopilot enforcement is active

### Performance Tests
- [ ] Response times are within SLA (p95 < 500ms)
- [ ] No memory leaks under load
- [ ] Database connection pool is healthy
- [ ] Redis connection is stable

### Monitoring Tests
- [ ] Metrics are appearing in Prometheus
- [ ] Logs are flowing to aggregator
- [ ] Alerts fire correctly (test with synthetic error)
- [ ] Dashboards show expected data

## Rollback Plan

### If Issues Detected
1. **Immediate Rollback** (< 5 minutes)
   - Route traffic to previous deployment
   - Keep new deployment running for debugging

2. **Database Rollback** (if migration issues)
   - Run `alembic downgrade -1`
   - Verify data integrity

3. **Investigation**
   - Check logs for errors
   - Review metrics for anomalies
   - Check database performance

## Production Environment Variables

```bash
# Required
APP_ENV=production
SECRET_KEY=<strong-random-string-32-chars>
JWT_SECRET_KEY=<strong-random-string-32-chars>
PII_ENCRYPTION_KEY=<base64-encoded-32-byte-key>
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/stratum?sslmode=require
REDIS_URL=redis://:password@host:6379/0

# Platform OAuth (obtain from platform developer portals)
META_APP_ID=<your-app-id>
META_APP_SECRET=<your-app-secret>
GOOGLE_CLIENT_ID=<your-client-id>
GOOGLE_CLIENT_SECRET=<your-client-secret>
TIKTOK_APP_ID=<your-app-id>
TIKTOK_APP_SECRET=<your-app-secret>
HUBSPOT_CLIENT_ID=<your-client-id>
HUBSPOT_CLIENT_SECRET=<your-client-secret>

# Optional
SENTRY_DSN=<your-sentry-dsn>
LOG_LEVEL=INFO
WORKERS=4
```

## Support Contacts

- **On-Call Engineer**: Check PagerDuty rotation
- **Infrastructure Team**: infrastructure@yourcompany.com
- **Database Team**: dba@yourcompany.com

## Revision History

| Date | Version | Changes |
|------|---------|---------|
| 2026-01-12 | 1.0 | Initial checklist |
