# Changelog

All notable changes to Stratum AI Platform will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-01-13

### Added

#### CDP (Customer Data Platform)
- **Event Ingestion API** (`POST /api/v1/cdp/events`)
  - Real-time event collection with batch support (up to 1000 events per request)
  - Idempotency key support for deduplication
  - Source key authentication for secure ingestion
  - Event Match Quality (EMQ) scoring per event

- **Profile Management**
  - Profile unification with multi-identifier matching
  - PII hashing (SHA256) before storage
  - Lifecycle stage tracking (anonymous → known → customer → churned)
  - Profile data and computed traits storage

- **Identity Resolution**
  - Email, phone, device_id, anonymous_id, external_id identifier types
  - Automatic identifier normalization (email lowercase, phone E.164)
  - Identity graph with confidence scoring
  - Cross-device profile linking

- **Consent Management**
  - GDPR/PDPL compliant consent tracking
  - Per-profile, per-type consent records
  - Consent history with grant/revoke timestamps
  - Integration with event ingestion

- **Data Sources**
  - Source configuration with API key generation
  - Source types: website, server, sgtm, import, crm
  - Per-source event counting and last activity tracking

- **Trust Engine Integration**
  - CDP EMQ Aggregator service for signal health integration
  - CDP contributes 10% weight to overall signal health score
  - CDP-specific recommendations in Trust Gate decisions
  - Profile quality and consent metrics in health calculations

- **Rate Limiting**
  - Event ingestion: 100 requests/minute
  - Profile lookups: 300 requests/minute
  - Source operations: 30 requests/minute
  - Webhook operations: 30 requests/minute
  - Per-tenant rate limiting with proper 429 responses

- **Frontend Components**
  - CDP ROI Calculator widget with locale/currency support
  - WCAG 2.1 AA accessible range inputs
  - CDPCalculator view page with value props
  - Error boundaries for graceful failure handling

- **API Client**
  - TypeScript types for all CDP data structures
  - React Query hooks for CDP endpoints
  - Tracker utility for simplified event ingestion

- **Webhook Destinations**
  - CRUD endpoints for webhook management
  - HMAC signature authentication for webhook payloads
  - Webhook testing endpoint with response validation
  - Secret key rotation support
  - Event types: event.received, profile.created, profile.updated, profile.merged, consent.updated

- **Anomaly Detection**
  - Z-score based event volume anomaly detection
  - Per-source and total volume analysis
  - Configurable detection parameters (window, threshold)
  - Anomaly summary endpoint with health status and volume trends
  - Severity levels: low, medium, high, critical

### Changed

- **Signal Health Calculator**
  - Now supports 5-component scoring (EMQ, Freshness, Variance, Anomaly, CDP)
  - Weights redistribute proportionally when CDP data is available
  - Added `cdp_emq_score` field to SignalHealth model

- **Trust Gate**
  - Added CDP-specific recommendations for identity resolution issues
  - Enhanced `to_dict()` to include CDP data in responses

### Security

- Source key authentication for event ingestion endpoints
- PII hashing before database storage
- Rate limiting on all CDP endpoints
- Tenant isolation on all operations

### Documentation

- Updated README.md with CDP section
- Added CDP endpoints documentation
- Added rate limit documentation
- Created CHANGELOG.md

## [1.0.0] - 2025-12-XX

### Added

- Initial release of Stratum AI Platform
- Trust Engine with 4-component signal health scoring
- Trust-Gated Autopilot with configurable enforcement modes
- Campaign Builder with multi-step wizard
- Multi-platform integrations (Meta, Google, TikTok, Snapchat)
- HubSpot CRM integration with bidirectional sync
- 6 attribution models including Markov Chain & Shapley Value
- Budget pacing with EWMA predictions
- A/B Testing with statistical power calculations
- Comprehensive API with 150+ endpoints
- Full documentation with 60+ screen directory

---

For more details, see the [full documentation](https://ibrahim-newaeon.github.io/Stratum-AI-Final-Updates-Dec-2025/).
