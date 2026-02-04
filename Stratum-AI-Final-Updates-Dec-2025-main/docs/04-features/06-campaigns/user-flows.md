# Campaign Builder User Flows

## Overview

Step-by-step user journeys for connecting platforms, managing ad accounts, and creating/publishing campaigns.

---

## Flow 1: Connect Ad Platform

**Actor**: Admin user

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                   CONNECT AD PLATFORM                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Navigate to Settings → Integrations                         │
│                                                                 │
│  2. View available platforms:                                   │
│     ├─► Meta (Facebook/Instagram)                              │
│     ├─► Google Ads                                             │
│     ├─► TikTok Ads                                             │
│     └─► Snapchat Ads                                           │
│                                                                 │
│  3. Click "Connect" on desired platform                         │
│     └─► e.g., Meta                                             │
│                                                                 │
│  4. Redirect to platform OAuth                                  │
│     └─► Facebook login page                                    │
│                                                                 │
│  5. Authorize app permissions:                                  │
│     ├─► ads_management                                         │
│     ├─► ads_read                                               │
│     └─► business_management                                    │
│                                                                 │
│  6. Redirect back to Stratum                                    │
│     └─► /oauth/callback?code=...&state=...                     │
│                                                                 │
│  7. System processes callback:                                  │
│     ├─► Exchange code for access token                         │
│     ├─► Store encrypted tokens                                 │
│     ├─► Fetch and sync ad accounts                             │
│     └─► Set status: connected                                  │
│                                                                 │
│  8. Display success:                                            │
│     ├─► Platform connected                                     │
│     └─► X ad accounts found                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Sequence Diagram

```
User            Stratum            Platform           Database
 │                │                   │                  │
 │ Click Connect  │                   │                  │
 │───────────────►│                   │                  │
 │                │ Generate state    │                  │
 │                │ Get OAuth URL     │                  │
 │                │                   │                  │
 │◄───────────────│ Redirect to       │                  │
 │                │ platform OAuth    │                  │
 │────────────────────────────────────►                  │
 │                │                   │                  │
 │ Authorize      │                   │                  │
 │ permissions    │                   │                  │
 │────────────────────────────────────►                  │
 │                │                   │                  │
 │◄───────────────────────────────────│ Redirect with    │
 │                │                   │ auth code        │
 │───────────────►│                   │                  │
 │                │ Exchange code     │                  │
 │                │──────────────────►│                  │
 │                │◄──────────────────│ Tokens           │
 │                │                   │                  │
 │                │ Encrypt tokens    │                  │
 │                │ Save connection   │                  │
 │                │──────────────────────────────────────►
 │                │                   │                  │
 │                │ Fetch ad accounts │                  │
 │                │──────────────────►│                  │
 │                │◄──────────────────│                  │
 │                │ Save accounts     │                  │
 │                │──────────────────────────────────────►
 │◄───────────────│ Connected!        │                  │
```

---

## Flow 2: Enable Ad Account

**Actor**: Admin user

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                    ENABLE AD ACCOUNT                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Navigate to Settings → Ad Accounts                          │
│                                                                 │
│  2. View synced accounts per platform:                          │
│     ┌──────────────────────────────────────────────┐           │
│     │ META AD ACCOUNTS                             │           │
│     │ ┌────────────────────────────────────────┐  │           │
│     │ │ act_123456789 - Acme Corp Main          │  │           │
│     │ │ Currency: USD | Status: Disabled        │  │           │
│     │ │ [Enable] [Set Budget Cap]               │  │           │
│     │ └────────────────────────────────────────┘  │           │
│     │ ┌────────────────────────────────────────┐  │           │
│     │ │ act_987654321 - Acme Corp Test          │  │           │
│     │ │ Currency: USD | Status: Disabled        │  │           │
│     │ │ [Enable] [Set Budget Cap]               │  │           │
│     │ └────────────────────────────────────────┘  │           │
│     └──────────────────────────────────────────────┘           │
│                                                                 │
│  3. Click "Enable" on desired account                           │
│                                                                 │
│  4. Optional: Set budget cap                                    │
│     ├─► Daily budget cap: $1,000                               │
│     └─► Monthly budget cap: $30,000                            │
│                                                                 │
│  5. Confirm enablement                                          │
│     └─► PUT /ad-accounts/{platform}/{id}                       │
│                                                                 │
│  6. Account now available for campaigns                         │
│     └─► Appears in campaign builder dropdown                   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Flow 3: Create Campaign Draft

**Actor**: Campaign creator

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                  CREATE CAMPAIGN DRAFT                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Navigate to Campaigns → Create New                          │
│                                                                 │
│  2. Select platform and ad account:                             │
│     ├─► Platform: Meta                                         │
│     └─► Ad Account: Acme Corp Main (act_123...)                │
│                                                                 │
│  3. Define campaign details:                                    │
│     ├─► Name: "Summer Sale 2024"                               │
│     ├─► Objective: Conversions                                 │
│     ├─► Budget: $1,000/day                                     │
│     └─► Schedule: Jun 1 - Aug 31                               │
│                                                                 │
│  4. Create ad set(s):                                           │
│     ├─► Name: "US - 25-54"                                     │
│     ├─► Targeting:                                             │
│     │   ├─► Location: United States                            │
│     │   ├─► Age: 25-54                                         │
│     │   └─► Interests: Fashion, Shopping                       │
│     ├─► Budget: $500/day                                       │
│     └─► Optimization: Conversions                              │
│                                                                 │
│  5. Create ad(s):                                               │
│     ├─► Name: "Summer Sale - Image Ad"                         │
│     ├─► Creative Type: Single Image                            │
│     ├─► Upload image                                           │
│     ├─► Headline: "Summer Sale - Up to 50% Off!"               │
│     ├─► Description: "Shop now for the best deals"             │
│     ├─► CTA: Shop Now                                          │
│     └─► URL: https://shop.example.com/summer                   │
│                                                                 │
│  6. Save as draft                                               │
│     └─► POST /campaign-drafts                                  │
│     └─► Status: "draft"                                        │
│                                                                 │
│  7. Preview campaign structure                                  │
│     └─► Verify all settings before submission                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Flow 4: Submit for Approval

**Actor**: Campaign creator

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                  SUBMIT FOR APPROVAL                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Open campaign draft                                         │
│                                                                 │
│  2. Review all settings:                                        │
│     ├─► Campaign name and objective                            │
│     ├─► Budget and schedule                                    │
│     ├─► Targeting configuration                                │
│     └─► Creative assets                                        │
│                                                                 │
│  3. Click "Submit for Approval"                                 │
│     └─► POST /campaign-drafts/{id}/submit                      │
│                                                                 │
│  4. System validates:                                           │
│     ├─► Required fields present                                │
│     ├─► Budget within account caps                             │
│     ├─► Platform is connected                                  │
│     └─► Ad account is enabled                                  │
│                                                                 │
│  5. Status changes to "submitted"                               │
│     ├─► submitted_at: timestamp                                │
│     └─► submitted_by_user_id: current user                     │
│                                                                 │
│  6. Notification sent to approvers                              │
│     └─► Email/in-app notification                              │
│                                                                 │
│  7. Draft now read-only until approved/rejected                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Flow 5: Approve/Reject Campaign

**Actor**: Campaign approver (admin)

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                  APPROVE/REJECT CAMPAIGN                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Navigate to Campaigns → Pending Approval                    │
│                                                                 │
│  2. View campaigns awaiting approval:                           │
│     ┌──────────────────────────────────────────────┐           │
│     │ PENDING APPROVAL                             │           │
│     │ ┌────────────────────────────────────────┐  │           │
│     │ │ Summer Sale 2024                        │  │           │
│     │ │ Meta | $1,000/day | Jun 1 - Aug 31     │  │           │
│     │ │ Submitted by: John @ 2024-01-15        │  │           │
│     │ │ [Review] [Approve] [Reject]            │  │           │
│     │ └────────────────────────────────────────┘  │           │
│     └──────────────────────────────────────────────┘           │
│                                                                 │
│  3. Click "Review" to examine details                           │
│     ├─► View full campaign structure                           │
│     ├─► Check targeting settings                               │
│     ├─► Preview creatives                                      │
│     └─► Verify budget/schedule                                 │
│                                                                 │
│  APPROVE PATH:                                                  │
│  ─────────────                                                  │
│  4a. Click "Approve"                                            │
│      └─► POST /campaign-drafts/{id}/approve                    │
│                                                                 │
│  5a. Status changes to "approved"                               │
│      ├─► approved_at: timestamp                                │
│      └─► approved_by_user_id: current user                     │
│                                                                 │
│  6a. Creator notified                                           │
│      └─► Can now publish campaign                              │
│                                                                 │
│  REJECT PATH:                                                   │
│  ────────────                                                   │
│  4b. Click "Reject"                                             │
│      └─► Enter rejection reason                                │
│                                                                 │
│  5b. Submit rejection                                           │
│      └─► POST /campaign-drafts/{id}/reject                     │
│      └─► reason: "Budget too high for test campaign"           │
│                                                                 │
│  6b. Status changes to "rejected"                               │
│      ├─► rejected_at: timestamp                                │
│      ├─► rejected_by_user_id: current user                     │
│      └─► rejection_reason: stored                              │
│                                                                 │
│  7b. Creator notified                                           │
│      └─► Can revise and resubmit                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Flow 6: Publish Campaign

**Actor**: Campaign publisher

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                    PUBLISH CAMPAIGN                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Open approved campaign                                      │
│                                                                 │
│  2. Click "Publish to Platform"                                 │
│                                                                 │
│  3. System validates:                                           │
│     ├─► Status is "approved"                                   │
│     ├─► Platform connection is valid                           │
│     ├─► Token not expired                                      │
│     └─► Budget within caps                                     │
│                                                                 │
│  4. Status changes to "publishing"                              │
│     └─► Processing indicator shown                             │
│                                                                 │
│  5. System publishes:                                           │
│     ├─► Convert draft_json to platform format                  │
│     ├─► Call platform API                                      │
│     ├─► Create campaign → ad sets → ads                        │
│     └─► Log request/response                                   │
│                                                                 │
│  SUCCESS:                                                       │
│  ────────                                                       │
│  6a. Status changes to "published"                              │
│      ├─► platform_campaign_id: "23842927..."                   │
│      └─► published_at: timestamp                               │
│                                                                 │
│  7a. Display success:                                           │
│      ├─► Campaign live on platform                             │
│      └─► Link to view in platform dashboard                    │
│                                                                 │
│  FAILURE:                                                       │
│  ────────                                                       │
│  6b. Status changes to "failed"                                 │
│      ├─► error_code: "INVALID_TARGETING"                       │
│      └─► error_message: "Age range invalid"                    │
│                                                                 │
│  7b. Display error:                                             │
│      ├─► Error details shown                                   │
│      └─► Option to retry or edit                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Publish Sequence

```
User            Stratum           Celery           Platform
 │                │                 │                  │
 │ Click Publish  │                 │                  │
 │───────────────►│                 │                  │
 │                │ Validate draft  │                  │
 │                │ Set: publishing │                  │
 │                │                 │                  │
 │◄───────────────│ Publishing...   │                  │
 │                │                 │                  │
 │                │ Queue task      │                  │
 │                │────────────────►│                  │
 │                │                 │                  │
 │                │                 │ Convert JSON     │
 │                │                 │ Call API         │
 │                │                 │─────────────────►│
 │                │                 │◄─────────────────│
 │                │                 │ Response         │
 │                │                 │                  │
 │                │◄────────────────│ Update status    │
 │                │                 │                  │
 │ (Poll or WS)   │                 │                  │
 │───────────────►│                 │                  │
 │◄───────────────│ Published!      │                  │
```

---

## Flow 7: Sync Ad Accounts

**Actor**: Admin user

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                   SYNC AD ACCOUNTS                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Navigate to Settings → Ad Accounts                          │
│                                                                 │
│  2. Click "Sync Accounts" for platform                          │
│     └─► POST /ad-accounts/{platform}/sync                      │
│                                                                 │
│  3. System fetches accounts:                                    │
│     ├─► Call platform API                                      │
│     ├─► Get all accessible ad accounts                         │
│     └─► Update local records                                   │
│                                                                 │
│  4. Comparison:                                                 │
│     ├─► New accounts: Added                                    │
│     ├─► Existing accounts: Updated                             │
│     └─► Missing accounts: Marked stale                         │
│                                                                 │
│  5. Display results:                                            │
│     ├─► 2 new accounts found                                   │
│     ├─► 3 accounts updated                                     │
│     └─► Last synced: just now                                  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Related Documentation

- [Specification](./spec.md) - Data models and architecture
- [API Contracts](./api-contracts.md) - API endpoints and schemas
- [Edge Cases](./edge-cases.md) - Error handling and edge cases
