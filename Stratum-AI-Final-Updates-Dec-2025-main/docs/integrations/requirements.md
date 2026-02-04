# Stratum AI - Integration Requirements

**Version:** 1.0.0
**Last Updated:** January 2026

This document outlines the requirements, setup steps, and prerequisites for all Stratum AI integrations.

---

## Table of Contents

1. [Ad Platform Integrations](#1-ad-platform-integrations)
   - [Meta Ads](#11-meta-ads)
   - [Google Ads](#12-google-ads)
   - [TikTok Ads](#13-tiktok-ads)
   - [Snapchat Ads](#14-snapchat-ads)
2. [CRM Integrations](#2-crm-integrations)
   - [Pipedrive](#21-pipedrive)
   - [Salesforce](#22-salesforce)
   - [HubSpot](#23-hubspot)
   - [Zoho CRM](#24-zoho-crm)
3. [Notification Integrations](#3-notification-integrations)
   - [Slack](#31-slack)
4. [Lead Generation Integrations](#4-lead-generation-integrations)
   - [LinkedIn Lead Gen](#41-linkedin-lead-gen)
5. [Audience Sync Platforms](#5-audience-sync-platforms)
   - [Meta Custom Audiences](#51-meta-custom-audiences)
   - [Google Customer Match](#52-google-customer-match)
   - [TikTok Custom Audiences](#53-tiktok-custom-audiences)
   - [Snapchat Audience Match](#54-snapchat-audience-match)
6. [API & Webhook Requirements](#6-api--webhook-requirements)

---

## 1. Ad Platform Integrations

### 1.1 Meta Ads

**Plan Availability:** Starter, Professional, Enterprise

#### Prerequisites

| Requirement | Details |
|-------------|---------|
| Business Manager | Active Meta Business Manager account |
| Ad Account Access | Admin or Advertiser role on ad accounts |
| App Review | Stratum's app is pre-approved |

#### Required Permissions

| Permission | Purpose | Scope |
|------------|---------|-------|
| `ads_read` | Read campaign data | Required |
| `ads_management` | Manage campaigns (optional) | Optional |
| `business_management` | Access business assets | Required |
| `pages_read_engagement` | Read page insights | Optional |

#### OAuth Scopes
```
ads_read
ads_management
business_management
read_insights
```

#### Setup Steps

1. **Initiate Connection**
   - Navigate to Settings > Integrations > Meta
   - Click "Connect Meta Ads"

2. **Authenticate**
   - Log into your Facebook account
   - Select the Business Manager to connect
   - Grant the requested permissions

3. **Select Ad Accounts**
   - Choose which ad accounts to sync
   - Configure sync frequency (hourly default)

4. **Verify Connection**
   - Green checkmark indicates success
   - Initial data sync begins immediately

#### Data Synced

| Data Type | Sync Frequency | Historical Data |
|-----------|----------------|-----------------|
| Campaigns | Hourly | 90 days |
| Ad Sets | Hourly | 90 days |
| Ads/Creatives | Hourly | 90 days |
| Insights/Metrics | Hourly | 90 days |
| Audiences | Daily | Current only |

#### Rate Limits

| Limit Type | Value |
|------------|-------|
| API Calls/Hour | 200 per ad account |
| Insights Requests | 60 per hour |
| Bulk Read | 500 objects per request |

#### Troubleshooting

| Issue | Solution |
|-------|----------|
| Connection expired | Re-authenticate via Settings |
| Missing ad accounts | Check Business Manager permissions |
| Data not syncing | Verify ad account is active |
| Rate limit errors | Wait 1 hour, then retry |

---

### 1.2 Google Ads

**Plan Availability:** Starter, Professional, Enterprise

#### Prerequisites

| Requirement | Details |
|-------------|---------|
| Google Ads Account | Active Google Ads account |
| Manager Account (MCC) | Recommended for agencies |
| Admin Access | Admin or Standard access to accounts |

#### Required Permissions

| Permission | Purpose |
|------------|---------|
| View performance data | Read campaign metrics |
| Manage campaigns | Edit campaigns (optional) |
| Manage account access | View linked accounts |

#### OAuth Scopes
```
https://www.googleapis.com/auth/adwords
```

#### Setup Steps

1. **Initiate Connection**
   - Navigate to Settings > Integrations > Google Ads
   - Click "Connect Google Ads"

2. **Authenticate**
   - Sign in with your Google account
   - Select the Google Ads account or MCC
   - Grant access permissions

3. **Link Customer IDs**
   - Enter Customer ID(s) to sync
   - For MCC: Select child accounts

4. **Configure Sync**
   - Choose metrics to track
   - Set sync frequency

#### Data Synced

| Data Type | Sync Frequency | Historical Data |
|-----------|----------------|-----------------|
| Campaigns | Hourly | 90 days |
| Ad Groups | Hourly | 90 days |
| Ads | Hourly | 90 days |
| Keywords | Daily | 90 days |
| Performance Metrics | Hourly | 90 days |
| Conversions | Hourly | 90 days |

#### Rate Limits

| Limit Type | Value |
|------------|-------|
| Requests/Day | 15,000 |
| Operations/Request | 10,000 |
| Pages/Query | 10,000 rows |

#### API Version
```
Google Ads API v15
```

---

### 1.3 TikTok Ads

**Plan Availability:** Starter, Professional, Enterprise

#### Prerequisites

| Requirement | Details |
|-------------|---------|
| TikTok for Business | Active business account |
| Advertiser Account | Access to TikTok Ads Manager |
| Admin Role | Admin access to ad accounts |

#### Required Permissions

| Permission | Purpose |
|------------|---------|
| Ad Account Read | View campaign data |
| Ad Account Write | Manage campaigns (optional) |
| Audience Read | Access custom audiences |

#### OAuth Scopes
```
ad.read
ad.write (optional)
audience.read
```

#### Setup Steps

1. **Initiate Connection**
   - Navigate to Settings > Integrations > TikTok
   - Click "Connect TikTok Ads"

2. **Authenticate**
   - Log into TikTok for Business
   - Authorize Stratum AI app
   - Select advertiser accounts

3. **Configure**
   - Choose accounts to sync
   - Set data preferences

#### Data Synced

| Data Type | Sync Frequency | Historical Data |
|-----------|----------------|-----------------|
| Campaigns | Hourly | 60 days |
| Ad Groups | Hourly | 60 days |
| Ads | Hourly | 60 days |
| Creatives | Daily | 60 days |
| Performance Metrics | Hourly | 60 days |

#### Rate Limits

| Limit Type | Value |
|------------|-------|
| Requests/Minute | 600 |
| Requests/Day | 864,000 |

---

### 1.4 Snapchat Ads

**Plan Availability:** Starter, Professional, Enterprise

#### Prerequisites

| Requirement | Details |
|-------------|---------|
| Snapchat Business | Active Snapchat Business account |
| Ad Account | Access to Snapchat Ads Manager |
| Admin Access | Admin role on ad accounts |

#### Required Permissions

| Permission | Purpose |
|------------|---------|
| Read Ad Accounts | View campaign data |
| Read Organizations | Access business info |
| Read Campaigns | View campaign structure |
| Read Stats | Access performance metrics |

#### OAuth Scopes
```
snapchat-marketing-api
```

#### Setup Steps

1. **Initiate Connection**
   - Navigate to Settings > Integrations > Snapchat
   - Click "Connect Snapchat Ads"

2. **Authenticate**
   - Log into Snapchat Business Manager
   - Authorize the connection
   - Select organizations and ad accounts

3. **Configure Sync**
   - Choose accounts
   - Set sync preferences

#### Data Synced

| Data Type | Sync Frequency | Historical Data |
|-----------|----------------|-----------------|
| Campaigns | Hourly | 90 days |
| Ad Squads | Hourly | 90 days |
| Ads | Hourly | 90 days |
| Creatives | Daily | 90 days |
| Performance Stats | Hourly | 90 days |

#### Rate Limits

| Limit Type | Value |
|------------|-------|
| Requests/Second | 10 |
| Requests/Minute | 300 |

---

## 2. CRM Integrations

### 2.1 Pipedrive

**Plan Availability:** Professional, Enterprise

#### Prerequisites

| Requirement | Details |
|-------------|---------|
| Pipedrive Account | Active Pipedrive subscription |
| Admin Access | Admin or regular user with API access |
| API Token | Personal API token from Pipedrive |

#### Required Permissions

| Permission | Purpose |
|------------|---------|
| Full Access | Read/write persons, deals, activities |
| Custom Fields | Create and update custom fields |
| Webhooks | Receive real-time updates |

#### Setup Steps

1. **Get API Token**
   - Log into Pipedrive
   - Go to Settings > Personal Preferences > API
   - Copy your personal API token

2. **Connect in Stratum**
   - Navigate to Settings > Integrations > CRM
   - Click "Connect Pipedrive"
   - Paste your API token
   - Click "Authorize"

3. **Configure Field Mapping**
   - Map Stratum fields to Pipedrive fields
   - Create custom fields for attribution data
   - Set sync direction (bidirectional recommended)

4. **Enable Sync**
   - Choose sync frequency
   - Select data types to sync
   - Start initial sync

#### Data Mapping

| Stratum Data | Pipedrive Object |
|--------------|------------------|
| CDP Profile | Person |
| Events | Activities |
| Segments | Labels |
| Attribution | Custom Fields |
| Revenue | Deal Value |

#### Custom Fields Required

Create these custom fields in Pipedrive:

**Person Fields:**
```
Stratum_Profile_ID (Text)
Stratum_Ad_Platform (Text)
Stratum_Campaign (Text)
Stratum_First_Touch (Text)
Stratum_Last_Touch (Text)
Stratum_Attribution_Revenue (Currency)
Stratum_Lifecycle_Stage (Text)
Stratum_Segment (Text)
```

**Deal Fields:**
```
Stratum_Attributed_Source (Text)
Stratum_Touch_Points (Number)
Stratum_Days_to_Close (Number)
```

#### Rate Limits

| Limit Type | Value |
|------------|-------|
| Requests/Second | 10 |
| Requests/Day | 8,000 (varies by plan) |

---

### 2.2 Salesforce

**Plan Availability:** Enterprise

#### Prerequisites

| Requirement | Details |
|-------------|---------|
| Salesforce Edition | Professional, Enterprise, or Unlimited |
| User License | Salesforce user with API access |
| System Admin | For initial setup and custom fields |
| Connected App | Created in Salesforce Setup |

#### Required Permissions

| Permission | Purpose |
|------------|---------|
| API Enabled | Allow API access |
| Modify All Data | Create/update records |
| View All Data | Read all records |
| Manage Connected Apps | OAuth configuration |

#### OAuth Scopes
```
api
refresh_token
offline_access
```

#### Setup Steps

1. **Create Connected App in Salesforce**
   - Go to Setup > App Manager > New Connected App
   - Enable OAuth Settings
   - Set callback URL: `https://app.stratum.ai/integrations/salesforce/callback`
   - Select scopes: `api`, `refresh_token`, `offline_access`
   - Save and note Consumer Key/Secret

2. **Create Custom Fields**
   - Go to Setup > Object Manager
   - Add custom fields to Contact and Opportunity (see below)

3. **Connect in Stratum**
   - Navigate to Settings > Integrations > Salesforce
   - Click "Connect Salesforce"
   - Choose Production or Sandbox
   - Log in and authorize

4. **Configure Sync**
   - Map fields
   - Set sync direction
   - Configure sync frequency

#### Custom Fields Required

**Contact Custom Fields:**
```
API Name: Stratum_Profile_ID__c
Type: Text(255)
Label: Stratum Profile ID

API Name: Stratum_Ad_Platform__c
Type: Text(255)
Label: Stratum - Ad Platform

API Name: Stratum_Campaign__c
Type: Text(255)
Label: Stratum - Campaign

API Name: Stratum_First_Touch_Source__c
Type: Text(255)
Label: Stratum - First Touch Source

API Name: Stratum_Last_Touch_Source__c
Type: Text(255)
Label: Stratum - Last Touch Source

API Name: Stratum_Attribution_Revenue__c
Type: Currency(16,2)
Label: Stratum - Attribution Revenue

API Name: Stratum_Touch_Count__c
Type: Number(18,0)
Label: Stratum - Touch Count

API Name: Stratum_Days_to_Convert__c
Type: Number(18,0)
Label: Stratum - Days to Convert

API Name: Stratum_First_Touch_Date__c
Type: Date
Label: Stratum - First Touch Date
```

**Opportunity Custom Fields:**
```
API Name: Stratum_Attributed_Platform__c
Type: Text(255)
Label: Stratum - Attributed Platform

API Name: Stratum_Attributed_Campaign__c
Type: Text(255)
Label: Stratum - Attributed Campaign

API Name: Stratum_Attribution_Model__c
Type: Picklist
Values: First Touch, Last Touch, Linear, Time Decay, Position Based

API Name: Stratum_Attribution_Weight__c
Type: Percent(5,2)
Label: Stratum - Attribution Weight

API Name: Stratum_Touch_Points__c
Type: Number(18,0)
Label: Stratum - Touch Points

API Name: Stratum_Customer_Segment__c
Type: Text(255)
Label: Stratum - Customer Segment

API Name: Stratum_Lifetime_Value__c
Type: Currency(16,2)
Label: Stratum - Lifetime Value

API Name: Stratum_Churn_Risk__c
Type: Percent(5,2)
Label: Stratum - Churn Risk
```

#### Data Mapping

| Stratum Data | Salesforce Object |
|--------------|-------------------|
| CDP Profile | Contact / Lead |
| Attribution | Custom Fields |
| Events | Task / Activity |
| Computed Traits | Custom Fields |
| Opportunities | Opportunity |

#### Rate Limits

| Edition | API Calls/24hr |
|---------|----------------|
| Professional | 15,000 + 1,000/user |
| Enterprise | 100,000 + 1,000/user |
| Unlimited | 100,000 + 1,000/user |

---

### 2.3 HubSpot

**Plan Availability:** Enterprise

#### Prerequisites

| Requirement | Details |
|-------------|---------|
| HubSpot Account | Marketing Hub Professional or Enterprise |
| Super Admin | For OAuth and API access |
| Private App | Created in HubSpot settings |

#### Required Scopes
```
crm.objects.contacts.read
crm.objects.contacts.write
crm.objects.deals.read
crm.objects.deals.write
crm.objects.companies.read
crm.objects.companies.write
crm.schemas.contacts.read
crm.schemas.contacts.write
timeline
```

#### Setup Steps

1. **Create Private App**
   - Go to Settings > Integrations > Private Apps
   - Create new app
   - Select required scopes
   - Generate access token

2. **Connect in Stratum**
   - Navigate to Settings > Integrations > HubSpot
   - Click "Connect HubSpot"
   - Enter access token or use OAuth
   - Authorize connection

3. **Configure Properties**
   - Create custom properties in HubSpot
   - Map to Stratum fields

#### Custom Properties Required

**Contact Properties:**
```
stratum_profile_id (Single-line text)
stratum_ad_platform (Single-line text)
stratum_first_touch_source (Single-line text)
stratum_attribution_revenue (Number)
stratum_lifecycle_stage (Dropdown)
stratum_churn_risk (Number)
```

#### Rate Limits

| Limit Type | Value |
|------------|-------|
| Requests/Second | 100 |
| Requests/Day | 250,000 |

---

### 2.4 Zoho CRM

**Plan Availability:** Enterprise

#### Prerequisites

| Requirement | Details |
|-------------|---------|
| Zoho CRM | Professional or Enterprise edition |
| Admin Access | Administrator role |
| API Access | Enabled in Zoho settings |

#### Required Scopes
```
ZohoCRM.modules.ALL
ZohoCRM.settings.ALL
ZohoCRM.users.READ
```

#### Setup Steps

1. **Register Client**
   - Go to Zoho API Console
   - Create Self Client
   - Note Client ID and Secret

2. **Connect in Stratum**
   - Navigate to Settings > Integrations > Zoho
   - Click "Connect Zoho CRM"
   - Complete OAuth flow
   - Select organization

3. **Configure Modules**
   - Map to Contacts, Leads, Deals
   - Create custom fields
   - Set sync preferences

#### Rate Limits

| Edition | Credits/Day |
|---------|-------------|
| Professional | 20,000 |
| Enterprise | 25,000 |

---

## 3. Notification Integrations

### 3.1 Slack

**Plan Availability:** Starter, Professional, Enterprise

#### Prerequisites

| Requirement | Details |
|-------------|---------|
| Slack Workspace | Active Slack workspace |
| Admin Access | Can create webhooks |
| Channel | Target channel for notifications |

#### Setup Steps

1. **Create Slack App**
   - Go to api.slack.com/apps
   - Create New App > From scratch
   - Name: "Stratum AI Notifications"
   - Select your workspace

2. **Enable Incoming Webhooks**
   - Features > Incoming Webhooks
   - Toggle "Activate" to ON
   - Click "Add New Webhook to Workspace"
   - Select the channel
   - Copy the webhook URL

3. **Configure in Stratum**
   - Navigate to Settings > Integrations > Slack
   - Paste webhook URL
   - Click "Test Connection"
   - Save configuration

4. **Configure Notifications**
   - Go to Settings > Notifications
   - Enable desired notification types
   - Set severity thresholds

#### Notification Types

| Type | Description |
|------|-------------|
| Signal Health Alerts | When health degrades |
| Anomaly Detected | Unusual metric changes |
| Autopilot Actions | Actions taken or pending |
| Daily Summary | Daily performance recap |
| Weekly Report | Weekly metrics summary |

#### Webhook Payload Format
```json
{
  "text": "Notification message",
  "blocks": [
    {
      "type": "section",
      "text": {
        "type": "mrkdwn",
        "text": "*Alert:* Signal Health Degraded"
      }
    }
  ],
  "attachments": [
    {
      "color": "#ff0000",
      "fields": [
        {"title": "Platform", "value": "Meta", "short": true},
        {"title": "Health Score", "value": "45", "short": true}
      ]
    }
  ]
}
```

---

## 4. Lead Generation Integrations

### 4.1 LinkedIn Lead Gen

**Plan Availability:** Enterprise

#### Prerequisites

| Requirement | Details |
|-------------|---------|
| LinkedIn Campaign Manager | Active account |
| Admin Access | Campaign Manager admin |
| Lead Gen Forms | Existing forms to sync |

#### Required Permissions

| Permission | Purpose |
|------------|---------|
| r_ads | Read campaign data |
| r_ads_reporting | Access reporting |
| rw_ads | Manage campaigns |
| r_organization_leadgen | Read lead gen form responses |

#### OAuth Scopes
```
r_ads
r_ads_reporting
r_organization_social
r_organization_leadgen
```

#### Setup Steps

1. **Create LinkedIn App**
   - Go to LinkedIn Developer Portal
   - Create new app
   - Request Marketing Developer Platform access
   - Wait for approval (may take days)

2. **Connect in Stratum**
   - Navigate to Settings > Integrations > LinkedIn
   - Click "Connect LinkedIn"
   - Complete OAuth
   - Select ad accounts

3. **Configure Lead Sync**
   - Select lead gen forms to sync
   - Map form fields to CDP fields
   - Set sync frequency

#### Data Synced

| Data Type | Frequency |
|-----------|-----------|
| Lead Form Responses | Real-time |
| Form Metadata | Daily |
| Campaign Data | Hourly |

---

## 5. Audience Sync Platforms

### 5.1 Meta Custom Audiences

**Plan Availability:** Professional, Enterprise

#### Prerequisites
- Meta Business Manager access
- Custom Audiences permission
- Ad account admin access

#### Required Permissions
```
ads_management
business_management
```

#### Hashed Fields
All PII is hashed before sending:
- Email (SHA256)
- Phone (SHA256, normalized)
- Mobile Advertiser ID

---

### 5.2 Google Customer Match

**Plan Availability:** Professional, Enterprise

#### Prerequisites
- Google Ads account with Customer Match enabled
- Minimum $50,000 lifetime spend
- Policy compliance history

#### Required Scopes
```
https://www.googleapis.com/auth/adwords
```

#### Hashed Fields
- Email (SHA256)
- Phone (SHA256)
- First Name + Last Name (SHA256)

---

### 5.3 TikTok Custom Audiences

**Plan Availability:** Professional, Enterprise

#### Prerequisites
- TikTok for Business account
- DMP Custom Audience access
- Ad account admin

#### Required Scopes
```
audience.write
audience.read
```

---

### 5.4 Snapchat Audience Match (SAM)

**Plan Availability:** Professional, Enterprise

#### Prerequisites
- Snapchat Business account
- SAM API access approved
- Ad account admin

---

## 6. API & Webhook Requirements

### API Access

| Plan | Access Level | Rate Limit |
|------|--------------|------------|
| Starter | Read | 10,000/month |
| Professional | Read/Write | 50,000/month |
| Enterprise | Full | Unlimited |

### API Authentication
```
Authorization: Bearer <api_key>
X-Tenant-ID: <tenant_id>
```

### Webhook Configuration

#### Setup
1. Go to Settings > Webhooks
2. Add endpoint URL
3. Select events to subscribe
4. Generate signing secret
5. Test endpoint

#### Available Events
```
profile.created
profile.updated
segment.entered
segment.exited
event.tracked
campaign.status_changed
signal_health.changed
autopilot.action_taken
```

#### Payload Format
```json
{
  "event": "profile.created",
  "timestamp": "2026-01-15T10:30:00Z",
  "tenant_id": "tenant_123",
  "data": {
    "profile_id": "profile_456",
    "email": "user@example.com"
  },
  "signature": "sha256=abc123..."
}
```

#### Signature Verification
```python
import hmac
import hashlib

def verify_signature(payload, signature, secret):
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

---

## Support

For integration support:
- **Documentation:** docs.stratum.ai/integrations
- **Email:** integrations@stratum.ai
- **Enterprise:** Contact your dedicated Success Manager

---

*Last updated: January 2026*
