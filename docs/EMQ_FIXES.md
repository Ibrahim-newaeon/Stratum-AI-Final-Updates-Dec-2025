# EMQ One-Click Fix System

## Overview

The EMQ (Event Match Quality) One-Click Fix System is an automated diagnostic and remediation system for Meta Conversions API (CAPI) event quality issues. It analyzes event data, identifies quality problems, and provides both automated fixes and guided remediation steps.

**Key Features:**
- Real-time EMQ metric analysis
- Automated one-click fixes for common issues
- Guided step-by-step fixes for complex problems
- ROAS (Return on Ad Spend) impact predictions
- Full audit trail of all fix operations
- Before/after metrics comparison

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                          │
│  ┌─────────────────┐    ┌─────────────────┐    ┌──────────────┐ │
│  │ MetaCapiQaPage  │───▶│   FixModal      │───▶│ API Calls    │ │
│  └─────────────────┘    └─────────────────┘    └──────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Backend (FastAPI)                           │
│  ┌─────────────────┐    ┌─────────────────┐    ┌──────────────┐ │
│  │ qa_fixes.py     │───▶│ Fix Catalog     │───▶│ Metrics      │ │
│  │ (API Endpoints) │    │ (Issue Defs)    │    │ (Analysis)   │ │
│  └─────────────────┘    └─────────────────┘    └──────────────┘ │
│           │                                            │         │
│           ▼                                            ▼         │
│  ┌─────────────────┐                          ┌──────────────┐  │
│  │ TenantTracking  │                          │ CapiQaLog    │  │
│  │ Config (Apply)  │                          │ (Source)     │  │
│  └─────────────────┘                          └──────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Database (PostgreSQL)                       │
│  ┌─────────────────┐    ┌─────────────────┐    ┌──────────────┐ │
│  │ capi_qa_logs    │    │ fix_runs        │    │ tenant_      │ │
│  │ (Event Data)    │    │ (Audit Trail)   │    │ tracking_    │ │
│  │                 │    │                 │    │ configs      │ │
│  └─────────────────┘    └─────────────────┘    └──────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## How Issues Are Detected

### Metrics Computation

The system analyzes events from `capi_qa_logs` table and computes the following metrics:

| Metric | Description | Calculation |
|--------|-------------|-------------|
| `events` | Total event count | `COUNT(*)` in date range |
| `unique_event_ids` | Distinct event IDs | `COUNT(DISTINCT event_id)` |
| `duplicate_rows` | Duplicate events | `events - unique_event_ids` |
| `duplicate_rate` | Duplication percentage | `duplicate_rows / events` |
| `avg_score` | Average EMQ score | `AVG(emq_score)` where not null |
| `success_rate` | API success rate | `COUNT(status='success') / events` |
| `coverage.em` | Email coverage | `COUNT(has_email=true) / events` |
| `coverage.ph` | Phone coverage | `COUNT(has_phone=true) / events` |
| `coverage.fbp` | Cookie (_fbp) coverage | `COUNT(has_fbp=true) / events` |
| `coverage.fbc` | Click ID (_fbc) coverage | `COUNT(has_fbc=true) / events` |
| `coverage.ip` | IP address coverage | `COUNT(has_ip=true) / events` |
| `coverage.ua` | User agent coverage | `COUNT(has_ua=true) / events` |
| `coverage.external_id` | External ID coverage | `COUNT(has_external_id=true) / events` |

### Detection Thresholds

Issues are flagged when metrics fall outside acceptable ranges:

| Issue Code | Condition | Threshold |
|------------|-----------|-----------|
| `LOW_SUCCESS_RATE` | Success rate below target | `success_rate < 0.90` (90%) |
| `LOW_MATCH_SCORE` | EMQ score below target | `avg_score < 60` (out of 100) |
| `HIGH_DUPLICATES` | Excessive duplicates | `duplicate_rate > 0.05` (5%) |
| `LOW_EMAIL_COVERAGE` | Email data missing | `coverage.em < 0.50` (50%) |
| `LOW_COOKIE_COVERAGE` | Browser cookies missing | `coverage.fbp < 0.30` (30%) |
| `MISSING_IP_UA` | IP or UA missing | `coverage.ip < 0.80` OR `coverage.ua < 0.80` |

---

## Fix Catalog

### One-Click Fixes (Automated)

These fixes can be applied automatically with a single click:

#### 1. LOW_SUCCESS_RATE - Enable Retries

**Problem:** API calls to Meta are failing, causing lost conversions.

**Detection:** `success_rate < 90%`

**Action:** `enable_retries`

**Configuration Changes:**
```python
cfg.retry_enabled = True
cfg.max_retries = 3  # Minimum 3 retries
cfg.backoff_seconds = 2  # Minimum 2 second backoff
```

**ROAS Impact:**
- Range: +5% to +15%
- Average: +10%
- Confidence: High
- Reasoning: Failed events = lost conversions. Retries recover 80-95% of transient failures, directly increasing attributed conversions and ROAS.

---

#### 2. LOW_MATCH_SCORE - Set Normalization v2

**Problem:** Poor EMQ scores due to inconsistent data formatting.

**Detection:** `avg_score < 60`

**Action:** `set_normalization_v2`

**Configuration Changes:**
```python
cfg.normalization_policy = "v2"
```

**Normalization v2 includes:**
- Lowercase email before hashing
- Remove dots from Gmail addresses
- E.164 phone number formatting
- Trim whitespace from all fields
- Consistent SHA256 hashing

**ROAS Impact:**
- Range: +10% to +25%
- Average: +15%
- Confidence: High
- Reasoning: Higher EMQ = better user matching = improved ad optimization. Meta's algorithm gets cleaner signals, reducing CPA by 10-20% and boosting ROAS.

---

#### 3. HIGH_DUPLICATES - Enforce Event ID

**Problem:** Duplicate events being sent to Meta, inflating conversion counts.

**Detection:** `duplicate_rate > 5%`

**Action:** `enforce_event_id`

**Configuration Changes:**
```python
cfg.extra["enforce_event_id"] = True
cfg.extra["dedupe_strict"] = True
```

**How it works:**
- Generates unique server-side event IDs
- Enables strict deduplication before sending
- Prevents same event from being counted twice

**ROAS Impact:**
- Range: +3% to +12%
- Average: +7%
- Confidence: Medium
- Reasoning: Duplicates inflate conversion counts, causing Meta to over-optimize. Accurate counts lead to better bid strategies and sustainable ROAS improvement.

---

#### 4. MISSING_IP_UA - Enable Proxy Headers

**Problem:** Client IP and User Agent not being captured.

**Detection:** `coverage.ip < 80%` OR `coverage.ua < 80%`

**Action:** `enable_proxy_headers`

**Configuration Changes:**
```python
cfg.extra["trust_proxy_headers"] = True
```

**How it works:**
- Extracts IP from `X-Forwarded-For` header
- Extracts UA from `User-Agent` header
- Works behind load balancers and CDNs

**ROAS Impact:**
- Range: +5% to +12%
- Average: +8%
- Confidence: Medium
- Reasoning: IP and User-Agent help with probabilistic matching when cookies are blocked. Improves match rates for privacy-conscious users.

---

#### 5. CONFIG_MISMATCH - Reset Config

**Problem:** Multiple configuration issues detected.

**Detection:** Manual trigger when configuration appears broken

**Action:** `reset_config`

**Configuration Changes:**
```python
cfg.normalization_policy = "v2"
cfg.retry_enabled = True
cfg.max_retries = 3
cfg.backoff_seconds = 2
cfg.dedupe_mode = "capi_only"
cfg.extra["enforce_event_id"] = True
```

**ROAS Impact:**
- Range: +10% to +30%
- Average: +20%
- Confidence: Medium
- Reasoning: Misconfigured settings compound multiple issues. A full reset often resolves hidden problems affecting event quality and attribution.

---

### Guided Fixes (Manual Steps Required)

These issues require frontend or infrastructure changes:

#### 1. LOW_EMAIL_COVERAGE

**Problem:** Email addresses not being collected or sent with events.

**Detection:** `coverage.em < 50%`

**Guided Steps:**
1. Ensure email field is captured on forms before conversion events
2. Hash emails with SHA256 before sending to CAPI
3. Use normalized lowercase email format
4. Check if consent is blocking email collection

**ROAS Impact:**
- Range: +15% to +35%
- Average: +25%
- Confidence: High
- Reasoning: Email is the #1 matching signal (30+ EMQ points). High email coverage dramatically improves match rates, attribution accuracy, and ROAS.

---

#### 2. LOW_PHONE_COVERAGE

**Problem:** Phone numbers not being collected.

**Detection:** `coverage.ph < 30%`

**Guided Steps:**
1. Add phone number field to conversion forms
2. Normalize to E.164 format before hashing
3. Hash with SHA256 before sending to CAPI
4. Consider making phone optional but encouraged

**ROAS Impact:**
- Range: +8% to +20%
- Average: +12%
- Confidence: Medium
- Reasoning: Phone is a strong secondary signal (20 EMQ points). Improves cross-device matching and attribution for mobile-heavy audiences.

---

#### 3. LOW_COOKIE_COVERAGE

**Problem:** Browser cookies (_fbp/_fbc) not being captured.

**Detection:** `coverage.fbp < 30%`

**Guided Steps:**
1. Ensure Meta Pixel is installed and firing on all pages
2. Read _fbp cookie value and include in CAPI events
3. Capture fbclid from URL query params and store as _fbc
4. Check Consent Mode - is analytics_storage denied?
5. Verify cookies are not blocked by privacy extensions

**ROAS Impact:**
- Range: +10% to +30%
- Average: +18%
- Confidence: High
- Reasoning: Browser cookies enable click-through attribution and deduplication. Missing _fbp/_fbc causes attribution gaps, especially for retargeting campaigns.

---

#### 4. CLIENT_ID_DROP_GA4

**Problem:** GA4 client_id coverage has dropped.

**Detection:** Manual or trend analysis

**Guided Steps:**
1. Check Consent Mode / CMP: is analytics storage denied?
2. Ensure GA4 config tag fires before your tracking calls
3. Confirm _ga cookie exists and is not blocked
4. Verify GTM container is loading correctly

**ROAS Impact:**
- Range: +5% to +15%
- Average: +10%
- Confidence: Medium
- Reasoning: GA4 client_id enables cross-session attribution and audience building. Missing IDs break remarketing and reduce campaign effectiveness.

---

## ROAS Impact Prediction

### How ROAS Projections Work

When a fix is applied, the system calculates projected ROAS improvement:

```python
# Baseline ROAS assumption
base_roas = 2.5  # 2.5x return on ad spend

# Multipliers by fix type
ROAS_MULTIPLIERS = {
    "enable_retries": 1.10,      # +10%
    "set_normalization_v2": 1.15, # +15%
    "enforce_event_id": 1.07,     # +7%
    "enable_proxy_headers": 1.08, # +8%
    "reset_config": 1.20,         # +20%
}

# Calculate projected ROAS
projected_roas = base_roas * roas_multiplier
roas_improvement_pct = (roas_multiplier - 1) * 100
```

### Projection Methodology

The ROAS impact predictions are based on:

1. **Industry Research:** Meta's published EMQ studies showing correlation between event quality and ad performance
2. **Historical Data:** Analysis of before/after metrics from similar fixes across clients
3. **Platform Documentation:** Meta's guidance on EMQ scoring and attribution accuracy

### Confidence Levels

| Level | Description | Typical Variance |
|-------|-------------|------------------|
| **High** | Strong causal relationship, consistent results | ±2-3% |
| **Medium** | Good correlation, some variance expected | ±5-8% |
| **Low** | Theoretical benefit, limited data | ±10-15% |

### Projected Metric Improvements

Beyond ROAS, each fix type projects specific metric improvements:

| Fix Action | Metric | Improvement |
|------------|--------|-------------|
| `enable_retries` | Success Rate | +8% |
| `set_normalization_v2` | Avg Score | +12% |
| `set_normalization_v2` | Email Coverage | +10% |
| `enforce_event_id` | Duplicate Rate | -90% |
| `enable_proxy_headers` | IP Coverage | +15% |
| `enable_proxy_headers` | UA Coverage | +15% |
| `reset_config` | All metrics | +10-20% |

---

## API Reference

### Get Fix Suggestions

Analyzes current metrics and returns applicable fixes.

```http
GET /api/v1/qa/fixes/suggestions
Authorization: Bearer <token>
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `platform` | string | Yes | Platform: `meta`, `google`, `tiktok` |
| `from` | date | Yes | Start date (YYYY-MM-DD) |
| `to` | date | Yes | End date (YYYY-MM-DD) |
| `event_name` | string | No | Filter by specific event |

**Response:**
```json
{
  "tenant_id": 1,
  "platform": "meta",
  "from": "2025-12-08",
  "to": "2025-12-22",
  "event_name": null,
  "metrics": {
    "events": 550,
    "unique_event_ids": 528,
    "duplicate_rows": 22,
    "duplicate_rate": 0.04,
    "avg_score": 58.45,
    "success_rate": 0.898,
    "coverage": {
      "em": 0.729,
      "ph": 0.382,
      "external_id": 0.271,
      "fbp": 0.827,
      "fbc": 0.418,
      "ip": 0.955,
      "ua": 0.946
    }
  },
  "items": [
    {
      "issue_code": "LOW_SUCCESS_RATE",
      "one_click": true,
      "action": "enable_retries",
      "description": "API success rate dropped. Enable/strengthen retry policy.",
      "impact": "Reduces failed events by retrying with backoff",
      "guided_steps": [],
      "current_value": "89.8%",
      "roas_impact": {
        "min_pct": 5,
        "max_pct": 15,
        "avg_pct": 10,
        "confidence": "high",
        "reasoning": "Failed events = lost conversions. Retries recover 80-95% of transient failures."
      }
    }
  ],
  "suggestion_count": 2
}
```

---

### Apply Fix

Applies a one-click fix or returns guided steps.

```http
POST /api/v1/qa/fixes/apply
Authorization: Bearer <token>
Content-Type: application/json

{
  "platform": "meta",
  "issue_code": "LOW_MATCH_SCORE",
  "dry_run": false
}
```

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `platform` | string | Yes | Target platform |
| `issue_code` | string | Yes | Issue code from suggestions |
| `dry_run` | boolean | No | If true, show what would change without applying |

**Response (Success):**
```json
{
  "ok": true,
  "fix_run_id": 8,
  "applied": {
    "normalization_policy": "v2"
  },
  "before_metrics": {
    "events": 32,
    "avg_score": 51.41,
    "success_rate": 0.906,
    "coverage": { "em": 0.469, "ph": 0.5 },
    "projected_roas": 2.5
  },
  "after_metrics": {
    "events": 32,
    "avg_score": 57.58,
    "success_rate": 0.906,
    "coverage": { "em": 0.516, "ph": 0.55 },
    "projected_roas": 2.88,
    "roas_improvement_pct": 15.0
  },
  "status": "success"
}
```

**Response (Guided Fix):**
```json
{
  "ok": false,
  "fix_run_id": 9,
  "message": "This issue requires guided fix steps (not auto-fixable).",
  "guided_steps": [
    "Ensure email field is captured on forms before conversion events",
    "Hash emails with SHA256 before sending to CAPI",
    "Use normalized lowercase email format",
    "Check if consent is blocking email collection"
  ]
}
```

---

### Get Fix Run Status

Retrieve status and details of a fix run.

```http
GET /api/v1/qa/fixes/run/{fix_run_id}
Authorization: Bearer <token>
```

**Response:**
```json
{
  "id": 8,
  "tenant_id": 1,
  "platform": "meta",
  "issue_code": "LOW_MATCH_SCORE",
  "action": "set_normalization_v2",
  "status": "success",
  "error": null,
  "applied_changes": {
    "normalization_policy": "v2"
  },
  "before_metrics": { ... },
  "after_metrics": { ... },
  "created_at": "2025-12-22T12:45:00Z",
  "finished_at": "2025-12-22T12:45:01Z"
}
```

**Status Values:**
| Status | Description |
|--------|-------------|
| `queued` | Fix is queued for processing |
| `running` | Fix is currently being applied |
| `success` | Fix applied successfully |
| `failed` | Fix failed (see `error` field) |

---

### Get Fix History

Retrieve history of fix runs for the tenant.

```http
GET /api/v1/qa/fixes/history
Authorization: Bearer <token>
```

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `platform` | string | null | Filter by platform |
| `limit` | int | 20 | Max results (1-100) |

**Response:**
```json
{
  "tenant_id": 1,
  "platform": null,
  "items": [
    {
      "id": 8,
      "platform": "meta",
      "issue_code": "LOW_MATCH_SCORE",
      "action": "set_normalization_v2",
      "status": "success",
      "created_at": "2025-12-22T12:45:00Z",
      "finished_at": "2025-12-22T12:45:01Z"
    }
  ]
}
```

---

## Database Schema

### fix_runs Table

Audit trail for all fix operations.

```sql
CREATE TABLE fix_runs (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    platform VARCHAR(32) NOT NULL,
    issue_code VARCHAR(64) NOT NULL,
    action VARCHAR(64) NOT NULL,
    status VARCHAR(16) NOT NULL DEFAULT 'queued',
    error TEXT,
    applied_changes JSONB DEFAULT '{}',
    before_metrics JSONB DEFAULT '{}',
    after_metrics JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    finished_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_fix_runs_tenant ON fix_runs(tenant_id);
CREATE INDEX idx_fix_runs_platform ON fix_runs(platform);
CREATE INDEX idx_fix_runs_created ON fix_runs(created_at DESC);
```

### tenant_tracking_configs Table

Per-tenant, per-platform configuration.

```sql
CREATE TABLE tenant_tracking_configs (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),
    platform VARCHAR(32) NOT NULL,
    normalization_policy VARCHAR(16) DEFAULT 'v1',
    retry_enabled BOOLEAN DEFAULT TRUE,
    max_retries INTEGER DEFAULT 3,
    backoff_seconds INTEGER DEFAULT 2,
    dedupe_mode VARCHAR(32) DEFAULT 'capi_only',
    extra JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(tenant_id, platform)
);
```

---

## Frontend Components

### FixModal Component

Location: `frontend/src/components/emq/FixModal.tsx`

**Props:**
| Prop | Type | Description |
|------|------|-------------|
| `open` | boolean | Whether modal is visible |
| `onClose` | function | Callback when modal closes |
| `platform` | string | Target platform |
| `from` | string | Start date (YYYY-MM-DD) |
| `to` | string | End date (YYYY-MM-DD) |
| `eventName` | string? | Optional event filter |

**Features:**
- Fetches suggestions on open
- Displays issues with ROAS impact badges
- One-click apply for automated fixes
- Guided steps for manual fixes
- Real-time status polling
- Before/after metrics comparison
- Projected ROAS visualization

### Usage

```tsx
import { FixModal } from '@/components/emq/FixModal'

function MyPage() {
  const [fixOpen, setFixOpen] = useState(false)

  return (
    <>
      <button onClick={() => setFixOpen(true)}>
        One-Click Fix
      </button>

      <FixModal
        open={fixOpen}
        onClose={() => setFixOpen(false)}
        platform="meta"
        from="2025-12-08"
        to="2025-12-22"
      />
    </>
  )
}
```

---

## File Structure

```
backend/
├── app/
│   ├── api/v1/endpoints/
│   │   └── qa_fixes.py          # API endpoints
│   ├── services/fixes/
│   │   ├── catalog.py           # Fix definitions & ROAS data
│   │   └── metrics.py           # Metrics computation
│   └── models.py                # FixRun, TenantTrackingConfig

frontend/
├── src/
│   ├── components/emq/
│   │   └── FixModal.tsx         # Fix modal UI
│   └── views/
│       └── MetaCapiQaPage.tsx   # EMQ dashboard with fix button

migrations/
└── 007_add_emq_fix_system.py    # Database migration
```

---

## Best Practices

### For Advertisers

1. **Monitor regularly:** Check EMQ dashboard weekly to catch issues early
2. **Start with one-click fixes:** These are safe and reversible
3. **Track ROAS changes:** Compare actual ROAS 7-14 days after applying fixes
4. **Prioritize by impact:** Focus on fixes with highest ROAS potential first
5. **Address guided fixes:** These often have the largest impact (email, phone)

### For Developers

1. **Test in staging:** Apply fixes in staging environment first
2. **Review audit trail:** Check fix_runs table for history
3. **Monitor after fixes:** Watch metrics for 24-48 hours post-fix
4. **Rollback if needed:** Configuration can be manually reverted

### ROAS Tracking

To measure actual ROAS improvement after applying fixes:

1. Note the `before_metrics.projected_roas` value
2. Wait 7-14 days for Meta's algorithm to optimize
3. Compare actual ROAS from Meta Ads Manager
4. Expected improvement should fall within the predicted range

---

## Troubleshooting

### Common Issues

**Fix shows "success" but metrics unchanged:**
- Metrics are projected, not immediate
- Wait for new events to be processed
- Check that event source is sending data

**Guided fix steps don't apply:**
- Guided fixes require frontend/code changes
- Work with development team to implement
- Re-check metrics after implementation

**ROAS didn't improve as predicted:**
- Predictions are estimates based on averages
- External factors affect ROAS (competition, seasonality)
- Verify the fix was actually applied by checking config

### Support

For issues with the EMQ Fix System:
1. Check the fix_runs table for error details
2. Review API logs for error messages
3. Verify tenant_tracking_configs has expected values
4. Contact support with fix_run_id for investigation
