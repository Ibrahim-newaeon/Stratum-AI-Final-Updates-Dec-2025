# Superadmin API Contracts

## Overview

API endpoints for platform administration and tenant management.

**Base URL**: `/api/v1/admin`

---

## Authentication

All endpoints require Bearer token authentication with admin role.

```
Authorization: Bearer <admin_token>
X-Admin-IP: <client_ip>
```

---

## Tenants

### GET /admin/tenants

List all tenants.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `search` | string | Search by name or email |
| `status` | string | Filter: active, suspended, pending, deleted |
| `plan` | string | Filter: starter, growth, enterprise |
| `page` | integer | Page number (default: 1) |
| `limit` | integer | Items per page (default: 20) |

#### Response

```json
{
  "success": true,
  "data": {
    "tenants": [
      {
        "id": 1,
        "name": "Acme Corp",
        "slug": "acme-corp",
        "status": "active",
        "subscription_tier": "growth",
        "max_users": 10,
        "max_campaigns": 50,
        "user_count": 5,
        "campaign_count": 12,
        "industry": "e-commerce",
        "onboarding_completed": true,
        "created_at": "2024-01-15T10:00:00Z",
        "last_activity_at": "2024-01-18T14:30:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 128,
      "pages": 7
    }
  }
}
```

### GET /admin/tenants/{tenant_id}

Get tenant details.

#### Response

```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "Acme Corp",
    "slug": "acme-corp",
    "status": "active",
    "subscription_tier": "growth",
    "max_users": 10,
    "max_campaigns": 50,
    "feature_flags": {
      "whatsapp_enabled": true,
      "advanced_analytics": true,
      "beta_features": false
    },
    "industry": "e-commerce",
    "company_size": "11-50",
    "onboarding_completed": true,
    "billing": {
      "stripe_customer_id": "cus_abc123",
      "current_period_end": "2024-02-15T00:00:00Z",
      "payment_status": "paid"
    },
    "usage": {
      "users": 5,
      "campaigns": 12,
      "events_this_month": 45000
    },
    "admin_users": [
      {
        "id": 101,
        "email": "admin@acme.com",
        "name": "John Admin",
        "last_login": "2024-01-18T10:00:00Z"
      }
    ],
    "created_at": "2024-01-15T10:00:00Z",
    "last_activity_at": "2024-01-18T14:30:00Z"
  }
}
```

### POST /admin/tenants

Create new tenant.

#### Request

```json
{
  "name": "NewCo Inc",
  "admin_email": "admin@newco.com",
  "admin_name": "Jane Admin",
  "subscription_tier": "growth",
  "initial_status": "active",
  "industry": "saas",
  "company_size": "11-50",
  "send_welcome_email": true,
  "skip_onboarding": false
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "id": 129,
    "name": "NewCo Inc",
    "slug": "newco-inc",
    "status": "active",
    "admin_user": {
      "id": 501,
      "email": "admin@newco.com",
      "temp_password": "auto-generated-shown-once"
    }
  },
  "message": "Tenant created successfully"
}
```

### PATCH /admin/tenants/{tenant_id}

Update tenant.

#### Request

```json
{
  "name": "NewCo Corporation",
  "subscription_tier": "enterprise",
  "max_users": 50,
  "max_campaigns": 200,
  "feature_flags": {
    "whatsapp_enabled": true
  }
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "id": 1,
    "name": "NewCo Corporation",
    "subscription_tier": "enterprise"
  },
  "message": "Tenant updated successfully"
}
```

### POST /admin/tenants/{tenant_id}/suspend

Suspend tenant.

#### Request

```json
{
  "reason": "Payment failed after 3 retry attempts",
  "notify_admins": true
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "id": 1,
    "status": "suspended",
    "suspended_at": "2024-01-18T12:00:00Z",
    "automations_disabled": 5
  },
  "message": "Tenant suspended"
}
```

### POST /admin/tenants/{tenant_id}/reactivate

Reactivate suspended tenant.

#### Request

```json
{
  "notes": "Payment received via bank transfer",
  "notify_admins": true
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "id": 1,
    "status": "active",
    "reactivated_at": "2024-01-20T10:00:00Z"
  },
  "message": "Tenant reactivated"
}
```

### DELETE /admin/tenants/{tenant_id}

Soft delete tenant.

#### Request

```json
{
  "reason": "Customer requested account deletion",
  "confirm": true
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "id": 1,
    "status": "deleted",
    "data_deletion_at": "2024-02-18T00:00:00Z"
  },
  "message": "Tenant marked for deletion"
}
```

---

## User Impersonation

### POST /admin/impersonate

Start impersonation session.

#### Request

```json
{
  "tenant_id": 1,
  "user_id": 101,
  "reason": "Support ticket #12345 - debugging campaign issue"
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "session_id": "imp_abc123",
    "impersonation_token": "eyJ...",
    "expires_at": "2024-01-18T15:00:00Z",
    "target_user": {
      "id": 101,
      "email": "user@acme.com",
      "name": "John User"
    }
  },
  "message": "Impersonation session started"
}
```

### DELETE /admin/impersonate/{session_id}

End impersonation session.

#### Response

```json
{
  "success": true,
  "data": {
    "session_id": "imp_abc123",
    "ended_at": "2024-01-18T14:30:00Z",
    "duration_minutes": 15
  },
  "message": "Impersonation session ended"
}
```

### GET /admin/impersonate/sessions

List active impersonation sessions.

#### Response

```json
{
  "success": true,
  "data": [
    {
      "session_id": "imp_abc123",
      "admin_id": 1,
      "admin_email": "admin@stratum.ai",
      "tenant_id": 1,
      "user_id": 101,
      "started_at": "2024-01-18T14:00:00Z",
      "expires_at": "2024-01-18T15:00:00Z"
    }
  ]
}
```

---

## System Health

### GET /admin/health

Get system health status.

#### Response

```json
{
  "success": true,
  "data": {
    "timestamp": "2024-01-18T14:00:00Z",
    "overall_status": "healthy",
    "components": {
      "database": {
        "status": "healthy",
        "latency_ms": 5,
        "connections": {
          "active": 45,
          "max": 100
        }
      },
      "redis": {
        "status": "healthy",
        "latency_ms": 1,
        "memory": {
          "used_bytes": 2147483648,
          "max_bytes": 8589934592
        }
      },
      "celery": {
        "status": "healthy",
        "workers": {
          "active": 8,
          "total": 8
        },
        "queue_depth": 125
      },
      "api": {
        "status": "healthy",
        "latency_ms": 45,
        "error_rate": 0.002
      }
    },
    "integrations": {
      "meta": {
        "status": "healthy",
        "rate_limit": {
          "current": 850,
          "max": 1000
        }
      },
      "google": {
        "status": "healthy",
        "rate_limit": {
          "current": 420,
          "max": 600
        }
      },
      "tiktok": {
        "status": "degraded",
        "rate_limit": {
          "current": 480,
          "max": 500
        },
        "message": "Approaching rate limit"
      },
      "snapchat": {
        "status": "healthy",
        "rate_limit": {
          "current": 100,
          "max": 500
        }
      }
    },
    "metrics": {
      "active_tenants": 128,
      "requests_per_minute": 1250,
      "error_rate": 0.0002,
      "avg_response_time_ms": 89
    }
  }
}
```

### POST /admin/health/check

Trigger manual health check.

#### Response

```json
{
  "success": true,
  "data": {
    "check_id": "chk_abc123",
    "started_at": "2024-01-18T14:00:00Z",
    "results": {
      "database": "passed",
      "redis": "passed",
      "celery": "passed",
      "integrations": "degraded"
    }
  }
}
```

---

## Feature Flags

### GET /admin/feature-flags

List all feature flags.

#### Response

```json
{
  "success": true,
  "data": [
    {
      "name": "whatsapp_enabled",
      "description": "Enable WhatsApp messaging integration",
      "default_value": false,
      "is_global": true,
      "rollout_percentage": 0,
      "tenant_overrides_count": 5,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-15T10:00:00Z",
      "updated_by": "admin@stratum.ai"
    },
    {
      "name": "new_dashboard_v2",
      "description": "New dashboard redesign",
      "default_value": false,
      "is_global": true,
      "rollout_percentage": 25,
      "tenant_overrides_count": 2,
      "created_at": "2024-01-10T00:00:00Z",
      "updated_at": "2024-01-18T09:00:00Z",
      "updated_by": "admin@stratum.ai"
    }
  ]
}
```

### GET /admin/feature-flags/{flag_name}

Get feature flag details.

#### Response

```json
{
  "success": true,
  "data": {
    "name": "new_dashboard_v2",
    "description": "New dashboard redesign",
    "default_value": false,
    "is_global": true,
    "rollout_percentage": 25,
    "tenant_overrides": {
      "1": true,
      "5": true
    },
    "created_at": "2024-01-10T00:00:00Z",
    "updated_at": "2024-01-18T09:00:00Z",
    "updated_by": "admin@stratum.ai"
  }
}
```

### POST /admin/feature-flags

Create feature flag.

#### Request

```json
{
  "name": "ai_recommendations",
  "description": "AI-powered campaign recommendations",
  "default_value": false,
  "is_global": true,
  "rollout_percentage": 5
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "name": "ai_recommendations",
    "created_at": "2024-01-18T14:00:00Z"
  },
  "message": "Feature flag created"
}
```

### PATCH /admin/feature-flags/{flag_name}

Update feature flag.

#### Request

```json
{
  "default_value": true,
  "rollout_percentage": 100,
  "tenant_overrides": {
    "1": false,
    "5": null
  }
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "name": "new_dashboard_v2",
    "default_value": true,
    "rollout_percentage": 100
  },
  "message": "Feature flag updated"
}
```

### DELETE /admin/feature-flags/{flag_name}

Delete feature flag.

#### Response

```
HTTP 204 No Content
```

---

## Audit Logs

### GET /admin/audit-logs

List audit logs.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `admin_id` | integer | Filter by admin |
| `action` | string | Filter by action type |
| `resource_type` | string | Filter: tenant, user, config |
| `tenant_id` | integer | Filter by affected tenant |
| `start_date` | datetime | From date |
| `end_date` | datetime | To date |
| `page` | integer | Page number |
| `limit` | integer | Items per page |

#### Response

```json
{
  "success": true,
  "data": {
    "logs": [
      {
        "id": 1234,
        "admin_id": 1,
        "admin_email": "admin@stratum.ai",
        "action": "tenant.suspend",
        "resource_type": "tenant",
        "resource_id": "45",
        "tenant_id": 45,
        "ip_address": "192.168.1.100",
        "reason": "Payment failed after 3 retry attempts",
        "created_at": "2024-01-18T12:00:00Z"
      }
    ],
    "pagination": {
      "page": 1,
      "limit": 20,
      "total": 1247,
      "pages": 63
    }
  }
}
```

### GET /admin/audit-logs/{log_id}

Get audit log details.

#### Response

```json
{
  "success": true,
  "data": {
    "id": 1234,
    "admin_id": 1,
    "admin_email": "admin@stratum.ai",
    "admin_name": "Platform Admin",
    "action": "tenant.suspend",
    "resource_type": "tenant",
    "resource_id": "45",
    "tenant_id": 45,
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0...",
    "reason": "Payment failed after 3 retry attempts",
    "changes": {
      "before": {
        "status": "active"
      },
      "after": {
        "status": "suspended",
        "suspended_at": "2024-01-18T12:00:00Z"
      }
    },
    "created_at": "2024-01-18T12:00:00Z"
  }
}
```

### POST /admin/audit-logs/export

Export audit logs.

#### Request

```json
{
  "start_date": "2024-01-01T00:00:00Z",
  "end_date": "2024-01-18T23:59:59Z",
  "format": "csv",
  "filters": {
    "action": "tenant.suspend"
  }
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "export_id": "exp_abc123",
    "status": "processing",
    "download_url": null,
    "estimated_records": 45
  }
}
```

---

## Admin Users

### GET /admin/users

List admin users.

#### Response

```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "email": "admin@stratum.ai",
      "name": "Platform Admin",
      "role": "superadmin",
      "is_active": true,
      "mfa_enabled": true,
      "last_login": "2024-01-18T10:00:00Z",
      "login_count": 245,
      "created_at": "2023-01-01T00:00:00Z"
    }
  ]
}
```

### POST /admin/users

Create admin user.

#### Request

```json
{
  "email": "support@stratum.ai",
  "name": "Support Agent",
  "role": "support",
  "allowed_actions": ["tenant.view", "user.impersonate"],
  "ip_allowlist": ["192.168.1.0/24"]
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "id": 5,
    "email": "support@stratum.ai",
    "role": "support",
    "temp_password": "auto-generated"
  },
  "message": "Admin user created"
}
```

### PATCH /admin/users/{admin_id}

Update admin user.

#### Request

```json
{
  "role": "audit",
  "is_active": false
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "id": 5,
    "role": "audit",
    "is_active": false
  }
}
```

---

## Platform Analytics

### GET /admin/analytics/overview

Get platform analytics overview.

#### Query Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `period` | string | 7d, 30d, 90d, 1y |

#### Response

```json
{
  "success": true,
  "data": {
    "period": "30d",
    "tenants": {
      "total": 128,
      "active_7d": 112,
      "new_30d": 18,
      "churned_30d": 3
    },
    "usage": {
      "total_campaigns": 1450,
      "total_events_30d": 12500000,
      "total_api_calls_30d": 8500000
    },
    "revenue": {
      "mrr_cents": 3850000,
      "arr_cents": 46200000,
      "arpu_cents": 30078
    },
    "health": {
      "healthy": 108,
      "warning": 15,
      "critical": 5
    },
    "plans": {
      "trial": 7,
      "starter": 32,
      "growth": 71,
      "enterprise": 18
    }
  }
}
```

### GET /admin/analytics/trends

Get trend data.

#### Response

```json
{
  "success": true,
  "data": {
    "period": "30d",
    "datapoints": [
      {
        "date": "2024-01-18",
        "tenants": 128,
        "active_users": 450,
        "events": 425000,
        "mrr_cents": 3850000
      }
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
    "code": "TENANT_NOT_FOUND",
    "message": "Tenant with ID 999 not found",
    "details": {}
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `UNAUTHORIZED` | 401 | Invalid or missing token |
| `FORBIDDEN` | 403 | Insufficient permissions |
| `TENANT_NOT_FOUND` | 404 | Tenant doesn't exist |
| `USER_NOT_FOUND` | 404 | User doesn't exist |
| `INVALID_ACTION` | 400 | Action not allowed |
| `IMPERSONATION_ACTIVE` | 400 | Already impersonating |
| `MFA_REQUIRED` | 403 | MFA verification needed |
| `IP_NOT_ALLOWED` | 403 | IP not in allowlist |

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| GET endpoints | 120/min |
| POST/PATCH endpoints | 60/min |
| Impersonation | 10/hour |
| Export | 5/hour |

---

## Related Documentation

- [Specification](./spec.md) - Data models and architecture
- [User Flows](./user-flows.md) - Step-by-step admin journeys
- [Edge Cases](./edge-cases.md) - Error handling
