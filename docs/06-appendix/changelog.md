# Changelog

All notable changes to the Stratum AI platform are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Mobile app native structure documentation
- CMS integration for landing page content
- Protected admin route for CMS access

### Changed
- Improved signal health calculation algorithm
- Enhanced CDP profile merge logic

### Fixed
- Race condition in audience sync
- Memory leak in event processing worker

---

## [2.5.0] - 2024-12-15

### Added

#### CDP Audience Sync
- One-click audience sync to Meta, Google, TikTok, and Snapchat
- Auto-sync scheduling (1 hour to 1 week intervals)
- Sync history tracking with match rate metrics
- Manual CSV/JSON export with traits and events

#### CMS Integration
- Headless CMS for landing page content
- Separate CMS login portal at `/cms/login`
- Protected admin dashboard for content management
- Real-time preview of content changes

#### WhatsApp Business
- WhatsApp Cloud API integration
- Message template management with Meta approval
- Contact management with opt-in tracking
- Broadcast campaigns to segments
- Webhook processing for delivery status

### Changed
- Upgraded React to v18.2
- Improved Trust Engine threshold configuration
- Enhanced Rules Engine condition builder UI
- Optimized CDP event ingestion pipeline

### Fixed
- Fixed segment evaluation timeout for large audiences
- Resolved duplicate events in CDP timeline
- Fixed timezone handling in analytics date ranges
- Corrected proration calculation for plan upgrades

### Security
- Added rate limiting to all API endpoints
- Implemented TOTP-based MFA for admin accounts
- Enhanced PII hashing for platform sync

---

## [2.4.0] - 2024-11-01

### Added

#### Trust-Gated Autopilot V2
- Enhanced signal health scoring with anomaly detection
- Configurable trust thresholds per automation
- Alert escalation for degraded signals
- Manual override with audit logging

#### Analytics Dashboard
- Real-time KPI tiles with trend indicators
- Demographic breakdown charts
- Heatmap visualization for activity patterns
- Platform performance comparison
- Executive summary report generation

#### Onboarding Wizard
- 5-step guided setup flow
- Platform connection assistance
- Goal-based automation recommendations
- Trust gate configuration helper
- Progress tracking with resume capability

### Changed
- Redesigned campaign builder interface
- Improved error messages across all forms
- Enhanced mobile responsiveness

### Fixed
- Fixed memory leak in WebSocket connections
- Resolved race condition in automation execution
- Fixed chart rendering on Safari

### Deprecated
- Legacy analytics endpoints (removal in v3.0)
- Old campaign creation flow (migration required)

---

## [2.3.0] - 2024-09-15

### Added

#### Rules Engine
- Visual rule builder with drag-and-drop
- Complex condition groups (AND/OR)
- Action chains with sequential execution
- Rule templates library
- Version history with rollback

#### Integrations V2
- Unified platform connector architecture
- Circuit breaker pattern for resilience
- Automatic rate limit handling
- Connection health monitoring
- Batch optimization for high-volume events

### Changed
- Migrated to PostgreSQL 15
- Upgraded Celery to v5.3
- Improved database query performance

### Fixed
- Fixed pagination in segment builder
- Resolved webhook signature validation
- Fixed date picker timezone issues

---

## [2.2.0] - 2024-07-01

### Added

#### CDP Core
- Unified customer profiles
- Identity resolution with merge
- Event timeline per profile
- Computed traits
- Profile search with filters

#### Segment Builder
- Dynamic segment creation
- RFM-based conditions
- Lifecycle stage targeting
- Real-time segment size preview
- Segment scheduling

### Changed
- Enhanced API rate limiting
- Improved logging structure
- Optimized Redis caching

### Fixed
- Fixed export timeout for large datasets
- Resolved profile deduplication edge case
- Fixed event count discrepancy

---

## [2.1.0] - 2024-05-01

### Added

#### Authentication V2
- OAuth 2.0 with PKCE
- Social login (Google, Microsoft)
- Session management
- Password policy configuration
- Account lockout protection

#### Team Management
- Role-based access control
- Custom permission sets
- Team invitation flow
- Activity audit log

### Changed
- Upgraded to FastAPI 0.100
- Improved JWT token handling
- Enhanced session security

### Fixed
- Fixed CORS configuration
- Resolved token refresh race condition
- Fixed permission caching

---

## [2.0.0] - 2024-03-01

### Added

#### Platform Launch
- Trust-Gated Autopilot core engine
- Campaign management
- Basic analytics
- Meta integration
- Google Ads integration

#### Multi-Tenancy
- Tenant isolation
- Subscription plans (Starter, Growth, Enterprise)
- Usage metering
- Billing with Stripe

### Infrastructure
- Kubernetes deployment
- CI/CD pipeline
- Monitoring with Prometheus/Grafana
- Distributed tracing with Jaeger

---

## [1.0.0] - 2023-12-01

### Added
- Initial beta release
- Core automation engine
- Basic campaign support
- Single-tenant architecture

---

## Migration Guides

### Migrating from v2.4 to v2.5

#### Audience Sync Setup
```python
# New: Configure platform connections for audience sync
from app.services.audience_sync import AudienceSyncService

# Connect platforms (one-time setup)
await AudienceSyncService.connect_platform(
    tenant_id=tenant.id,
    platform="meta",
    credentials=meta_credentials,
)
```

#### CMS Content Migration
```sql
-- Migrate existing landing content to CMS
INSERT INTO cms_content (type, slug, data, published_at)
SELECT 'feature', slug, json_build_object('title', title, 'description', description),
       NOW()
FROM landing_features;
```

### Migrating from v2.3 to v2.4

#### Trust Threshold Configuration
```yaml
# config/trust_engine.yaml
# New threshold configuration format
thresholds:
  healthy: 70          # Previously hardcoded
  degraded: 40         # Previously hardcoded
  anomaly_sensitivity: 0.8  # New setting
```

#### Analytics API Changes
```python
# Old endpoint (deprecated)
GET /api/v1/analytics/summary

# New endpoint
GET /api/v1/analytics/dashboard
# Returns enhanced response with trends
```

### Migrating from v2.2 to v2.3

#### Rules Engine Migration
```python
# Existing automations auto-converted to rules
# Manual review recommended for complex logic

# Check migration status
GET /api/v1/automations/migration-status
```

---

## Version Support

| Version | Status | Support Until |
|---------|--------|---------------|
| 2.5.x | Current | Active |
| 2.4.x | Supported | 2025-06-01 |
| 2.3.x | Security only | 2025-03-01 |
| 2.2.x | End of life | 2024-12-01 |
| < 2.2 | Unsupported | - |

---

## Release Schedule

| Release Type | Frequency | Description |
|--------------|-----------|-------------|
| Major (x.0.0) | Annually | Breaking changes, major features |
| Minor (x.y.0) | Quarterly | New features, enhancements |
| Patch (x.y.z) | As needed | Bug fixes, security patches |

---

## Related Documentation

- [Roadmap](./roadmap.md) - Future plans
- [Security](./security.md) - Security updates
- [API Contracts](../04-features/) - API documentation
