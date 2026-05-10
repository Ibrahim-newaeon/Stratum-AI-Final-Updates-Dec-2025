# Authentication & Authorization

## Overview

Stratum AI uses JWT-based authentication with optional MFA (Multi-Factor Authentication).

---

## Authentication Flow

### Standard Login

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant DB

    User->>Frontend: Enter email/password
    Frontend->>API: POST /auth/login
    API->>DB: Verify credentials
    DB-->>API: User record

    alt Password Valid
        alt MFA Enabled
            API-->>Frontend: { mfa_required: true, mfa_token: "..." }
            Frontend->>User: Enter TOTP code
            User->>Frontend: TOTP code
            Frontend->>API: POST /auth/mfa/verify
            API->>API: Verify TOTP
        end
        API->>API: Generate JWT tokens
        API-->>Frontend: { access_token, refresh_token }
    else Password Invalid
        API-->>Frontend: 401 Unauthorized
    end
```

### JWT Token Structure

**Access Token Payload:**
```json
{
  "sub": "user_id",
  "tenant_id": 1,
  "role": "admin",
  "permissions": ["read", "write"],
  "exp": 1705320000,
  "iat": 1705318200,
  "type": "access"
}
```

**Refresh Token Payload:**
```json
{
  "sub": "user_id",
  "exp": 1705924000,
  "iat": 1705318200,
  "type": "refresh"
}
```

### Token Expiration

| Token Type | Default Expiry | Configuration |
|------------|---------------|---------------|
| Access Token | 30 minutes | `ACCESS_TOKEN_EXPIRE_MINUTES` |
| Refresh Token | 7 days | `REFRESH_TOKEN_EXPIRE_DAYS` |
| Email Verification | 24 hours | `EMAIL_VERIFICATION_EXPIRE_HOURS` |
| Password Reset | 1 hour | `PASSWORD_RESET_EXPIRE_HOURS` |

---

## Token Refresh Flow

```mermaid
sequenceDiagram
    participant Frontend
    participant API

    Frontend->>API: POST /auth/refresh
    Note right of Frontend: { refresh_token: "..." }

    API->>API: Validate refresh token

    alt Token Valid
        API->>API: Generate new access token
        API-->>Frontend: { access_token: "...", expires_in: 1800 }
    else Token Expired/Invalid
        API-->>Frontend: 401 Unauthorized
        Note right of Frontend: Redirect to login
    end
```

---

## Multi-Factor Authentication (MFA)

### Enabling MFA

```http
POST /api/v1/mfa/enable
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "secret": "JBSWY3DPEHPK3PXP",
  "qr_code_url": "otpauth://totp/Stratum:user@example.com?secret=JBSWY3DPEHPK3PXP&issuer=Stratum",
  "backup_codes": [
    "abc12345",
    "def67890",
    "ghi11223",
    "jkl44556",
    "mno77889"
  ]
}
```

### MFA Verification During Login

```http
POST /api/v1/auth/mfa/verify
```

**Request:**
```json
{
  "mfa_token": "temporary_token_from_login",
  "code": "123456"
}
```

### Backup Codes

- 5 backup codes generated on MFA enable
- Each code can only be used once
- Regenerate codes via `/api/v1/mfa/backup-codes/regenerate`

### Lockout Policy

| Condition | Action |
|-----------|--------|
| 5 failed TOTP attempts | 15-minute lockout |
| 10 failed attempts | Account locked |

---

## Role-Based Access Control (RBAC)

### Roles

| Role | Description | Scope |
|------|-------------|-------|
| `superadmin` | Platform administrator | Cross-tenant |
| `admin` | Tenant administrator | Single tenant |
| `manager` | Team manager | Single tenant |
| `analyst` | Data analyst | Single tenant |
| `viewer` | Read-only access | Single tenant |

### Role Hierarchy

```
superadmin
    └── admin
        └── manager
            └── analyst
                └── viewer
```

### Default Permissions by Role

```python
ROLE_PERMISSIONS = {
    "superadmin": ["*"],  # All permissions
    "admin": [
        "users:read", "users:write", "users:delete",
        "campaigns:read", "campaigns:write",
        "rules:read", "rules:write",
        "analytics:read",
        "settings:read", "settings:write",
    ],
    "manager": [
        "users:read",
        "campaigns:read", "campaigns:write",
        "rules:read", "rules:write",
        "analytics:read",
    ],
    "analyst": [
        "campaigns:read",
        "rules:read",
        "analytics:read",
    ],
    "viewer": [
        "campaigns:read",
        "analytics:read",
    ],
}
```

---

## API Authentication

### Bearer Token

Include in Authorization header:

```http
GET /api/v1/campaigns
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### API Keys

For server-to-server integrations:

```http
POST /api/v1/cdp/events
X-API-Key: sk_live_abc123...
```

### Creating API Keys

```http
POST /api/v1/api-keys
Authorization: Bearer {access_token}
```

**Request:**
```json
{
  "name": "Production Integration",
  "permissions": ["cdp:events:write", "cdp:profiles:read"],
  "expires_at": "2025-12-31T23:59:59Z"
}
```

**Response:**
```json
{
  "id": 1,
  "name": "Production Integration",
  "key": "sk_live_abc123...",  // Only shown once!
  "key_prefix": "sk_live_abc1",
  "permissions": ["cdp:events:write", "cdp:profiles:read"],
  "expires_at": "2025-12-31T23:59:59Z"
}
```

---

## FastAPI Dependencies

### Get Current User

```python
from app.auth.deps import get_current_user

@router.get("/me")
async def get_profile(
    current_user: User = Depends(get_current_user)
):
    return current_user
```

### Require Specific Role

```python
from app.auth.deps import require_role

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(require_role(["admin", "superadmin"]))
):
    ...
```

### Require Specific Permission

```python
from app.auth.deps import require_permission

@router.post("/campaigns")
async def create_campaign(
    campaign: CampaignCreate,
    current_user: User = Depends(require_permission("campaigns:write"))
):
    ...
```

### Get Tenant Context

```python
from app.auth.deps import get_tenant_id

@router.get("/dashboard")
async def get_dashboard(
    tenant_id: int = Depends(get_tenant_id)
):
    # tenant_id is extracted from JWT
    ...
```

---

## Password Security

### Requirements

- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character

### Hashing

Passwords are hashed using bcrypt:

```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Hash password
hashed = pwd_context.hash("password123")

# Verify password
is_valid = pwd_context.verify("password123", hashed)
```

---

## OAuth Integrations

### Supported Platforms

| Platform | OAuth Type | Scopes |
|----------|------------|--------|
| Meta | OAuth 2.0 | `ads_management`, `ads_read` |
| Google | OAuth 2.0 | `https://www.googleapis.com/auth/adwords` |
| TikTok | OAuth 2.0 | `advertiser_management` |
| Snapchat | OAuth 2.0 | `snapchat-marketing-api` |

### OAuth Flow

```mermaid
sequenceDiagram
    participant User
    participant Frontend
    participant API
    participant Platform

    User->>Frontend: Click "Connect Platform"
    Frontend->>API: GET /oauth/{platform}/authorize
    API-->>Frontend: Redirect URL
    Frontend->>Platform: Redirect to OAuth
    Platform->>User: Authorize app
    User->>Platform: Approve
    Platform->>API: Callback with code
    API->>Platform: Exchange code for token
    Platform-->>API: Access + Refresh tokens
    API->>API: Store encrypted tokens
    API-->>Frontend: Redirect to success page
```

### Token Storage

OAuth tokens are encrypted at rest using AES-256:

```python
from app.core.security import encrypt_token, decrypt_token

# Store token
encrypted = encrypt_token(access_token)
connection.access_token = encrypted

# Retrieve token
decrypted = decrypt_token(connection.access_token)
```

---

## Security Best Practices

### Token Security

1. **Never log tokens** - Use structured logging that excludes sensitive fields
2. **HTTPS only** - All endpoints require HTTPS in production
3. **Secure cookies** - Set `httpOnly`, `secure`, `sameSite` flags

### Rate Limiting

| Endpoint | Limit |
|----------|-------|
| `/auth/login` | 5 requests/minute per IP |
| `/auth/mfa/verify` | 5 requests/minute per user |
| Other endpoints | 100 requests/minute per user |

### Audit Logging

All authentication events are logged:

```python
audit_log.create(
    action="login",
    user_id=user.id,
    ip_address=request.client.host,
    user_agent=request.headers.get("user-agent"),
    metadata={"mfa_used": True}
)
```

---

## Session Management

### Protected User Flag

Users with `is_protected=True` cannot be:
- Deleted
- Demoted from admin role
- Deactivated

Used for root admin accounts.

### Account Lockout

| Condition | Action |
|-----------|--------|
| 5 failed login attempts | 15-minute lockout |
| 10 failed login attempts | Account locked, admin intervention required |

### Token Revocation

Tokens can be revoked by:
1. Logout endpoint (invalidates refresh token)
2. Password change (invalidates all tokens)
3. Admin action (user deactivation)
