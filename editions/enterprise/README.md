# Stratum AI - Enterprise Edition

**Price: Custom | Ad Spend: Unlimited**

## Quick Start

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with all credentials

# 2. Start the application
docker compose up -d

# 3. Access
# Frontend: http://localhost:5173
# API Docs: http://localhost:8000/docs
# Flower (Celery): http://localhost:5555
```

## ALL Features Included

### Core Platform
| Feature | Included |
|---------|----------|
| Ad Accounts | Unlimited |
| Users | Unlimited |
| Segments | Unlimited |
| Automations | Unlimited |
| API Rate Limit | 1000/min |
| Data Retention | 2 years |

### Analytics & AI
| Feature | Included |
|---------|----------|
| Signal Health Monitoring | ✓ |
| Anomaly Detection | ✓ |
| RFM Customer Analysis | ✓ |
| Funnel Builder | ✓ |
| Computed Traits | ✓ |
| **Predictive Churn** | ✓ |
| **What-If Simulator** | ✓ |
| **Custom Report Builder** | ✓ |

### Automation
| Feature | Included |
|---------|----------|
| Trust Gate Audit Logs | ✓ |
| Action Dry-Run Mode | ✓ |
| **Custom Autopilot Rules** | ✓ |
| **Webhooks** | ✓ |

### CRM Integrations
| Feature | Included |
|---------|----------|
| Pipedrive | ✓ |
| HubSpot | ✓ |
| **Salesforce** | ✓ |
| **Zoho** | ✓ |
| **CRM Writeback** | ✓ |

### CDP & Identity
| Feature | Included |
|---------|----------|
| CDP Profiles | ✓ |
| CDP Events | ✓ |
| Segment Builder | ✓ |
| **Identity Graph** | ✓ |
| **Consent Management** | ✓ |
| **GDPR Tools** | ✓ |

### Audience Sync
| Platform | Included |
|----------|----------|
| Meta Custom Audiences | ✓ |
| Google Customer Match | ✓ |
| **TikTok DMP** | ✓ |
| **Snapchat SAM** | ✓ |

## CRM Setup

### Salesforce (Enterprise)
```env
SALESFORCE_CLIENT_ID=your_client_id
SALESFORCE_CLIENT_SECRET=your_client_secret
SALESFORCE_INSTANCE_URL=https://your-instance.salesforce.com
SALESFORCE_IS_SANDBOX=false
```

### Zoho (Enterprise)
```env
ZOHO_CLIENT_ID=your_client_id
ZOHO_CLIENT_SECRET=your_client_secret
ZOHO_REFRESH_TOKEN=your_refresh_token
```

## ML Configuration

### Local ML (Default)
```env
ML_PROVIDER=local
ML_MODELS_PATH=/app/ml_service/models
```

### Google Vertex AI (Optional)
```env
ML_PROVIDER=vertex
GOOGLE_CLOUD_PROJECT=your-gcp-project
VERTEX_AI_ENDPOINT=projects/{project}/locations/{location}/endpoints/{endpoint}
```

## Monitoring

### Flower (Celery Dashboard)
- URL: http://localhost:5555
- Monitor background tasks
- View worker status

### Sentry (Error Tracking)
```env
SENTRY_DSN=your_sentry_dsn
```

### Prometheus Metrics
- Endpoint: /metrics
- Grafana dashboards available in `/infrastructure/grafana/`

## Support

- **Dedicated Success Manager**
- 4-hour response SLA
- Custom onboarding
- Direct Slack channel

## Commands

```bash
# Start all services
docker compose up -d

# Scale workers
docker compose up -d --scale worker=3

# View logs
docker compose logs -f api worker

# Backup database
docker compose exec db pg_dump -U stratum_enterprise stratum_enterprise > backup.sql
```

## High Availability

For production HA setup:
1. Use managed PostgreSQL (RDS, Cloud SQL)
2. Use managed Redis (ElastiCache, Memorystore)
3. Deploy API behind load balancer
4. Use container orchestration (ECS, Kubernetes)

Contact your success manager for architecture guidance.
