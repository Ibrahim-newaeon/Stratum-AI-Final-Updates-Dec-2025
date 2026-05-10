# Authentication Edge Cases

## Overview

This document covers error handling, edge cases, and known limitations for the Authentication module.

---

## Edge Cases

### 1. Login with MFA During Session Expiry

**Scenario**: MFA session token expires before user enters TOTP code.

**Behavior**:
- Session token expires after 5 minutes
- Second step fails with `INVALID_SESSION`
- User must restart login flow

**Response**:
```json
{
  "error": {
    "code": "INVALID_SESSION",
    "message": "Invalid or expired MFA session. Please login again."
  }
}
```

**Recovery**: Restart from `/login` with email/password.

---

### 2. Account Lockout from MFA Failures

**Scenario**: User enters wrong TOTP code 5 times.

**Behavior**:
- Account locked for 15 minutes
- All login attempts blocked
- Lockout applies even with correct code

**Response**:
```json
{
  "error": {
    "code": "ACCOUNT_LOCKED",
    "message": "Account locked due to too many failed MFA attempts. Try again in 15 minutes.",
    "details": {
      "lockout_until": "2024-01-15T15:00:00Z",
      "remaining_minutes": 12
    }
  }
}
```

**Handling**:
```python
if user.totp_lockout_until and now < user.totp_lockout_until:
    remaining = (user.totp_lockout_until - now).seconds // 60
    raise HTTPException(429, f"Account locked. Try again in {remaining} minutes.")
```

---

### 3. Email Already Registered (Signup)

**Scenario**: User tries to signup with existing email.

**Behavior**:
- Returns generic error (prevents enumeration)
- Does not reveal if email exists

**Response**:
```json
{
  "error": {
    "code": "EMAIL_EXISTS",
    "message": "An account with this email already exists"
  }
}
```

---

### 4. Email Enumeration Prevention

**Scenario**: Attacker tries to discover valid emails.

**Mitigation**:
- `/forgot-password` always returns success
- `/resend-verification` always returns success
- Same response time for existing/non-existing emails

**Response** (regardless of email existence):
```json
{
  "success": true,
  "data": {
    "message": "If the email exists, a reset link has been sent"
  }
}
```

---

### 5. Expired Verification Token

**Scenario**: User clicks verification link after token expires.

**Behavior**:
- Token expires after 24 hours
- Link shows error page
- Option to resend verification

**Response**:
```json
{
  "error": {
    "code": "INVALID_TOKEN",
    "message": "Invalid or expired verification token",
    "details": {
      "action": "resend_verification"
    }
  }
}
```

---

### 6. Password Reset Token Reuse

**Scenario**: User tries to use reset token twice.

**Behavior**:
- Token deleted after first use
- Second attempt fails

**Response**:
```json
{
  "error": {
    "code": "INVALID_TOKEN",
    "message": "Invalid or expired reset token"
  }
}
```

---

### 7. Backup Code Exhaustion

**Scenario**: User uses all 10 backup codes.

**Behavior**:
- Backup codes cannot be used for login
- TOTP still works
- Warning shown in MFA status

**MFA Status Response**:
```json
{
  "enabled": true,
  "backup_codes_remaining": 0,
  "warning": "No backup codes remaining. Regenerate for account recovery."
}
```

**Recovery**:
1. Login with TOTP code
2. Navigate to MFA settings
3. Regenerate backup codes (requires valid TOTP)

---

### 8. Device Time Skew

**Scenario**: User's device clock is significantly off.

**Behavior**:
- TOTP allows ±1 step (30 seconds)
- Larger skew causes failures
- User sees "invalid code" repeatedly

**Mitigation**:
- Display time sync suggestion in error
- Recommend using authenticator app's time sync

**Response**:
```json
{
  "error": {
    "code": "INVALID_CODE",
    "message": "Invalid verification code. Please try again.",
    "details": {
      "hint": "Ensure your device time is synchronized"
    }
  }
}
```

---

### 9. Concurrent Login Sessions

**Scenario**: User logs in from multiple devices.

**Current Behavior**:
- All sessions valid simultaneously
- No session limit enforced
- Each device gets own tokens

**Security Note**: Production should consider:
- Session limit per user
- Notification of new logins
- Ability to revoke all sessions

---

### 10. Refresh Token After Password Change

**Scenario**: User changes password, has existing refresh token.

**Current Behavior**:
- Existing refresh tokens remain valid
- No automatic invalidation

**Recommended**:
```python
# On password change
await invalidate_all_refresh_tokens(user_id)
```

---

### 11. MFA Setup Abandoned

**Scenario**: User initiates MFA setup but never verifies.

**Behavior**:
- TOTP secret stored but not enabled
- `totp_enabled = False`
- User can restart setup anytime

**Cleanup**:
```python
# Clear pending setup on new setup request
if not user.totp_enabled and user.totp_secret:
    # Previous setup was abandoned, overwrite
    user.totp_secret = generate_new_secret()
```

---

### 12. WhatsApp OTP Rate Limiting

**Scenario**: User requests OTPs repeatedly.

**Limits**:
- 3 OTPs per phone per minute
- 10 OTPs per phone per hour

**Response**:
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many OTP requests. Please wait before trying again.",
    "details": {
      "retry_after": 60
    }
  }
}
```

---

### 13. Invalid Phone Number Format

**Scenario**: User provides malformed phone number.

**Behavior**:
- Normalize to E.164 format
- Reject if cannot normalize

**Normalization**:
```python
# Add + if missing
if not phone.startswith('+'):
    phone = '+' + phone

# Remove spaces, dashes, parentheses
phone = re.sub(r'[\s\-\(\)]', '', phone)
```

---

### 14. Token Decoded But User Deleted

**Scenario**: Valid JWT but user was deleted after issuance.

**Behavior**:
- Token decodes successfully
- User lookup fails
- Return 401 Unauthorized

**Handling**:
```python
user = await db.get(User, user_id)
if not user or user.is_deleted:
    raise HTTPException(401, "User not found or inactive")
```

---

### 15. Role Change Mid-Session

**Scenario**: Admin demotes user while they have valid token.

**Current Behavior**:
- Token contains old role
- Database has new role
- API uses token role (stale)

**Mitigation**:
- Fetch user role from DB on sensitive operations
- Or use short token expiry (30 min)

---

## Known Limitations

### 1. No Refresh Token Revocation

**Limitation**: Cannot revoke individual refresh tokens.

**Impact**: Logged-out users could technically still refresh.

**Mitigation**: Short refresh token expiry, password change invalidates all.

---

### 2. Single Authenticator App

**Limitation**: Only one TOTP secret per user.

**Impact**: Cannot have backup authenticator device with separate secret.

**Workaround**: Backup codes provide alternative access.

---

### 3. No Session Management UI

**Limitation**: Users cannot see or manage active sessions.

**Future**: Add `/me/sessions` endpoint to list/revoke sessions.

---

### 4. PII Encryption Key Rotation

**Limitation**: Key rotation requires re-encryption of all data.

**Process**:
1. Generate new key
2. Decrypt all PII with old key
3. Re-encrypt with new key
4. Update all lookup hashes
5. Deploy new key

---

## Error Recovery

### Authentication Failures

| Error | Recovery |
|-------|----------|
| Invalid credentials | Verify email/password |
| Account locked | Wait for lockout expiry |
| Token expired | Refresh or re-login |
| MFA session expired | Restart login flow |
| Email not verified | Request new verification email |

### MFA Failures

| Error | Recovery |
|-------|----------|
| Invalid TOTP | Check device time, try again |
| No backup codes | Use TOTP, regenerate codes |
| Lockout | Wait 15 minutes |
| Lost authenticator | Use backup code, reconfigure MFA |

---

## Monitoring

### Key Metrics

| Metric | Alert Threshold |
|--------|-----------------|
| Failed login rate | > 100/min |
| MFA failure rate | > 20% |
| Account lockouts | > 10/hour |
| Token refresh failures | > 5% |
| Password reset requests | > 50/hour |

### Security Alerts

| Event | Action |
|-------|--------|
| 50+ failed logins same email | Potential brute force |
| 100+ failed logins same IP | Block IP temporarily |
| Unusual login location | Send notification email |
| Password reset after failed logins | Monitor for takeover |

### Health Checks

```python
async def auth_health() -> dict:
    return {
        "status": "healthy",
        "checks": {
            "database": await check_db_connection(),
            "redis": await check_redis_connection(),
            "email_service": await check_email_service(),
            "whatsapp_service": await check_whatsapp_api(),
        }
    }
```

---

## Security Best Practices

### For Users

1. Use strong, unique passwords
2. Enable MFA immediately after signup
3. Store backup codes securely (password manager)
4. Don't share TOTP secrets
5. Use authenticator app, not SMS

### For Administrators

1. Monitor failed login patterns
2. Review lockout events
3. Implement session limits
4. Enable audit logging
5. Regular security reviews

---

## Related Documentation

- [Specification](./spec.md) - Data models and architecture
- [User Flows](./user-flows.md) - Step-by-step user journeys
- [API Contracts](./api-contracts.md) - API endpoints and schemas
