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

- **Identity Graph & Profile Merging**
  - Full identity graph with nodes (identifiers) and edges (links)
  - Priority-based identity resolution (external_id > email > phone > device_id > anonymous_id)
  - Automatic profile merging when same person detected
  - Manual profile merge API endpoint
  - Merge history with full audit trail and rollback support
  - Canonical identity tracking (golden identity per profile)
  - BFS graph traversal for identity stitching
  - Link types: same_session, same_event, login, form_submit, purchase, manual, inferred
  - API endpoints for identity graph visualization and merge management

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

- **Segment Builder**
  - Dynamic segments with rule-based evaluation
  - Static segments with manual membership management
  - 18 condition operators (equals, contains, greater_than, within_last, etc.)
  - Nested rule groups with AND/OR logic
  - Segment preview with estimated count
  - Auto-refresh with configurable intervals
  - Profile membership tracking with match scores
  - API endpoints: CRUD, compute, preview, get profiles

- **Computed Traits**
  - Profile enrichment with derived values
  - Trait types: count, sum, average, min, max, first, last, unique_count, exists
  - Time-window based calculations
  - Batch computation for all profiles
  - Per-profile on-demand computation

- **RFM Analysis**
  - Recency, Frequency, Monetary scoring (1-5 scale)
  - 12 customer segments: champions, loyal_customers, potential_loyalists, new_customers, promising, need_attention, about_to_sleep, at_risk, cannot_lose, hibernating, lost, other
  - Configurable purchase event and revenue property
  - Batch RFM calculation with segment distribution
  - RFM summary endpoint with coverage statistics

- **Funnel/Journey Tracking**
  - Define multi-step conversion funnels (2-20 steps)
  - Track user progression through event sequences
  - Step-by-step conversion rate analysis
  - Drop-off point identification with profile retrieval
  - Configurable conversion windows (1-365 days)
  - Optional step timeout limits
  - Date-filtered funnel analysis
  - Profile journey tracking across multiple funnels
  - Auto-refresh with configurable intervals
  - API endpoints: CRUD, compute, analyze, drop-offs, profile journeys

- **Profile Search API**
  - Advanced profile search with comprehensive filtering
  - Text search in external_id and profile_data
  - Filter by multiple segments (include/exclude)
  - Filter by lifecycle stages
  - Filter by RFM segments
  - Filter by identifier types
  - Filter by event/revenue thresholds
  - Filter by date ranges
  - Email/phone identifier presence filters
  - Customer status filter
  - Flexible sorting (last_seen, first_seen, events, revenue)
  - Configurable output fields

- **Audience Export (Enhanced)**
  - Advanced filtering for audience export
  - Filter by segment membership
  - Filter by lifecycle stage
  - Filter by RFM segment
  - Filter by event/revenue thresholds
  - Filter by date ranges (first_seen, last_seen)
  - Filter by identifier type presence
  - Configurable output fields (traits, identifiers, RFM)
  - JSON and CSV format support
  - Up to 50,000 profiles per export
  - Export metadata with applied filters

- **Profile Deletion (GDPR)**
  - Right to erasure endpoint (DELETE /profiles/{id})
  - Cascading deletion of events, identifiers, consents, segment memberships
  - Optional event retention
  - Deletion audit logging

- **Event Statistics & Analytics**
  - Event statistics endpoint with period-based analysis (GET /events/statistics)
  - Event trends with period-over-period comparison (GET /events/trends)
  - Profile statistics with lifecycle and coverage metrics (GET /profiles/statistics)
  - Event volume by name and source
  - Daily event volume trends
  - EMQ score distribution analysis
  - Profile lifecycle distribution
  - Email/phone coverage percentages
  - Customer conversion rates
  - Revenue statistics (total, average, max)
  - React Query hooks for real-time dashboard integration

- **Async Computation (Celery Tasks)**
  - Background segment computation with rule evaluation
  - Async RFM calculation for all tenant profiles
  - Computed traits batch processing
  - Funnel metrics computation with step analysis
  - Scheduled refresh for segments and funnels
  - Task routing to dedicated CDP queue
  - Exponential backoff retry with max 3 attempts
  - Real-time event publishing on completion
  - Beat schedule: segments hourly, funnels every 2 hours

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
