# Audience Sync User Flows

## Overview

This document describes the key user journeys for syncing CDP segments to ad platforms.

---

## Flow 1: Create Platform Audience

### Description
User creates a new platform audience linked to a CDP segment.

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                CREATE PLATFORM AUDIENCE FLOW                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Navigate to CDP → Audience Sync                             │
│         │                                                       │
│         ▼                                                       │
│  2. Click "Create Audience"                                     │
│         │                                                       │
│         ▼                                                       │
│  3. Select source segment                                       │
│     ┌────────────────────────────────────────────────────────┐ │
│     │ Select Segment                                         │ │
│     │ ──────────────────────────────────────────────────────│ │
│     │                                                        │ │
│     │ ○ High Value Customers (1,234 profiles)               │ │
│     │ ○ Newsletter Subscribers (5,678 profiles)              │ │
│     │ ○ At Risk Churning (890 profiles)                      │ │
│     │                                                        │ │
│     │ [Next]                                                 │ │
│     └────────────────────────────────────────────────────────┘ │
│         │                                                       │
│         ▼                                                       │
│  4. Select platform and ad account                              │
│     ┌────────────────────────────────────────────────────────┐ │
│     │ Select Platform                                        │ │
│     │ ──────────────────────────────────────────────────────│ │
│     │                                                        │ │
│     │ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                  │ │
│     │ │ Meta │ │Google│ │TikTok│ │Snap  │                  │ │
│     │ │  ✓   │ │      │ │      │ │      │                  │ │
│     │ └──────┘ └──────┘ └──────┘ └──────┘                  │ │
│     │                                                        │ │
│     │ Ad Account: [act_123456789 - Main Account        ▼]   │ │
│     │                                                        │ │
│     │ [Next]                                                 │ │
│     └────────────────────────────────────────────────────────┘ │
│         │                                                       │
│         ▼                                                       │
│  5. Configure audience settings                                 │
│     ┌────────────────────────────────────────────────────────┐ │
│     │ Audience Settings                                      │ │
│     │ ──────────────────────────────────────────────────────│ │
│     │                                                        │ │
│     │ Name: [High Value Customers - Stratum           ]      │ │
│     │                                                        │ │
│     │ Description: [                                   ]      │ │
│     │                                                        │ │
│     │ Auto-sync: [✓]                                         │ │
│     │ Sync interval: [Every 24 hours                   ▼]   │ │
│     │                                                        │ │
│     │ [Create Audience]                                      │ │
│     └────────────────────────────────────────────────────────┘ │
│         │                                                       │
│         ▼                                                       │
│  6. System creates audience and syncs                           │
│     ┌────────────────────────────────────────────────────────┐ │
│     │ Creating audience...                                   │ │
│     │ ████████████████████░░░░░░░░░░░░░░ 60%                │ │
│     │                                                        │ │
│     │ • Creating audience on Meta... ✓                       │ │
│     │ • Uploading 1,234 profiles... ⟳                       │ │
│     │ • Processing identifiers...                            │ │
│     └────────────────────────────────────────────────────────┘ │
│         │                                                       │
│         ▼                                                       │
│  7. View sync results                                           │
│     ┌────────────────────────────────────────────────────────┐ │
│     │ ✓ Audience Created Successfully                        │ │
│     │ ──────────────────────────────────────────────────────│ │
│     │                                                        │ │
│     │ Audience: High Value Customers - Stratum               │ │
│     │ Platform: Meta (act_123456789)                         │ │
│     │                                                        │ │
│     │ Sync Results:                                          │ │
│     │ • Profiles Sent: 1,234                                 │ │
│     │ • Matched: 1,087 (88.1%)                               │ │
│     │ • Next Sync: Jan 16, 2024 14:30                        │ │
│     │                                                        │ │
│     │ [View in Meta] [Done]                                  │ │
│     └────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Flow 2: Manual Sync Trigger

### Description
User manually triggers a sync for an existing platform audience.

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                  MANUAL SYNC TRIGGER FLOW                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. View platform audiences list                                │
│     ┌────────────────────────────────────────────────────────┐ │
│     │ Platform Audiences                                     │ │
│     │ ──────────────────────────────────────────────────────│ │
│     │                                                        │ │
│     │ ┌───────────────────────────────────────────────────┐ │ │
│     │ │ High Value Customers                    Meta      │ │ │
│     │ │ Last sync: 2 hours ago | Match rate: 88%         │ │ │
│     │ │ [Sync Now] [View History] [⋮]                    │ │ │
│     │ └───────────────────────────────────────────────────┘ │ │
│     │                                                        │ │
│     │ ┌───────────────────────────────────────────────────┐ │ │
│     │ │ Newsletter Subscribers                   Google   │ │ │
│     │ │ Last sync: 1 day ago | Match rate: 75%           │ │ │
│     │ │ [Sync Now] [View History] [⋮]                    │ │ │
│     │ └───────────────────────────────────────────────────┘ │ │
│     └────────────────────────────────────────────────────────┘ │
│         │                                                       │
│         ▼                                                       │
│  2. Click "Sync Now"                                            │
│         │                                                       │
│         ▼                                                       │
│  3. Confirm sync operation                                      │
│     ┌────────────────────────────────────────────────────────┐ │
│     │ Sync Audience                                          │ │
│     │ ──────────────────────────────────────────────────────│ │
│     │                                                        │ │
│     │ Sync "High Value Customers" to Meta?                   │ │
│     │                                                        │ │
│     │ Current segment size: 1,302 profiles                   │ │
│     │ Last synced size: 1,234 profiles                       │ │
│     │ Expected changes: +68 added                            │ │
│     │                                                        │ │
│     │ Sync type:                                             │ │
│     │ ○ Incremental (add/remove changes only)                │ │
│     │ ○ Full replace (replace entire audience)               │ │
│     │                                                        │ │
│     │ [Cancel] [Sync Now]                                    │ │
│     └────────────────────────────────────────────────────────┘ │
│         │                                                       │
│         ▼                                                       │
│  4. View sync progress                                          │
│     ┌────────────────────────────────────────────────────────┐ │
│     │ Syncing...                                             │ │
│     │ ████████████████████████████░░░░░░ 75%                │ │
│     │                                                        │ │
│     │ • Getting segment members... ✓                         │ │
│     │ • Calculating delta... ✓                               │ │
│     │ • Hashing identifiers... ✓                             │ │
│     │ • Uploading to Meta... ⟳                              │ │
│     └────────────────────────────────────────────────────────┘ │
│         │                                                       │
│         ▼                                                       │
│  5. View sync results                                           │
│     ┌────────────────────────────────────────────────────────┐ │
│     │ ✓ Sync Completed                                       │ │
│     │ ──────────────────────────────────────────────────────│ │
│     │                                                        │ │
│     │ • Profiles Sent: 68                                    │ │
│     │ • Added: 68                                            │ │
│     │ • Removed: 0                                           │ │
│     │ • Failed: 0                                            │ │
│     │ • Duration: 4.2 seconds                                │ │
│     │                                                        │ │
│     │ Current audience size: 1,155 (matched)                 │ │
│     │ Match rate: 88.7%                                      │ │
│     └────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Flow 3: View Sync History

### Description
User reviews the history of sync operations for an audience.

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                    SYNC HISTORY FLOW                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Navigate to audience → View History                         │
│         │                                                       │
│         ▼                                                       │
│  2. View sync history table                                     │
│     ┌────────────────────────────────────────────────────────┐ │
│     │ Sync History: High Value Customers                     │ │
│     │ ──────────────────────────────────────────────────────│ │
│     │                                                        │ │
│     │ ┌─────────┬─────────┬───────┬────────┬───────┬──────┐ │ │
│     │ │ Date    │Operation│Status │ Sent   │ Match │ Time │ │ │
│     │ ├─────────┼─────────┼───────┼────────┼───────┼──────┤ │ │
│     │ │ Jan 15  │ Update  │ ✓     │ +68    │ 88.7% │ 4.2s │ │ │
│     │ │ Jan 14  │ Update  │ ✓     │ +23    │ 88.1% │ 3.1s │ │ │
│     │ │ Jan 13  │ Update  │ ✓     │ -12    │ 87.9% │ 2.8s │ │ │
│     │ │ Jan 12  │ Update  │ ✓     │ +45    │ 88.2% │ 3.5s │ │ │
│     │ │ Jan 11  │ Replace │ ✓     │ 1,156  │ 88.0% │ 15s  │ │ │
│     │ │ Jan 10  │ Create  │ ✓     │ 1,100  │ 87.5% │ 12s  │ │ │
│     │ └─────────┴─────────┴───────┴────────┴───────┴──────┘ │ │
│     │                                                        │ │
│     │ Summary (30 days):                                     │ │
│     │ • Total syncs: 15                                      │ │
│     │ • Success rate: 100%                                   │ │
│     │ • Avg match rate: 87.9%                                │ │
│     │ • Audience growth: +256 profiles                       │ │
│     └────────────────────────────────────────────────────────┘ │
│         │                                                       │
│         ▼                                                       │
│  3. Click row for detailed view                                 │
│     ┌────────────────────────────────────────────────────────┐ │
│     │ Sync Details: Jan 15, 2024 14:30:00                    │ │
│     │ ──────────────────────────────────────────────────────│ │
│     │                                                        │ │
│     │ Operation: Update (Incremental)                        │ │
│     │ Status: Completed                                      │ │
│     │ Triggered by: Scheduled                                │ │
│     │                                                        │ │
│     │ Metrics:                                               │ │
│     │ • Profiles Sent: 68                                    │ │
│     │ • Added: 68                                            │ │
│     │ • Removed: 0                                           │ │
│     │ • Failed: 0                                            │ │
│     │                                                        │ │
│     │ Platform Response:                                     │ │
│     │ • Audience ID: 23847583947582                          │ │
│     │ • Audience Size: 1,155                                 │ │
│     │ • Match Rate: 88.7%                                    │ │
│     │                                                        │ │
│     │ Duration: 4.2 seconds                                  │ │
│     │ Started: 14:30:00 | Completed: 14:30:04                │ │
│     └────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Flow 4: Export Audience

### Description
User exports a segment as a CSV/JSON file for manual upload or analysis.

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                    EXPORT AUDIENCE FLOW                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Navigate to segment → Export                                │
│         │                                                       │
│         ▼                                                       │
│  2. Configure export options                                    │
│     ┌────────────────────────────────────────────────────────┐ │
│     │ Export Segment                                         │ │
│     │ ──────────────────────────────────────────────────────│ │
│     │                                                        │ │
│     │ Segment: High Value Customers (1,234 profiles)         │ │
│     │                                                        │ │
│     │ Format:                                                │ │
│     │ ○ CSV (Recommended)                                    │ │
│     │ ○ JSON                                                 │ │
│     │                                                        │ │
│     │ Include identifiers:                                   │ │
│     │ [✓] Email (hashed)                                     │ │
│     │ [✓] Phone (hashed)                                     │ │
│     │ [ ] Device ID                                          │ │
│     │                                                        │ │
│     │ Include data:                                          │ │
│     │ [✓] Computed traits                                    │ │
│     │ [ ] Recent events (last 30 days)                       │ │
│     │ [ ] Profile attributes                                 │ │
│     │                                                        │ │
│     │ Hash identifiers: [✓]                                  │ │
│     │                                                        │ │
│     │ [Export]                                               │ │
│     └────────────────────────────────────────────────────────┘ │
│         │                                                       │
│         ▼                                                       │
│  3. Generate export                                             │
│     ┌────────────────────────────────────────────────────────┐ │
│     │ Generating export...                                   │ │
│     │ ████████████████████████████████████ 100%             │ │
│     └────────────────────────────────────────────────────────┘ │
│         │                                                       │
│         ▼                                                       │
│  4. Download file                                               │
│     ┌────────────────────────────────────────────────────────┐ │
│     │ ✓ Export Ready                                         │ │
│     │ ──────────────────────────────────────────────────────│ │
│     │                                                        │ │
│     │ File: high-value-customers-2024-01-15.csv              │ │
│     │ Size: 245 KB                                           │ │
│     │ Profiles: 1,234                                        │ │
│     │                                                        │ │
│     │ [Download] [Copy Link]                                 │ │
│     │                                                        │ │
│     │ Link expires in 24 hours                               │ │
│     └────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Flow 5: Connect Platform

### Description
User connects an ad platform account for audience sync.

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                   CONNECT PLATFORM FLOW                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Navigate to Audience Sync → Connected Platforms             │
│         │                                                       │
│         ▼                                                       │
│  2. Click "Connect Platform"                                    │
│         │                                                       │
│         ▼                                                       │
│  3. Select platform                                             │
│     ┌────────────────────────────────────────────────────────┐ │
│     │ Connect Platform                                       │ │
│     │ ──────────────────────────────────────────────────────│ │
│     │                                                        │ │
│     │ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐                  │ │
│     │ │ Meta │ │Google│ │TikTok│ │Snap  │                  │ │
│     │ │      │ │      │ │      │ │      │                  │ │
│     │ └──────┘ └──────┘ └──────┘ └──────┘                  │ │
│     └────────────────────────────────────────────────────────┘ │
│         │                                                       │
│         ▼                                                       │
│  4. OAuth authorization (Meta example)                          │
│     ┌────────────────────────────────────────────────────────┐ │
│     │                                                        │ │
│     │           [Meta Login Page]                            │ │
│     │                                                        │ │
│     │  Stratum AI wants to access your                       │ │
│     │  Facebook advertising account.                         │ │
│     │                                                        │ │
│     │  This will allow Stratum AI to:                        │ │
│     │  • Manage your custom audiences                        │ │
│     │  • Upload customer lists                               │ │
│     │                                                        │ │
│     │  [Cancel] [Continue]                                   │ │
│     │                                                        │ │
│     └────────────────────────────────────────────────────────┘ │
│         │                                                       │
│         ▼                                                       │
│  5. Select ad accounts                                          │
│     ┌────────────────────────────────────────────────────────┐ │
│     │ Select Ad Accounts                                     │ │
│     │ ──────────────────────────────────────────────────────│ │
│     │                                                        │ │
│     │ [✓] act_123456789 - Main Ad Account                    │ │
│     │ [✓] act_987654321 - Secondary Account                  │ │
│     │ [ ] act_111222333 - Test Account                       │ │
│     │                                                        │ │
│     │ [Connect Selected]                                     │ │
│     └────────────────────────────────────────────────────────┘ │
│         │                                                       │
│         ▼                                                       │
│  6. View connected platforms                                    │
│     ┌────────────────────────────────────────────────────────┐ │
│     │ Connected Platforms                                    │ │
│     │ ──────────────────────────────────────────────────────│ │
│     │                                                        │ │
│     │ Meta                                        Connected  │ │
│     │ • act_123456789 - Main Ad Account          ✓           │ │
│     │ • act_987654321 - Secondary Account        ✓           │ │
│     │ [Disconnect] [Refresh]                                 │ │
│     │                                                        │ │
│     │ Google                                  Not Connected  │ │
│     │ [Connect]                                              │ │
│     │                                                        │ │
│     │ TikTok                                  Not Connected  │ │
│     │ [Connect]                                              │ │
│     └────────────────────────────────────────────────────────┘ │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## User Permissions

| Action | Required Permission |
|--------|---------------------|
| View platform audiences | `audience_sync:read` |
| Create platform audience | `audience_sync:create` |
| Trigger manual sync | `audience_sync:sync` |
| Delete platform audience | `audience_sync:delete` |
| Connect platform | `audience_sync:admin` |
| Export audience | `audience_sync:export` |
| View sync history | `audience_sync:read` |

---

## Related Flows

- [CDP Segment Builder](../02-cdp/user-flows.md#flow-3-segment-builder)
- [Campaign Targeting](../06-campaigns/user-flows.md)
