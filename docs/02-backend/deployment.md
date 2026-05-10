# Deployment Guide

## Overview

Stratum AI backend is containerized and can be deployed to various environments.

---

## Docker Configuration

### Dockerfile

```dockerfile
# backend/Dockerfile

FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Build Image

```bash
# Build
docker build -t stratum-api:latest ./backend

# With build args
docker build \
    --build-arg APP_VERSION=1.0.0 \
    -t stratum-api:1.0.0 \
    ./backend
```

---

## Docker Compose (Development)

```yaml
# docker-compose.yml

services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-stratum}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-stratum_secure_password}
      POSTGRES_DB: ${POSTGRES_DB:-stratum_ai}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U stratum"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    environment:
      - APP_ENV=development
      - DATABASE_URL=postgresql+asyncpg://stratum:stratum_secure_password@db:5432/stratum_ai
      - REDIS_URL=redis://redis:6379/0
      - CELERY_BROKER_URL=redis://redis:6379/1
    volumes:
      - ./backend:/app
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    command: >
      sh -c "alembic upgrade head &&
             uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

  worker:
    build:
      context: ./backend
    environment:
      - DATABASE_URL=postgresql+asyncpg://stratum:stratum_secure_password@db:5432/stratum_ai
      - CELERY_BROKER_URL=redis://redis:6379/1
    depends_on:
      - api
    command: celery -A app.workers.celery_app worker --loglevel=info

  scheduler:
    build:
      context: ./backend
    environment:
      - CELERY_BROKER_URL=redis://redis:6379/1
    depends_on:
      - worker
    command: celery -A app.workers.celery_app beat --loglevel=info

volumes:
  postgres_data:
  redis_data:
```

---

## AWS Deployment

### Architecture

```mermaid
graph TB
    subgraph "Internet"
        USERS[Users]
    end

    subgraph "AWS"
        subgraph "Edge"
            CF[CloudFront]
            WAF[WAF]
        end

        subgraph "VPC"
            subgraph "Public Subnet"
                ALB[Application Load Balancer]
            end

            subgraph "Private Subnet - Compute"
                ECS[ECS Fargate]
                API1[API Container]
                API2[API Container]
                WORKER[Worker Container]
            end

            subgraph "Private Subnet - Data"
                RDS[(RDS PostgreSQL)]
                REDIS[(ElastiCache Redis)]
            end
        end

        S3[S3 Static Assets]
        SM[Secrets Manager]
    end

    USERS --> CF
    CF --> WAF
    WAF --> ALB
    ALB --> ECS
    ECS --> API1 & API2 & WORKER
    API1 & API2 --> RDS & REDIS
    WORKER --> RDS & REDIS
    ECS --> SM
```

### ECS Task Definition

```json
{
  "family": "stratum-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::ACCOUNT:role/ecsTaskExecutionRole",
  "taskRoleArn": "arn:aws:iam::ACCOUNT:role/stratumTaskRole",
  "containerDefinitions": [
    {
      "name": "api",
      "image": "ACCOUNT.dkr.ecr.REGION.amazonaws.com/stratum-api:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {"name": "APP_ENV", "value": "production"}
      ],
      "secrets": [
        {
          "name": "DATABASE_URL",
          "valueFrom": "arn:aws:secretsmanager:REGION:ACCOUNT:secret:stratum/db-url"
        },
        {
          "name": "SECRET_KEY",
          "valueFrom": "arn:aws:secretsmanager:REGION:ACCOUNT:secret:stratum/secret-key"
        }
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/stratum-api",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      },
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 10,
        "retries": 3,
        "startPeriod": 60
      }
    }
  ]
}
```

### RDS Configuration

| Setting | Value |
|---------|-------|
| Engine | PostgreSQL 16 |
| Instance | db.r6g.large |
| Storage | gp3, 100GB |
| Multi-AZ | Yes (production) |
| Encryption | Yes |
| Backup | 7 days retention |

### ElastiCache Configuration

| Setting | Value |
|---------|-------|
| Engine | Redis 7 |
| Node Type | cache.r6g.large |
| Cluster Mode | Disabled |
| Replicas | 1 (production) |
| Encryption | In-transit + At-rest |

---

## Environment Variables (Production)

### Required

```env
# Application
APP_ENV=production
DEBUG=false

# Security (from Secrets Manager)
SECRET_KEY=<from-secrets-manager>
JWT_SECRET_KEY=<from-secrets-manager>
PII_ENCRYPTION_KEY=<from-secrets-manager>

# Database (from Secrets Manager)
DATABASE_URL=postgresql+asyncpg://user:password@rds-endpoint:5432/stratum

# Redis
REDIS_URL=redis://elasticache-endpoint:6379/0
CELERY_BROKER_URL=redis://elasticache-endpoint:6379/1

# CORS
CORS_ORIGINS=https://app.stratum.ai

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json
SENTRY_DSN=https://key@sentry.io/project
```

### Secrets Manager

Store sensitive values in AWS Secrets Manager:

```bash
# Create secret
aws secretsmanager create-secret \
    --name stratum/production/secrets \
    --secret-string '{
        "SECRET_KEY": "...",
        "JWT_SECRET_KEY": "...",
        "DATABASE_URL": "..."
    }'
```

---

## Database Migrations

### During Deployment

```bash
# Run migrations before starting the app
alembic upgrade head
```

### CI/CD Pipeline

```yaml
# Deploy workflow
- name: Run migrations
  run: |
    aws ecs run-task \
      --cluster stratum-cluster \
      --task-definition stratum-migration \
      --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx]}"
```

### Migration Task Definition

```json
{
  "family": "stratum-migration",
  "containerDefinitions": [
    {
      "name": "migration",
      "image": "stratum-api:latest",
      "command": ["alembic", "upgrade", "head"],
      "essential": true
    }
  ]
}
```

---

## Health Checks

### Application Health

```
GET /health
```

Response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production",
  "database": "healthy",
  "redis": "healthy"
}
```

### Kubernetes Probes

```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

### ALB Health Check

| Setting | Value |
|---------|-------|
| Path | /health |
| Protocol | HTTP |
| Interval | 30s |
| Timeout | 10s |
| Healthy threshold | 2 |
| Unhealthy threshold | 3 |

---

## Scaling

### Horizontal Scaling

```yaml
# ECS Service Auto Scaling
Type: AWS::ApplicationAutoScaling::ScalableTarget
Properties:
  MaxCapacity: 10
  MinCapacity: 2
  ResourceId: service/stratum-cluster/stratum-api
  ScalableDimension: ecs:service:DesiredCount
  ServiceNamespace: ecs
```

### Scaling Policies

```yaml
# CPU-based scaling
Type: AWS::ApplicationAutoScaling::ScalingPolicy
Properties:
  PolicyType: TargetTrackingScaling
  TargetTrackingScalingPolicyConfiguration:
    PredefinedMetricSpecification:
      PredefinedMetricType: ECSServiceAverageCPUUtilization
    TargetValue: 70.0
    ScaleInCooldown: 300
    ScaleOutCooldown: 60
```

---

## Monitoring

### CloudWatch Metrics

| Metric | Description | Alarm Threshold |
|--------|-------------|-----------------|
| CPUUtilization | Container CPU | > 80% |
| MemoryUtilization | Container memory | > 80% |
| TargetResponseTime | ALB response time | > 1s |
| HTTP5xxCount | Server errors | > 10/min |

### CloudWatch Logs

```python
# Log group structure
/ecs/stratum-api        # API logs
/ecs/stratum-worker     # Worker logs
/ecs/stratum-scheduler  # Scheduler logs
```

### Alerts

```yaml
# SNS Alert for high error rate
Type: AWS::CloudWatch::Alarm
Properties:
  AlarmName: stratum-high-error-rate
  MetricName: HTTPCode_Target_5XX_Count
  Namespace: AWS/ApplicationELB
  Statistic: Sum
  Period: 60
  EvaluationPeriods: 2
  Threshold: 10
  ComparisonOperator: GreaterThanThreshold
  AlarmActions:
    - !Ref AlertSNSTopic
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] All tests passing
- [ ] Coverage meets threshold
- [ ] Security scan passed
- [ ] Environment variables configured
- [ ] Secrets in Secrets Manager
- [ ] Database backup completed

### Deployment

- [ ] Run database migrations
- [ ] Deploy new containers
- [ ] Health checks passing
- [ ] Monitor error rates
- [ ] Monitor response times

### Post-Deployment

- [ ] Verify key functionality
- [ ] Check logs for errors
- [ ] Confirm metrics normal
- [ ] Update deployment log

---

## Rollback Procedure

### ECS Rollback

```bash
# List recent deployments
aws ecs describe-services \
    --cluster stratum-cluster \
    --services stratum-api

# Force new deployment with previous image
aws ecs update-service \
    --cluster stratum-cluster \
    --service stratum-api \
    --force-new-deployment \
    --task-definition stratum-api:PREVIOUS_VERSION
```

### Database Rollback

```bash
# Rollback one migration
alembic downgrade -1

# Rollback to specific revision
alembic downgrade abc123
```

### Blue-Green Deployment

1. Deploy to green environment
2. Run health checks
3. Switch ALB to green
4. Monitor for issues
5. Keep blue as rollback option
