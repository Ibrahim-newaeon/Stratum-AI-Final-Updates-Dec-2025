# Authentication Specification

## Overview

The Authentication module provides secure user authentication including JWT-based sessions, multi-factor authentication (TOTP), password management, email verification, and WhatsApp OTP verification. All PII is encrypted at rest with GDPR-compliant practices.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                  AUTHENTICATION ARCHITECTURE                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    CLIENT REQUEST                         │  │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐     │  │
│  │  │   Login      │ │   Signup     │ │   Refresh    │     │  │
│  │  │  (email/pw)  │ │  (new user)  │ │   (token)    │     │  │
│  │  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘     │  │
│  └─────────┼────────────────┼────────────────┼─────────────┘  │
│            │                │                │                 │
│            └────────────────┴────────────────┘                 │
│                            │                                   │
│                            ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │               AUTHENTICATION SERVICE                      │  │
│  │                                                          │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │  │
│  │  │  Password   │  │    MFA      │  │    JWT      │      │  │
│  │  │ Verification│  │   (TOTP)    │  │   Tokens    │      │  │
│  │  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘      │  │
│  │         │                │                │              │  │
│  │         └────────────────┴────────────────┘              │  │
│  │                            │                              │  │
│  └────────────────────────────┼──────────────────────────────┘  │
│                               │                                 │
│         ┌─────────────────────┼─────────────────────┐          │
│         ▼                     ▼                     ▼          │
│  ┌───────────┐         ┌───────────┐         ┌───────────┐    │
│  │ PostgreSQL│         │   Redis   │         │  Email    │    │
│  │   Users   │         │   OTPs    │         │  Service  │    │
│  │  (PII enc)│         │  Sessions │         │           │    │
│  └───────────┘         └───────────┘         └───────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Authentication Flows

### Login Flow (with MFA)

```
┌────────────┐      ┌────────────┐      ┌────────────┐
│   Client   │      │    API     │      │  Database  │
└─────┬──────┘      └─────┬──────┘      └─────┬──────┘
      │                   │                   │
      │ POST /login       │                   │
      │ {email, password} │                   │
      │──────────────────►│                   │
      │                   │ Lookup by hash    │
      │                   │──────────────────►│
      │                   │◄──────────────────│
      │                   │                   │
      │                   │ Verify password   │
      │                   │ (bcrypt)          │
      │                   │                   │
      │                   │ Check MFA enabled │
      │                   │──────────────────►│
      │                   │◄──────────────────│
      │                   │                   │
      │ IF MFA disabled:  │                   │
      │ {access_token,    │                   │
      │  refresh_token}   │                   │
      │◄──────────────────│                   │
      │                   │                   │
      │ IF MFA enabled:   │                   │
      │ {mfa_required,    │                   │
      │  mfa_session_token}│                  │
      │◄──────────────────│                   │
      │                   │                   │
      │ POST /login/mfa   │                   │
      │ {mfa_session, code}│                  │
      │──────────────────►│                   │
      │                   │ Verify TOTP       │
      │                   │──────────────────►│
      │ {access_token,    │◄──────────────────│
      │  refresh_token}   │                   │
      │◄──────────────────│                   │
      │                   │                   │
```

---

## Data Models

### User Model

```python
class User:
    id: int                         # Primary key
    tenant_id: int                  # Tenant association

    # PII (encrypted at rest)
    email: str                      # Fernet encrypted
    email_hash: str                 # SHA256 for lookup
    full_name: str | None           # Fernet encrypted
    phone: str | None               # Fernet encrypted

    # Authentication
    password_hash: str              # bcrypt hash
    role: UserRole                  # admin, user, superadmin
    permissions: dict | None        # Custom permissions

    # Status
    is_active: bool = True
    is_verified: bool = False       # Email verified
    is_deleted: bool = False

    # MFA fields
    totp_secret: str | None         # Encrypted TOTP secret
    totp_enabled: bool = False
    totp_verified_at: datetime | None
    backup_codes: dict | None       # {"codes": [hashed_codes]}
    failed_totp_attempts: int = 0
    totp_lockout_until: datetime | None

    # Metadata
    last_login_at: datetime | None
    avatar_url: str | None
    locale: str = "en"
    timezone: str = "UTC"

    # Timestamps
    created_at: datetime
    updated_at: datetime
```

### UserRole Enum

```python
class UserRole(str, Enum):
    SUPERADMIN = "superadmin"    # Platform-wide access
    ADMIN = "admin"              # Tenant admin
    USER = "user"                # Regular user
    VIEWER = "viewer"            # Read-only access
```

---

## JWT Token Structure

### Access Token

```python
{
    "sub": "123",                    # User ID
    "exp": 1705320600,               # Expiration timestamp
    "iat": 1705318800,               # Issued at
    "type": "access",
    "tenant_id": 1,
    "role": "admin",
    "email": "user@example.com"      # For convenience
}
```

**Expiration**: 30 minutes (configurable)

### Refresh Token

```python
{
    "sub": "123",                    # User ID
    "exp": 1706014800,               # 7 days later
    "iat": 1705318800,
    "type": "refresh",
    "jti": "unique-token-id"         # For revocation
}
```

**Expiration**: 7 days (configurable)

---

## Password Security

### Requirements

| Requirement | Minimum |
|-------------|---------|
| Length | 8 characters |
| Uppercase | 1+ |
| Lowercase | 1+ |
| Digits | 1+ |
| Special chars | Recommended |

### Hashing

- **Algorithm**: bcrypt
- **Rounds**: Auto (default ~12)
- **Salt**: Auto-generated per hash

```python
def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(
        plain.encode("utf-8"),
        hashed.encode("utf-8")
    )
```

---

## Multi-Factor Authentication (MFA)

### TOTP Configuration

| Setting | Value |
|---------|-------|
| Digits | 6 |
| Interval | 30 seconds |
| Algorithm | SHA1 |
| Issuer | "Stratum AI" |
| Valid Window | ±1 step (clock drift) |

### Backup Codes

- **Count**: 10 codes
- **Format**: XXXX-XXXX (8 alphanumeric)
- **Storage**: SHA256 hashed
- **Single use**: Marked null after use

### Account Lockout

| Setting | Value |
|---------|-------|
| Max failed attempts | 5 |
| Lockout duration | 15 minutes |

---

## PII Encryption (GDPR)

### Encryption Method

- **Algorithm**: Fernet (AES-128-CBC)
- **Key Derivation**: PBKDF2-HMAC-SHA256
- **Iterations**: 100,000
- **Salt**: Fixed per installation

### Encrypted Fields

| Field | Searchable Hash |
|-------|-----------------|
| email | ✅ email_hash |
| full_name | ❌ |
| phone | ❌ |

### Lookup Hash

```python
def hash_pii_for_lookup(value: str) -> str:
    """Create deterministic hash for searching encrypted data."""
    salted = f"{settings.pii_encryption_key}:{value}".encode("utf-8")
    return hashlib.sha256(salted).hexdigest()
```

---

## Email Verification

### Flow

1. User signs up → verification email sent
2. Email contains unique token
3. User clicks link → token validated
4. `is_verified = True`

### Token Storage

- **Storage**: Redis
- **Key**: `email_verify:{token}`
- **Value**: `{user_id}:{email}`
- **Expiry**: Configurable (default 24 hours)

---

## WhatsApp OTP Verification

### Flow

1. User requests OTP → `POST /whatsapp/send-otp`
2. 6-digit OTP sent via WhatsApp template
3. User enters OTP → `POST /whatsapp/verify-otp`
4. Returns verification token for registration

### OTP Storage

- **Storage**: Redis
- **Key**: `whatsapp_otp:{phone}`
- **Value**: 6-digit code
- **Expiry**: 5 minutes

---

## Session Management

### Redis Keys

| Key Pattern | Purpose | Expiry |
|-------------|---------|--------|
| `whatsapp_otp:{phone}` | WhatsApp OTP | 5 min |
| `email_verify:{token}` | Email verification | 24 hours |
| `password_reset:{token}` | Password reset | Configurable |
| `mfa_session:{token}` | MFA login step | 5 min |
| `phone_verified:{phone}` | Phone verification token | 30 min |

---

## Role-Based Access Control

### Permission Checking

```python
async def get_current_user(request, credentials, db) -> CurrentUser:
    # Extract and validate JWT
    # Fetch user from database
    # Store in request.state for middleware
    request.state.user_id = user.id
    request.state.tenant_id = user.tenant_id
    request.state.role = user.role.value
    request.state.permissions = list(user.permissions.keys())
```

### Role Dependencies

```python
# Require specific roles
@router.get("/admin", dependencies=[Depends(require_role(UserRole.ADMIN))])

# Require admin or superadmin
@router.get("/manage", dependencies=[Depends(require_admin())])

# Superadmin only
@router.get("/platform", dependencies=[Depends(require_superadmin())])
```

---

## Configuration

### Environment Variables

```bash
# JWT Settings
JWT_SECRET_KEY=your-secret-key-min-32-chars
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# PII Encryption
PII_ENCRYPTION_KEY=your-encryption-key

# Email Verification
EMAIL_VERIFICATION_EXPIRE_HOURS=24

# Password Reset
PASSWORD_RESET_EXPIRE_HOURS=1

# Redis
REDIS_URL=redis://localhost:6379
```

---

## Database Schema

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    tenant_id INTEGER NOT NULL REFERENCES tenants(id),

    -- PII (encrypted)
    email TEXT NOT NULL,               -- Fernet encrypted
    email_hash VARCHAR(64) NOT NULL,   -- SHA256 for lookup
    full_name TEXT,                    -- Fernet encrypted
    phone TEXT,                        -- Fernet encrypted

    -- Authentication
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'user',
    permissions JSONB,

    -- Status
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified BOOLEAN NOT NULL DEFAULT FALSE,
    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,

    -- MFA
    totp_secret TEXT,                  -- Encrypted
    totp_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    totp_verified_at TIMESTAMPTZ,
    backup_codes JSONB,
    failed_totp_attempts INTEGER NOT NULL DEFAULT 0,
    totp_lockout_until TIMESTAMPTZ,

    -- Metadata
    last_login_at TIMESTAMPTZ,
    avatar_url VARCHAR(500),
    locale VARCHAR(10) DEFAULT 'en',
    timezone VARCHAR(50) DEFAULT 'UTC',

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(tenant_id, email_hash)
);

CREATE INDEX idx_users_email_hash ON users(email_hash);
CREATE INDEX idx_users_tenant_id ON users(tenant_id);
```

---

## Audit Logging

All authentication events are logged to the `audit_logs` table:

| Action | Description |
|--------|-------------|
| `LOGIN` | Successful login |
| `LOGOUT` | User logout |
| `LOGIN_FAILED` | Failed login attempt |
| `PASSWORD_CHANGE` | Password changed |
| `PASSWORD_RESET` | Password reset completed |
| `MFA_ENABLED` | MFA turned on |
| `MFA_DISABLED` | MFA turned off |
| `MFA_FAILED` | Failed MFA attempt |

---

## Security Considerations

### Protections

1. **Password hashing**: bcrypt with auto-salt
2. **PII encryption**: Fernet (AES-128-CBC)
3. **Rate limiting**: Per-IP and per-user
4. **Account lockout**: After failed MFA attempts
5. **Token expiration**: Short-lived access tokens
6. **Secure token generation**: `secrets` module
7. **Timing-safe comparison**: For sensitive operations

### Attack Mitigations

| Attack | Mitigation |
|--------|------------|
| Brute force | Account lockout, rate limiting |
| Credential stuffing | Unique salts, bcrypt |
| Token theft | Short expiry, refresh rotation |
| Email enumeration | Consistent responses |
| TOTP replay | Single-use codes, time window |

---

## Related Documentation

- [User Flows](./user-flows.md) - Step-by-step user journeys
- [API Contracts](./api-contracts.md) - API endpoints and schemas
- [Edge Cases](./edge-cases.md) - Error handling and edge cases
