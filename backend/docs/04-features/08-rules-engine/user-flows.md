# Rules Engine User Flows

## Overview

Step-by-step user journeys for creating, managing, and testing automation rules.

---

## Flow 1: Create a New Rule

**Actor**: User

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                    CREATE AUTOMATION RULE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Navigate to Automation → Rules                              │
│                                                                 │
│  2. Click "Create Rule"                                         │
│                                                                 │
│  3. Enter basic info:                                           │
│     ┌──────────────────────────────────────────────────────┐   │
│     │ NEW AUTOMATION RULE                                  │   │
│     │                                                      │   │
│     │ Name: [Pause Low ROAS Campaigns______]               │   │
│     │                                                      │   │
│     │ Description:                                         │   │
│     │ [Auto-pause campaigns with ROAS below 1.0 for 7 days]│   │
│     └──────────────────────────────────────────────────────┘   │
│                                                                 │
│  4. Define condition (IF):                                      │
│     ┌──────────────────────────────────────────────────────┐   │
│     │ CONDITION                                            │   │
│     │                                                      │   │
│     │ IF [ROAS ▼] [is less than ▼] [1.0____]               │   │
│     │                                                      │   │
│     │ Duration: [24___] hours                              │   │
│     │ (How long condition must be true before triggering)  │   │
│     └──────────────────────────────────────────────────────┘   │
│                                                                 │
│  5. Define action (THEN):                                       │
│     ┌──────────────────────────────────────────────────────┐   │
│     │ ACTION                                               │   │
│     │                                                      │   │
│     │ THEN [Pause Campaign ▼]                              │   │
│     │                                                      │   │
│     │ Configuration: (none required for pause)             │   │
│     └──────────────────────────────────────────────────────┘   │
│                                                                 │
│  6. Define scope (FOR):                                         │
│     ┌──────────────────────────────────────────────────────┐   │
│     │ SCOPE                                                │   │
│     │                                                      │   │
│     │ Apply to:                                            │   │
│     │ ○ All campaigns                                      │   │
│     │ ● Specific platforms: [☑ Meta] [☑ Google] [☐ TikTok]│   │
│     │ ○ Specific campaigns: [Select campaigns ▼]          │   │
│     └──────────────────────────────────────────────────────┘   │
│                                                                 │
│  7. Set frequency:                                              │
│     ┌──────────────────────────────────────────────────────┐   │
│     │ FREQUENCY CONTROL                                    │   │
│     │                                                      │   │
│     │ Cooldown: [24___] hours between triggers             │   │
│     │ (Prevents rule from triggering too frequently)       │   │
│     └──────────────────────────────────────────────────────┘   │
│                                                                 │
│  8. Save as draft:                                              │
│     └─► POST /rules                                            │
│     └─► Status: "draft"                                        │
│                                                                 │
│  9. Rule created:                                               │
│     ┌──────────────────────────────────────────┐               │
│     │ ✓ Rule "Pause Low ROAS Campaigns" created│               │
│     │ Status: Draft                            │               │
│     │ [Test Rule] [Activate]                   │               │
│     └──────────────────────────────────────────┘               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Flow 2: Test Rule (Dry-Run)

**Actor**: User

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                      TEST RULE (DRY-RUN)                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Navigate to rule detail page                                │
│                                                                 │
│  2. Click "Test Rule"                                           │
│                                                                 │
│  3. System runs dry-run evaluation:                             │
│     └─► POST /rules/{id}/test                                  │
│                                                                 │
│  4. View results:                                               │
│     ┌──────────────────────────────────────────────────────┐   │
│     │ TEST RESULTS                                         │   │
│     │                                                      │   │
│     │ Status: Completed                                    │   │
│     │ Campaigns Evaluated: 15                              │   │
│     │ Campaigns Matched: 3                                 │   │
│     │                                                      │   │
│     │ MATCHED CAMPAIGNS (would be affected)                │   │
│     │ ────────────────────────────────────────────────────│   │
│     │ Campaign              Platform   ROAS    Action      │   │
│     │ ────────────────────────────────────────────────────│   │
│     │ Summer Sale 2024      Meta       0.72    Pause      │   │
│     │ Q1 Promo              Google     0.45    Pause      │   │
│     │ Brand Awareness       Meta       0.88    Pause      │   │
│     │                                                      │   │
│     │ NON-MATCHED CAMPAIGNS (12)                          │   │
│     │ [Show details ▼]                                    │   │
│     └──────────────────────────────────────────────────────┘   │
│                                                                 │
│  5. Review and decide:                                          │
│     • If results look correct → Activate rule                   │
│     • If unexpected → Modify rule conditions                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Flow 3: Activate Rule

**Actor**: User

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                       ACTIVATE RULE                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. From rule detail page, click "Activate"                     │
│                                                                 │
│  2. Confirmation dialog:                                        │
│     ┌──────────────────────────────────────────┐               │
│     │ ACTIVATE RULE?                           │               │
│     │                                          │               │
│     │ Rule: Pause Low ROAS Campaigns           │               │
│     │                                          │               │
│     │ This rule will:                          │               │
│     │ • Check campaigns every 15 minutes       │               │
│     │ • Auto-pause campaigns with ROAS < 1.0   │               │
│     │ • Apply to: Meta, Google campaigns       │               │
│     │                                          │               │
│     │ [Cancel] [Activate]                      │               │
│     └──────────────────────────────────────────┘               │
│                                                                 │
│  3. Confirm:                                                    │
│     └─► POST /rules/{id}/activate                              │
│                                                                 │
│  4. Rule activated:                                             │
│     ┌──────────────────────────────────────────┐               │
│     │ ✓ Rule activated                         │               │
│     │ Status: Active                           │               │
│     │ Next evaluation: in 15 minutes           │               │
│     └──────────────────────────────────────────┘               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Flow 4: View Rule Executions

**Actor**: User

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                   VIEW RULE EXECUTIONS                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Navigate to rule detail page                                │
│                                                                 │
│  2. Click "Execution History" tab                               │
│                                                                 │
│  3. View execution log:                                         │
│     ┌──────────────────────────────────────────────────────┐   │
│     │ EXECUTION HISTORY                                    │   │
│     │                                                      │   │
│     │ Rule: Pause Low ROAS Campaigns                       │   │
│     │ Trigger Count: 12                                    │   │
│     │ Last Triggered: Jan 15, 2024 14:30                   │   │
│     │                                                      │   │
│     │ ────────────────────────────────────────────────────│   │
│     │ Date           Campaign           Result    Action   │   │
│     │ ────────────────────────────────────────────────────│   │
│     │ Jan 15 14:30   Summer Sale 2024   ✓ Match  Paused   │   │
│     │   └─ ROAS 0.72 < 1.0                                │   │
│     │                                                      │   │
│     │ Jan 15 14:30   Q1 Promo           ✓ Match  Paused   │   │
│     │   └─ ROAS 0.45 < 1.0                                │   │
│     │                                                      │   │
│     │ Jan 15 14:30   Winter Campaign    ✗ No match        │   │
│     │   └─ ROAS 2.3 ≥ 1.0                                 │   │
│     │                                                      │   │
│     │ Jan 15 14:15   (15 campaigns)     Cooldown active   │   │
│     │   └─ Skipped - 23h 45m remaining                    │   │
│     └──────────────────────────────────────────────────────┘   │
│                                                                 │
│  4. Filter options:                                             │
│     • Date range                                                │
│     • Campaign                                                  │
│     • Result (matched/not matched)                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Flow 5: Create Budget Adjustment Rule

**Actor**: User

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│              CREATE BUDGET ADJUSTMENT RULE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Navigate to Automation → Rules → Create                     │
│                                                                 │
│  2. Configure rule:                                             │
│     ┌──────────────────────────────────────────────────────┐   │
│     │ CREATE RULE                                          │   │
│     │                                                      │   │
│     │ Name: [Scale High Performers___________]             │   │
│     │                                                      │   │
│     │ CONDITION:                                           │   │
│     │ IF [ROAS ▼] [is greater than ▼] [3.0___]             │   │
│     │ Duration: [48__] hours                               │   │
│     │                                                      │   │
│     │ ACTION:                                              │   │
│     │ THEN [Adjust Budget ▼]                               │   │
│     │                                                      │   │
│     │ Budget Adjustment:                                   │   │
│     │ [Increase ▼] by [20___]%                             │   │
│     │                                                      │   │
│     │ SCOPE:                                               │   │
│     │ Apply to: ● All campaigns                            │   │
│     │                                                      │   │
│     │ FREQUENCY:                                           │   │
│     │ Cooldown: [72__] hours                               │   │
│     └──────────────────────────────────────────────────────┘   │
│                                                                 │
│  3. Save and test                                               │
│                                                                 │
│  4. Activate when ready                                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Flow 6: Create Alert Rule with Slack

**Actor**: User

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│               CREATE SLACK ALERT RULE                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Navigate to Automation → Rules → Create                     │
│                                                                 │
│  2. Configure rule:                                             │
│     ┌──────────────────────────────────────────────────────┐   │
│     │ CREATE RULE                                          │   │
│     │                                                      │   │
│     │ Name: [High CPA Alert__________________]             │   │
│     │                                                      │   │
│     │ CONDITION:                                           │   │
│     │ IF [CPA ▼] [is greater than ▼] [50.00__]             │   │
│     │ Duration: [24__] hours                               │   │
│     │                                                      │   │
│     │ ACTION:                                              │   │
│     │ THEN [Notify Slack ▼]                                │   │
│     │                                                      │   │
│     │ Slack Configuration:                                 │   │
│     │ Webhook URL: [https://hooks.slack.com/____]          │   │
│     │ Channel (optional): [#ad-alerts_________]            │   │
│     │                                                      │   │
│     │ Message will include:                                │   │
│     │ • Campaign name                                      │   │
│     │ • Current CPA                                        │   │
│     │ • Threshold value                                    │   │
│     │ • Trigger time                                       │   │
│     └──────────────────────────────────────────────────────┘   │
│                                                                 │
│  3. Save, test, and activate                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Flow 7: Create WhatsApp Notification Rule

**Actor**: User

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│            CREATE WHATSAPP NOTIFICATION RULE                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Navigate to Automation → Rules → Create                     │
│                                                                 │
│  2. Configure rule:                                             │
│     ┌──────────────────────────────────────────────────────┐   │
│     │ CREATE RULE                                          │   │
│     │                                                      │   │
│     │ Name: [Critical ROAS Alert_____________]             │   │
│     │                                                      │   │
│     │ CONDITION:                                           │   │
│     │ IF [ROAS ▼] [is less than ▼] [0.5____]               │   │
│     │ Duration: [12__] hours                               │   │
│     │                                                      │   │
│     │ ACTION:                                              │   │
│     │ THEN [Notify WhatsApp ▼]                             │   │
│     │                                                      │   │
│     │ WhatsApp Configuration:                              │   │
│     │ Contacts: [Select opted-in contacts ▼]               │   │
│     │   ☑ John Smith (+1 555-0100)                        │   │
│     │   ☑ Jane Doe (+1 555-0200)                          │   │
│     │   ☐ Bob Wilson (+1 555-0300) - Not opted in         │   │
│     │                                                      │   │
│     │ Template: [rule_alert ▼]                             │   │
│     │                                                      │   │
│     │ Note: Only opted-in contacts will receive messages   │   │
│     └──────────────────────────────────────────────────────┘   │
│                                                                 │
│  3. Save, test, and activate                                    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Flow 8: Pause and Resume Rule

**Actor**: User

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                   PAUSE AND RESUME RULE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  PAUSE RULE:                                                    │
│  ───────────                                                    │
│  1. Navigate to rule detail page                                │
│                                                                 │
│  2. Click "Pause"                                               │
│     └─► POST /rules/{id}/pause                                 │
│                                                                 │
│  3. Rule paused:                                                │
│     ┌──────────────────────────────────────────┐               │
│     │ ⏸ Rule paused                            │               │
│     │ Will not evaluate until reactivated      │               │
│     └──────────────────────────────────────────┘               │
│                                                                 │
│  RESUME RULE:                                                   │
│  ────────────                                                   │
│  4. Click "Activate"                                            │
│     └─► POST /rules/{id}/activate                              │
│                                                                 │
│  5. Rule reactivated:                                           │
│     ┌──────────────────────────────────────────┐               │
│     │ ✓ Rule reactivated                       │               │
│     │ Cooldown reset - will evaluate next cycle│               │
│     └──────────────────────────────────────────┘               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Flow 9: Delete Rule

**Actor**: User

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                        DELETE RULE                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Navigate to rule detail page                                │
│                                                                 │
│  2. Click "Delete"                                              │
│                                                                 │
│  3. Confirmation dialog:                                        │
│     ┌──────────────────────────────────────────┐               │
│     │ DELETE RULE?                             │               │
│     │                                          │               │
│     │ Rule: Pause Low ROAS Campaigns           │               │
│     │ Trigger Count: 12                        │               │
│     │                                          │               │
│     │ This action cannot be undone.            │               │
│     │ Execution history will be preserved.     │               │
│     │                                          │               │
│     │ [Cancel] [Delete]                        │               │
│     └──────────────────────────────────────────┘               │
│                                                                 │
│  4. Confirm:                                                    │
│     └─► DELETE /rules/{id}                                     │
│                                                                 │
│  5. Rule deleted (soft delete):                                 │
│     ┌──────────────────────────────────────────┐               │
│     │ ✓ Rule deleted                           │               │
│     │ Execution history retained for audit     │               │
│     └──────────────────────────────────────────┘               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Related Documentation

- [Specification](./spec.md) - Data models and architecture
- [API Contracts](./api-contracts.md) - API endpoints and schemas
- [Edge Cases](./edge-cases.md) - Error handling and edge cases
