# Stratum AI - Starter Plan Tutorial

**Version:** 1.0.0
**Last Updated:** January 2026
**Estimated Time:** 30 minutes

---

## Welcome to Stratum AI Starter Plan

This tutorial will guide you through setting up and using all features available in the **Starter Plan**. By the end, you'll be able to:

- Connect your ad platforms
- Monitor campaign performance
- Track signal health
- Use RFM analysis for customer insights
- Export dashboard data
- Set up Slack notifications

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Connecting Ad Platforms](#2-connecting-ad-platforms)
3. [Understanding the Dashboard](#3-understanding-the-dashboard)
4. [Signal Health Monitoring](#4-signal-health-monitoring)
5. [CDP Overview & RFM Analysis](#5-cdp-overview--rfm-analysis)
6. [Dashboard Export](#6-dashboard-export)
7. [Slack Notifications](#7-slack-notifications)
8. [Next Steps](#8-next-steps)

---

## 1. Getting Started

### 1.1 Logging In

1. Navigate to your Stratum AI login page
2. Enter your email and password
3. Complete two-factor authentication (if enabled)
4. You'll land on the **Overview Dashboard**

### 1.2 Initial Setup Checklist

Before diving into features, complete these steps:

- [ ] Verify your email address
- [ ] Set up your profile (Settings > Profile)
- [ ] Connect at least one ad platform
- [ ] Configure your timezone (Settings > Preferences)

---

## 2. Connecting Ad Platforms

### 2.1 Supported Platforms

The Starter Plan supports connections to:
- **Meta** (Facebook & Instagram Ads)
- **Google Ads**
- **TikTok Ads**
- **Snapchat Ads**

### 2.2 How to Connect a Platform

1. Navigate to **Settings > Integrations** or use the tenant-scoped `/app/{tenantId}/campaigns/connect`
2. Click **Connect** next to your desired platform
3. You'll be redirected to the platform's OAuth page
4. Grant the required permissions
5. Upon success, you'll see a green checkmark

**Example: Connecting Meta Ads**

```
Step 1: Click "Connect Meta"
Step 2: Log into your Facebook Business account
Step 3: Select the Ad Accounts you want to connect
Step 4: Grant permissions:
        - ads_read
        - ads_management
        - business_management
Step 5: Click "Confirm"
```

### 2.3 Selecting Ad Accounts

After connecting a platform:
1. Navigate to **Campaigns > Ad Accounts**
2. You'll see all ad accounts from your connected platforms
3. Toggle the accounts you want to track
4. Click **Save Selection**

**Note:** Data syncing begins immediately after selection. Historical data (up to 90 days) will be backfilled.

---

## 3. Understanding the Dashboard

### 3.1 Overview Dashboard

The Overview Dashboard (`/dashboard/overview`) provides a unified view of all your campaigns.

**Key Metrics Displayed:**
| Metric | Description |
|--------|-------------|
| Total Spend | Combined ad spend across all platforms |
| Revenue | Attributed revenue from conversions |
| ROAS | Return on Ad Spend (Revenue / Spend) |
| Conversions | Total conversion events |
| CPA | Cost Per Acquisition |
| CTR | Click-Through Rate |

### 3.2 Date Range Selection

Use the date picker in the top-right corner to:
- Select preset ranges (Today, Last 7 Days, Last 30 Days)
- Choose custom date ranges
- Compare periods (e.g., this week vs. last week)

### 3.3 Platform Filter

Filter your data by platform:
1. Click the **Platform** dropdown
2. Select one or multiple platforms
3. The dashboard updates in real-time

### 3.4 Campaign Performance Table

Below the KPI cards, you'll find a detailed campaign table showing:
- Campaign name
- Platform
- Status (Active, Paused, etc.)
- Spend, Revenue, ROAS
- Conversions and CPA

**Tip:** Click any column header to sort. Click a campaign row to view detailed metrics.

---

## 4. Signal Health Monitoring

### 4.1 What is Signal Health?

Signal Health measures the reliability of your data connections. Healthy signals ensure accurate analytics and enable automation features.

### 4.2 Viewing Signal Health

Navigate to **Data Quality** or check the Signal Health indicator in the Overview Dashboard.

**Health Statuses:**

| Status | Indicator | Meaning |
|--------|-----------|---------|
| Healthy | Green | All systems operational |
| At Risk | Yellow | Minor issues detected |
| Degraded | Orange | Significant problems |
| Critical | Red | Immediate action required |

### 4.3 Signal Health Metrics

| Metric | Healthy Threshold | Description |
|--------|-------------------|-------------|
| EMQ Score | >= 8.0 | Event Match Quality (Meta CAPI) |
| Event Loss | < 5% | Percentage of lost events |
| Data Freshness | < 60 min | Time since last sync |
| API Error Rate | < 1% | Failed API calls |

### 4.4 Signal Health History (Starter Feature)

Track signal health over time:
1. Navigate to **Data Quality > History**
2. View daily health scores for the past 30 days
3. Identify patterns and recurring issues
4. Export history data for reporting

---

## 5. CDP Overview & RFM Analysis

### 5.1 Accessing the CDP

The Customer Data Platform (CDP) is available at `/dashboard/cdp`.

**Starter Plan CDP Features:**
- CDP Overview Dashboard
- Customer Profiles (view only)
- RFM Analysis
- Basic Segments (view only)

### 5.2 CDP Overview Dashboard

The CDP Overview shows:
- Total customer profiles
- Profile growth trends
- Lifecycle stage distribution
- Recent activity feed

### 5.3 RFM Analysis

RFM (Recency, Frequency, Monetary) analysis helps you understand customer value.

**Accessing RFM:**
1. Navigate to **CDP > RFM Analysis**
2. View the 12 RFM segments

**RFM Segments:**

| Segment | Description | Recommended Action |
|---------|-------------|-------------------|
| Champions | Best customers | Reward and upsell |
| Loyal Customers | Frequent buyers | Engage with new products |
| Potential Loyalists | Recent buyers | Nurture with offers |
| New Customers | Just started | Welcome campaigns |
| Promising | Average engagement | Build relationship |
| Need Attention | Above average but slipping | Re-engage |
| About to Sleep | Below average, risky | Win-back campaigns |
| At Risk | Once good, now gone | Aggressive re-engagement |
| Can't Lose | Previously high value | Priority win-back |
| Hibernating | Long inactive | Consider suppression |
| Lost | No recent activity | Last-chance campaigns |
| Others | Uncategorized | Segment further |

**Using RFM Data:**
1. Click any segment to view profiles
2. Export segment lists for campaigns
3. Track segment migration over time

---

## 6. Dashboard Export

### 6.1 Exporting Dashboard Data

Export your dashboard metrics for reporting or analysis.

**How to Export:**
1. Navigate to any dashboard view
2. Click the **Export** button (top-right)
3. Choose your format:
   - **CSV** - For spreadsheet analysis
   - **JSON** - For programmatic use
4. Select date range
5. Click **Download**

### 6.2 What's Included in Exports

| Export Type | Included Data |
|-------------|---------------|
| Overview Export | KPIs, campaign performance, platform breakdown |
| Campaign Export | All campaign metrics, ad sets, creatives |
| Signal Health Export | Daily health scores, issues, alerts |
| CDP Export | Profile counts, segment sizes, events |

### 6.3 Scheduled Exports (Basic)

Set up recurring exports:
1. Go to **Settings > Export Preferences**
2. Enable scheduled exports
3. Choose frequency (weekly recommended for Starter)
4. Enter recipient email addresses
5. Select export format

---

## 7. Slack Notifications

### 7.1 Setting Up Slack Integration

Receive important alerts directly in Slack.

**Step 1: Create a Slack Webhook**
1. Go to [Slack API](https://api.slack.com/apps)
2. Create a new app or use an existing one
3. Navigate to **Incoming Webhooks**
4. Activate webhooks and create a new webhook
5. Select the channel for notifications
6. Copy the webhook URL

**Step 2: Configure in Stratum AI**
1. Navigate to **Settings > Integrations > Slack**
2. Paste your webhook URL
3. Click **Test Connection**
4. If successful, click **Save**

### 7.2 Notification Types

| Notification | Description |
|--------------|-------------|
| Signal Health Alerts | When health degrades below threshold |
| Anomaly Alerts | Unusual metric changes detected |
| Daily Summary | Daily performance overview |
| Weekly Report | Weekly metrics summary |

### 7.3 Customizing Notifications

1. Go to **Settings > Notifications**
2. Toggle notification types on/off
3. Set quiet hours (optional)
4. Configure severity thresholds

---

## 8. Next Steps

### 8.1 Maximizing Your Starter Plan

- **Connect all your ad platforms** for a unified view
- **Monitor signal health daily** to ensure data quality
- **Use RFM analysis** to understand your customer base
- **Set up Slack alerts** to stay informed

### 8.2 Upgrading to Professional

Ready for more? The **Professional Plan** adds:
- Funnel Builder for conversion analysis
- Computed Traits for dynamic segmentation
- Trust Gate Audit Logs
- Action Dry-Run mode
- Pipedrive CRM integration

[Compare Plans](/pricing) | [Contact Sales](mailto:sales@stratum.ai)

---

## Quick Reference

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `G` then `O` | Go to Overview |
| `G` then `C` | Go to Campaigns |
| `G` then `D` | Go to CDP |
| `?` | Show all shortcuts |

### Starter Plan Limits

| Feature | Limit |
|---------|-------|
| Ad Accounts | 5 |
| Team Members | 3 |
| Data Retention | 90 days |
| API Requests | 10,000/month |
| Export Frequency | Weekly |

### Support Resources

- **Documentation:** [docs.stratum.ai](https://docs.stratum.ai)
- **Help Center:** [help.stratum.ai](https://help.stratum.ai)
- **Email Support:** support@stratum.ai (48-hour response)

---

**Congratulations!** You've completed the Starter Plan tutorial. You're now ready to get value from Stratum AI.

---

*Need help? Contact support@stratum.ai*
