# Onboarding Wizard API Contracts

## Overview

API endpoints for the tenant onboarding wizard.

**Base URL**: `/api/v1/tenant/{tenant_id}/onboarding`

---

## Authentication

All endpoints require Bearer token authentication with tenant context.

---

## Onboarding State

### GET /onboarding/status

Get current onboarding status and progress.

#### Response

```json
{
  "success": true,
  "data": {
    "tenant_id": 1,
    "overall_status": "in_progress",
    "current_step": "goals_setup",
    "progress_percent": 40,
    "started_at": "2024-01-15T10:00:00Z",
    "completed_at": null,
    "steps": {
      "business_profile": {
        "status": "completed",
        "completed_at": "2024-01-15T10:05:00Z"
      },
      "platform_selection": {
        "status": "completed",
        "completed_at": "2024-01-15T10:10:00Z"
      },
      "goals_setup": {
        "status": "not_started",
        "completed_at": null
      },
      "automation_preferences": {
        "status": "not_started",
        "completed_at": null
      },
      "trust_gate_config": {
        "status": "not_started",
        "completed_at": null
      }
    }
  }
}
```

---

## Step 1: Business Profile

### GET /onboarding/business-profile

Get saved business profile data.

#### Response

```json
{
  "success": true,
  "data": {
    "company_name": "Acme Corporation",
    "industry": "ecommerce",
    "monthly_ad_spend": "10k_50k",
    "team_size": "2_5",
    "website_url": "https://acme.com",
    "timezone": "America/Los_Angeles"
  }
}
```

---

### POST /onboarding/business-profile

Save business profile and proceed.

#### Request

```json
{
  "company_name": "Acme Corporation",
  "industry": "ecommerce",
  "monthly_ad_spend": "10k_50k",
  "team_size": "2_5",
  "website_url": "https://acme.com",
  "timezone": "America/Los_Angeles"
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "step": "business_profile",
    "status": "completed",
    "next_step": "platform_selection"
  },
  "message": "Business profile saved successfully"
}
```

---

## Step 2: Platform Selection

### GET /onboarding/platform-selection

Get saved platform selection.

#### Response

```json
{
  "success": true,
  "data": {
    "platforms": ["meta", "google"],
    "primary_platform": "google",
    "connections": {
      "meta": {
        "status": "connected",
        "connected_at": "2024-01-15T10:08:00Z"
      },
      "google": {
        "status": "connected",
        "connected_at": "2024-01-15T10:09:00Z"
      }
    }
  }
}
```

---

### POST /onboarding/platform-selection

Save platform selection and proceed.

#### Request

```json
{
  "platforms": ["meta", "google"],
  "primary_platform": "google",
  "connect_later": false
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "step": "platform_selection",
    "status": "completed",
    "next_step": "goals_setup",
    "platforms_selected": ["meta", "google"],
    "platforms_connected": ["google"]
  },
  "message": "Platforms selected. 1 platform pending connection."
}
```

---

## Step 3: Goals Setup

### GET /onboarding/goals-setup

Get saved goals configuration.

#### Response

```json
{
  "success": true,
  "data": {
    "primary_kpi": "roas",
    "target_roas": 2.5,
    "target_cpa": null,
    "monthly_budget_target": 25000.00,
    "revenue_goal": 62500.00
  }
}
```

---

### POST /onboarding/goals-setup

Save goals and proceed.

#### Request

```json
{
  "primary_kpi": "roas",
  "target_roas": 2.5,
  "monthly_budget_target": 25000.00,
  "revenue_goal": 62500.00
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "step": "goals_setup",
    "status": "completed",
    "next_step": "automation_preferences"
  },
  "message": "Goals configured successfully"
}
```

---

## Step 4: Automation Preferences

### GET /onboarding/automation-preferences

Get saved automation preferences.

#### Response

```json
{
  "success": true,
  "data": {
    "automation_mode": "moderate",
    "auto_pause_enabled": true,
    "budget_automation": true,
    "max_budget_change_percent": 20.0,
    "notification_email": "admin@acme.com",
    "slack_webhook": null
  }
}
```

---

### POST /onboarding/automation-preferences

Save automation preferences and proceed.

#### Request

```json
{
  "automation_mode": "moderate",
  "auto_pause_enabled": true,
  "budget_automation": true,
  "max_budget_change_percent": 20.0,
  "notification_email": "admin@acme.com"
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "step": "automation_preferences",
    "status": "completed",
    "next_step": "trust_gate_config"
  },
  "message": "Automation preferences saved"
}
```

---

## Step 5: Trust Gate Configuration

### GET /onboarding/trust-gate-config

Get saved trust gate configuration.

#### Response

```json
{
  "success": true,
  "data": {
    "signal_health_threshold": 70,
    "min_roas_threshold": 1.0,
    "max_budget_increase_percent": 20.0,
    "max_budget_decrease_percent": 30.0,
    "cooldown_hours": 24,
    "require_confirmation": true
  }
}
```

---

### POST /onboarding/trust-gate-config

Save trust gate config and complete onboarding.

#### Request

```json
{
  "signal_health_threshold": 70,
  "min_roas_threshold": 1.0,
  "max_budget_increase_percent": 20.0,
  "max_budget_decrease_percent": 30.0,
  "cooldown_hours": 24,
  "require_confirmation": true
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "step": "trust_gate_config",
    "status": "completed",
    "onboarding_status": "completed",
    "completed_at": "2024-01-15T10:20:00Z"
  },
  "message": "Onboarding completed! Welcome to Stratum AI."
}
```

---

## Skip Step

### POST /onboarding/{step}/skip

Skip an optional step.

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `step` | string | Step to skip: goals_setup, automation_preferences, trust_gate_config |

#### Response

```json
{
  "success": true,
  "data": {
    "step": "goals_setup",
    "status": "skipped",
    "defaults_applied": {
      "primary_kpi": "roas",
      "target_roas": 2.0
    },
    "next_step": "automation_preferences"
  },
  "message": "Step skipped. Default values applied."
}
```

---

## Complete Onboarding

### POST /onboarding/complete

Force complete onboarding (applies defaults to remaining steps).

#### Response

```json
{
  "success": true,
  "data": {
    "onboarding_status": "completed",
    "completed_at": "2024-01-15T10:20:00Z",
    "steps_completed": 3,
    "steps_skipped": 2
  },
  "message": "Onboarding completed with defaults applied to remaining steps."
}
```

---

## Reset Onboarding

### POST /onboarding/reset

Reset onboarding to start over (admin only).

#### Response

```json
{
  "success": true,
  "data": {
    "onboarding_status": "not_started",
    "steps_reset": 5
  },
  "message": "Onboarding reset. You can start the wizard again."
}
```

---

## Enum Values

### GET /onboarding/enums

Get available enum values for dropdowns.

#### Response

```json
{
  "success": true,
  "data": {
    "industries": [
      {"value": "ecommerce", "label": "E-Commerce"},
      {"value": "saas", "label": "SaaS"},
      {"value": "lead_gen", "label": "Lead Generation"},
      {"value": "mobile_app", "label": "Mobile App"},
      {"value": "agency", "label": "Agency"},
      {"value": "retail", "label": "Retail"},
      {"value": "finance", "label": "Finance"},
      {"value": "healthcare", "label": "Healthcare"},
      {"value": "education", "label": "Education"},
      {"value": "other", "label": "Other"}
    ],
    "monthly_ad_spend": [
      {"value": "under_10k", "label": "Under $10K"},
      {"value": "10k_50k", "label": "$10K - $50K"},
      {"value": "50k_100k", "label": "$50K - $100K"},
      {"value": "100k_500k", "label": "$100K - $500K"},
      {"value": "over_500k", "label": "Over $500K"}
    ],
    "team_sizes": [
      {"value": "solo", "label": "Just me"},
      {"value": "2_5", "label": "2-5 people"},
      {"value": "6_20", "label": "6-20 people"},
      {"value": "21_50", "label": "21-50 people"},
      {"value": "50_plus", "label": "50+ people"}
    ],
    "automation_modes": [
      {"value": "conservative", "label": "Conservative", "description": "Advisory only"},
      {"value": "moderate", "label": "Moderate", "description": "Smart automation with confirmations"},
      {"value": "aggressive", "label": "Aggressive", "description": "Full autopilot"}
    ],
    "primary_kpis": [
      {"value": "roas", "label": "ROAS"},
      {"value": "cpa", "label": "CPA"},
      {"value": "revenue", "label": "Revenue"},
      {"value": "conversions", "label": "Conversions"},
      {"value": "leads", "label": "Leads"}
    ],
    "platforms": [
      {"value": "meta", "label": "Meta (Facebook/Instagram)"},
      {"value": "google", "label": "Google Ads"},
      {"value": "tiktok", "label": "TikTok Ads"},
      {"value": "snapchat", "label": "Snapchat Ads"}
    ]
  }
}
```

---

## Error Responses

### Error Format

```json
{
  "success": false,
  "error": {
    "code": "STEP_NOT_SKIPPABLE",
    "message": "This step cannot be skipped",
    "details": {
      "step": "business_profile",
      "reason": "Required for account setup"
    }
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `ONBOARDING_COMPLETE` | 400 | Onboarding already completed |
| `STEP_NOT_SKIPPABLE` | 400 | Step is required |
| `STEP_NOT_FOUND` | 404 | Invalid step name |
| `PREVIOUS_STEP_INCOMPLETE` | 400 | Must complete previous step first |
| `INVALID_FIELD` | 400 | Invalid field value |
| `PLATFORM_NOT_SELECTED` | 400 | Must select at least one platform |

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| GET endpoints | 60/min |
| POST endpoints | 20/min |
| Reset | 5/day |

---

## Related Documentation

- [Specification](./spec.md) - Data models and architecture
- [User Flows](./user-flows.md) - Step-by-step user journeys
- [Edge Cases](./edge-cases.md) - Error handling and edge cases
