# Autopilot Edge Cases

## Overview

This document covers error handling, edge cases, and known limitations for the Autopilot system.

---

## Edge Cases

### 1. Signal Health Below Threshold

**Scenario**: Autopilot action proposed but signal health is degraded.

**Behavior**:
- Signal health score checked before execution
- Score < 70: Action held for review
- Score < 40: Action blocked entirely

**Response**:
```json
{
  "error": {
    "code": "SIGNAL_HEALTH_DEGRADED",
    "message": "Signal health 45% is below healthy threshold (70%)",
    "details": {
      "signal_health_score": 45.0,
      "signal_health_status": "degraded",
      "healthy_threshold": 70.0,
      "decision": "hold"
    }
  }
}
```

**Recovery**: Wait for signal health to improve or manually approve action.

---

### 2. Budget Increase Exceeds Cap

**Scenario**: Proposed budget increase exceeds enforcement cap.

**Behavior**:
- Mode: `advisory` → Warning logged, action proceeds
- Mode: `soft_block` → Confirmation required
- Mode: `hard_block` → Action blocked

**Response (Soft Block)**:
```json
{
  "success": true,
  "data": {
    "allowed": false,
    "mode": "soft_block",
    "violations": [
      {
        "type": "budget_increase_limit",
        "threshold": 30.0,
        "actual": 50.0,
        "message": "Budget increase 50% exceeds limit of 30%"
      }
    ],
    "requires_confirmation": true,
    "confirmation_token": "..."
  }
}
```

---

### 3. Confirmation Token Expired

**Scenario**: User attempts to confirm soft-blocked action after token expires.

**Behavior**:
- Tokens expire after 15 minutes
- User must re-check enforcement to get new token

**Response**:
```json
{
  "error": {
    "code": "INVALID_CONFIRMATION_TOKEN",
    "message": "Confirmation token is invalid or expired",
    "details": {
      "action_required": "re-check_enforcement"
    }
  }
}
```

---

### 4. Action Already Processed

**Scenario**: Approve request for already-applied action.

**Behavior**:
- Check current status before processing
- Return 404 if not in `queued` status

**Response**:
```json
{
  "error": {
    "code": "ACTION_NOT_FOUND",
    "message": "Action not found or already processed",
    "details": {
      "current_status": "applied",
      "applied_at": "2024-01-15T10:30:00Z"
    }
  }
}
```

---

### 5. Platform API Failure During Execution

**Scenario**: Action approved but platform API call fails.

**Behavior**:
- Status changes to `failed`
- Error message captured
- Retry available

**Response**:
```json
{
  "success": true,
  "data": {
    "action": {
      "id": "uuid-...",
      "status": "failed",
      "error": "Meta API Error 2654: Targeting audience is too narrow",
      "applied_at": null
    },
    "retry_available": true
  }
}
```

**Recovery**:
1. Check error message for actionable feedback
2. Modify action if needed
3. Requeue with corrected parameters

---

### 6. Concurrent Rule Evaluation

**Scenario**: Multiple rules trigger conflicting actions for same campaign.

**Behavior**:
- Rules evaluated in priority order
- First action queued, subsequent conflict detected
- Later actions marked as "skipped (conflict)"

**Handling**:
```python
async def evaluate_campaign(campaign_id):
    pending = await get_pending_actions(campaign_id)
    if pending:
        return {
            "status": "skipped",
            "reason": "Pending action exists for this campaign",
            "pending_action_id": pending[0].id
        }
```

---

### 7. Kill Switch Disabled but Action Blocked

**Scenario**: Kill switch OFF, but action still blocked.

**Behavior**:
- Kill switch only disables enforcement checks
- Trust Gate checks (signal health) still active
- Both must pass for execution

**Response**:
```json
{
  "error": {
    "code": "TRUST_GATE_BLOCKED",
    "message": "Action blocked by Trust Gate despite enforcement being disabled",
    "details": {
      "enforcement_enabled": false,
      "signal_health_score": 35.0,
      "signal_health_status": "unhealthy",
      "gate_decision": "blocked"
    }
  }
}
```

---

### 8. Cooldown Period Active

**Scenario**: Budget change requested within cooldown period.

**Behavior**:
- `min_hours_between_changes` enforced
- Action queued but flagged

**Response**:
```json
{
  "success": true,
  "data": {
    "action": { "...": "..." },
    "warnings": [
      "Action queued but cooldown period active. 2 hours remaining before execution."
    ],
    "cooldown_ends_at": "2024-01-15T16:00:00Z"
  }
}
```

---

### 9. Max Daily Changes Exceeded

**Scenario**: Budget change count exceeds daily limit.

**Behavior**:
- `max_budget_changes_per_day` enforced
- Subsequent actions blocked until next day

**Response**:
```json
{
  "error": {
    "code": "FREQUENCY_CAP_EXCEEDED",
    "message": "Maximum budget changes (5) reached for today",
    "details": {
      "changes_today": 5,
      "max_allowed": 5,
      "resets_at": "2024-01-16T00:00:00Z"
    }
  }
}
```

---

### 10. ROAS Below Minimum Threshold

**Scenario**: Campaign ROAS drops below minimum threshold.

**Behavior**:
- `min_roas_threshold` checked for scaling actions
- Budget increases blocked for underperforming campaigns
- Auto-pause suggested if severely below

**Response**:
```json
{
  "error": {
    "code": "ROAS_BELOW_THRESHOLD",
    "message": "Campaign ROAS 0.8x is below minimum threshold 1.0x",
    "details": {
      "current_roas": 0.8,
      "min_threshold": 1.0,
      "lookback_days": 7,
      "suggested_action": "pause_campaign"
    }
  }
}
```

---

### 11. Dry-Run Feature Disabled

**Scenario**: Tenant doesn't have dry-run feature enabled.

**Behavior**:
- Feature flag `action_dry_run` checked
- Returns 403 if disabled

**Response**:
```json
{
  "error": {
    "code": "FEATURE_NOT_ENABLED",
    "message": "Action dry-run feature not enabled for this tenant",
    "details": {
      "feature": "action_dry_run",
      "contact": "support@stratum.ai"
    }
  }
}
```

---

### 12. Orphaned Actions After Tenant Changes

**Scenario**: Actions queued but tenant settings changed.

**Behavior**:
- Actions validated against current settings at execution time
- May fail if thresholds changed

**Handling**:
```python
async def execute_action(action):
    # Re-validate against current settings
    settings = await get_enforcement_settings(action.tenant_id)
    validation = await validate_action(action, settings)

    if not validation.passed:
        action.status = "failed"
        action.error = f"Settings changed: {validation.reason}"
        await db.commit()
```

---

## Known Limitations

### 1. No Real-Time Platform Sync

**Limitation**: Platform changes not reflected in real-time.

**Impact**: Action may succeed in Stratum but fail on platform.

**Workaround**: Always check platform response after execution.

---

### 2. Single Tenant Kill Switch

**Limitation**: Kill switch is tenant-wide, not per-platform.

**Impact**: Disabling enforcement affects all platforms.

**Planned**: Per-platform enforcement toggles.

---

### 3. No Action Scheduling

**Limitation**: Cannot schedule actions for future execution.

**Impact**: Actions execute immediately when approved.

**Workaround**: Use external scheduling to trigger approvals.

---

### 4. Limited Rollback

**Limitation**: No automatic rollback for failed actions.

**Impact**: Manual intervention required to revert changes.

**Planned**: Rollback mechanism with `before_value` restoration.

---

## Error Recovery

### Action Failures

| Error | Recovery |
|-------|----------|
| Platform API error | Check error, retry or modify |
| Signal health degraded | Wait for improvement or manual approval |
| Enforcement blocked | Request confirmation or adjust settings |
| Token expired | Re-check enforcement for new token |

### System Failures

| Error | Recovery |
|-------|----------|
| Database unavailable | Retry with exponential backoff |
| Redis unavailable | Fallback to database checks |
| Network timeout | Retry with timeout adjustment |

---

## Monitoring

### Key Metrics

| Metric | Alert Threshold |
|--------|-----------------|
| Action success rate | < 90% |
| Enforcement block rate | > 30% |
| Average execution time | > 5 seconds |
| Pending actions age | > 24 hours |
| Kill switch toggles | > 2/week |

### Health Checks

```python
async def autopilot_health():
    return {
        "status": "healthy",
        "checks": {
            "database": await check_db(),
            "redis": await check_redis(),
            "platform_apis": {
                "meta": await check_meta_api(),
                "google": await check_google_api(),
                "tiktok": await check_tiktok_api(),
                "snapchat": await check_snapchat_api()
            },
            "pending_actions": await count_pending_actions(),
            "failed_actions_24h": await count_failed_actions(hours=24)
        }
    }
```

---

## Security Considerations

### Authorization

- All endpoints require tenant authentication
- Kill switch requires admin role
- Override confirmations logged with user ID

### Audit Trail

- All enforcement decisions logged
- Override reasons captured
- Kill switch changes tracked

### Rate Limiting

- Kill switch toggles limited to prevent abuse
- Confirmation attempts rate-limited

---

## Related Documentation

- [Specification](./spec.md) - Data models and architecture
- [User Flows](./user-flows.md) - Step-by-step user journeys
- [API Contracts](./api-contracts.md) - API endpoints and schemas
