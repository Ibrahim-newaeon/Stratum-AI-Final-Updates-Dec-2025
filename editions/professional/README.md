# Stratum AI - Professional Edition

**Price: $999/month | Ad Spend: Up to $500K monthly**

## Quick Start

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your secure keys and CRM credentials

# 2. Start the application
docker compose up -d

# 3. Access
# Frontend: http://localhost:5173
# API Docs: http://localhost:8000/docs
```

## Features Included

### Everything in Starter, PLUS:

| Feature | Included |
|---------|----------|
| Ad Accounts | 15 max |
| Users | 10 max |
| Segments | 50 max |
| Automations | 25 max |
| Funnel Builder | ✓ |
| Computed Traits | ✓ |
| Segment Builder | ✓ |
| Trust Gate Audit Logs | ✓ |
| Action Dry-Run Mode | ✓ |
| Pipedrive CRM | ✓ |
| HubSpot CRM | ✓ |
| Audience Sync | 2 platforms |
| Priority Support | 24hr response |

## Features NOT Included

- Predictive Churn Modeling (Enterprise)
- Custom Autopilot Rules (Enterprise)
- Salesforce CRM (Enterprise)
- Zoho CRM (Enterprise)
- Identity Graph Visualization (Enterprise)
- GDPR/Consent Tools (Enterprise)
- Unlimited Ad Accounts (Enterprise)
- Full Audience Sync (Enterprise)

## CRM Setup

### Pipedrive
```env
PIPEDRIVE_API_TOKEN=your_api_token
PIPEDRIVE_COMPANY_DOMAIN=your_company
```

### HubSpot
```env
HUBSPOT_API_KEY=your_api_key
HUBSPOT_PORTAL_ID=your_portal_id
```

## Audience Sync

Professional includes 2 platform sync:
- Meta Custom Audiences
- Google Customer Match

To enable:
1. Connect ad accounts in Settings
2. Create segments in CDP
3. Push to platforms via Audience Sync

## Upgrade to Enterprise

For unlimited accounts, predictive churn, and full CRM suite:
- Contact sales
- Visit `/settings/billing`

## Support

- Priority email support (24hr response)
- Documentation: `/docs`
- Live chat during business hours

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
```
