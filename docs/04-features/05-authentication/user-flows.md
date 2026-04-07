# Authentication User Flows

## Overview

Step-by-step user journeys for authentication, registration, password management, and MFA configuration.

---

## Flow 1: Self-Service Signup

**Actor**: New user without existing account

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                   SELF-SERVICE SIGNUP                           │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Navigate to /signup                                         │
│                                                                 │
│  2. Fill signup form:                                           │
│     ├─► Email: user@company.com                                │
│     ├─► Password: (min 8 chars, upper, lower, digit)           │
│     ├─► Full name: John Doe                                    │
│     ├─► Company name: Acme Corp                                │
│     └─► Phone: +1-555-0123 (optional)                          │
│                                                                 │
│  3. Submit form                                                 │
│     └─► POST /api/v1/auth/signup                               │
│                                                                 │
│  4. System creates:                                             │
│     ├─► New tenant (organization)                              │
│     ├─► New user as tenant admin                               │
│     └─► Sends verification email                               │
│                                                                 │
│  5. User receives response:                                     │
│     ├─► user_id                                                │
│     ├─► message: "Check email to verify"                       │
│     └─► verification_required: true                            │
│                                                                 │
│  6. User checks email                                           │
│     └─► Clicks verification link                               │
│                                                                 │
│  7. Email verified                                              │
│     ├─► is_verified = true                                     │
│     └─► Welcome email sent                                     │
│                                                                 │
│  8. User can now login                                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Sequence Diagram

```
User            Frontend           API              Redis        Email
 │                │                 │                 │            │
 │  Fill form     │                 │                 │            │
 │───────────────►│                 │                 │            │
 │                │ POST /signup    │                 │            │
 │                │────────────────►│                 │            │
 │                │                 │ Check email     │            │
 │                │                 │ uniqueness      │            │
 │                │                 │                 │            │
 │                │                 │ Create tenant   │            │
 │                │                 │ Create user     │            │
 │                │                 │                 │            │
 │                │                 │ Store token     │            │
 │                │                 │────────────────►│            │
 │                │                 │                 │            │
 │                │                 │ Send email      │            │
 │                │                 │────────────────────────────►│
 │                │◄────────────────│                 │            │
 │◄───────────────│                 │                 │            │
 │                │                 │                 │            │
 │  Click link    │                 │                 │            │
 │───────────────►│ POST /verify-email              │            │
 │                │────────────────►│                 │            │
 │                │                 │ Validate token  │            │
 │                │                 │────────────────►│            │
 │                │                 │◄────────────────│            │
 │                │                 │ Mark verified   │            │
 │                │◄────────────────│                 │            │
 │◄───────────────│ Verified!       │                 │            │
```

---

## Flow 2: Login (Without MFA)

**Actor**: Registered user with MFA disabled

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                   LOGIN (NO MFA)                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Navigate to /login                                          │
│                                                                 │
│  2. Enter credentials:                                          │
│     ├─► Email: user@company.com                                │
│     └─► Password: ********                                     │
│                                                                 │
│  3. Submit login                                                │
│     └─► POST /api/v1/auth/login                                │
│                                                                 │
│  4. Server validates:                                           │
│     ├─► Hash email for lookup                                  │
│     ├─► Find user by email_hash                                │
│     ├─► Verify password (bcrypt)                               │
│     └─► Check MFA status                                       │
│                                                                 │
│  5. MFA not enabled → direct tokens                             │
│     ├─► Update last_login_at                                   │
│     ├─► Create audit log entry                                 │
│     └─► Return tokens                                          │
│                                                                 │
│  6. User receives:                                              │
│     {                                                           │
│       "mfa_required": false,                                    │
│       "access_token": "eyJ...",                                │
│       "refresh_token": "eyJ...",                               │
│       "expires_in": 1800                                        │
│     }                                                           │
│                                                                 │
│  7. Store tokens in client                                      │
│     └─► Access subsequent protected routes                     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Flow 3: Login (With MFA)

**Actor**: Registered user with MFA enabled

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                   LOGIN WITH MFA                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  STEP 1: Password Authentication                                │
│  ──────────────────────────────                                 │
│  1. Enter email + password                                      │
│     └─► POST /api/v1/auth/login                                │
│                                                                 │
│  2. Server validates credentials                                │
│                                                                 │
│  3. MFA enabled → return session token                          │
│     {                                                           │
│       "mfa_required": true,                                     │
│       "mfa_session_token": "abc123..."                         │
│     }                                                           │
│                                                                 │
│  4. Session stored in Redis (5 min expiry)                      │
│     Key: mfa_session:{token}                                    │
│     Value: {user_id}:{tenant_id}:{email}                       │
│                                                                 │
│  STEP 2: TOTP Verification                                      │
│  ────────────────────────                                       │
│  5. Open authenticator app                                      │
│     └─► Get 6-digit code                                       │
│                                                                 │
│  6. Enter TOTP code                                             │
│     └─► POST /api/v1/auth/login/mfa                            │
│     {                                                           │
│       "mfa_session_token": "abc123...",                        │
│       "code": "123456"                                         │
│     }                                                           │
│                                                                 │
│  7. Server validates:                                           │
│     ├─► Retrieve session from Redis                            │
│     ├─► Delete session (single use)                            │
│     └─► Verify TOTP code                                       │
│                                                                 │
│  8. Success → return JWT tokens                                 │
│     {                                                           │
│       "access_token": "eyJ...",                                │
│       "refresh_token": "eyJ...",                               │
│       "expires_in": 1800                                        │
│     }                                                           │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### State Diagram

```
┌─────────────────┐
│   Enter creds   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Verify password │
└────────┬────────┘
         │
    ┌────┴────┐
    │ MFA?    │
    └────┬────┘
         │
    ┌────┴────┐         ┌─────────────────┐
    │  Yes    │────────►│ Return session  │
    └─────────┘         │     token       │
         │              └────────┬────────┘
         │                       │
    ┌────┴────┐                  ▼
    │   No    │         ┌─────────────────┐
    └────┬────┘         │  Enter TOTP     │
         │              └────────┬────────┘
         │                       │
         │                       ▼
         │              ┌─────────────────┐
         │              │  Verify code    │
         │              └────────┬────────┘
         │                       │
         └───────────────┬───────┘
                         │
                         ▼
                ┌─────────────────┐
                │  Return tokens  │
                └─────────────────┘
```

---

## Flow 4: Enable MFA

**Actor**: Authenticated user without MFA

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                      ENABLE MFA                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Navigate to Security Settings                               │
│     └─► /settings/security                                     │
│                                                                 │
│  2. Click "Enable Two-Factor Authentication"                    │
│                                                                 │
│  3. Initiate setup                                              │
│     └─► POST /api/v1/mfa/setup                                 │
│                                                                 │
│  4. Server returns:                                             │
│     {                                                           │
│       "secret": "JBSWY3DPEHPK3PXP",                            │
│       "provisioning_uri": "otpauth://totp/...",                │
│       "qr_code_base64": "iVBORw0KGgo..."                       │
│     }                                                           │
│                                                                 │
│  5. Display setup screen:                                       │
│     ├─► QR code image                                          │
│     ├─► Manual entry code                                      │
│     └─► Code verification field                                │
│                                                                 │
│  6. User scans QR with authenticator app                        │
│     ├─► Google Authenticator                                   │
│     ├─► Authy                                                  │
│     ├─► 1Password                                              │
│     └─► etc.                                                   │
│                                                                 │
│  7. Enter 6-digit code from app                                 │
│     └─► POST /api/v1/mfa/verify                                │
│     {                                                           │
│       "code": "123456"                                         │
│     }                                                           │
│                                                                 │
│  8. Server enables MFA and returns backup codes:                │
│     {                                                           │
│       "success": true,                                          │
│       "backup_codes": [                                         │
│         "ABCD-1234",                                           │
│         "EFGH-5678",                                           │
│         ...                                                     │
│       ]                                                         │
│     }                                                           │
│                                                                 │
│  9. IMPORTANT: Display backup codes                             │
│     ├─► User must save these                                   │
│     ├─► Only shown once                                        │
│     └─► Can be used if device lost                             │
│                                                                 │
│ 10. MFA is now active                                           │
│     └─► Next login requires TOTP                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Flow 5: Forgot Password

**Actor**: User who forgot their password

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                   FORGOT PASSWORD                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Click "Forgot Password" on login page                       │
│     └─► Navigate to /forgot-password                           │
│                                                                 │
│  2. Enter email address                                         │
│     └─► POST /api/v1/auth/forgot-password                      │
│                                                                 │
│  3. Server ALWAYS responds with:                                │
│     "If the email exists, a reset link has been sent"          │
│     (Prevents email enumeration)                                │
│                                                                 │
│  4. If email exists:                                            │
│     ├─► Generate reset token                                   │
│     ├─► Store in Redis (1 hour expiry)                         │
│     └─► Send reset email                                       │
│                                                                 │
│  5. User clicks link in email                                   │
│     └─► /reset-password?token=abc123...                        │
│                                                                 │
│  6. Enter new password (twice for confirmation)                 │
│     └─► POST /api/v1/auth/reset-password                       │
│     {                                                           │
│       "token": "abc123...",                                    │
│       "new_password": "NewSecurePass123"                       │
│     }                                                           │
│                                                                 │
│  7. Server validates:                                           │
│     ├─► Token exists and not expired                           │
│     ├─► Password meets requirements                            │
│     ├─► Delete token (single use)                              │
│     └─► Update password hash                                   │
│                                                                 │
│  8. Password reset complete                                     │
│     └─► Redirect to login                                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Flow 6: Change Password

**Actor**: Authenticated user wanting to change password

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                   CHANGE PASSWORD                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Navigate to Security Settings                               │
│     └─► /settings/security                                     │
│                                                                 │
│  2. Click "Change Password"                                     │
│                                                                 │
│  3. Fill form:                                                  │
│     ├─► Current password: ********                             │
│     ├─► New password: **********                               │
│     └─► Confirm new password: **********                       │
│                                                                 │
│  4. Submit                                                      │
│     └─► POST /api/v1/auth/change-password                      │
│     {                                                           │
│       "current_password": "...",                               │
│       "new_password": "..."                                    │
│     }                                                           │
│                                                                 │
│  5. Server validates:                                           │
│     ├─► Current password correct                               │
│     ├─► New password meets requirements                        │
│     └─► Update password hash                                   │
│                                                                 │
│  6. Password changed successfully                               │
│     └─► Current session remains valid                          │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Flow 7: Token Refresh

**Actor**: Client with expiring access token

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                   TOKEN REFRESH                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Access token expires (30 min)                               │
│     └─► API returns 401 Unauthorized                           │
│                                                                 │
│  2. Client sends refresh token                                  │
│     └─► POST /api/v1/auth/refresh                              │
│     {                                                           │
│       "refresh_token": "eyJ..."                                │
│     }                                                           │
│                                                                 │
│  3. Server validates:                                           │
│     ├─► Token not expired (7 days)                             │
│     ├─► Token type is "refresh"                                │
│     ├─► User still exists and active                           │
│     └─► Generate new token pair                                │
│                                                                 │
│  4. Response:                                                   │
│     {                                                           │
│       "access_token": "eyJ...",                                │
│       "refresh_token": "eyJ...",                               │
│       "expires_in": 1800                                        │
│     }                                                           │
│                                                                 │
│  5. Client updates stored tokens                                │
│     └─► Retry original request                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Flow 8: WhatsApp OTP Verification

**Actor**: User verifying phone during registration

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                WHATSAPP OTP VERIFICATION                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Enter phone number                                          │
│     └─► +1-555-0123                                            │
│                                                                 │
│  2. Request OTP                                                 │
│     └─► POST /api/v1/auth/whatsapp/send-otp                    │
│     {                                                           │
│       "phone_number": "+15550123"                              │
│     }                                                           │
│                                                                 │
│  3. Server:                                                     │
│     ├─► Generate 6-digit OTP                                   │
│     ├─► Store in Redis (5 min expiry)                          │
│     └─► Send via WhatsApp template                             │
│                                                                 │
│  4. User receives WhatsApp message:                             │
│     "Your Stratum AI verification code is: 123456"             │
│                                                                 │
│  5. Enter OTP code                                              │
│     └─► POST /api/v1/auth/whatsapp/verify-otp                  │
│     {                                                           │
│       "phone_number": "+15550123",                             │
│       "otp_code": "123456"                                     │
│     }                                                           │
│                                                                 │
│  6. Server validates:                                           │
│     ├─► OTP matches stored value                               │
│     ├─► OTP not expired                                        │
│     └─► Delete OTP (single use)                                │
│                                                                 │
│  7. Response:                                                   │
│     {                                                           │
│       "verified": true,                                         │
│       "verification_token": "xyz789..."                        │
│     }                                                           │
│                                                                 │
│  8. Include token in registration                               │
│     └─► Phone marked as verified                               │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Flow 9: Logout

**Actor**: Authenticated user

### Steps

```
┌─────────────────────────────────────────────────────────────────┐
│                       LOGOUT                                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. Click "Logout" in app                                       │
│                                                                 │
│  2. Send request                                                │
│     └─► POST /api/v1/auth/logout                               │
│     (with Authorization header)                                 │
│                                                                 │
│  3. Server:                                                     │
│     ├─► Extract user from token                                │
│     └─► Create audit log (LOGOUT)                              │
│                                                                 │
│  4. Client:                                                     │
│     ├─► Clear stored tokens                                    │
│     └─► Redirect to login                                      │
│                                                                 │
│  Note: In production, refresh token should be                   │
│  invalidated server-side (token blacklist)                      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Related Documentation

- [Specification](./spec.md) - Data models and architecture
- [API Contracts](./api-contracts.md) - API endpoints and schemas
- [Edge Cases](./edge-cases.md) - Error handling and edge cases
