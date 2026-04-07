# Superadmin Specification

## Overview

The Superadmin module provides platform administrators with tools to manage tenants, monitor system health, configure platform settings, and access cross-tenant analytics.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   SUPERADMIN ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  ADMIN DASHBOARD                          │  │
│  │                                                          │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │  │
│  │  │ Tenant   │ │  System  │ │ Platform │ │  Audit   │   │  │
│  │  │Management│ │  Health  │ │ Analytics│ │   Logs   │   │  │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘   │  │
│  │       │            │            │            │          │  │
│  │       └────────────┴─────┬──────┴────────────┘          │  │
│  └──────────────────────────┼───────────────────────────────┘  │
│                             ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  ADMIN SERVICES                           │  │
│  │                                                          │  │
│  │  • Tenant CRUD operations                                │  │
│  │  • User impersonation                                    │  │
│  │  • Feature flag management                               │  │
│  │  • System configuration                                  │  │
│  │  • Audit logging                                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  ACCESS CONTROL                           │  │
│  │                                                          │  │
│  │  SuperAdmin Role → Full platform access                  │  │
│  │  Support Role → Read + limited write                     │  │
│  │  Audit Role → Read only                                  │  │
│  │                                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Data Models

### AdminUser

```python
class AdminUser:
    id: int
    email: str
    name: str
    role: AdminRole                   # superadmin, support, audit
    is_active: bool

    # Security
    mfa_enabled: bool
    last_login: datetime | None
    login_count: int

    # Access
    allowed_actions: list[str]
    ip_allowlist: list[str] | None

    created_at: datetime
    created_by: int | None
```

### Tenant

```python
class Tenant:
    id: int
    name: str
    slug: str                         # URL-friendly identifier

    # Status
    status: TenantStatus              # active, suspended, deleted
    subscription_tier: str

    # Limits
    max_users: int
    max_campaigns: int
    feature_flags: dict[str, bool]

    # Metadata
    industry: str | None
    company_size: str | None
    onboarding_completed: bool

    # Tracking
    created_at: datetime
    last_activity_at: datetime
```

### AuditLog

```python
class AuditLog:
    id: int
    admin_id: int
    action: str                       # tenant.create, user.impersonate, etc.
    resource_type: str                # tenant, user, config
    resource_id: str

    # Context
    tenant_id: int | None
    ip_address: str
    user_agent: str

    # Details
    changes: dict                     # Before/after state
    reason: str | None                # Required for some actions

    created_at: datetime
```

### SystemHealth

```python
class SystemHealth:
    timestamp: datetime
    overall_status: str               # healthy, degraded, unhealthy

    # Components
    database: ComponentHealth
    redis: ComponentHealth
    celery: ComponentHealth
    api: ComponentHealth
    integrations: dict[str, ComponentHealth]

    # Metrics
    active_tenants: int
    requests_per_minute: int
    error_rate: float
    avg_response_time_ms: float
```

---

## Enums

### AdminRole

```python
class AdminRole(str, Enum):
    SUPERADMIN = "superadmin"         # Full access
    SUPPORT = "support"               # Read + limited write
    AUDIT = "audit"                   # Read only
```

### TenantStatus

```python
class TenantStatus(str, Enum):
    ACTIVE = "active"
    SUSPENDED = "suspended"
    PENDING = "pending"
    DELETED = "deleted"
```

### AuditAction

```python
class AuditAction(str, Enum):
    # Tenant actions
    TENANT_CREATE = "tenant.create"
    TENANT_UPDATE = "tenant.update"
    TENANT_SUSPEND = "tenant.suspend"
    TENANT_DELETE = "tenant.delete"

    # User actions
    USER_IMPERSONATE = "user.impersonate"
    USER_PASSWORD_RESET = "user.password_reset"

    # Config actions
    CONFIG_UPDATE = "config.update"
    FEATURE_FLAG_TOGGLE = "feature_flag.toggle"

    # System actions
    SYSTEM_MAINTENANCE = "system.maintenance"
```

---

## Admin Roles & Permissions

### Permission Matrix

| Permission | Superadmin | Support | Audit |
|------------|------------|---------|-------|
| View tenants | ✓ | ✓ | ✓ |
| Create tenants | ✓ | - | - |
| Update tenants | ✓ | ✓ | - |
| Suspend/delete tenants | ✓ | - | - |
| Impersonate users | ✓ | ✓ | - |
| View system health | ✓ | ✓ | ✓ |
| Modify system config | ✓ | - | - |
| Toggle feature flags | ✓ | - | - |
| View audit logs | ✓ | ✓ | ✓ |
| Manage admin users | ✓ | - | - |

---

## Tenant Management

### Tenant Lifecycle

```
┌─────────┐     ┌─────────┐     ┌─────────┐     ┌─────────┐
│ PENDING │ ──► │ ACTIVE  │ ──► │SUSPENDED│ ──► │ DELETED │
└─────────┘     └─────────┘     └─────────┘     └─────────┘
                     │               │
                     └───────────────┘
                     (Reactivation)
```

### Suspension Flow

```python
async def suspend_tenant(tenant_id: int, reason: str, admin_id: int):
    tenant = await get_tenant(tenant_id)

    # Update status
    tenant.status = TenantStatus.SUSPENDED
    tenant.suspended_at = datetime.now(timezone.utc)
    tenant.suspension_reason = reason

    # Disable automations
    await disable_tenant_automations(tenant_id)

    # Log action
    await create_audit_log(
        admin_id=admin_id,
        action=AuditAction.TENANT_SUSPEND,
        resource_type="tenant",
        resource_id=str(tenant_id),
        reason=reason,
    )

    # Notify tenant admins
    await send_suspension_notification(tenant_id, reason)

    await db.commit()
```

---

## User Impersonation

### Impersonation Flow

```python
async def impersonate_user(admin_id: int, tenant_id: int, user_id: int, reason: str):
    # Validate admin permission
    admin = await get_admin(admin_id)
    if admin.role not in [AdminRole.SUPERADMIN, AdminRole.SUPPORT]:
        raise PermissionDenied()

    # Create impersonation session
    session = ImpersonationSession(
        admin_id=admin_id,
        tenant_id=tenant_id,
        user_id=user_id,
        started_at=datetime.now(timezone.utc),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    # Log action
    await create_audit_log(
        admin_id=admin_id,
        action=AuditAction.USER_IMPERSONATE,
        resource_type="user",
        resource_id=str(user_id),
        tenant_id=tenant_id,
        reason=reason,
    )

    # Generate impersonation token
    token = create_impersonation_token(session)

    return token
```

### Session Constraints

- Maximum duration: 1 hour
- All actions logged with impersonation context
- Clear visual indicator in UI
- Cannot modify admin settings

---

## Feature Flags

### Flag Types

| Type | Description |
|------|-------------|
| Global | Applies to all tenants |
| Tenant | Per-tenant override |
| Percentage | Gradual rollout |
| User | Per-user testing |

### Flag Management

```python
class FeatureFlag:
    name: str
    description: str
    default_value: bool
    is_global: bool = True

    # Rollout
    rollout_percentage: int = 0       # 0-100
    tenant_overrides: dict[int, bool] = {}

    # Metadata
    created_at: datetime
    updated_at: datetime
    updated_by: int
```

---

## System Health Monitoring

### Health Checks

```python
async def get_system_health() -> SystemHealth:
    return SystemHealth(
        timestamp=datetime.now(timezone.utc),
        overall_status=calculate_overall_status(),
        database=await check_database(),
        redis=await check_redis(),
        celery=await check_celery_workers(),
        api=await check_api_health(),
        integrations={
            "meta": await check_platform_health("meta"),
            "google": await check_platform_health("google"),
            "tiktok": await check_platform_health("tiktok"),
            "snapchat": await check_platform_health("snapchat"),
        },
        active_tenants=await count_active_tenants(),
        requests_per_minute=await get_request_rate(),
        error_rate=await get_error_rate(),
        avg_response_time_ms=await get_avg_response_time(),
    )
```

### Alerting Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| Error rate | > 1% | > 5% |
| Response time | > 500ms | > 2000ms |
| Database connections | > 70% | > 90% |
| Redis memory | > 70% | > 90% |
| Celery queue depth | > 1000 | > 5000 |

---

## Platform Analytics

### Cross-Tenant Metrics

```python
class PlatformAnalytics:
    # Tenant metrics
    total_tenants: int
    active_tenants_7d: int
    new_tenants_30d: int
    churned_tenants_30d: int

    # Usage metrics
    total_campaigns: int
    total_events_30d: int
    total_api_calls_30d: int

    # Revenue metrics
    mrr_cents: int
    arr_cents: int
    average_revenue_per_tenant_cents: int

    # Health metrics
    tenants_by_health: dict[str, int]
    tenants_by_plan: dict[str, int]
```

---

## Audit Logging

### Required Logging

All admin actions must be logged with:
- Admin user ID
- Action type
- Resource affected
- Before/after state
- IP address
- Timestamp
- Reason (for destructive actions)

### Log Retention

- Active logs: 90 days in database
- Archived logs: 7 years in cold storage
- Compliance: SOC 2, GDPR

---

## Related Documentation

- [User Flows](./user-flows.md) - Step-by-step admin journeys
- [API Contracts](./api-contracts.md) - Admin API endpoints
- [Edge Cases](./edge-cases.md) - Error handling
