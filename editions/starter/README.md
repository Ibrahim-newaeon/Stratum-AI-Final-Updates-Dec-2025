# Stratum AI - Starter Edition

**Price: $499/month | Ad Spend: Up to $100K monthly**

## Quick Start

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your secure keys

# 2. Start the application
docker compose up -d

# 3. Access
# Frontend: http://localhost:5173
# API Docs: http://localhost:8000/docs
```

## Features Included

| Feature | Included |
|---------|----------|
| Ad Accounts | 5 max |
| Users | 3 max |
| Signal Health Monitoring | ✓ |
| Anomaly Detection | ✓ |
| RFM Customer Analysis | ✓ |
| Dashboard Exports | ✓ |
| Slack Notifications | ✓ |
| Email Notifications | ✓ |
| CDP Profiles | ✓ |
| CDP Events | ✓ |

## Features NOT Included

- Funnel Builder (Professional+)
- Computed Traits (Professional+)
- Segment Builder (Professional+)
- CRM Integrations (Professional+)
- Audience Sync (Professional+)
- Predictive Churn (Enterprise)
- Custom Autopilot Rules (Enterprise)
- Identity Graph (Enterprise)
- GDPR Tools (Enterprise)

## Upgrade Path

To upgrade to Professional or Enterprise:

1. Contact sales or visit `/settings/billing`
2. Migrate your data (we provide migration tools)
3. Deploy the new edition

## Support

- Email support with 48-hour response time
- Documentation: `/docs`
- Community forum access

## Commands

```bash
# Start
docker compose up -d

# Stop
docker compose down

# View logs
docker compose logs -f api

# Restart
docker compose restart

# Update
docker compose pull && docker compose up -d
```
