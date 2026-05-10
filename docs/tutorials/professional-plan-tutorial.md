# Stratum AI - Professional Plan Tutorial

**Version:** 1.0.0
**Last Updated:** January 2026
**Estimated Time:** 45 minutes

---

## Welcome to Stratum AI Professional Plan

This tutorial covers all features available in the **Professional Plan**, building on the Starter Plan capabilities. You'll learn to:

- Build and analyze conversion funnels
- Create computed traits for dynamic segmentation
- Access Trust Gate audit logs
- Use action dry-run mode for safe testing
- Integrate with Pipedrive CRM
- Advanced CDP segmentation

---

## Table of Contents

1. [Professional Plan Overview](#1-professional-plan-overview)
2. [Funnel Builder](#2-funnel-builder)
3. [Computed Traits](#3-computed-traits)
4. [Trust Gate Audit Logs](#4-trust-gate-audit-logs)
5. [Action Dry-Run Mode](#5-action-dry-run-mode)
6. [Pipedrive CRM Integration](#6-pipedrive-crm-integration)
7. [Advanced CDP Features](#7-advanced-cdp-features)
8. [Next Steps](#8-next-steps)

---

## 1. Professional Plan Overview

### 1.1 What's Included

The Professional Plan includes everything in Starter, plus:

| Feature | Description |
|---------|-------------|
| Funnel Builder | Visualize and analyze conversion funnels |
| Computed Traits | Create dynamic customer attributes |
| Trust Gate Audit Logs | Full audit trail of automation decisions |
| Action Dry-Run | Test automations safely before execution |
| Pipedrive CRM | Bi-directional CRM sync |
| Advanced Segments | Complex segmentation rules |

### 1.2 Plan Limits

| Resource | Professional Limit |
|----------|-------------------|
| Ad Accounts | 15 |
| Team Members | 10 |
| Data Retention | 180 days |
| API Requests | 50,000/month |
| Custom Segments | 50 |
| Computed Traits | 25 |
| CRM Connections | 1 (Pipedrive) |

---

## 2. Funnel Builder

### 2.1 What is Funnel Analysis?

Funnel analysis helps you understand how customers move through your conversion process, identifying where they drop off and opportunities for optimization.

### 2.2 Accessing the Funnel Builder

Navigate to **CDP > Funnels** (`/dashboard/cdp/funnels`)

### 2.3 Creating Your First Funnel

**Step 1: Define Funnel Steps**

1. Click **Create Funnel**
2. Enter a funnel name (e.g., "Purchase Funnel")
3. Add steps in order:

```
Example E-commerce Funnel:
Step 1: page_view (Landing Page)
Step 2: view_content (Product Page)
Step 3: add_to_cart
Step 4: initiate_checkout
Step 5: purchase
```

**Step 2: Configure Step Settings**

For each step, configure:
- **Event Name**: The event that qualifies for this step
- **Event Properties** (optional): Filter by specific properties
- **Time Window**: Maximum time to complete funnel

**Step 3: Set Analysis Parameters**

| Parameter | Description | Recommended |
|-----------|-------------|-------------|
| Conversion Window | Max time from first to last step | 7-30 days |
| Counting Method | Unique users vs. total events | Unique users |
| Date Range | Analysis period | Last 30 days |

### 2.4 Understanding Funnel Metrics

| Metric | Definition |
|--------|------------|
| Conversion Rate | % completing the funnel |
| Drop-off Rate | % leaving at each step |
| Avg. Time to Convert | Average completion time |
| Step Conversion | % moving to next step |

### 2.5 Funnel Visualization

The funnel visualization shows:
- **Bar Chart**: Users at each step
- **Drop-off Indicators**: Red arrows showing losses
- **Conversion Percentages**: Step-to-step rates

**Example Output:**
```
Step 1: Page View       10,000 users (100%)
    ↓ 60% convert, 40% drop-off
Step 2: View Content     6,000 users (60%)
    ↓ 50% convert, 50% drop-off
Step 3: Add to Cart      3,000 users (30%)
    ↓ 40% convert, 60% drop-off
Step 4: Checkout         1,200 users (12%)
    ↓ 75% convert, 25% drop-off
Step 5: Purchase           900 users (9%)

Overall Conversion: 9%
```

### 2.6 Funnel Breakdown

Segment your funnel by:
- **Platform**: Meta vs. Google traffic
- **Device**: Mobile vs. Desktop
- **Campaign**: Specific campaign performance
- **Segment**: CDP segments

### 2.7 Funnel Insights

The AI-powered insights feature identifies:
- Steps with unusually high drop-off
- Time periods with poor performance
- Segments that convert better/worse
- Recommended optimizations

---

## 3. Computed Traits

### 3.1 What are Computed Traits?

Computed Traits are dynamic customer attributes calculated from behavior data. They automatically update as new events arrive.

### 3.2 Accessing Computed Traits

Navigate to **CDP > Computed Traits** (`/dashboard/cdp/computed-traits`)

### 3.3 Creating a Computed Trait

**Step 1: Choose Trait Type**

| Type | Description | Example |
|------|-------------|---------|
| Aggregation | Sum, count, average | Total purchases |
| Most Frequent | Mode value | Favorite category |
| First/Last | Temporal value | First purchase date |
| Unique Count | Distinct values | Products viewed |

**Step 2: Configure the Trait**

Example: Creating "Total Spend (30 Days)"

```yaml
Name: total_spend_30d
Type: Aggregation
Aggregation: SUM
Event: purchase
Property: revenue
Time Window: 30 days
Update Frequency: Daily
```

**Step 3: Set Conditions (Optional)**

Add filters to narrow the calculation:
- Event properties
- Time constraints
- Profile attributes

### 3.4 Computed Trait Examples

**Example 1: Purchase Frequency**
```yaml
Name: purchase_frequency_30d
Type: Aggregation
Aggregation: COUNT
Event: purchase
Time Window: 30 days
```

**Example 2: Favorite Product Category**
```yaml
Name: favorite_category
Type: Most Frequent
Event: purchase
Property: category
Time Window: 90 days
```

**Example 3: Days Since Last Purchase**
```yaml
Name: days_since_purchase
Type: Last
Event: purchase
Property: timestamp
Calculation: DAYS_SINCE
```

**Example 4: Average Order Value**
```yaml
Name: average_order_value
Type: Aggregation
Aggregation: AVG
Event: purchase
Property: revenue
Time Window: All time
```

### 3.5 Using Computed Traits

Once created, computed traits can be used in:
- **Segmentation**: Build segments based on trait values
- **Personalization**: Tailor messaging
- **Analysis**: Group profiles by trait
- **CRM Sync**: Push traits to Pipedrive

### 3.6 Trait Management

- **Backfill**: Calculate trait for existing profiles
- **Preview**: See sample calculations before saving
- **Versioning**: Track trait definition changes
- **Dependencies**: View segments using this trait

---

## 4. Trust Gate Audit Logs

### 4.1 What are Trust Gate Audit Logs?

Audit logs provide a complete history of all Trust Gate decisions, showing when and why automations were allowed or blocked.

### 4.2 Accessing Audit Logs

Navigate to **Data Quality > Audit Logs** or through the Trust Layer section.

### 4.3 Audit Log Entry Structure

Each log entry contains:

| Field | Description |
|-------|-------------|
| Timestamp | When the decision was made |
| Action Type | What automation was attempted |
| Decision | PASS, HOLD, or BLOCK |
| Signal Health | Health score at decision time |
| Reason | Explanation for the decision |
| Entity | Campaign/Ad Set/Creative affected |
| User | Who initiated (if manual) |

### 4.4 Understanding Decisions

**PASS Decision:**
```json
{
  "decision": "PASS",
  "signal_health": 85,
  "reason": "All signals healthy, automation approved",
  "action": "budget_increase",
  "entity": "Campaign: Summer Sale 2026",
  "change": "+15% budget"
}
```

**HOLD Decision:**
```json
{
  "decision": "HOLD",
  "signal_health": 62,
  "reason": "Signal health below threshold (70), action queued for manual review",
  "action": "pause_adset",
  "entity": "Ad Set: Retargeting - Cart Abandoners"
}
```

**BLOCK Decision:**
```json
{
  "decision": "BLOCK",
  "signal_health": 35,
  "reason": "Critical signal degradation, automation blocked",
  "action": "scale_budget",
  "entity": "Campaign: Brand Awareness Q1",
  "blocked_reason": "EMQ score 3.2 (below 4.0 threshold)"
}
```

### 4.5 Filtering Audit Logs

Filter logs by:
- **Date Range**: Last 7 days, 30 days, custom
- **Decision Type**: PASS, HOLD, BLOCK
- **Action Type**: Budget changes, pauses, etc.
- **Entity**: Specific campaigns or ad sets
- **Signal Health Range**: e.g., only show < 70

### 4.6 Audit Log Analytics

The dashboard shows:
- Decision distribution (pie chart)
- Decision trends over time
- Most common block reasons
- Actions by entity type

### 4.7 Exporting Audit Logs

Export for compliance or analysis:
1. Set your filters
2. Click **Export**
3. Choose format (CSV, JSON, PDF)
4. Download or schedule delivery

---

## 5. Action Dry-Run Mode

### 5.1 What is Dry-Run Mode?

Dry-run mode lets you test automation actions without actually executing them. See exactly what would happen before committing.

### 5.2 Enabling Dry-Run Mode

**Method 1: Global Setting**
1. Go to **Settings > Autopilot**
2. Toggle **Dry-Run Mode** ON
3. All automations will simulate only

**Method 2: Per-Action**
1. Navigate to **Autopilot > Action Queue**
2. Find the action you want to test
3. Click **Test (Dry-Run)** instead of **Approve**

### 5.3 Dry-Run Results

A dry-run shows:

```
DRY-RUN RESULTS
===============
Action: Increase budget by 20%
Entity: Campaign "Holiday Promo 2026"
Current Budget: $500/day
Proposed Budget: $600/day

Pre-flight Checks:
✓ Signal Health: 88 (PASS)
✓ Budget Cap: $600 < $1000 limit (PASS)
✓ Daily Spend Limit: $600 < $2000 (PASS)
✓ Cooldown Period: 48 hours since last change (PASS)

Projected Impact:
- Estimated additional spend: $100/day
- Estimated additional conversions: 8-12
- Projected ROAS change: +0.2 to -0.1

Platform Validation:
✓ Meta API: Ready to accept change
✓ No conflicting rules detected

Result: Action WOULD EXECUTE if approved
```

### 5.4 Dry-Run Scenarios

Use dry-run to test:
- New autopilot rules before enabling
- Budget changes on high-spend campaigns
- Pause actions during peak periods
- Bid adjustments on competitive auctions

### 5.5 Dry-Run Reporting

Access dry-run history at **Autopilot > Dry-Run History**:
- View all past dry-run tests
- Compare predicted vs. actual outcomes
- Identify rules that often fail checks

---

## 6. Pipedrive CRM Integration

### 6.1 Overview

Sync your Stratum AI data with Pipedrive CRM for a unified view of leads and customers.

### 6.2 Connecting Pipedrive

**Step 1: Get API Credentials**
1. Log into Pipedrive
2. Go to **Settings > Personal Preferences > API**
3. Copy your API Token

**Step 2: Connect in Stratum**
1. Navigate to **Settings > Integrations > CRM**
2. Click **Connect Pipedrive**
3. Enter your API Token
4. Click **Authorize**
5. Select data to sync

### 6.3 Data Sync Options

| Stratum Data | Pipedrive Object | Direction |
|--------------|------------------|-----------|
| CDP Profiles | Persons | Bidirectional |
| Events | Activities | Stratum → Pipedrive |
| Segments | Labels/Filters | Stratum → Pipedrive |
| Attribution | Custom Fields | Stratum → Pipedrive |
| Deals | Revenue Data | Pipedrive → Stratum |

### 6.4 Field Mapping

Map Stratum fields to Pipedrive:

| Stratum Field | Pipedrive Field |
|---------------|-----------------|
| email | Email |
| first_name | First Name |
| last_name | Last Name |
| phone | Phone |
| total_spend | Custom: LTV |
| last_purchase_date | Custom: Last Purchase |
| lifecycle_stage | Label |

### 6.5 Setting Up Attribution Fields

Create custom fields in Pipedrive for attribution:

1. In Pipedrive, go to **Settings > Data Fields > Person**
2. Add custom fields:
   - Stratum - Ad Platform (Text)
   - Stratum - Campaign (Text)
   - Stratum - First Touch Source (Text)
   - Stratum - Attribution Revenue (Currency)
3. Map these in Stratum's field mapping

### 6.6 Sync Schedule

Configure sync frequency:
- **Real-time**: Instant sync on changes (premium)
- **Hourly**: Sync every hour
- **Daily**: Once per day (recommended)

### 6.7 Sync Monitoring

Monitor sync health at **Integrations > Pipedrive > Sync Status**:
- Last sync time
- Records synced
- Errors and warnings
- Sync queue depth

---

## 7. Advanced CDP Features

### 7.1 Advanced Segmentation

Professional Plan unlocks advanced segment conditions:

**Behavioral Conditions:**
- Performed event X times in Y days
- Did NOT perform event in last N days
- Sequential events (A then B then C)
- Event property comparisons

**Computed Trait Conditions:**
- Trait value ranges
- Trait comparisons
- Trait existence

**Example: High-Value At-Risk Segment**
```
Conditions (AND):
- total_spend_lifetime > $500
- days_since_purchase > 60
- email_open_rate_30d < 10%
- NOT performed: purchase in last 90 days
```

### 7.2 Segment Overlap Analysis

Understand how segments relate:
1. Go to **CDP > Segments**
2. Select multiple segments
3. Click **Analyze Overlap**
4. View Venn diagram and overlap statistics

### 7.3 Segment Forecasting

Predict segment growth:
1. Select a segment
2. Click **Forecast**
3. View projected size over next 30/60/90 days
4. Based on historical entry/exit rates

---

## 8. Next Steps

### 8.1 Maximizing Professional Plan

- **Build funnels** for your key conversion paths
- **Create computed traits** for customer scoring
- **Review audit logs** weekly for optimization insights
- **Use dry-run** before enabling new automations
- **Integrate Pipedrive** for sales team alignment

### 8.2 Upgrading to Enterprise

Ready for maximum power? **Enterprise Plan** adds:
- Consent Management for compliance
- Real-time Streaming events
- Predictive Churn modeling
- Custom Autopilot Rules
- Salesforce CRM integration
- LinkedIn Lead Gen integration
- Dashboard Customization
- Custom Report Builder

[Compare Plans](/pricing) | [Contact Sales](mailto:sales@stratum.ai)

---

## Quick Reference

### Professional Plan Feature Flags

```python
# Features enabled in Professional Plan
funnel_builder: True
computed_traits: True
trust_audit_logs: True
action_dry_run: True
crm_pipedrive: True
advanced_segments: True

# Plus all Starter features
rfm_analysis: True
signal_health_history: True
slack_notifications: True
dashboard_export: True
```

### API Endpoints (Professional)

```
# Funnels
GET  /api/v1/cdp/funnels
POST /api/v1/cdp/funnels
GET  /api/v1/cdp/funnels/{id}/analyze

# Computed Traits
GET  /api/v1/cdp/computed-traits
POST /api/v1/cdp/computed-traits
POST /api/v1/cdp/computed-traits/{id}/backfill

# Audit Logs
GET  /api/v1/trust-layer/audit-logs
GET  /api/v1/trust-layer/audit-logs/export

# Dry-Run
POST /api/v1/autopilot/actions/{id}/dry-run

# Pipedrive
POST /api/v1/integrations/pipedrive/connect
GET  /api/v1/integrations/pipedrive/status
POST /api/v1/integrations/pipedrive/sync
```

### Support Resources

- **Documentation:** [docs.stratum.ai](https://docs.stratum.ai)
- **Help Center:** [help.stratum.ai](https://help.stratum.ai)
- **Email Support:** support@stratum.ai (24-hour response)
- **Chat Support:** Available in-app (business hours)

---

**Congratulations!** You've mastered the Professional Plan features. You're now equipped to run sophisticated marketing operations with Stratum AI.

---

*Need help? Contact support@stratum.ai or chat with us in-app.*
