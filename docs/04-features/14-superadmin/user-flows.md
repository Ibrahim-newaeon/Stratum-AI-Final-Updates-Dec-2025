# Superadmin User Flows

## Overview

Step-by-step user journeys for platform administration and tenant management.

---

## Flow 1: Admin Login

**Actor**: Platform Admin
**Goal**: Access superadmin dashboard

### Steps

1. Admin navigates to admin portal
2. Email/password form displays
3. Admin enters credentials
4. MFA challenge presented
5. Admin enters TOTP code
6. Session created with IP logging
7. Dashboard loads

### Login Screen

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                    STRATUM ADMIN                            │
│                                                             │
│  Email                                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ admin@stratum.ai                                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Password                                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ••••••••••••                                        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [Sign In]                                                  │
│                                                             │
│  ⚠️ This system is monitored. All actions are logged.      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Flow 2: View Tenant List

**Actor**: Platform Admin
**Goal**: Browse and search tenants

### Steps

1. Admin navigates to Tenants section
2. Tenant list loads with pagination
3. Admin uses search/filters
4. Results update in real-time
5. Admin clicks tenant for details

### Tenant List View

```
┌─────────────────────────────────────────────────────────────┐
│  Tenants                              [+ Create Tenant]     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Search: [________________] Status: [All ▼] Plan: [All ▼]  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Name          Status    Plan       Users   Created  │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ Acme Corp     ● Active  Growth     12      Jan 15   │   │
│  │ TechStart     ● Active  Starter    3       Jan 10   │   │
│  │ BigRetail     ● Active  Enterprise 45      Dec 20   │   │
│  │ OldCo         ○ Suspended Growth   8       Nov 05   │   │
│  │ NewBiz        ◐ Pending  Trial     1       Jan 18   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Showing 1-5 of 128 tenants    [◀ Prev] [1] [2] [Next ▶]   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Flow 3: Create New Tenant

**Actor**: Superadmin
**Goal**: Provision new tenant account

### Steps

1. Admin clicks "Create Tenant"
2. Tenant form modal appears
3. Admin enters tenant details
4. Admin selects subscription plan
5. Admin sets initial limits
6. Tenant created with welcome email
7. Admin can impersonate to configure

### Create Tenant Form

```
┌─────────────────────────────────────────────────────────────┐
│  Create New Tenant                                    [×]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Company Name *                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Admin Email *                                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Subscription Plan                                          │
│  ○ Starter ($99/mo)                                         │
│  ● Growth ($299/mo)                                         │
│  ○ Enterprise (Custom)                                      │
│                                                             │
│  Initial Status                                             │
│  ● Active (Skip trial)                                      │
│  ○ Trial (14 days)                                          │
│                                                             │
│  Industry                     Company Size                  │
│  [E-commerce ▼]              [11-50 ▼]                     │
│                                                             │
│  ☑ Send welcome email                                       │
│  ☐ Skip onboarding wizard                                   │
│                                                             │
│  [Cancel]                              [Create Tenant]      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Flow 4: Suspend Tenant

**Actor**: Superadmin
**Goal**: Suspend tenant for policy violation or non-payment

### Steps

1. Admin opens tenant details
2. Admin clicks "Suspend Tenant"
3. Confirmation modal with reason required
4. Admin enters suspension reason
5. Tenant suspended
6. Automations disabled
7. Notification sent to tenant admins
8. Audit log created

### Suspension Confirmation

```
┌─────────────────────────────────────────────────────────────┐
│  Suspend Tenant: Acme Corp                            [×]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ⚠️ Warning: This will immediately:                        │
│                                                             │
│  • Disable all active automations                          │
│  • Block user logins                                        │
│  • Pause all scheduled tasks                               │
│  • Send notification to 3 admin users                      │
│                                                             │
│  Suspension Reason *                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Payment failed after 3 retry attempts. Account     │   │
│  │ past due for 15 days.                              │   │
│  │                                                     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Notify tenant admins: [Yes ▼]                             │
│                                                             │
│  [Cancel]                              [Confirm Suspend]    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Flow 5: Impersonate User

**Actor**: Support Admin
**Goal**: Debug issue from user's perspective

### Steps

1. Admin searches for user
2. Admin clicks "Impersonate"
3. Reason form displays
4. Admin enters support ticket reference
5. Impersonation session starts
6. Admin sees user's dashboard
7. Yellow banner indicates impersonation
8. Admin can end session anytime

### Impersonation Banner

```
┌─────────────────────────────────────────────────────────────┐
│ ⚠️ IMPERSONATION ACTIVE                                    │
│ Viewing as: john@acme.com | Tenant: Acme Corp              │
│ Session expires: 45 minutes | [End Impersonation]          │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  Dashboard                                                  │
│  (User's actual view - all actions logged)                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Flow 6: View System Health

**Actor**: Any Admin
**Goal**: Monitor platform health and metrics

### Steps

1. Admin navigates to System Health
2. Overall status displayed
3. Component health shown
4. Admin can drill into details
5. Recent incidents listed
6. Admin can trigger manual checks

### System Health Dashboard

```
┌─────────────────────────────────────────────────────────────┐
│  System Health                              Last: 30s ago  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Overall Status: ● HEALTHY                                  │
│                                                             │
│  Components                                                 │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Database      ● Healthy    Connections: 45/100      │   │
│  │ Redis         ● Healthy    Memory: 2.1GB/8GB        │   │
│  │ Celery        ● Healthy    Workers: 8/8 active      │   │
│  │ API           ● Healthy    Latency: 45ms avg        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Integrations                                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Meta          ● Healthy    Rate: 850/1000 req/min   │   │
│  │ Google        ● Healthy    Rate: 420/600 req/min    │   │
│  │ TikTok        ◐ Degraded   Rate limit approaching    │   │
│  │ Snapchat      ● Healthy    Rate: 100/500 req/min    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Metrics (Last 24h)                                        │
│  • Active tenants: 128                                     │
│  • Requests: 1.2M                                          │
│  • Error rate: 0.02%                                       │
│  • Avg response: 89ms                                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Flow 7: Manage Feature Flags

**Actor**: Superadmin
**Goal**: Enable/disable features for tenants

### Steps

1. Admin navigates to Feature Flags
2. Flag list displays
3. Admin selects flag to modify
4. Admin adjusts settings
5. Changes saved and applied
6. Affected tenants notified

### Feature Flag Editor

```
┌─────────────────────────────────────────────────────────────┐
│  Feature Flags                             [+ New Flag]     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Search: [________________]                                 │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Flag                  Default   Rollout   Override  │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ whatsapp_enabled      OFF       --        5 tenants │   │
│  │ new_dashboard_v2      OFF       25%       2 tenants │   │
│  │ advanced_analytics    ON        100%      --        │   │
│  │ beta_autopilot        OFF       10%       12 tenants│   │
│  │ ai_recommendations    OFF       5%        --        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Selected: new_dashboard_v2                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Description: New dashboard redesign with charts     │   │
│  │                                                     │   │
│  │ Default: [OFF ▼]  Rollout: [25 ]%                  │   │
│  │                                                     │   │
│  │ Tenant Overrides:                                   │   │
│  │ • Acme Corp: ON                                     │   │
│  │ • TechStart: ON                                     │   │
│  │ [+ Add Override]                                    │   │
│  │                                                     │   │
│  │ [Cancel] [Save Changes]                             │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Flow 8: View Audit Logs

**Actor**: Audit Admin
**Goal**: Review admin activity

### Steps

1. Admin navigates to Audit Logs
2. Logs display with filters
3. Admin filters by action/user/date
4. Admin clicks entry for details
5. Full context shown in modal
6. Admin can export logs

### Audit Log View

```
┌─────────────────────────────────────────────────────────────┐
│  Audit Logs                                    [Export]     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Date: [Last 7 days ▼] Action: [All ▼] Admin: [All ▼]     │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Time            Admin         Action         Target │   │
│  ├─────────────────────────────────────────────────────┤   │
│  │ Jan 18 14:32    sarah@...     user.impersonate   →  │   │
│  │ Jan 18 14:15    sarah@...     tenant.update      →  │   │
│  │ Jan 18 13:45    admin@...     feature_flag.toggle→  │   │
│  │ Jan 18 12:00    admin@...     tenant.suspend     →  │   │
│  │ Jan 18 11:30    audit@...     login              →  │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Showing 1-5 of 1,247 entries                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Audit Detail Modal

```
┌─────────────────────────────────────────────────────────────┐
│  Audit Log Detail                                     [×]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Action: tenant.suspend                                     │
│  Timestamp: 2024-01-18T12:00:00Z                           │
│  Admin: admin@stratum.ai                                    │
│  IP Address: 192.168.1.100                                 │
│                                                             │
│  Target                                                     │
│  • Resource Type: tenant                                    │
│  • Resource ID: 45                                          │
│  • Tenant: OldCo Inc                                        │
│                                                             │
│  Reason                                                     │
│  "Payment failed after 3 retry attempts. Account           │
│   past due for 15 days."                                   │
│                                                             │
│  Changes                                                    │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Field       Before          After                   │   │
│  │ status      active          suspended               │   │
│  │ suspended_at null           2024-01-18T12:00:00Z   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│                                              [Close]        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Flow 9: Platform Analytics

**Actor**: Superadmin
**Goal**: View cross-tenant platform metrics

### Steps

1. Admin navigates to Analytics
2. Platform overview displays
3. Admin selects date range
4. Charts update with data
5. Admin can drill into segments

### Platform Analytics View

```
┌─────────────────────────────────────────────────────────────┐
│  Platform Analytics                    [Last 30 days ▼]    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ Total Tenants│ │ Active (7d)  │ │ New (30d)    │        │
│  │     128      │ │     112      │ │     18       │        │
│  │   +5 MTD     │ │   87% rate   │ │  +20% MoM    │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
│                                                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐        │
│  │ MRR          │ │ ARR          │ │ ARPU         │        │
│  │   $38,500    │ │   $462,000   │ │    $301      │        │
│  │   +8% MoM    │ │   +25% YoY   │ │   +5% MoM    │        │
│  └──────────────┘ └──────────────┘ └──────────────┘        │
│                                                             │
│  Tenants by Plan                     Tenants by Health     │
│  ┌────────────────────┐             ┌────────────────────┐ │
│  │ ████████░░ Enterprise 15%       │ │ ██████████░ Healthy 85%  │ │
│  │ ████████████████ Growth 55%     │ │ ████░░░░░░ Warning 10%  │ │
│  │ ████████░░░░ Starter 25%        │ │ ██░░░░░░░░ Critical 5%  │ │
│  │ ████░░░░░░ Trial 5%             │ └────────────────────┘ │
│  └────────────────────┘                                    │
│                                                             │
│  Churn Rate: 2.1% (Target: <3%)                            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Flow 10: Reactivate Tenant

**Actor**: Superadmin
**Goal**: Restore suspended tenant

### Steps

1. Admin opens suspended tenant
2. Admin clicks "Reactivate"
3. Confirmation modal appears
4. Admin confirms reactivation
5. Tenant status restored
6. Automations remain paused
7. Tenant admin notified
8. Admin must manually re-enable automations

### Reactivation Flow

```
┌─────────────────────────────────────────────────────────────┐
│  Reactivate Tenant: OldCo Inc                         [×]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Tenant was suspended on: Jan 18, 2024                     │
│  Reason: Payment failed after 3 retry attempts             │
│                                                             │
│  Reactivation will:                                        │
│  ✓ Restore user login access                               │
│  ✓ Change status to Active                                 │
│  ⚠️ Automations will remain paused (must enable manually)   │
│                                                             │
│  Outstanding Issues:                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ⚠️ Past due invoice: $299.00 (INV-2024-0045)        │   │
│  │   [Mark Paid] [Waive]                               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Notes                                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Payment received via bank transfer.                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [Cancel]                              [Reactivate]         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Related Documentation

- [Specification](./spec.md) - Data models and architecture
- [API Contracts](./api-contracts.md) - Admin API endpoints
- [Edge Cases](./edge-cases.md) - Error handling
