# Onboarding Wizard Edge Cases

## Overview

This document covers error handling, edge cases, and known limitations for the onboarding wizard.

---

## Edge Cases

### 1. Refresh During Step

**Scenario**: User refreshes browser mid-step.

**Behavior**:
- Data saved after each field change
- Refresh loads current step with saved data
- Unsaved changes may be lost

**Handling**:
```javascript
// Auto-save on field change with debounce
const debouncedSave = debounce(async (field, value) => {
  await api.saveOnboardingField(currentStep, field, value);
}, 1000);

// On page load, restore from server
useEffect(() => {
  const savedData = await api.getStepData(currentStep);
  setFormData(savedData);
}, [currentStep]);
```

---

### 2. Session Timeout During Onboarding

**Scenario**: User's session expires while completing wizard.

**Behavior**:
- Next API call returns 401
- User redirected to login
- After login, resume from last saved step

**Response**:
```json
{
  "error": {
    "code": "SESSION_EXPIRED",
    "message": "Your session has expired",
    "details": {
      "redirect": "/login?return=/onboarding"
    }
  }
}
```

---

### 3. Skip Required Step Attempt

**Scenario**: User tries to skip business_profile or platform_selection.

**Behavior**:
- Skip request rejected
- Error message displayed
- User must complete step

**Response**:
```json
{
  "error": {
    "code": "STEP_NOT_SKIPPABLE",
    "message": "Business profile is required and cannot be skipped",
    "details": {
      "step": "business_profile",
      "skippable_steps": ["goals_setup", "automation_preferences", "trust_gate_config"]
    }
  }
}
```

---

### 4. Navigate to Future Step

**Scenario**: User tries to access Step 4 without completing Step 2.

**Behavior**:
- Redirect to first incomplete step
- Toast notification explains requirement

**Handling**:
```python
async def validate_step_access(tenant_id: int, requested_step: OnboardingStep):
    state = await get_onboarding_state(tenant_id)

    step_order = list(OnboardingStep)
    requested_index = step_order.index(requested_step)

    for i in range(requested_index):
        previous_step = step_order[i]
        if state.steps.get(previous_step, {}).status == OnboardingStatus.NOT_STARTED:
            raise HTTPException(
                status_code=400,
                detail=f"Must complete {previous_step.value} first"
            )
```

---

### 5. Back Navigation Data Loss

**Scenario**: User goes back to previous step and changes data.

**Behavior**:
- Previous step data editable
- Changes saved on submit
- Forward progress preserved

**UI Handling**:
```
┌─────────────────────────────────────────────────────────────┐
│  Update Business Profile?                             [×]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  You've already completed this step. Changes will update   │
│  your existing profile.                                     │
│                                                             │
│  [Cancel]                                    [Update & Continue]│
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

### 6. Platform Connection Failure During Step 2

**Scenario**: User attempts to connect platform but credentials fail.

**Behavior**:
- Error shown in modal
- User can retry or skip connection
- Step can complete without connection

**Response**:
```json
{
  "success": false,
  "error": {
    "code": "CONNECTION_FAILED",
    "message": "Could not connect to Meta Ads",
    "details": {
      "platform": "meta",
      "reason": "Invalid access token"
    }
  },
  "data": {
    "can_continue": true,
    "message": "You can connect this platform later from Settings"
  }
}
```

---

### 7. Invalid Target Values

**Scenario**: User enters unrealistic target ROAS (e.g., 100x).

**Behavior**:
- Validation warning shown
- User can proceed but gets warning
- Recommendation provided

**Response**:
```json
{
  "success": true,
  "data": { "...": "..." },
  "warnings": [
    {
      "field": "target_roas",
      "message": "Target ROAS of 100x is unusually high. Industry average is 2-4x.",
      "recommendation": "Consider a target between 2.0x and 5.0x for realistic goals."
    }
  ]
}
```

---

### 8. Conflicting Settings

**Scenario**: User selects "Aggressive" mode but sets 80% signal threshold.

**Behavior**:
- Warning about conflicting settings
- Explain impact
- Allow proceed with acknowledgment

**Response**:
```json
{
  "success": true,
  "data": { "...": "..." },
  "warnings": [
    {
      "type": "config_conflict",
      "message": "Aggressive automation with 80% threshold may limit automation effectiveness",
      "explanation": "High thresholds mean fewer actions will auto-execute",
      "suggestion": "Consider 60-70% threshold for aggressive mode"
    }
  ]
}
```

---

### 9. Onboarding Already Completed

**Scenario**: User visits onboarding URL after completion.

**Behavior**:
- Redirect to dashboard
- Option to access settings instead

**Handling**:
```python
async def check_onboarding_status(tenant_id: int):
    state = await get_onboarding_state(tenant_id)

    if state.overall_status == OnboardingStatus.COMPLETED:
        raise HTTPException(
            status_code=302,
            headers={"Location": "/dashboard?onboarding=complete"}
        )
```

---

### 10. Multiple Tabs Open

**Scenario**: User opens onboarding in multiple tabs.

**Behavior**:
- Both tabs sync to same step
- Last save wins
- No corruption

**Handling**:
```javascript
// Listen for storage events
window.addEventListener('storage', (event) => {
  if (event.key === 'onboarding_step') {
    // Reload current step from server
    refetchStepData();
  }
});

// Broadcast changes
const saveStep = async (step, data) => {
  await api.saveStep(step, data);
  localStorage.setItem('onboarding_step', step);
};
```

---

### 11. Tenant Deleted Mid-Onboarding

**Scenario**: Admin deletes tenant while user is in wizard.

**Behavior**:
- Next API call returns 404
- User shown error page
- Suggest contact support

**Response**:
```json
{
  "error": {
    "code": "TENANT_NOT_FOUND",
    "message": "Account not found",
    "details": {
      "action": "contact_support"
    }
  }
}
```

---

### 12. Reset and Re-onboard

**Scenario**: Admin resets onboarding after completion.

**Behavior**:
- All step data cleared
- Previous settings preserved in main config
- Onboarding can start fresh

**Response**:
```json
{
  "success": true,
  "data": {
    "onboarding_status": "not_started",
    "steps_reset": 5,
    "settings_preserved": true,
    "note": "Your existing settings remain active. Onboarding will update them."
  }
}
```

---

## Known Limitations

### 1. No Offline Support

**Limitation**: Wizard requires internet connection.

**Impact**: Cannot save progress offline.

**Workaround**: Save frequently; data persists server-side.

---

### 2. Single Tenant Onboarding

**Limitation**: Each tenant onboards independently.

**Impact**: Agency admins must onboard each client separately.

**Planned**: Bulk onboarding template.

---

### 3. No Undo After Complete

**Limitation**: Cannot undo completion status.

**Impact**: Must manually change settings.

**Workaround**: Admin reset available.

---

### 4. Limited Customization

**Limitation**: Cannot add custom onboarding steps.

**Impact**: All tenants have same flow.

**Planned**: Custom step injection for enterprise.

---

## Error Recovery

### Form Errors

| Error | Recovery |
|-------|----------|
| Validation failed | Show inline errors, keep form data |
| Server error | Retry with exponential backoff |
| Timeout | Show retry button |

### Navigation Errors

| Error | Recovery |
|-------|----------|
| Step not accessible | Redirect to first incomplete |
| Session expired | Preserve URL, redirect after login |
| Tenant not found | Show support contact |

---

## Monitoring

### Key Metrics

| Metric | Alert Threshold |
|--------|-----------------|
| Completion rate | < 60% |
| Average completion time | > 15 minutes |
| Step abandonment rate | > 20% per step |
| Error rate | > 5% |

### Funnel Analytics

```python
async def get_onboarding_funnel():
    return {
        "business_profile": {
            "started": 1000,
            "completed": 950,
            "drop_rate": 5.0
        },
        "platform_selection": {
            "started": 950,
            "completed": 900,
            "drop_rate": 5.3
        },
        "goals_setup": {
            "started": 900,
            "completed": 820,
            "skipped": 50,
            "drop_rate": 3.3
        },
        "automation_preferences": {
            "started": 870,
            "completed": 800,
            "skipped": 40,
            "drop_rate": 3.4
        },
        "trust_gate_config": {
            "started": 840,
            "completed": 780,
            "skipped": 30,
            "drop_rate": 3.6
        },
        "overall_completion": 78.0
    }
```

---

## Related Documentation

- [Specification](./spec.md) - Data models and architecture
- [User Flows](./user-flows.md) - Step-by-step user journeys
- [API Contracts](./api-contracts.md) - API endpoints and schemas
