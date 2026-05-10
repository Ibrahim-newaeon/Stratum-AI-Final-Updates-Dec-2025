# Security Practices

## Overview

This document outlines security practices, policies, and guidelines for the Stratum AI platform.

---

## Security Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    SECURITY ARCHITECTURE                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                   PERIMETER LAYER                         │  │
│  │                                                          │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │  │
│  │  │   WAF    │ │  DDoS    │ │   CDN    │ │Rate Limit│   │  │
│  │  │ Cloudflare│ │Protection│ │  Cache   │ │ (API)   │   │  │
│  │  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘   │  │
│  └───────┼────────────┼────────────┼────────────┼──────────┘  │
│          │            │            │            │              │
│          └────────────┴─────┬──────┴────────────┘              │
│                             ▼                                   │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  APPLICATION LAYER                        │  │
│  │                                                          │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │  │
│  │  │   Auth   │ │  RBAC    │ │  Input   │ │  Audit   │   │  │
│  │  │  (JWT)   │ │  Perms   │ │Validation│ │  Logging │   │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                    DATA LAYER                             │  │
│  │                                                          │  │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐   │  │
│  │  │Encryption│ │  Tenant  │ │   PII    │ │  Backup  │   │  │
│  │  │ at Rest  │ │ Isolation│ │ Handling │ │Encryption│   │  │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘   │  │
│  └──────────────────────────────────────────────────────────┘  │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Authentication

### JWT Configuration

```python
JWT_CONFIG = {
    "algorithm": "RS256",           # Asymmetric signing
    "access_token_expire": 900,     # 15 minutes
    "refresh_token_expire": 604800, # 7 days
    "issuer": "stratum.ai",
    "audience": "stratum-api",
}
```

### Token Structure

```json
{
  "header": {
    "alg": "RS256",
    "typ": "JWT",
    "kid": "key-2024-01"
  },
  "payload": {
    "sub": "user:123",
    "tenant_id": 1,
    "roles": ["admin"],
    "permissions": ["campaigns:write", "analytics:read"],
    "iat": 1705584000,
    "exp": 1705584900,
    "iss": "stratum.ai",
    "aud": "stratum-api"
  }
}
```

### Multi-Factor Authentication

- TOTP-based (Google Authenticator, Authy)
- Required for admin accounts
- Optional for tenant users
- Backup codes available

```python
MFA_CONFIG = {
    "issuer": "Stratum AI",
    "digits": 6,
    "period": 30,
    "algorithm": "SHA1",
    "backup_codes_count": 10,
}
```

---

## Authorization

### Role-Based Access Control

```python
ROLES = {
    "owner": {
        "description": "Full tenant access",
        "permissions": ["*"],
    },
    "admin": {
        "description": "Administrative access",
        "permissions": [
            "users:*",
            "campaigns:*",
            "analytics:*",
            "settings:*",
            "integrations:*",
        ],
    },
    "manager": {
        "description": "Campaign management",
        "permissions": [
            "campaigns:*",
            "analytics:read",
            "integrations:read",
        ],
    },
    "analyst": {
        "description": "Read-only analytics",
        "permissions": [
            "campaigns:read",
            "analytics:read",
        ],
    },
}
```

### Permission Checking

```python
from functools import wraps
from fastapi import HTTPException, Depends

def require_permission(permission: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user=Depends(get_current_user), **kwargs):
            if not has_permission(current_user, permission):
                raise HTTPException(
                    status_code=403,
                    detail=f"Permission denied: {permission}"
                )
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator

@router.delete("/campaigns/{id}")
@require_permission("campaigns:delete")
async def delete_campaign(id: int, current_user: User):
    ...
```

---

## Data Protection

### Encryption at Rest

| Data Type | Encryption | Key Management |
|-----------|------------|----------------|
| Database | AES-256 (RDS) | AWS KMS |
| File storage | AES-256 (S3) | AWS KMS |
| Backups | AES-256 | AWS KMS |
| Redis | TLS + Auth | AWS Secrets Manager |

### Encryption in Transit

- TLS 1.3 required for all connections
- HSTS enabled with 1-year max-age
- Certificate pinning for mobile apps

```nginx
# Nginx TLS configuration
ssl_protocols TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
ssl_prefer_server_ciphers off;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```

### PII Handling

```python
class PIIHandler:
    """Handles PII data with appropriate security measures."""

    SENSITIVE_FIELDS = ["email", "phone", "address", "ssn", "ip_address"]

    @staticmethod
    def hash_for_matching(value: str) -> str:
        """Hash PII for platform matching (e.g., CAPI)."""
        normalized = value.lower().strip()
        return hashlib.sha256(normalized.encode()).hexdigest()

    @staticmethod
    def mask_for_display(value: str, field_type: str) -> str:
        """Mask PII for UI display."""
        if field_type == "email":
            parts = value.split("@")
            return f"{parts[0][:2]}***@{parts[1]}"
        elif field_type == "phone":
            return f"***-***-{value[-4:]}"
        return "***"

    @staticmethod
    def encrypt_for_storage(value: str) -> bytes:
        """Encrypt PII for database storage."""
        from cryptography.fernet import Fernet
        return Fernet(settings.ENCRYPTION_KEY).encrypt(value.encode())
```

---

## Tenant Isolation

### Database Isolation

```python
# Row-level security via tenant_id
class TenantMixin:
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False, index=True)

# Query filtering
def get_campaigns(tenant_id: int) -> list[Campaign]:
    return db.query(Campaign).filter(Campaign.tenant_id == tenant_id).all()

# Middleware enforcement
@app.middleware("http")
async def tenant_isolation_middleware(request: Request, call_next):
    tenant_id = get_tenant_from_token(request)
    request.state.tenant_id = tenant_id

    # Inject tenant filter into all queries
    with tenant_context(tenant_id):
        response = await call_next(request)

    return response
```

### Resource Isolation

| Resource | Isolation Method |
|----------|------------------|
| Database | Tenant ID column + RLS |
| Redis | Key prefix: `tenant:{id}:` |
| Files | S3 prefix: `tenants/{id}/` |
| Logs | Tenant ID label |

---

## Input Validation

### API Request Validation

```python
from pydantic import BaseModel, validator, EmailStr
from typing import Optional
import re

class CreateUserRequest(BaseModel):
    email: EmailStr
    name: str
    phone: Optional[str] = None

    @validator("name")
    def validate_name(cls, v):
        if len(v) < 2 or len(v) > 100:
            raise ValueError("Name must be 2-100 characters")
        if not re.match(r"^[\w\s\-\.]+$", v):
            raise ValueError("Name contains invalid characters")
        return v.strip()

    @validator("phone")
    def validate_phone(cls, v):
        if v is None:
            return v
        # E.164 format
        if not re.match(r"^\+[1-9]\d{1,14}$", v):
            raise ValueError("Invalid phone number format")
        return v
```

### SQL Injection Prevention

```python
# Always use parameterized queries
from sqlalchemy import text

# GOOD
result = db.execute(
    text("SELECT * FROM users WHERE email = :email"),
    {"email": user_email}
)

# BAD - Never do this
# result = db.execute(f"SELECT * FROM users WHERE email = '{user_email}'")
```

### XSS Prevention

```python
import bleach

def sanitize_html(content: str) -> str:
    """Sanitize HTML content to prevent XSS."""
    allowed_tags = ["p", "br", "strong", "em", "ul", "ol", "li"]
    allowed_attrs = {}
    return bleach.clean(content, tags=allowed_tags, attributes=allowed_attrs)
```

---

## Secrets Management

### Secret Storage

| Secret Type | Storage | Rotation |
|-------------|---------|----------|
| JWT signing keys | AWS Secrets Manager | Monthly |
| Database credentials | AWS Secrets Manager | Quarterly |
| API keys | AWS Secrets Manager | On demand |
| Encryption keys | AWS KMS | Annually |

### Environment Variables

```python
# settings.py
from pydantic import BaseSettings

class Settings(BaseSettings):
    # Never log or expose these
    DATABASE_URL: str
    JWT_SECRET_KEY: str
    ENCRYPTION_KEY: str
    STRIPE_SECRET_KEY: str

    class Config:
        env_file = ".env"
        # Prevent secrets from appearing in logs
        fields = {
            "DATABASE_URL": {"env": "DATABASE_URL"},
            "JWT_SECRET_KEY": {"env": "JWT_SECRET_KEY", "repr": False},
            "ENCRYPTION_KEY": {"env": "ENCRYPTION_KEY", "repr": False},
            "STRIPE_SECRET_KEY": {"env": "STRIPE_SECRET_KEY", "repr": False},
        }
```

---

## Audit Logging

### Events Logged

| Category | Events |
|----------|--------|
| Authentication | Login, logout, MFA, password change |
| Authorization | Permission denied, role change |
| Data access | PII access, export, bulk operations |
| Admin actions | User management, tenant changes |
| Security events | Failed logins, suspicious activity |

### Log Format

```python
audit_logger.info(
    "security_event",
    event_type="user_login",
    user_id=user.id,
    tenant_id=user.tenant_id,
    ip_address=request.client.host,
    user_agent=request.headers.get("user-agent"),
    success=True,
    mfa_used=True,
    timestamp=datetime.now(timezone.utc).isoformat(),
)
```

### Log Retention

| Log Type | Hot Storage | Cold Storage | Total Retention |
|----------|-------------|--------------|-----------------|
| Security events | 90 days | 7 years | 7 years |
| Access logs | 30 days | 1 year | 1 year |
| Application logs | 14 days | 90 days | 90 days |

---

## Vulnerability Management

### Dependency Scanning

```yaml
# GitHub Actions workflow
- name: Security Scan
  uses: snyk/actions/python@master
  env:
    SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
  with:
    args: --severity-threshold=high

- name: SAST Scan
  uses: github/codeql-action/analyze@v2
  with:
    languages: python, javascript
```

### Penetration Testing

- Annual third-party penetration test
- Quarterly automated scanning
- Bug bounty program (planned)

### Patch Management

| Severity | Response Time | Deployment |
|----------|---------------|------------|
| Critical (CVSS 9+) | < 24 hours | Immediate |
| High (CVSS 7-8.9) | < 7 days | Next release |
| Medium (CVSS 4-6.9) | < 30 days | Scheduled |
| Low (CVSS < 4) | < 90 days | Backlog |

---

## Security Headers

```python
# FastAPI security headers middleware
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' https://js.stripe.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://api.stripe.com; "
        "frame-src https://js.stripe.com;"
    )
    response.headers["Permissions-Policy"] = (
        "geolocation=(), microphone=(), camera=()"
    )

    return response
```

---

## Incident Response

### Security Incident Types

| Type | Severity | Response |
|------|----------|----------|
| Data breach | Critical | Immediate escalation, legal notification |
| Account compromise | High | Account lockdown, investigation |
| DDoS attack | High | WAF rules, scaling |
| Vulnerability discovered | Varies | Patch and monitor |

### Response Procedure

1. **Detect**: Alert triggered or report received
2. **Contain**: Isolate affected systems
3. **Investigate**: Determine scope and cause
4. **Eradicate**: Remove threat
5. **Recover**: Restore services
6. **Report**: Document and notify (if required)

### Notification Requirements

| Regulation | Notification Deadline |
|------------|----------------------|
| GDPR | 72 hours |
| CCPA | "Without unreasonable delay" |
| SOC 2 | Per incident response plan |

---

## Compliance

### Standards

| Standard | Status | Last Audit |
|----------|--------|------------|
| SOC 2 Type II | Compliant | Q4 2024 |
| GDPR | Compliant | Ongoing |
| CCPA | Compliant | Ongoing |
| PCI DSS | N/A (via Stripe) | - |

### Data Processing

- Data Processing Agreement (DPA) available
- Sub-processor list maintained
- Privacy policy published
- Cookie consent implemented

---

## Security Checklist

### Development

- [ ] Input validation on all endpoints
- [ ] Parameterized queries only
- [ ] Sensitive data encrypted
- [ ] No secrets in code
- [ ] Dependencies scanned
- [ ] Code review completed

### Deployment

- [ ] TLS configured correctly
- [ ] Security headers set
- [ ] Secrets rotated
- [ ] Access logs enabled
- [ ] Monitoring configured
- [ ] Backup verified

### Operations

- [ ] Access reviewed quarterly
- [ ] Patches applied timely
- [ ] Audit logs reviewed
- [ ] Incident response tested
- [ ] Security training completed

---

## Related Documentation

- [Monitoring](../05-operations/monitoring.md) - Security monitoring
- [Incidents](../05-operations/incidents.md) - Incident response
- [Authentication](../04-features/05-authentication/spec.md) - Auth implementation
