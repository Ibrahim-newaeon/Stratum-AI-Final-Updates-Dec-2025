# Operational Runbooks

## Overview

Step-by-step procedures for common operational tasks and incident response.

---

## Deployment

### Deploy to Production

**When**: Scheduled release or hotfix
**Who**: On-call engineer or release manager

#### Prerequisites

- [ ] All tests passing in CI
- [ ] Staging deployment verified
- [ ] Release notes prepared
- [ ] Rollback plan ready

#### Steps

```bash
# 1. Verify current state
kubectl get pods -n production
kubectl get deployments -n production

# 2. Create backup tag
git tag -a backup-$(date +%Y%m%d-%H%M) -m "Pre-deployment backup"
git push origin --tags

# 3. Deploy API
kubectl set image deployment/stratum-api \
  api=stratum/api:${VERSION} \
  -n production

# 4. Watch rollout
kubectl rollout status deployment/stratum-api -n production --timeout=5m

# 5. Verify health
curl -f https://api.stratum.ai/health/detailed

# 6. Deploy workers
kubectl set image deployment/stratum-workers \
  worker=stratum/workers:${VERSION} \
  -n production

# 7. Monitor for 15 minutes
watch -n 10 'kubectl get pods -n production'
```

#### Rollback

```bash
# If issues detected
kubectl rollout undo deployment/stratum-api -n production
kubectl rollout undo deployment/stratum-workers -n production

# Verify rollback
kubectl rollout status deployment/stratum-api -n production
```

---

### Database Migration

**When**: Schema changes required
**Who**: Backend engineer + DBA review

#### Prerequisites

- [ ] Migration tested on staging
- [ ] Backup verified
- [ ] Maintenance window scheduled (if destructive)

#### Steps

```bash
# 1. Take snapshot
aws rds create-db-snapshot \
  --db-instance-identifier stratum-prod \
  --db-snapshot-identifier pre-migration-$(date +%Y%m%d)

# 2. Verify snapshot
aws rds describe-db-snapshots \
  --db-snapshot-identifier pre-migration-$(date +%Y%m%d)

# 3. Run migration (dry run)
alembic upgrade head --sql > migration.sql
# Review migration.sql

# 4. Execute migration
alembic upgrade head

# 5. Verify schema
alembic current
psql -c "\dt" $DATABASE_URL

# 6. Run health check
python -c "from app.db import engine; engine.connect()"
```

#### Rollback

```bash
# Downgrade to previous version
alembic downgrade -1

# Or restore from snapshot if needed
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier stratum-prod-restore \
  --db-snapshot-identifier pre-migration-$(date +%Y%m%d)
```

---

## Incident Response

### High Error Rate

**Alert**: `HighErrorRate` (> 5% 5xx errors)
**Severity**: Critical
**Response Time**: < 5 minutes

#### Triage

```bash
# 1. Check error distribution
kubectl logs -l app=stratum-api -n production --tail=100 | grep ERROR

# 2. Identify failing endpoints
curl -s http://prometheus:9090/api/v1/query \
  --data-urlencode 'query=topk(5, rate(api_requests_total{status_code=~"5.."}[5m]))'

# 3. Check recent deployments
kubectl rollout history deployment/stratum-api -n production

# 4. Check external dependencies
curl -f https://graph.facebook.com/v18.0/me?access_token=test || echo "Meta API issue"
```

#### Resolution Paths

**If recent deployment**:
```bash
kubectl rollout undo deployment/stratum-api -n production
```

**If database issue**:
```bash
# Check connection pool
psql -c "SELECT count(*), state FROM pg_stat_activity GROUP BY state;" $DATABASE_URL

# Restart connection pool
kubectl rollout restart deployment/stratum-api -n production
```

**If external API issue**:
```bash
# Enable circuit breaker bypass for critical flows
kubectl set env deployment/stratum-api \
  CIRCUIT_BREAKER_DISABLED=true \
  -n production
```

---

### Database Connection Exhaustion

**Alert**: `DatabaseConnectionsHigh` (> 80% of max)
**Severity**: Warning/Critical
**Response Time**: < 10 minutes

#### Triage

```bash
# 1. Check current connections
psql -c "
SELECT usename, application_name, state, count(*)
FROM pg_stat_activity
GROUP BY usename, application_name, state
ORDER BY count DESC
LIMIT 20;
" $DATABASE_URL

# 2. Find long-running queries
psql -c "
SELECT pid, now() - pg_stat_activity.query_start AS duration, query
FROM pg_stat_activity
WHERE state = 'active'
  AND now() - pg_stat_activity.query_start > interval '30 seconds'
ORDER BY duration DESC;
" $DATABASE_URL

# 3. Check for connection leaks
kubectl logs -l app=stratum-api -n production | grep -i "connection"
```

#### Resolution

```bash
# 1. Terminate idle connections
psql -c "
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle'
  AND query_start < now() - interval '10 minutes'
  AND usename = 'stratum';
" $DATABASE_URL

# 2. Scale down workers temporarily
kubectl scale deployment/stratum-workers --replicas=4 -n production

# 3. Increase pool size (if capacity allows)
kubectl set env deployment/stratum-api \
  DATABASE_POOL_SIZE=20 \
  -n production

# 4. Restart to reset connections
kubectl rollout restart deployment/stratum-api -n production
```

---

### Redis Memory Pressure

**Alert**: `RedisMemoryHigh` (> 80%)
**Severity**: Warning
**Response Time**: < 15 minutes

#### Triage

```bash
# 1. Check memory usage
redis-cli -h redis.production INFO memory

# 2. Find large keys
redis-cli -h redis.production --bigkeys

# 3. Check key patterns
redis-cli -h redis.production DBSIZE
redis-cli -h redis.production SCAN 0 COUNT 100
```

#### Resolution

```bash
# 1. Clear expired keys
redis-cli -h redis.production DEBUG DIGEST

# 2. Clear specific cache namespace
redis-cli -h redis.production KEYS "cache:analytics:*" | xargs redis-cli DEL

# 3. Adjust TTLs for high-volume keys
# Update application config to reduce cache duration

# 4. Scale Redis cluster (if applicable)
aws elasticache modify-replication-group \
  --replication-group-id stratum-redis \
  --node-group-configuration NodeGroupId=0001,NewReplicaCount=2
```

---

### Celery Queue Backlog

**Alert**: `CeleryQueueBacklog` (> 1000 tasks)
**Severity**: Warning
**Response Time**: < 10 minutes

#### Triage

```bash
# 1. Check queue depths
celery -A app.worker inspect active_queues

# 2. Identify slow tasks
celery -A app.worker inspect stats

# 3. Check worker health
celery -A app.worker inspect ping
```

#### Resolution

```bash
# 1. Scale up workers
kubectl scale deployment/stratum-workers --replicas=16 -n production

# 2. Purge specific queue (if safe)
celery -A app.worker purge -Q low_priority

# 3. Prioritize critical queues
kubectl set env deployment/stratum-workers \
  CELERY_QUEUES="high_priority,default" \
  -n production

# 4. Identify and fix slow tasks
# Review task code for optimization
```

---

### Integration Rate Limited

**Alert**: Platform rate limit approaching
**Severity**: Warning
**Response Time**: < 15 minutes

#### Triage

```bash
# 1. Check current rate usage
curl -s http://prometheus:9090/api/v1/query \
  --data-urlencode 'query=integration_rate_limit_usage{platform="meta"}'

# 2. Identify high-volume tenants
kubectl logs -l app=stratum-api -n production | grep "rate_limit" | jq '.tenant_id' | sort | uniq -c | sort -rn

# 3. Check batch queue depth
redis-cli -h redis.production LLEN "batch:meta:pending"
```

#### Resolution

```bash
# 1. Enable request throttling
kubectl set env deployment/stratum-api \
  META_RATE_LIMIT_BUFFER=0.2 \
  -n production

# 2. Increase batch sizes
kubectl set env deployment/stratum-workers \
  CAPI_BATCH_SIZE=1000 \
  -n production

# 3. Temporarily pause low-priority syncs
redis-cli -h redis.production SET "pause:low_priority_sync" "true" EX 3600
```

---

## Maintenance Tasks

### Rotate Secrets

**When**: Scheduled rotation or compromise suspected
**Who**: Security engineer

#### Steps

```bash
# 1. Generate new secrets
openssl rand -base64 32 > new_jwt_secret.txt
openssl rand -base64 32 > new_encryption_key.txt

# 2. Update secrets in AWS
aws secretsmanager update-secret \
  --secret-id stratum/production/jwt-secret \
  --secret-string file://new_jwt_secret.txt

# 3. Deploy new version that reads updated secrets
kubectl rollout restart deployment/stratum-api -n production

# 4. Verify functionality
curl -f https://api.stratum.ai/health/detailed

# 5. Invalidate old sessions (if JWT secret changed)
redis-cli -h redis.production FLUSHDB

# 6. Document rotation
echo "Secrets rotated at $(date)" >> /var/log/secret-rotations.log
```

---

### Database Maintenance

**When**: Weekly maintenance window
**Who**: DBA or on-call engineer

#### Steps

```bash
# 1. Announce maintenance
slack-cli post "#platform-status" "Database maintenance starting in 15 minutes"

# 2. Run VACUUM ANALYZE
psql -c "VACUUM ANALYZE;" $DATABASE_URL

# 3. Reindex high-churn tables
psql -c "REINDEX TABLE cdp_events CONCURRENTLY;" $DATABASE_URL
psql -c "REINDEX TABLE audit_logs CONCURRENTLY;" $DATABASE_URL

# 4. Update table statistics
psql -c "ANALYZE VERBOSE;" $DATABASE_URL

# 5. Check bloat
psql -c "
SELECT schemaname, relname, n_dead_tup, n_live_tup,
       round(n_dead_tup::numeric / (n_live_tup + 1) * 100, 2) as dead_pct
FROM pg_stat_user_tables
WHERE n_dead_tup > 1000
ORDER BY n_dead_tup DESC
LIMIT 10;
" $DATABASE_URL

# 6. Announce completion
slack-cli post "#platform-status" "Database maintenance completed"
```

---

### Log Rotation and Cleanup

**When**: Daily automated or manual cleanup
**Who**: Automated job or on-call

#### Steps

```bash
# 1. Archive old logs
aws s3 sync /var/log/stratum/ s3://stratum-logs/archive/$(date +%Y/%m/%d)/

# 2. Compress logs older than 7 days
find /var/log/stratum -name "*.log" -mtime +7 -exec gzip {} \;

# 3. Delete logs older than 30 days
find /var/log/stratum -name "*.log.gz" -mtime +30 -delete

# 4. Clean up Docker logs
docker system prune -f --filter "until=168h"

# 5. Verify disk space
df -h /var/log
```

---

## Scaling Operations

### Scale API Horizontally

```bash
# Check current state
kubectl get hpa -n production

# Manual scale
kubectl scale deployment/stratum-api --replicas=10 -n production

# Update HPA limits
kubectl patch hpa stratum-api -n production \
  --patch '{"spec":{"maxReplicas":20}}'
```

### Scale Database Vertically

```bash
# 1. Schedule maintenance window
# 2. Take snapshot
aws rds create-db-snapshot ...

# 3. Modify instance
aws rds modify-db-instance \
  --db-instance-identifier stratum-prod \
  --db-instance-class db.r6g.2xlarge \
  --apply-immediately

# 4. Monitor modification
aws rds describe-db-instances \
  --db-instance-identifier stratum-prod \
  --query 'DBInstances[0].DBInstanceStatus'
```

---

## Related Documentation

- [Monitoring](./monitoring.md) - Metrics and alerting
- [Incidents](./incidents.md) - Incident management process
- [Security](../06-appendix/security.md) - Security procedures
