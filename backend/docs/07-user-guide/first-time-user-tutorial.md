# Stratum AI — First-Time User Tutorial

> **Welcome to Stratum AI.** This tutorial walks you from signup to your first automated campaign decision in 20 minutes. No prior experience required.

---

## Table of Contents

1. [What Is Stratum AI?](#what-is-stratum-ai)
2. [Create Your Account](#step-1-create-your-account)
3. [Set Up Your First Tenant](#step-2-set-up-your-first-tenant)
4. [Connect Your Ad Platforms](#step-3-connect-your-ad-platforms)
5. [Explore the Dashboard](#step-4-explore-the-dashboard)
6. [Understand Your Trust Score](#step-5-understand-your-trust-score)
7. [Create Your First Campaign](#step-6-create-your-first-campaign)
8. [Set Up Autopilot](#step-7-set-up-autopilot)
9. [Review Insights & Take Action](#step-8-review-insights--take-action)
10. [Invite Your Team](#step-9-invite-your-team)
11. [What to Do Next](#what-to-do-next)

---

## What Is Stratum AI?

Stratum AI is a **Revenue Operating System** for marketing agencies and growth teams. It brings all your ad platforms, customer data, and campaign intelligence into one place — then automates decisions **only when your data quality is good enough**.

### The Core Idea: Trust-Gated Automation

Most automation tools execute blindly. Stratum AI checks the health of your data signals first:

```
Signal Health Check → Trust Gate → Automation Decision

   [HEALTHY]    →    [PASS]    →    [EXECUTE]
   [DEGRADED]   →    [HOLD]    →    [ALERT ONLY]
   [UNHEALTHY]  →    [BLOCK]   →    [MANUAL REVIEW]
```

This means you get the speed of automation **without** the risk of bad-data disasters.

---

## Step 1: Create Your Account

### Sign Up

1. Go to `https://app.stratum.ai` and click **Get Started**.
2. Enter your work email and create a password.
3. Verify your email (check your inbox for a confirmation link).
4. **Optional but recommended**: Enable WhatsApp OTP for extra security. Enter your phone number, receive a 6-digit code, and confirm.

> 💡 **Tip:** Use your agency's domain email (e.g., `you@agency.com`) so teammates can join the same organization later.

### First Login

After verification, you'll land on the **Tenant Setup** screen. A "tenant" is your workspace — it holds all your campaigns, data, and team settings.

---

## Step 2: Set Up Your First Tenant

### Create Your Workspace

1. **Tenant Name**: Enter your agency or brand name (e.g., "GrowthRocket").
2. **Slug**: This becomes your workspace URL (`growthrocket.stratum.ai`). Keep it short and lowercase.
3. **Industry**: Select your primary vertical (E-commerce, SaaS, Lead Gen, etc.). This helps Stratum tune its recommendations.
4. **Time Zone**: Pick your reporting timezone. All dashboards and schedules use this.

Click **Create Tenant**. You'll land on the **Overview Dashboard**.

### Understanding the Layout

```
┌─────────────────────────────────────────────────────────────┐
│  [Sidebar]        [Main Content Area]                       │
│  ┌────────┐       ┌─────────────────────────────────────┐   │
│  │ Logo   │       │  KPI Strip: Spend | Revenue | ROAS  │   │
│  ├────────┤       ├─────────────────────────────────────┤   │
│  │Overview│       │  Charts & Tables                    │   │
│  │Campaign│       │                                     │   │
│  │Trust   │       │  Insights Panel                     │   │
│  │CDP     │       │                                     │   │
│  │Settings│       └─────────────────────────────────────┘   │
│  └────────┘                                                 │
└─────────────────────────────────────────────────────────────┘
```

- **Sidebar**: Navigate between major sections.
- **KPI Strip**: Top-line metrics updated in real time.
- **Main Area**: Charts, tables, and actionable cards.
- **Insights Panel**: AI-generated suggestions and anomaly alerts.

---

## Step 3: Connect Your Ad Platforms

Without data, Stratum AI can't help you. Let's connect your first platform.

### Go to Settings → Integrations

1. Click **Settings** in the sidebar.
2. Select the **Integrations** tab.
3. You'll see cards for: **Meta Ads**, **Google Ads**, **TikTok Ads**, **Snapchat Ads**, **LinkedIn Ads**.

### Connect Meta (Facebook/Instagram) Ads

1. Click **Connect** on the Meta card.
2. You'll be redirected to Facebook's OAuth flow. Log in with your Business Manager account.
3. Grant permissions for: Ad Accounts, Campaigns, Insights, and Conversions API (CAPI).
4. You'll be redirected back to Stratum. Select the **ad account(s)** you want to sync.
5. Click **Save & Sync**.

> ⏱️ **First sync takes 2-5 minutes.** You'll see a progress bar. Once complete, your campaigns, spend, and conversion data appear in the dashboard.

### Connect Google Ads

1. Click **Connect** on the Google card.
2. Sign in with your Google Ads MCC (My Client Center) account.
3. Select the customer ID(s) to sync.
4. Click **Authorize & Sync**.

### Verify the Connection

Go back to **Overview**. You should now see:
- Campaign names from your connected accounts
- Real spend and revenue numbers
- Platform breakdown (Meta vs. Google pie chart)

If numbers look wrong, go to **Trust → Signal Health** to diagnose.

---

## Step 4: Explore the Dashboard

### The Overview Page

This is your mission control. Here's what each section tells you:

| Section | What It Shows | Why It Matters |
|---------|---------------|----------------|
| **KPI Strip** | Total Spend, Revenue, ROAS, CPA, Conversions | Instant health check of today's performance |
| **Daily Trend** | Spend vs. Revenue over time | Spot trends and anomalies at a glance |
| **Platform Breakdown** | Spend share by platform | Know where your budget is going |
| **ROAS by Platform** | Comparative ROAS bar chart | Identify your best and worst performers |
| **Top Campaigns** | Sorted by revenue or ROAS | Quick access to what's working |

### Toggle Time Ranges

Use the date picker (top right) to switch between:
- **Today** (real-time)
- **Last 7 Days**
- **Last 30 Days**
- **This Month vs. Last Month**
- **Custom Range**

### Dark Mode

Click the **moon/sun icon** in the top bar to toggle dark mode. Your preference is saved per device.

---

## Step 5: Understand Your Trust Score

The Trust Score is Stratum's unique safety mechanism. It ranges from **0 to 100**.

### Where to Find It

Navigate to **Trust → Overview**. You'll see:
- **Overall Trust Score** (big number at top)
- **5 Component Scores**: CAPI Health, Pixel Firing, Event Match Quality, Attribution Variance, Autopilot History
- **Trend Line**: How the score changed over the last 30 days

### Score Interpretation

| Score | Status | Meaning |
|-------|--------|---------|
| 90-100 | Excellent | Data is reliable. Autopilot can execute freely. |
| 70-89 | Good | Minor issues. Autopilot runs in Supervised mode. |
| 50-69 | Fair | Significant gaps. Actions require approval. |
| 0-49 | Poor | Data is untrustworthy. Automation is blocked. |

### Fix Your First Signal Issue

If any component is below 70, click it to see:
- **What's wrong** (e.g., "Event match rate is 62%")
- **Impact** (e.g., "Attribution accuracy reduced by 18%")
- **Recommended fix** (e.g., "Enable Advanced Matching in Meta Events Manager")

Follow the recommendation, wait 24 hours for data to refresh, and watch your score improve.

---

## Step 6: Create Your First Campaign

### Go to Campaigns → New Campaign

1. Click **Campaigns** in the sidebar.
2. Click the **+ New Campaign** button.
3. The **Campaign Builder** wizard opens.

### Step 1: Basics

- **Campaign Name**: "Summer Sale 2025"
- **Objective**: Conversions (or Traffic, Leads, etc.)
- **Platforms**: Select Meta and Google
- **Budget**: $5,000 total ($3,000 Meta, $2,000 Google)
- **Schedule**: Start today, run for 30 days

### Step 2: Targeting

- **Audiences**: Choose from your synced Meta/Google audiences, or create a new one using CDP segments
- **Locations**: United States, Canada
- **Age/Gender**: 25-54, All

### Step 3: Creative

- Upload images or videos
- Add primary text and headlines
- Stratum previews how your ad looks on each platform

### Step 4: Review & Publish

- Review all settings
- **Trust Gate Check**: Stratum runs a pre-flight check. If your Trust Score is above 70, you'll see a green checkmark.
- Click **Publish** or **Save as Draft**

> 🎯 **Pro Tip:** Save as draft if you want a teammate to review before going live.

---

## Step 7: Set Up Autopilot

Autopilot is where Stratum AI earns its name. It monitors your campaigns and takes action — but only when your Trust Score permits.

### Go to Autopilot → Settings

1. Click **Autopilot** in the sidebar.
2. Select your **Enforcement Mode**:
   - **Advisory**: Suggests actions, never executes. Best for learning.
   - **Supervised**: Suggests actions, executes only after you approve. **Recommended for new users.**
   - **Hard Block**: Blocks risky actions automatically. Executes safe ones without approval.

3. Set **Budget Guardrails**:
   - Max daily increase: 20%
   - Max daily decrease: 30%
   - Min ROAS threshold: 2.0x

4. Enable **Actions**:
   - ✅ Budget reallocation (move spend to best performers)
   - ✅ Pause underperformers (ROAS < 1.0 for 3+ days)
   - ✅ Scale winners (ROAS > 3.5 for 3+ days)
   - ⬜ Label campaigns (optional, for organization)

### Approve Your First Action

Within 24-48 hours of connecting platforms, Autopilot will generate its first recommendation. You'll see:

1. A notification bell icon (top right) with a red badge.
2. Click it to see: *"Increase Summer Sale 2025 budget by 15%? ROAS is 4.2x."*
3. Review the reasoning, then click **Approve** or **Dismiss**.

> 🛡️ **If Trust Score drops below 70**, Autopilot pauses and alerts you. Fix the signal issue to resume.

---

## Step 8: Review Insights & Take Action

### The Insights Panel

On the Overview page, the **Insights Panel** shows AI-generated findings:

| Type | Example | Action |
|------|---------|--------|
| **Opportunity** | "Meta CAPI event match rate improved to 94% — scale budget" | Approve in Autopilot |
| **Warning** | "Google Ads CTR dropped 32% vs. last week" | Investigate creative fatigue |
| **Suggestion** | "Optimal posting time for your audience is 9-11 AM" | Adjust schedule |
| **Anomaly** | "Revenue spiked 3x on Tuesday with no spend change" | Check for tracking errors |

### Drill Down

Click any insight to:
- See the raw data behind it
- View historical context
- Get step-by-step fix instructions
- Create a Jira/Slack ticket directly

---

## Step 9: Invite Your Team

### Go to Settings → Team

1. Click **Invite Member**.
2. Enter their email.
3. Assign a role:
   - **Admin**: Full access, billing, integrations
   - **Manager**: Campaigns, reports, CDP
   - **Analyst**: Read-only dashboards and exports
   - **Viewer**: Overview only

4. Click **Send Invite**. They'll receive an email with a join link.

### Role-Based Dashboards

- **Admins** see everything including billing and superadmin tools
- **Managers** see campaigns, CDP, and trust settings
- **Analysts** see dashboards and can export reports
- **Viewers** see the Overview page only

---

## What to Do Next

You've completed the essentials. Here's your 30-60-90 day roadmap:

### First 30 Days — Foundation
- [ ] Connect all active ad platforms
- [ ] Review and resolve all Trust Score components above 70
- [ ] Create 3-5 campaigns through the builder
- [ ] Approve or dismiss 10 Autopilot actions to train your preferences
- [ ] Set up Slack notifications (Settings → Notifications)

### Days 31-60 — Optimization
- [ ] Explore the **CDP** section and upload your first customer list
- [ ] Create a computed trait (e.g., "High LTV Customers")
- [ ] Set up **Audience Sync** to push segments to Meta/Google
- [ ] Run your first **A/B test** in the Campaigns section
- [ ] Review **Attribution** models and pick your preferred one

### Days 61-90 — Scale
- [ ] Add a second tenant (for a different brand or client)
- [ ] Use **Client Assignments** to manage multi-client workflows
- [ ] Set up **Webhook integrations** for your CRM
- [ ] Schedule automated **Reports** (weekly email to stakeholders)
- [ ] Explore **WhatsApp Marketing** for retention campaigns

---

## Need Help?

| Resource | Where to Find It |
|----------|------------------|
| In-app help | Press `?` for keyboard shortcuts; click the **?** icon in the sidebar |
| Feature docs | `docs/04-features/` in the project repository |
| API reference | `docs/04-features/{feature}/api-contracts.md` |
| Support email | `support@stratum.ai` |
| Status page | `status.stratum.ai` |

---

> 🎉 **Congratulations!** You're now a Stratum AI operator. The platform learns from every decision you make — the more you use it, the smarter it gets.
