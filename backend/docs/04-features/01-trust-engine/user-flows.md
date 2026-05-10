# Trust Engine User Flows

## Overview

This document describes the key user journeys and system flows involving the Trust Engine. Each flow includes diagrams, state transitions, and expected outcomes.

---

## Flow 1: Signal Health Dashboard View

### Description
User views the current signal health status and component breakdown on the dashboard.

### Actors
- **User**: Advertiser or account manager
- **System**: Trust Engine

### Preconditions
- User is authenticated
- User has access to the tenant
- `signal_health` feature is enabled

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                    SIGNAL HEALTH VIEW FLOW                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. User navigates to Dashboard                                 │
│         │                                                       │
│         ▼                                                       │
│  2. Frontend requests GET /signal-health                        │
│         │                                                       │
│         ▼                                                       │
│  3. Backend calculates signal health                            │
│     ┌─────────────────────────────────────────┐                │
│     │ - Fetch EMQ scores from platforms       │                │
│     │ - Check data freshness timestamps       │                │
│     │ - Calculate attribution variance        │                │
│     │ - Run anomaly detection                 │                │
│     │ - Compute weighted composite score      │                │
│     └─────────────────────────────────────────┘                │
│         │                                                       │
│         ▼                                                       │
│  4. Return signal health response                               │
│         │                                                       │
│         ▼                                                       │
│  5. Frontend displays:                                          │
│     ┌─────────────────────────────────────────┐                │
│     │ - Overall health score (0-100)          │                │
│     │ - Status badge (healthy/degraded/crit)  │                │
│     │ - Component breakdown cards             │                │
│     │ - Platform-specific details             │                │
│     │ - Active banners/alerts                 │                │
│     └─────────────────────────────────────────┘                │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Response States

| Status | Badge Color | User Message |
|--------|-------------|--------------|
| `healthy` | Green | "Signal health is excellent" |
| `risk` | Yellow | "Signal health needs attention" |
| `degraded` | Orange | "Signal health is degraded - automation limited" |
| `critical` | Red | "Signal health critical - automation blocked" |

---

## Flow 2: Trust Gate Evaluation

### Description
System evaluates a proposed automation action through the Trust Gate before execution.

### Actors
- **Autopilot Engine**: Proposes actions based on rules
- **Trust Gate**: Evaluates and decides
- **Action Executor**: Executes approved actions

### Flow Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                   TRUST GATE EVALUATION FLOW                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Autopilot proposes action                                   │
│     ┌────────────────────────────┐                             │
│     │ Action: increase_budget    │                             │
│     │ Entity: campaign/12345     │                             │
│     │ Amount: +20%               │                             │
│     └────────────────────────────┘                             │
│         │                                                       │
│         ▼                                                       │
│  2. Get current signal health                                   │
│     ┌────────────────────────────┐                             │
│     │ Score: 75.2                │                             │
│     │ Status: healthy            │                             │
│     └────────────────────────────┘                             │
│         │                                                       │
│         ▼                                                       │
│  3. Determine action threshold                                  │
│     "increase_budget" → high_risk → threshold = 80             │
│         │                                                       │
│         ▼                                                       │
│  4. Compare score vs threshold                                  │
│     75.2 < 80 → DOES NOT MEET                                  │
│         │                                                       │
│         ▼                                                       │
│  5. Gate Decision: HOLD                                         │
│     ┌────────────────────────────┐                             │
│     │ Decision: hold             │                             │
│     │ Reason: Score 75.2 below   │                             │
│     │         threshold 80.0     │                             │
│     │ Action: queued for review  │                             │
│     └────────────────────────────┘                             │
│         │                                                       │
│         ▼                                                       │
│  6. Log to audit trail                                          │
│  7. Send alert notification                                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Decision Matrix

| Action Type | Risk Level | Required Score | Score 85 | Score 72 | Score 45 |
|-------------|------------|----------------|----------|----------|----------|
| increase_budget | High | 80 | PASS | HOLD | BLOCK |
| update_budget | Standard | 70 | PASS | PASS | BLOCK |
| reduce_budget | Conservative | 60 | PASS | PASS | HOLD |
| pause_all | Always Allowed | Any | PASS | PASS | PASS |

---

## Flow 3: Autopilot Mode Transition

### Description
System transitions between autopilot modes based on signal health changes.

### State Diagram

```
                    ┌─────────────────────────────────────────┐
                    │         AUTOPILOT MODE STATES           │
                    ├─────────────────────────────────────────┤
                    │                                         │
                    │   ┌──────────────────────────────────┐  │
                    │   │                                  │  │
    score >= 80 ───▶│   │           NORMAL                 │  │
                    │   │   Full autopilot enabled         │  │
                    │   │   All actions available          │  │
                    │   │                                  │  │
                    │   └───────────────┬──────────────────┘  │
                    │                   │                     │
                    │           score < 70                    │
                    │                   │                     │
                    │                   ▼                     │
                    │   ┌──────────────────────────────────┐  │
                    │   │                                  │  │
    score >= 70 ───▶│   │           LIMITED                │  │
                    │   │   Conservative actions only      │  │
                    │   │   High-risk actions blocked      │  │
                    │   │                                  │  │
                    │   └───────────────┬──────────────────┘  │
                    │                   │                     │
                    │           score < 60                    │
                    │                   │                     │
                    │                   ▼                     │
                    │   ┌──────────────────────────────────┐  │
                    │   │                                  │  │
    score >= 60 ───▶│   │         CUTS_ONLY               │  │
                    │   │   Only pause/reduce allowed     │  │
                    │   │   No increases permitted         │  │
                    │   │                                  │  │
                    │   └───────────────┬──────────────────┘  │
                    │                   │                     │
                    │           score < 40                    │
                    │                   │                     │
                    │                   ▼                     │
                    │   ┌──────────────────────────────────┐  │
                    │   │                                  │  │
                    │   │           FROZEN                 │  │
                    │   │   All automation disabled        │  │
                    │   │   Manual intervention required   │  │
                    │   │                                  │  │
                    │   └──────────────────────────────────┘  │
                    │                                         │
                    └─────────────────────────────────────────┘
```

### Transition Notifications

| Transition | Notification Type | Recipients |
|------------|-------------------|------------|
| Normal → Limited | Warning | Account managers |
| Limited → Cuts Only | Urgent | Account managers + Admins |
| Any → Frozen | Critical | All stakeholders |
| Any → Normal | Info | Account managers |

---

## Flow 4: Manual Override

### Description
User manually overrides a Trust Gate HOLD decision to execute an action.

### Preconditions
- Action is in HOLD status
- User has `automation:override` permission
- Signal health is not CRITICAL

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                    MANUAL OVERRIDE FLOW                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. User views pending actions                                  │
│     ┌────────────────────────────────────────────┐             │
│     │ Action: Increase Campaign A budget +25%    │             │
│     │ Status: HOLD                               │             │
│     │ Reason: Signal health 68 < threshold 80   │             │
│     │ [Approve] [Reject] [View Details]         │             │
│     └────────────────────────────────────────────┘             │
│         │                                                       │
│         ▼                                                       │
│  2. User clicks [Approve]                                       │
│         │                                                       │
│         ▼                                                       │
│  3. System displays confirmation                                │
│     ┌────────────────────────────────────────────┐             │
│     │ ⚠️ Warning: Signal health is below target  │             │
│     │                                            │             │
│     │ You are about to override the Trust Gate   │             │
│     │ decision. This action will:                │             │
│     │                                            │             │
│     │ • Increase Campaign A budget by 25%        │             │
│     │ • Execute despite signal health of 68%     │             │
│     │                                            │             │
│     │ Reason for override: [____________]        │             │
│     │                                            │             │
│     │ [Cancel] [Confirm Override]                │             │
│     └────────────────────────────────────────────┘             │
│         │                                                       │
│         ▼                                                       │
│  4. User provides reason and confirms                           │
│         │                                                       │
│         ▼                                                       │
│  5. System logs override with:                                  │
│     - User ID                                                   │
│     - Reason provided                                           │
│     - Signal health at time of override                         │
│     - Timestamp                                                 │
│         │                                                       │
│         ▼                                                       │
│  6. Action executes                                             │
│         │                                                       │
│         ▼                                                       │
│  7. Result logged and user notified                             │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Override Restrictions

| Condition | Override Allowed |
|-----------|------------------|
| Signal health >= 40 | Yes |
| Signal health < 40 (Critical) | No |
| High-risk action, score < 60 | Requires admin approval |
| Emergency stop action | N/A - always allowed |

---

## Flow 5: Signal Health History Review

### Description
User reviews historical signal health trends for analysis and reporting.

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                 SIGNAL HEALTH HISTORY FLOW                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. User navigates to Signal Health → History                   │
│         │                                                       │
│         ▼                                                       │
│  2. User selects date range (7/14/30 days)                      │
│         │                                                       │
│         ▼                                                       │
│  3. Frontend requests GET /signal-health/history?days=14        │
│         │                                                       │
│         ▼                                                       │
│  4. Backend returns historical data                             │
│         │                                                       │
│         ▼                                                       │
│  5. Frontend displays:                                          │
│                                                                 │
│     ┌─────────────────────────────────────────────────────┐    │
│     │  Signal Health Trend                                │    │
│     │                                                     │    │
│     │  100 ─┬─────────────────────────────────────────    │    │
│     │   90 ─┤           ••                                │    │
│     │   80 ─┤       ••••  •••                             │    │
│     │   70 ─┼─────────────────•••••────────────────────   │    │
│     │   60 ─┤                      ••                     │    │
│     │   50 ─┤                        •••                  │    │
│     │   40 ─┤                                             │    │
│     │       └─────────────────────────────────────────    │    │
│     │        Jan 1  Jan 4  Jan 7  Jan 10  Jan 14          │    │
│     │                                                     │    │
│     │  Summary:                                           │    │
│     │  • Average Score: 74.2                              │    │
│     │  • Days at Risk: 3                                  │    │
│     │  • Automation Blocked: 1 day                        │    │
│     │  • Primary Issues: Freshness (4), EMQ (2)           │    │
│     └─────────────────────────────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Flow 6: Trust Gate Audit Review

### Description
User reviews the audit trail of all Trust Gate decisions.

### Steps

1. Navigate to Trust Gate → Audit Logs
2. Apply filters (date range, decision type, entity type)
3. View paginated list of decisions
4. Click on entry for full details

### Audit Log Entry Detail

```
┌─────────────────────────────────────────────────────────────────┐
│              TRUST GATE AUDIT LOG DETAIL                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Decision ID: 7f3a2b1c-...                                      │
│  Timestamp: 2024-01-15 14:32:18 UTC                            │
│                                                                 │
│  ┌───────────────────────────────────────────────────────────┐ │
│  │ Decision: HOLD                                            │ │
│  └───────────────────────────────────────────────────────────┘ │
│                                                                 │
│  Action Details:                                                │
│  • Type: increase_budget                                        │
│  • Entity: campaign/12345 (Summer Sale Campaign)                │
│  • Platform: Meta                                               │
│  • Parameters: {daily_budget: 150.00}                           │
│                                                                 │
│  Signal Health at Decision:                                     │
│  • Overall Score: 72.4                                          │
│  • Status: healthy                                              │
│  • Components:                                                  │
│    - EMQ: 78.0                                                  │
│    - Freshness: 92.0                                            │
│    - Variance: 61.0                                             │
│    - Anomaly: 85.0                                              │
│                                                                 │
│  Gate Evaluation:                                               │
│  • Threshold Required: 80.0 (high-risk action)                  │
│  • Score: 72.4                                                  │
│  • Reason: "Signal health 72.4 below threshold 80.0 for        │
│             increase_budget - action queued for review"         │
│                                                                 │
│  Recommendations:                                               │
│  • Review signal health issues before proceeding                │
│  • Consider conservative actions only                           │
│  • Check platform EMQ/data quality settings                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## User Permissions

### Required Permissions by Flow

| Flow | Permission Required |
|------|---------------------|
| View Signal Health | `dashboard:read` |
| View History | `signal_health:read` |
| View Audit Logs | `audit:read` |
| Override HOLD | `automation:override` |
| Override (admin) | `automation:admin_override` |
| Configure Thresholds | `settings:write` |

---

## Related Flows

- [Autopilot Rule Execution](../07-autopilot/user-flows.md)
- [Campaign Management](../06-campaigns/user-flows.md)
- [Analytics Dashboard](../09-analytics/user-flows.md)
