# Stratum AI - Standalone Editions

This folder contains standalone deployable packages for each subscription tier.

## Structure

```
editions/
├── starter/           # Starter Edition ($499/mo)
│   ├── .env.example
│   ├── docker-compose.yml
│   └── README.md
├── professional/      # Professional Edition ($999/mo)
│   ├── .env.example
│   ├── docker-compose.yml
│   └── README.md
├── enterprise/        # Enterprise Edition (Custom)
│   ├── .env.example
│   ├── docker-compose.yml
│   └── README.md
└── build.sh           # Build script for all editions
```

## Quick Start

### Deploy Starter Edition
```bash
cd editions/starter
cp .env.example .env
docker compose up -d
```

### Deploy Professional Edition
```bash
cd editions/professional
cp .env.example .env
docker compose up -d
```

### Deploy Enterprise Edition
```bash
cd editions/enterprise
cp .env.example .env
docker compose up -d
```

## Feature Comparison

| Feature | Starter | Professional | Enterprise |
|---------|---------|--------------|------------|
| Ad Accounts | 5 | 15 | Unlimited |
| Users | 3 | 10 | Unlimited |
| Signal Health | ✓ | ✓ | ✓ |
| Anomaly Detection | ✓ | ✓ | ✓ |
| RFM Analysis | ✓ | ✓ | ✓ |
| Funnel Builder | - | ✓ | ✓ |
| Computed Traits | - | ✓ | ✓ |
| Pipedrive CRM | - | ✓ | ✓ |
| HubSpot CRM | - | ✓ | ✓ |
| Predictive Churn | - | - | ✓ |
| Custom Rules | - | - | ✓ |
| Salesforce CRM | - | - | ✓ |
| Identity Graph | - | - | ✓ |
| GDPR Tools | - | - | ✓ |

## Building Custom Packages

To create distributable packages for each edition:

```bash
./build.sh all        # Build all editions
./build.sh starter    # Build Starter only
./build.sh professional  # Build Professional only
./build.sh enterprise    # Build Enterprise only
```

## Configuration

Each edition is configured via environment variables:

- `SUBSCRIPTION_TIER`: starter | professional | enterprise
- `APP_NAME`: Customizable per deployment
- All other standard Stratum AI variables

## White-labeling

Each edition supports white-labeling:

1. Set `APP_NAME` in .env
2. Replace logo in `frontend/public/`
3. Update colors in `frontend/src/styles/`
4. Rebuild frontend: `docker compose build frontend`
