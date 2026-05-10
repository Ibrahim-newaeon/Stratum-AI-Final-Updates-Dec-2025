# Stratum AI - User Guide

## Table of Contents

1. [Getting Started](#getting-started)
2. [Dashboard Overview](#dashboard-overview)
3. [Account Management](#account-management)
4. [Trust Engine](#trust-engine)
5. [Campaign Management](#campaign-management)
6. [Customer Data Platform (CDP)](#customer-data-platform-cdp)
7. [Integrations](#integrations)
8. [Settings & Configuration](#settings--configuration)
9. [Billing & Subscriptions](#billing--subscriptions)
10. [Keyboard Shortcuts](#keyboard-shortcuts)
11. [FAQ](#faq)

---

## Getting Started

### Logging In

1. Navigate to `https://your-domain.com`
2. Click **Sign In** or go directly to `/login`
3. Enter your email and password
4. If 2FA is enabled, enter your authentication code

### First-Time Setup

After your first login, complete these steps:

1. **Verify Email**: Check your inbox for verification email
2. **Complete Profile**: Add your name and organization details
3. **Connect Integrations**: Link your ad platforms (Google, Meta, TikTok, etc.)
4. **Explore Dashboard**: Familiarize yourself with the main interface

---

## Dashboard Overview

### Main Navigation

The sidebar provides access to all major sections:

| Section | Description |
|---------|-------------|
| **Dashboard** | Overview metrics and quick actions |
| **Campaigns** | Manage advertising campaigns |
| **Trust Engine** | Monitor signal health and automations |
| **CDP** | Customer data platform features |
| **Integrations** | Connect external platforms |
| **Settings** | Account and system configuration |

### Dashboard Widgets

#### Performance Metrics
- **Total Revenue**: Aggregate revenue across all campaigns
- **Active Campaigns**: Number of running campaigns
- **Signal Health**: Overall trust engine health score
- **Conversion Rate**: Average conversion percentage

#### Quick Actions
- Create new campaign
- View recent alerts
- Access trust gate status
- Export reports

---

## Account Management

### Profile Settings

Navigate to **Settings > Profile** to manage:

- **Personal Information**: Name, email, avatar
- **Password**: Change your password
- **Two-Factor Authentication**: Enable/disable 2FA
- **Notification Preferences**: Email and in-app alerts

### Enabling Two-Factor Authentication

1. Go to **Settings > Security**
2. Click **Enable 2FA**
3. Scan the QR code with your authenticator app
4. Enter the verification code to confirm
5. Save your backup codes securely

### Managing Team Members

*Available on Professional and Enterprise plans*

1. Navigate to **Settings > Team**
2. Click **Invite Member**
3. Enter email and select role:
   - **Admin**: Full access
   - **Manager**: Campaign management
   - **Analyst**: View-only access
4. Click **Send Invitation**

---

## Trust Engine

### Understanding Signal Health

The Trust Engine evaluates data reliability before executing automations:

| Health Score | Status | Action |
|--------------|--------|--------|
| 70-100 | **Healthy** (Green) | Automations execute normally |
| 40-69 | **Degraded** (Yellow) | Alerts sent, actions held |
| 0-39 | **Unhealthy** (Red) | Manual intervention required |

### Signal Types

- **Conversion Signals**: Purchase, signup, lead events
- **Engagement Signals**: Clicks, views, time on site
- **Attribution Signals**: Source tracking accuracy
- **Quality Signals**: Data completeness and freshness

### Trust Gates

Trust Gates are checkpoints that validate conditions before automation:

1. **Signal Health Gate**: Verifies data quality threshold
2. **Budget Gate**: Ensures spending limits
3. **Performance Gate**: Checks ROI thresholds
4. **Time Gate**: Validates scheduling constraints

### Configuring Automations

1. Go to **Trust Engine > Automations**
2. Click **Create Automation**
3. Define trigger conditions:
   - Signal type
   - Health threshold
   - Time window
4. Set actions:
   - Adjust bids
   - Pause/enable campaigns
   - Send notifications
5. Configure trust gates
6. Save and activate

---

## Campaign Management

### Creating a Campaign

1. Navigate to **Campaigns**
2. Click **New Campaign**
3. Select campaign type:
   - **Performance**: Optimize for conversions
   - **Awareness**: Maximize reach
   - **Engagement**: Drive interactions
4. Configure settings:
   - Name and description
   - Budget and schedule
   - Target audience
   - Bid strategy
5. Review and launch

### Campaign Dashboard

Each campaign shows:

- **Performance Metrics**: Spend, conversions, ROAS
- **Signal Health**: Data quality indicators
- **Trust Gate Status**: Automation eligibility
- **Recent Activity**: Timeline of changes

### Bulk Operations

Select multiple campaigns to:
- Pause/Resume
- Update budgets
- Change bid strategies
- Export data

---

## Customer Data Platform (CDP)

### Overview

The CDP unifies customer data across all touchpoints, providing:

- **Unified Profiles**: Single view of each customer
- **Segmentation**: Dynamic audience building
- **Identity Resolution**: Cross-device tracking
- **Audience Sync**: Push segments to ad platforms

### Customer Profiles

Navigate to **CDP > Profiles** to:

1. **Search Profiles**: By email, ID, or attributes
2. **View Profile Details**:
   - Contact information
   - Event history
   - Segment memberships
   - Identity graph
3. **Edit Profiles**: Update attributes manually

### Building Segments

1. Go to **CDP > Segments**
2. Click **Create Segment**
3. Add conditions using the builder:
   - **Event-based**: "Purchased in last 30 days"
   - **Attribute-based**: "VIP tier = Gold"
   - **Behavioral**: "Visited pricing page 3+ times"
4. Preview audience size
5. Save segment

#### Segment Condition Types

| Type | Example |
|------|---------|
| **Has Done** | User completed purchase event |
| **Has Not Done** | User hasn't logged in 30+ days |
| **Attribute Is** | Country equals "USA" |
| **Attribute Contains** | Email contains "@company.com" |

### Identity Graph

Visualize how customer identities connect:

1. Go to **CDP > Identity Graph**
2. Search for a profile
3. View connected identities:
   - Email addresses
   - Phone numbers
   - Device IDs
   - Anonymous IDs

### Audience Sync

Push CDP segments to advertising platforms:

1. Navigate to **CDP > Audience Sync**
2. Click **Create Audience**
3. Select segment and platform:
   - Meta (Custom Audiences)
   - Google (Customer Match)
   - TikTok (DMP Audiences)
   - Snapchat (SAM Audiences)
4. Configure sync settings:
   - Auto-sync interval (1 hour to 1 week)
   - Include/exclude options
5. Activate sync

#### Monitoring Sync Status

View sync history showing:
- Profiles sent
- Profiles matched
- Match rate percentage
- Last sync timestamp

---

## Integrations

### Connecting Platforms

#### Google Ads

1. Go to **Integrations > Google Ads**
2. Click **Connect Account**
3. Sign in with your Google account
4. Grant required permissions
5. Select accounts to sync

#### Meta (Facebook/Instagram)

1. Go to **Integrations > Meta**
2. Click **Connect Account**
3. Authorize with Facebook
4. Select ad accounts and pages
5. Configure data sharing settings

#### TikTok Ads

1. Go to **Integrations > TikTok**
2. Click **Connect Account**
3. Sign in to TikTok Business Center
4. Authorize access
5. Select advertiser accounts

#### Snapchat Ads

1. Go to **Integrations > Snapchat**
2. Click **Connect Account**
3. Authenticate with Snapchat
4. Select organization and ad accounts

### Webhook Configuration

Receive real-time notifications:

1. Go to **Settings > Webhooks**
2. Click **Add Webhook**
3. Configure:
   - Endpoint URL
   - Events to subscribe
   - Secret key for verification
4. Test webhook delivery

---

## Settings & Configuration

### Organization Settings

*Admin only*

- **Organization Name**: Display name
- **Logo**: Upload company logo
- **Timezone**: Default timezone for reports
- **Currency**: Reporting currency

### Notification Settings

Configure alerts for:

| Event | Email | In-App | Slack |
|-------|-------|--------|-------|
| Signal Health Change | Yes | Yes | Yes |
| Campaign Status Change | Yes | Yes | Yes |
| Budget Alerts | Yes | Yes | Yes |
| Trust Gate Failures | Yes | Yes | Yes |

### API Keys

Generate API keys for external integrations:

1. Go to **Settings > API Keys**
2. Click **Generate New Key**
3. Set permissions and expiration
4. Copy and store securely (shown only once)

### Data Export

Export your data:

1. Go to **Settings > Data Export**
2. Select data type:
   - Campaigns
   - Profiles
   - Events
   - Reports
3. Choose format (CSV, JSON)
4. Request export
5. Download when ready

---

## Billing & Subscriptions

### Subscription Plans

| Feature | Starter | Professional | Enterprise |
|---------|---------|--------------|------------|
| Monthly Price | $99 | $299 | Custom |
| Team Members | 2 | 10 | Unlimited |
| Campaigns | 5 | 25 | Unlimited |
| CDP Profiles | 10,000 | 100,000 | Unlimited |
| Integrations | 2 | All | All + Custom |
| Support | Email | Priority | Dedicated |

### Managing Subscription

1. Go to **Settings > Billing**
2. View current plan and usage
3. Upgrade/downgrade options
4. Update payment method

### Payment Methods

Accepted payment methods:
- Credit/Debit Cards (Visa, Mastercard, Amex)
- Bank Transfer (Enterprise only)

### Invoices

Access billing history:

1. Go to **Settings > Billing > Invoices**
2. View/download past invoices
3. Update billing email for receipts

---

## Keyboard Shortcuts

### Global Shortcuts

| Shortcut | Action |
|----------|--------|
| `G` then `D` | Go to Dashboard |
| `G` then `C` | Go to Campaigns |
| `G` then `T` | Go to Trust Engine |
| `G` then `P` | Go to CDP Profiles |
| `G` then `S` | Go to Settings |
| `/` | Open search |
| `?` | Show keyboard shortcuts |
| `Esc` | Close modal/dialog |

### Campaign Shortcuts

| Shortcut | Action |
|----------|--------|
| `N` | New campaign |
| `E` | Edit selected campaign |
| `P` | Pause/Resume campaign |
| `D` | Duplicate campaign |

### Table Navigation

| Shortcut | Action |
|----------|--------|
| `J` | Next row |
| `K` | Previous row |
| `Enter` | Open selected item |
| `Space` | Select/deselect row |

---

## FAQ

### General

**Q: How do I reset my password?**
A: Click "Forgot Password" on the login page, enter your email, and follow the reset link.

**Q: Can I change my email address?**
A: Go to Settings > Profile. Note that changing email requires verification.

**Q: How do I enable dark mode?**
A: The platform uses dark mode by default. Light mode is coming soon.

### Trust Engine

**Q: Why is my signal health low?**
A: Low signal health indicates data quality issues. Check:
- Tracking pixel installation
- Event firing correctly
- Data freshness (stale data reduces score)

**Q: Can I override a trust gate?**
A: Admins can manually approve held actions. Go to Trust Engine > Pending Actions.

**Q: How often are signals recalculated?**
A: Signal health is recalculated every 15 minutes by default.

### CDP

**Q: How long is event data retained?**
A: Events are retained for 12 months by default. Enterprise plans can configure longer retention.

**Q: Can I merge duplicate profiles?**
A: Yes. In CDP > Profiles, select profiles and click "Merge". The system will combine data and preserve history.

**Q: What data is hashed for audience sync?**
A: Email addresses and phone numbers are SHA256 hashed before sending to platforms.

### Integrations

**Q: Why isn't my Google Ads data syncing?**
A: Verify:
1. OAuth token hasn't expired
2. Required permissions granted
3. Account is active and accessible

**Q: How do I disconnect an integration?**
A: Go to Integrations, find the connected platform, and click "Disconnect".

### Billing

**Q: Can I get a refund?**
A: Contact support@stratum.ai within 14 days of purchase for refund requests.

**Q: What happens if I exceed my plan limits?**
A: You'll receive warnings at 80% and 100%. Service continues but you'll need to upgrade.

**Q: Do you offer annual billing?**
A: Yes, annual billing includes a 20% discount. Contact sales for details.

---

## Getting Help

### Support Channels

- **Documentation**: https://docs.stratum.ai
- **Email Support**: support@stratum.ai
- **Live Chat**: Available in-app (Professional+ plans)
- **Phone Support**: Enterprise plans only

### Response Times

| Plan | Response Time |
|------|---------------|
| Starter | 48 hours |
| Professional | 24 hours |
| Enterprise | 4 hours |

### Reporting Issues

When contacting support, include:
1. Account email
2. Browser and version
3. Steps to reproduce issue
4. Screenshots if applicable
5. Any error messages
