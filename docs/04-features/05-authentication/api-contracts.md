# Authentication API Contracts

## Overview

API endpoints for user authentication, registration, password management, and MFA.

**Base URL**: `/api/v1/auth`

---

## Public Endpoints

### POST /signup

Self-service signup that creates a new tenant and admin user.

#### Request

```json
{
  "email": "user@company.com",
  "password": "SecurePass123",
  "full_name": "John Doe",
  "company_name": "Acme Corp",
  "phone": "+1-555-0123"
}
```

#### Password Requirements

- Minimum 8 characters
- At least 1 uppercase letter
- At least 1 lowercase letter
- At least 1 digit

#### Response

```json
{
  "success": true,
  "data": {
    "user_id": 123,
    "email": "user@company.com",
    "message": "Account created. Please check your email to verify your account.",
    "verification_required": true
  }
}
```

---

### POST /login

Authenticate user with email and password.

#### Request

```json
{
  "email": "user@company.com",
  "password": "SecurePass123"
}
```

#### Response (No MFA)

```json
{
  "success": true,
  "data": {
    "mfa_required": false,
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 1800
  }
}
```

#### Response (MFA Required)

```json
{
  "success": true,
  "data": {
    "mfa_required": true,
    "mfa_session_token": "abc123...",
    "access_token": null,
    "refresh_token": null
  },
  "message": "MFA verification required. Use /login/mfa to complete login."
}
```

---

### POST /login/mfa

Complete login with MFA verification.

#### Request

```json
{
  "mfa_session_token": "abc123...",
  "code": "123456"
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 1800
  }
}
```

---

### POST /register

Register a new user (admin-created, requires tenant_id).

#### Request

```json
{
  "tenant_id": 1,
  "email": "newuser@company.com",
  "password": "SecurePass123",
  "full_name": "Jane Smith",
  "role": "user",
  "locale": "en",
  "timezone": "America/New_York"
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "id": 124,
    "tenant_id": 1,
    "email": "newuser@company.com",
    "full_name": "Jane Smith",
    "role": "user",
    "is_active": true,
    "is_verified": false,
    "created_at": "2024-01-15T10:00:00Z"
  }
}
```

---

### POST /refresh

Refresh access token using refresh token.

#### Request

```json
{
  "refresh_token": "eyJ..."
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 1800
  }
}
```

---

### POST /verify-email

Verify email address using token from verification email.

#### Request

```json
{
  "token": "abc123xyz789..."
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "message": "Email verified successfully"
  }
}
```

---

### POST /resend-verification

Resend email verification link.

#### Request

```json
{
  "email": "user@company.com"
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "message": "If the email exists, a verification link has been sent"
  }
}
```

---

### POST /forgot-password

Request password reset email.

#### Request

```json
{
  "email": "user@company.com"
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "message": "If the email exists, a password reset link has been sent"
  }
}
```

---

### POST /reset-password

Reset password using token from reset email.

#### Request

```json
{
  "token": "abc123xyz789...",
  "new_password": "NewSecurePass456"
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "message": "Password reset successfully"
  }
}
```

---

## WhatsApp OTP Endpoints

### POST /whatsapp/send-otp

Send WhatsApp OTP verification code.

#### Request

```json
{
  "phone_number": "+15550123456"
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "message": "Verification code sent to your WhatsApp",
    "expires_in": 300
  }
}
```

---

### POST /whatsapp/verify-otp

Verify WhatsApp OTP code.

#### Request

```json
{
  "phone_number": "+15550123456",
  "otp_code": "123456"
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "verified": true,
    "verification_token": "xyz789..."
  },
  "message": "Phone number verified successfully"
}
```

---

## Authenticated Endpoints

All endpoints below require `Authorization: Bearer {access_token}` header.

### GET /me

Get current authenticated user profile.

#### Response

```json
{
  "success": true,
  "data": {
    "id": 123,
    "tenant_id": 1,
    "email": "user@company.com",
    "full_name": "John Doe",
    "role": "admin",
    "locale": "en",
    "timezone": "America/New_York",
    "is_active": true,
    "is_verified": true,
    "last_login_at": "2024-01-15T14:30:00Z",
    "avatar_url": null,
    "created_at": "2024-01-01T10:00:00Z",
    "updated_at": "2024-01-15T14:30:00Z"
  }
}
```

---

### POST /change-password

Change password for authenticated user.

#### Request

```json
{
  "current_password": "OldSecurePass123",
  "new_password": "NewSecurePass456"
}
```

#### Response

```json
{
  "success": true,
  "data": {
    "message": "Password changed successfully"
  }
}
```

---

### POST /logout

Log out the current user.

#### Response

```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

---

## MFA Endpoints

**Base URL**: `/api/v1/mfa`

### GET /status

Get current MFA status for authenticated user.

#### Response

```json
{
  "enabled": true,
  "verified_at": "2024-01-15T10:30:00Z",
  "backup_codes_remaining": 8,
  "is_locked": false,
  "lockout_until": null
}
```

---

### POST /setup

Initiate MFA setup (returns QR code).

#### Response

```json
{
  "secret": "JBSWY3DPEHPK3PXP",
  "provisioning_uri": "otpauth://totp/Stratum%20AI:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=Stratum%20AI",
  "qr_code_base64": "iVBORw0KGgoAAAANSUhEUgAA..."
}
```

---

### POST /verify

Verify TOTP code and enable MFA.

#### Request

```json
{
  "code": "123456"
}
```

#### Response

```json
{
  "success": true,
  "message": "MFA enabled successfully. Store your backup codes securely.",
  "backup_codes": [
    "ABCD-1234",
    "EFGH-5678",
    "IJKL-9012",
    "MNOP-3456",
    "QRST-7890",
    "UVWX-1234",
    "YZAB-5678",
    "CDEF-9012",
    "GHIJ-3456",
    "KLMN-7890"
  ]
}
```

---

### POST /disable

Disable MFA (requires valid code).

#### Request

```json
{
  "code": "123456"
}
```

#### Response

```json
{
  "success": true,
  "message": "MFA has been disabled.",
  "backup_codes": []
}
```

---

### POST /backup-codes

Regenerate backup codes (requires TOTP code).

#### Request

```json
{
  "code": "123456"
}
```

#### Response

```json
{
  "success": true,
  "message": "Backup codes regenerated. Store them securely.",
  "backup_codes": [
    "ABCD-1234",
    "EFGH-5678",
    ...
  ]
}
```

---

### POST /validate

Validate MFA code during login (no auth required).

#### Request

```json
{
  "user_id": 123,
  "code": "123456"
}
```

#### Response

```json
{
  "valid": true,
  "message": "Code verified"
}
```

---

### GET /check/{user_id}

Check if MFA is required for user (no auth required).

#### Response

```json
{
  "mfa_required": true,
  "is_locked": false,
  "lockout_until": null
}
```

---

## Schemas

### LoginRequest

```typescript
interface LoginRequest {
  email: string     // Email address
  password: string  // User password
}
```

### LoginResponse

```typescript
interface LoginResponse {
  mfa_required: boolean
  mfa_session_token?: string    // Only if MFA required
  access_token?: string         // Only if MFA not required
  refresh_token?: string        // Only if MFA not required
  token_type?: string           // "bearer"
  expires_in?: number           // Seconds until expiry
}
```

### SignupRequest

```typescript
interface SignupRequest {
  email: string        // Valid email
  password: string     // Min 8, upper+lower+digit
  full_name: string    // 2-255 chars
  company_name: string // 2-255 chars
  phone?: string       // Optional, max 50 chars
}
```

### UserResponse

```typescript
interface UserResponse {
  id: number
  tenant_id: number
  email: string
  full_name?: string
  role: 'superadmin' | 'admin' | 'user' | 'viewer'
  locale: string
  timezone: string
  is_active: boolean
  is_verified: boolean
  last_login_at?: string   // ISO 8601
  avatar_url?: string
  created_at: string       // ISO 8601
  updated_at: string       // ISO 8601
}
```

### TokenResponse

```typescript
interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string       // "bearer"
  expires_in: number       // Seconds (1800 = 30 min)
}
```

### MFAStatusResponse

```typescript
interface MFAStatusResponse {
  enabled: boolean
  verified_at?: string           // ISO 8601
  backup_codes_remaining: number
  is_locked: boolean
  lockout_until?: string         // ISO 8601
}
```

---

## Error Responses

### Error Format

```json
{
  "success": false,
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Invalid email or password",
    "details": {}
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_CREDENTIALS` | 401 | Wrong email or password |
| `INVALID_TOKEN` | 401 | Token expired or invalid |
| `INVALID_TOKEN_TYPE` | 401 | Wrong token type used |
| `USER_NOT_FOUND` | 401 | User doesn't exist |
| `USER_INACTIVE` | 403 | Account is deactivated |
| `EMAIL_NOT_VERIFIED` | 403 | Email verification required |
| `EMAIL_EXISTS` | 400 | Email already registered |
| `PASSWORD_REQUIREMENTS` | 400 | Password doesn't meet requirements |
| `INVALID_OTP` | 400 | OTP code invalid or expired |
| `MFA_ALREADY_ENABLED` | 400 | MFA is already configured |
| `MFA_NOT_ENABLED` | 400 | MFA not configured |
| `MFA_SETUP_NOT_INITIATED` | 400 | Must call /setup first |
| `ACCOUNT_LOCKED` | 429 | Too many failed attempts |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| POST /login | 10/min per IP |
| POST /login/mfa | 5/min per session |
| POST /signup | 5/min per IP |
| POST /forgot-password | 3/min per IP |
| POST /whatsapp/send-otp | 3/min per phone |
| POST /whatsapp/verify-otp | 5/min per phone |
| POST /mfa/validate | 5/min per user |

---

## JWT Token Claims

### Access Token

| Claim | Description |
|-------|-------------|
| `sub` | User ID (string) |
| `exp` | Expiration timestamp |
| `iat` | Issued at timestamp |
| `type` | `"access"` |
| `tenant_id` | Tenant ID (int) |
| `role` | User role string |
| `email` | User email (convenience) |

### Refresh Token

| Claim | Description |
|-------|-------------|
| `sub` | User ID (string) |
| `exp` | Expiration timestamp |
| `iat` | Issued at timestamp |
| `type` | `"refresh"` |
| `jti` | Unique token ID |

---

## Related Documentation

- [Specification](./spec.md) - Data models and architecture
- [User Flows](./user-flows.md) - Step-by-step user journeys
- [Edge Cases](./edge-cases.md) - Error handling and edge cases
