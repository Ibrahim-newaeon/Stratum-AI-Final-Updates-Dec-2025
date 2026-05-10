# Superadmin Edge Cases

## Overview

This document covers error handling, edge cases, and known limitations for platform administration.

---

## Edge Cases

### 1. Admin MFA Lost

**Scenario**: Admin loses MFA device and cannot log in.

**Behavior**:
- Login blocked
- Recovery flow required
- Another superadmin must assist

**Recovery Flow**:
```python
async def reset_admin_mfa(admin_id: int, requester_id: int, verification: str):
    # Verify requester is superadmin
    requester = await get_admin(requester_id)
    if requester.role != AdminRole.SUPERADMIN:
        raise PermissionDenied()

    # Require secondary verification
    if not await verify_identity(admin_id, verification):
        raise IdentityVerificationFailed()

    # Disable MFA
    admin = await get_admin(admin_id)
    admin.mfa_enabled = False
    admin.mfa_secret = None

    # Force password reset
    admin.force_password_reset = True

    # Audit log
    await create_audit_log(
        admin_id=requester_id,
        action="admin.mfa_reset",
        resource_type="admin",
        resource_id=str(admin_id),
        reason=f"MFA recovery requested",
    )

    await db.commit()
```

---

### 2. IP Allowlist Lockout

**Scenario**: Admin changes IP allowlist and locks themselves out.

**Behavior**:
- Admin cannot access from current IP
- Must contact another superadmin
- Emergency bypass available

**Response**:
```json
{
  "error": {
    "code": "IP_NOT_ALLOWED",
    "message": "Access denied from current IP address",
    "details": {
      "client_ip": "203.0.113.50",
      "allowed_ranges": ["192.168.1.0/24"],
      "recovery": "Contact another superadmin to update IP allowlist"
    }
  }
}
```

---

### 3. Impersonation Session Expired

**Scenario**: Admin's impersonation session expires mid-action.

**Behavior**:
- Action fails
- Session terminated
- Admin redirected to admin portal

**Response**:
```json
{
  "error": {
    "code": "IMPERSONATION_EXPIRED",
    "message": "Impersonation session has expired",
    "details": {
      "session_id": "imp_abc123",
      "expired_at": "2024-01-18T15:00:00Z",
      "action": "Start new impersonation session"
    }
  }
}
```

**Handling**:
```python
async def check_impersonation_session(token: str) -> ImpersonationSession:
    session = await get_session_from_token(token)

    if session.expires_at < datetime.now(timezone.utc):
        await end_impersonation_session(session.id, reason="expired")
        raise ImpersonationExpired(session_id=session.id)

    return session
```

---

### 4. Tenant Suspension with Active Campaigns

**Scenario**: Suspending tenant with running automations.

**Behavior**:
- All automations immediately paused
- In-flight events allowed to complete
- New events blocked

**Response**:
```json
{
  "success": true,
  "data": {
    "id": 45,
    "status": "suspended",
    "impact": {
      "automations_paused": 5,
      "events_in_flight": 12,
      "scheduled_tasks_cancelled": 3
    }
  },
  "warnings": [
    "12 events were in-flight and allowed to complete",
    "5 automations have been paused"
  ]
}
```

---

### 5. Feature Flag Conflict

**Scenario**: Tenant override conflicts with rollout percentage.

**Behavior**:
- Explicit override takes precedence
- Rollout percentage ignored for tenant

**Logic**:
```python
def evaluate_feature_flag(flag: FeatureFlag, tenant_id: int) -> bool:
    # 1. Check explicit tenant override (highest priority)
    if tenant_id in flag.tenant_overrides:
        return flag.tenant_overrides[tenant_id]

    # 2. Check rollout percentage
    if flag.rollout_percentage > 0:
        # Deterministic hash for consistent experience
        hash_value = hash(f"{flag.name}:{tenant_id}") % 100
        if hash_value < flag.rollout_percentage:
            return True

    # 3. Return default
    return flag.default_value
```

---

### 6. Concurrent Tenant Modifications

**Scenario**: Two admins edit same tenant simultaneously.

**Behavior**:
- Optimistic locking applied
- Second save fails
- Admin must refresh and retry

**Response**:
```json
{
  "error": {
    "code": "CONCURRENT_MODIFICATION",
    "message": "Tenant was modified by another admin",
    "details": {
      "your_version": 5,
      "current_version": 6,
      "modified_by": "other@stratum.ai",
      "modified_at": "2024-01-18T14:30:00Z",
      "action": "Refresh and reapply your changes"
    }
  }
}
```

---

### 7. Audit Log Storage Full

**Scenario**: Audit log database reaches capacity.

**Behavior**:
- Alert triggered
- Old logs archived
- New logs continue writing

**Handling**:
```python
async def handle_audit_log_capacity():
    usage = await get_audit_log_storage_usage()

    if usage > 0.9:  # 90% threshold
        # Trigger alert
        await send_alert(
            severity="warning",
            message=f"Audit log storage at {usage*100}%"
        )

        # Archive logs older than 90 days
        archived = await archive_old_audit_logs(days=90)

        await create_system_log(
            event="audit_log_archived",
            details={"records_archived": archived}
        )
```

---

### 8. Admin Role Downgrade

**Scenario**: Superadmin downgrades their own role.

**Behavior**:
- Blocked if last superadmin
- Warning shown
- Confirmation required

**Response**:
```json
{
  "error": {
    "code": "LAST_SUPERADMIN",
    "message": "Cannot downgrade the last superadmin",
    "details": {
      "superadmin_count": 1,
      "action": "Create another superadmin first"
    }
  }
}
```

---

### 9. Tenant Data Export During Deletion

**Scenario**: Data export requested for tenant being deleted.

**Behavior**:
- Export allowed during grace period
- Blocked after final deletion
- Warning about timeline

**Response**:
```json
{
  "success": true,
  "data": {
    "export_id": "exp_abc123",
    "status": "processing"
  },
  "warnings": [
    "Tenant is scheduled for deletion on 2024-02-18",
    "Export must complete before deletion date"
  ]
}
```

---

### 10. System Health Check Timeout

**Scenario**: Component health check times out.

**Behavior**:
- Component marked as degraded
- Timeout logged
- Retry scheduled

**Response**:
```json
{
  "success": true,
  "data": {
    "overall_status": "degraded",
    "components": {
      "database": {
        "status": "healthy"
      },
      "redis": {
        "status": "unknown",
        "error": "Health check timeout after 5000ms"
      }
    }
  }
}
```

---

### 11. Impersonation of Another Admin

**Scenario**: Admin tries to impersonate platform admin.

**Behavior**:
- Action blocked
- Security alert triggered
- Audit logged

**Response**:
```json
{
  "error": {
    "code": "CANNOT_IMPERSONATE_ADMIN",
    "message": "Cannot impersonate platform administrators",
    "details": {
      "target_user_id": 101,
      "reason": "Target user has admin privileges"
    }
  }
}
```

---

### 12. Bulk Operation Timeout

**Scenario**: Bulk tenant update times out.

**Behavior**:
- Partial completion possible
- Results reported
- Failed items can retry

**Response**:
```json
{
  "success": false,
  "error": {
    "code": "BULK_OPERATION_PARTIAL",
    "message": "Bulk operation partially completed",
    "details": {
      "total": 50,
      "succeeded": 35,
      "failed": 5,
      "pending": 10,
      "failed_ids": [12, 45, 67, 89, 101],
      "action": "Retry failed items individually"
    }
  }
}
```

---

## Known Limitations

### 1. Single Region

**Limitation**: Admin portal runs in single region.

**Impact**: Higher latency for remote admins.

**Planned**: Multi-region deployment.

---

### 2. No Scheduled Actions

**Limitation**: Cannot schedule admin actions (e.g., future suspension).

**Impact**: Manual intervention required at scheduled time.

**Workaround**: Set calendar reminders.

---

### 3. Impersonation Duration

**Limitation**: Maximum 1-hour impersonation sessions.

**Impact**: Must restart for longer debugging.

**Mitigation**: Can start new session immediately.

---

### 4. Audit Log Search

**Limitation**: Full-text search not available.

**Impact**: Must filter by specific fields.

**Planned**: Elasticsearch integration.

---

## Error Recovery

### Admin Errors

| Error | Recovery |
|-------|----------|
| MFA lost | Another superadmin resets |
| IP locked out | Another admin updates allowlist |
| Password forgotten | Self-service reset with MFA |
| Account disabled | Superadmin reactivates |

### System Errors

| Error | Recovery |
|-------|----------|
| Health check failed | Automatic retry |
| Audit storage full | Auto-archive triggered |
| Session expired | Re-authenticate |
| Component degraded | Alert + manual intervention |

---

## Security Measures

### Access Control

```python
ROLE_PERMISSIONS = {
    AdminRole.SUPERADMIN: [
        "tenant.*",
        "user.*",
        "config.*",
        "audit.*",
        "admin.*",
    ],
    AdminRole.SUPPORT: [
        "tenant.view",
        "tenant.update",
        "user.view",
        "user.impersonate",
        "audit.view",
    ],
    AdminRole.AUDIT: [
        "tenant.view",
        "user.view",
        "audit.view",
        "health.view",
    ],
}

async def check_permission(admin: AdminUser, action: str) -> bool:
    allowed = ROLE_PERMISSIONS.get(admin.role, [])

    for pattern in allowed:
        if fnmatch.fnmatch(action, pattern):
            return True

    return False
```

### Rate Limiting

| Action | Limit | Window |
|--------|-------|--------|
| Login attempts | 5 | 15 min |
| Impersonation | 10 | 1 hour |
| Bulk operations | 5 | 1 hour |
| Exports | 5 | 1 hour |

### Monitoring

```python
ALERT_THRESHOLDS = {
    "failed_logins_1h": 10,         # Security alert
    "impersonations_1h": 5,          # Activity alert
    "tenant_suspensions_1h": 3,      # Review alert
    "config_changes_1h": 10,         # Change alert
}
```

---

## Related Documentation

- [Specification](./spec.md) - Data models and architecture
- [User Flows](./user-flows.md) - Step-by-step admin journeys
- [API Contracts](./api-contracts.md) - Admin API endpoints
