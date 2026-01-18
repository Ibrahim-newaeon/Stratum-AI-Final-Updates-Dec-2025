# Stratum AI - Enterprise Plan Tutorial

**Version:** 1.0.0
**Last Updated:** January 2026
**Estimated Time:** 60 minutes

---

## Welcome to Stratum AI Enterprise Plan

This tutorial covers the advanced features exclusive to the **Enterprise Plan**. You'll master:

- Consent Management for GDPR/CCPA compliance
- Real-time Streaming event processing
- Predictive Churn modeling with ML
- Custom Autopilot Rules with advanced logic
- Salesforce CRM integration
- LinkedIn Lead Gen integration
- Dashboard Customization
- Custom Report Builder

---

## Table of Contents

1. [Enterprise Plan Overview](#1-enterprise-plan-overview)
2. [Consent Management](#2-consent-management)
3. [Real-Time Streaming](#3-real-time-streaming)
4. [Predictive Churn Model](#4-predictive-churn-model)
5. [Custom Autopilot Rules](#5-custom-autopilot-rules)
6. [Salesforce CRM Integration](#6-salesforce-crm-integration)
7. [LinkedIn Lead Gen Integration](#7-linkedin-lead-gen-integration)
8. [Dashboard Customization](#8-dashboard-customization)
9. [Custom Report Builder](#9-custom-report-builder)
10. [Enterprise Administration](#10-enterprise-administration)

---

## 1. Enterprise Plan Overview

### 1.1 What's Included

Enterprise includes everything in Professional, plus:

| Feature | Description |
|---------|-------------|
| Consent Management | GDPR/CCPA compliance tools |
| Real-Time Streaming | Sub-second event processing |
| Predictive Churn | ML-powered churn prediction |
| Custom Autopilot Rules | Build complex automation logic |
| Salesforce CRM | Full Salesforce integration |
| LinkedIn Lead Gen | Lead form integrations |
| Dashboard Customization | Custom widget layouts |
| Custom Report Builder | Build any report you need |

### 1.2 Enterprise Limits

| Resource | Enterprise Limit |
|----------|-----------------|
| Ad Accounts | Unlimited |
| Team Members | Unlimited |
| Data Retention | 365 days |
| API Requests | Unlimited |
| Custom Segments | Unlimited |
| Computed Traits | Unlimited |
| CRM Connections | All (Salesforce, Pipedrive, HubSpot, Zoho) |
| Custom Reports | Unlimited |
| Custom Dashboards | 20 |

### 1.3 Enterprise Support

- **Dedicated Success Manager**
- **Priority Support** (4-hour response SLA)
- **Custom Training Sessions**
- **Quarterly Business Reviews**
- **Custom Development** (upon request)

---

## 2. Consent Management

### 2.1 Overview

Consent Management ensures your data collection and processing complies with GDPR, CCPA, and other privacy regulations.

### 2.2 Accessing Consent Management

Navigate to **CDP > Consent** (`/dashboard/cdp/consent`)

### 2.3 Consent Categories

Define categories of consent:

| Category | Description | Example Uses |
|----------|-------------|--------------|
| Marketing | Marketing communications | Email campaigns, SMS |
| Analytics | Behavioral tracking | Event collection, profiling |
| Personalization | Content customization | Product recommendations |
| Advertising | Ad targeting | Audience sync, retargeting |
| Third-Party | External data sharing | CRM sync, partner data |

### 2.4 Setting Up Consent Collection

**Step 1: Configure Consent Banner**
```javascript
// Embed this on your website
StratumConsent.init({
  tenantId: 'your-tenant-id',
  categories: ['marketing', 'analytics', 'advertising'],
  position: 'bottom',
  theme: 'light',
  onConsent: (categories) => {
    console.log('Consented to:', categories);
  }
});
```

**Step 2: Record Consent Events**
```javascript
// When user gives consent
Stratum.track('consent_given', {
  categories: ['marketing', 'analytics'],
  source: 'cookie_banner',
  version: '2.0'
});
```

### 2.5 Consent Dashboard

The consent dashboard shows:
- Consent rates by category
- Consent trends over time
- Geographic breakdown
- Consent by acquisition source

**Key Metrics:**

| Metric | Description |
|--------|-------------|
| Consent Rate | % of visitors who consent |
| Full Consent | % who accept all categories |
| Partial Consent | % who accept some categories |
| Opt-Out Rate | % who decline all |

### 2.6 Enforcing Consent

Stratum automatically enforces consent:

| Category | Blocked if No Consent |
|----------|----------------------|
| Marketing | Email/SMS sends blocked |
| Analytics | Events not stored |
| Advertising | Audience sync blocked |
| Third-Party | CRM sync blocked |

### 2.7 Right to Be Forgotten (RTBF)

Handle deletion requests:

1. Navigate to **CDP > Profiles**
2. Search for the profile
3. Click **Privacy Actions > Delete Profile**
4. Confirm deletion
5. All data removed within 48 hours

**Bulk Deletion:**
```
POST /api/v1/cdp/profiles/delete-batch
{
  "profile_ids": ["id1", "id2", "id3"],
  "reason": "RTBF request",
  "reference": "TICKET-12345"
}
```

### 2.8 Data Export (DSAR)

Export user data for Data Subject Access Requests:

1. Go to **CDP > Profiles > {profile}**
2. Click **Export Profile Data**
3. Choose format (JSON, CSV)
4. All profile data, events, and traits included

---

## 3. Real-Time Streaming

### 3.1 Overview

Real-time streaming processes events in under 1 second, enabling immediate personalization and alerting.

### 3.2 Enabling Real-Time Streaming

1. Go to **Settings > Features**
2. Enable **Real-Time Streaming**
3. Configure stream endpoints

### 3.3 Real-Time Event Flow

```
Event Occurs → Stratum SDK → Stream Processor → Actions
    |                             |
    └─────────── < 1 second ──────┘
```

### 3.4 Real-Time Use Cases

**Instant Personalization:**
- Show relevant content based on just-viewed product
- Update recommendations in real-time
- Trigger live chat for high-intent visitors

**Immediate Alerts:**
- Notify sales when high-value prospect is active
- Alert support when churning customer visits
- Trigger retention offer for at-risk user

**Live Dashboards:**
- Real-time conversion tracking
- Live campaign performance
- Instant anomaly detection

### 3.5 Configuring Real-Time Actions

**Step 1: Create Real-Time Trigger**
```yaml
Name: High-Value Visitor Active
Trigger:
  Event: page_view
  Conditions:
    - profile.total_spend > 1000
    - profile.days_since_purchase > 30
Actions:
  - type: webhook
    url: https://your-server.com/vip-visitor
  - type: slack
    channel: #sales-alerts
```

**Step 2: Test the Trigger**
1. Go to **Streaming > Triggers**
2. Select your trigger
3. Click **Test**
4. Send a test event
5. Verify action executed

### 3.6 Stream Analytics

Monitor streaming health:
- Events/second throughput
- Processing latency (p50, p95, p99)
- Failed events and retries
- Action execution success rate

---

## 4. Predictive Churn Model

### 4.1 Overview

The Predictive Churn Model uses machine learning to identify customers likely to churn, enabling proactive retention.

### 4.2 Accessing Predictive Churn

Navigate to **CDP > Predictive Churn** (`/dashboard/cdp/predictive-churn`)

### 4.3 Model Overview

**Model Metrics:**

| Metric | Description | Target |
|--------|-------------|--------|
| Accuracy | Overall correctness | > 85% |
| Precision | Correct churn predictions | > 80% |
| Recall | Actual churners caught | > 90% |
| AUC-ROC | Model discrimination | > 0.90 |

### 4.4 Understanding Churn Scores

Each profile receives a churn probability (0-100%):

| Score | Risk Level | Recommended Action |
|-------|------------|-------------------|
| 0-25% | Low | Monitor, standard engagement |
| 25-50% | Medium | Proactive outreach |
| 50-75% | High | Urgent intervention |
| 75-100% | Critical | Immediate action required |

### 4.5 Churn Factors

The model identifies top factors driving churn:

**Common Churn Indicators:**

| Factor | Impact Direction | Example |
|--------|------------------|---------|
| Days since last purchase | Increases churn | 45 days = high risk |
| Support tickets | Increases churn | 4+ open tickets |
| Email open rate | Decreases churn | <10% = risk |
| Feature usage decline | Increases churn | -60% usage |
| Contract end proximity | Increases churn | <30 days |
| NPS score | Decreases churn | Score 4 vs 9 |

### 4.6 Setting Up Retention Campaigns

**Step 1: Create At-Risk Segment**
```yaml
Segment: High Churn Risk
Conditions:
  - churn_probability > 50%
  - lifecycle_stage NOT IN ['churned', 'lost']
```

**Step 2: Configure Intervention**
1. Go to **Predictive Churn > Interventions**
2. Click **New Campaign**
3. Configure:
   - Target: High-risk segment
   - Channel: Email, SMS, or In-app
   - Offer: Discount, feature access, support call
4. Enable and monitor

### 4.7 Model Retraining

The model automatically retrains monthly. Manual retraining:

1. Go to **Predictive Churn > Model**
2. Click **Retrain Model**
3. Select training data range
4. Review new metrics
5. Deploy updated model

### 4.8 Churn Analytics Dashboard

Monitor churn metrics:
- Total profiles at risk
- Revenue at risk
- Predicted churn rate trend
- Intervention success rate
- Saved revenue from interventions

---

## 5. Custom Autopilot Rules

### 5.1 Overview

Custom Autopilot Rules let you build complex automation logic beyond pre-built rules.

### 5.2 Accessing Custom Rules

Navigate to **Custom Autopilot** (`/dashboard/custom-autopilot-rules`)

### 5.3 Rule Components

**Condition Groups:**
Build complex logic with AND/OR groups:

```
IF (Condition Group 1 - OR)
  - Spend > $1000/day
  - ROAS < 1.5
AND (Condition Group 2 - AND)
  - Signal Health > 70
  - Campaign active > 7 days
THEN
  - Reduce budget by 20%
```

**Available Conditions:**

| Category | Conditions |
|----------|------------|
| Performance | Spend, Revenue, ROAS, CPA, CTR, CVR |
| Time | Days active, days since change, time of day |
| Trust | Signal health, EMQ score, attribution variance |
| Comparison | vs. account avg, vs. benchmark, vs. goal |

### 5.4 Creating a Custom Rule

**Example: Smart Budget Optimizer**

**Step 1: Define Conditions**
```
Condition Group 1 (AND):
  - ROAS >= 2.5
  - Spend < 80% of daily budget
  - Signal Health >= 75
  - Days since last change >= 3

Condition Group 2 (OR):
  - CPM < Account Average
  - CTR > 2%
```

**Step 2: Configure Actions**
```
Actions (Priority Order):
1. Increase budget by 25%
   Max: $500/day cap

2. Send Slack notification
   Channel: #campaign-wins
   Message: "{{campaign_name}} performing well, budget increased"
```

**Step 3: Set Targeting**
```
Targeting:
  Platforms: Meta, Google
  Campaign Types: Conversion, Catalog Sales
  Exclude: Brand campaigns, Retargeting
```

**Step 4: Configure Schedule**
```
Schedule:
  Frequency: Daily
  Time: 9:00 AM
  Days: Monday-Friday
  Timezone: Account timezone
```

**Step 5: Safety Settings (Trust Gate)**
```
Trust Gate Config:
  Enabled: Yes
  Min Signal Health: 70
  Require Approval: No (auto-execute)
  Dry Run First: Yes (first 3 executions)
```

### 5.5 Rule Testing

Before enabling:
1. Click **Test Rule**
2. Select a date range
3. View which entities would match
4. See projected actions
5. Review impact estimates

### 5.6 Rule Monitoring

Track rule performance:
- Executions: How often the rule runs
- Matches: Entities matching conditions
- Actions: Actions taken
- Impact: Revenue/ROAS change attributed to rule

---

## 6. Salesforce CRM Integration

### 6.1 Overview

Full bi-directional integration with Salesforce, syncing leads, contacts, opportunities, and attribution data.

### 6.2 Connecting Salesforce

**Step 1: OAuth Connection**
1. Navigate to **Settings > Integrations > Salesforce**
2. Click **Connect Salesforce**
3. Log into Salesforce
4. Grant permissions
5. Select Production or Sandbox

**Required Permissions:**
- `api` - API access
- `refresh_token, offline_access` - Keep connected
- Object permissions for Contacts, Leads, Opportunities

### 6.3 Data Sync Configuration

**Sync Direction:**

| Data Type | Stratum → Salesforce | Salesforce → Stratum |
|-----------|---------------------|---------------------|
| Contacts/Leads | Attribution data | Contact info |
| Opportunities | Attribution | Deal stages, values |
| Activities | Events | Logged activities |
| Custom Fields | Computed traits | Custom data |

### 6.4 Custom Field Setup

Create custom fields in Salesforce for attribution:

**Contact Custom Fields:**
```
Stratum_Ad_Platform__c (Text)
Stratum_Campaign__c (Text)
Stratum_First_Touch_Source__c (Text)
Stratum_Last_Touch_Source__c (Text)
Stratum_Attribution_Revenue__c (Currency)
Stratum_Touch_Count__c (Number)
Stratum_Days_to_Convert__c (Number)
Stratum_First_Touch_Date__c (Date)
Stratum_Profile_ID__c (Text)
```

**Opportunity Custom Fields:**
```
Stratum_Attributed_Platform__c (Text)
Stratum_Attributed_Campaign__c (Text)
Stratum_Attribution_Model__c (Picklist)
Stratum_Attribution_Weight__c (Percent)
Stratum_Touch_Points__c (Number)
Stratum_First_Touch_Date__c (Date)
Stratum_MQL_Date__c (Date)
Stratum_SQL_Date__c (Date)
Stratum_Customer_Segment__c (Text)
Stratum_Lifetime_Value__c (Currency)
Stratum_Churn_Risk__c (Percent)
```

### 6.5 Identity Matching

Stratum matches profiles to Salesforce records using:
1. Email (primary)
2. Phone number
3. External ID
4. Custom matching rules

### 6.6 Pipeline Insights

View Salesforce pipeline data in Stratum:
- Pipeline value by stage
- Attributed pipeline from ads
- Conversion rates by source
- Revenue forecasts

### 6.7 Sync Monitoring

**Sync Dashboard Shows:**
- Last sync time
- Records synced (Contacts, Leads, Opportunities)
- Sync errors and warnings
- Data freshness

---

## 7. LinkedIn Lead Gen Integration

### 7.1 Overview

Connect LinkedIn Lead Gen Forms to capture leads directly into your CDP.

### 7.2 Connecting LinkedIn

1. Navigate to **Settings > Integrations > LinkedIn**
2. Click **Connect LinkedIn**
3. Log into LinkedIn Campaign Manager
4. Grant permissions
5. Select Ad Accounts

### 7.3 Lead Form Mapping

Map LinkedIn form fields to CDP profile:

| LinkedIn Field | CDP Field |
|----------------|-----------|
| First Name | first_name |
| Last Name | last_name |
| Email | email |
| Phone | phone |
| Company | company_name |
| Job Title | job_title |
| Custom Question 1 | custom.linkedin_q1 |

### 7.4 Automation Triggers

Trigger actions on new LinkedIn leads:

```yaml
Trigger: New LinkedIn Lead
Conditions:
  - form_name = "Whitepaper Download"
Actions:
  - Add to segment: "Content Leads"
  - Create Salesforce Lead
  - Send Slack notification
  - Trigger email sequence
```

### 7.5 Lead Attribution

LinkedIn leads automatically include:
- Campaign name
- Ad creative
- Form name
- Lead gen form ID
- Cost per lead

---

## 8. Dashboard Customization

### 8.1 Overview

Create custom dashboards with drag-and-drop widgets.

### 8.2 Creating a Custom Dashboard

1. Navigate to **Dashboard > Custom**
2. Click **Create Dashboard**
3. Name your dashboard
4. Add widgets

### 8.3 Available Widgets

| Widget | Description |
|--------|-------------|
| KPI Card | Single metric with trend |
| Line Chart | Time series data |
| Bar Chart | Categorical comparison |
| Pie Chart | Distribution view |
| Table | Detailed data grid |
| Funnel | Conversion funnel |
| Heatmap | Cross-dimensional analysis |
| Leaderboard | Ranked list |

### 8.4 Widget Configuration

For each widget, configure:
- **Data Source**: Campaigns, CDP, Trust Engine, etc.
- **Metrics**: Which metrics to display
- **Dimensions**: How to slice data
- **Filters**: Limit data shown
- **Date Range**: Fixed or relative

### 8.5 Dashboard Layout

Drag and resize widgets:
- 12-column grid system
- Snap-to-grid placement
- Responsive mobile view
- Save layout templates

### 8.6 Sharing Dashboards

- **Team Access**: Share with team members
- **Public Link**: Generate view-only link
- **Scheduled Snapshots**: Email PNG/PDF weekly
- **Embed**: Embed in external tools

---

## 9. Custom Report Builder

### 9.1 Overview

Build any report you need with the Custom Report Builder.

### 9.2 Accessing Report Builder

Navigate to **Custom Reports** (`/dashboard/custom-reports`)

### 9.3 Creating a Report

**Step 1: Choose Data Source**

| Source | Available Data |
|--------|---------------|
| Campaigns | Spend, impressions, clicks, conversions, ROAS |
| CDP | Profiles, events, segments, lifecycle |
| Trust Engine | Signal health, gate decisions, automations |
| Pacing | Budget, forecasts, alerts |
| Attribution | Touchpoints, paths, models |

**Step 2: Select Metrics**

```
Example: Campaign Performance Report
Metrics:
  - Ad Spend (SUM)
  - Impressions (SUM)
  - Clicks (SUM)
  - Conversions (SUM)
  - ROAS (AVG)
  - CPA (AVG)
```

**Step 3: Add Dimensions**

```
Dimensions:
  - Platform
  - Campaign Name
  - Date (daily/weekly/monthly)
  - Device
```

**Step 4: Configure Filters**

```
Filters:
  - Platform = "Meta" OR "Google"
  - Spend > $100
  - Date = Last 30 days
```

**Step 5: Add Visualizations**

- Line chart: ROAS over time
- Bar chart: Spend by platform
- Table: Campaign details

### 9.4 Report Scheduling

Automate report delivery:

```
Schedule:
  Frequency: Weekly (Monday 9am)
  Format: PDF
  Recipients:
    - team@company.com
    - client@agency.com
```

### 9.5 Report Templates

Save and reuse report configurations:
1. Build your report
2. Click **Save as Template**
3. Name your template
4. Use for future reports

---

## 10. Enterprise Administration

### 10.1 Advanced User Management

**SSO/SAML Integration:**
1. Go to **Settings > Security > SSO**
2. Configure SAML provider
3. Upload metadata
4. Test connection

**Role Customization:**
Create custom roles beyond defaults:
```yaml
Role: Media Buyer Manager
Permissions:
  - campaigns:read
  - campaigns:write
  - analytics:read
  - autopilot:approve
  - reports:create
Restrictions:
  - Cannot access billing
  - Cannot manage users
  - Cannot view raw data exports
```

### 10.2 Audit & Compliance

**Comprehensive Audit Logs:**
- User actions
- Data exports
- Permission changes
- API access
- Configuration changes

**Compliance Reports:**
- GDPR compliance status
- Consent audit trail
- Data processing records
- DSAR response logs

### 10.3 API Management

**API Keys:**
- Create multiple API keys
- Set permissions per key
- Rate limit configuration
- Usage monitoring

**Webhooks:**
- Configure outbound webhooks
- Set event triggers
- Monitor delivery status
- Retry configuration

### 10.4 Multi-Region Deployment

Enterprise customers can request:
- EU data residency
- Dedicated infrastructure
- Custom SLAs
- Disaster recovery

---

## Quick Reference

### Enterprise Feature Flags

```python
# All Enterprise features
consent_management: True
realtime_streaming: True
predictive_churn: True
custom_autopilot_rules: True
crm_salesforce: True
linkedin_leadgen: True
dashboard_customization: True
custom_reports: True

# Plus all Professional features
funnel_builder: True
computed_traits: True
trust_audit_logs: True
action_dry_run: True
crm_pipedrive: True

# Plus all Starter features
rfm_analysis: True
signal_health_history: True
slack_notifications: True
dashboard_export: True
```

### Enterprise API Endpoints

```
# Consent Management
GET  /api/v1/cdp/consent/settings
POST /api/v1/cdp/consent/record
POST /api/v1/cdp/profiles/delete-batch
POST /api/v1/cdp/profiles/{id}/export

# Predictive Churn
GET  /api/v1/cdp/churn/predictions
GET  /api/v1/cdp/churn/model/metrics
POST /api/v1/cdp/churn/model/retrain
GET  /api/v1/cdp/churn/interventions

# Custom Autopilot Rules
GET  /api/v1/autopilot/custom-rules
POST /api/v1/autopilot/custom-rules
POST /api/v1/autopilot/custom-rules/{id}/test
POST /api/v1/autopilot/custom-rules/{id}/execute

# Salesforce
POST /api/v1/integrations/salesforce/connect
GET  /api/v1/integrations/salesforce/status
POST /api/v1/integrations/salesforce/sync
GET  /api/v1/integrations/salesforce/pipeline

# Custom Reports
GET  /api/v1/reports/custom
POST /api/v1/reports/custom
POST /api/v1/reports/custom/{id}/run
POST /api/v1/reports/custom/{id}/schedule

# Custom Dashboards
GET  /api/v1/dashboards/custom
POST /api/v1/dashboards/custom
PUT  /api/v1/dashboards/custom/{id}/layout
```

### Support Resources

- **Dedicated Success Manager:** Assigned upon onboarding
- **Priority Support:** support-enterprise@stratum.ai (4-hour SLA)
- **Phone Support:** +1-800-STRATUM
- **Slack Connect:** Direct channel with Stratum team
- **Documentation:** [docs.stratum.ai/enterprise](https://docs.stratum.ai/enterprise)

---

**Congratulations!** You've completed the Enterprise Plan tutorial. You now have the knowledge to leverage all of Stratum AI's most powerful features.

**Need help implementing any feature?** Contact your dedicated Success Manager or reach out to support-enterprise@stratum.ai.

---

*Stratum AI Enterprise - The Complete Revenue Operating System*
