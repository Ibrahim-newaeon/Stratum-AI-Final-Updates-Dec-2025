# Phase 6 — Auth & Security

## 1. Authentication Flow

1. POST `/api/v1/auth/login` → access + refresh JWT (public)
2. MFA: POST `/api/v1/auth/login/mfa` with challenge token (public)
3. Refresh: POST `/api/v1/auth/refresh` (public)
4. Subsequent requests: `Authorization: Bearer <access>` processed by TenantMiddleware

Token claims include `type: access|refresh`, `sub`, `exp`, `iat`; refresh includes `jti` (`security.py:98-144`).

## 2. Authorization

- **Role/permission:** `require_permission()` factory (`security.py:549-578`) — superadmin bypass
- **Superadmin:** router-level `require_super_admin` (`api/v1/__init__.py:79`)
- **Tenant isolation:** path/body `tenant_id` compared to `request.state.tenant_id` (e.g. `qa_fixes.py:76-77`)

## 3. Session Revocation

| Mechanism | Implementation |
|-----------|----------------|
| Per-token jti blacklist | Redis `token_blacklist:{jti}` |
| User-wide cutoff | Redis `user_revoked_at:{user_id}` |
| Fail mode | Closed → 503 if Redis down (`tenant.py:96-112`) |

## 4. CSRF

`CSRFMiddleware` registered (`main.py:408-409`). Unit tests: `test_csrf_middleware.py`.

## 5. Rate Limiting

- Global: `RateLimitMiddleware` 100/min (`config.py:420-421`)
- Login: 5 failures → 15 min lockout (`security.py:497-501`)

## 6. Security Headers

Production CSP + HSTS via `SecurityHeadersMiddleware` (`middleware/security.py:28-29, 60+`).

## 7. Secrets Management

| Secret | Validation |
|--------|------------|
| SECRET_KEY, JWT_SECRET_KEY, PII_ENCRYPTION_KEY | Reject autogen in prod (`config.py:529-542`) |
| Stripe webhook | `construct_event` or 503 (`stripe_webhook.py:150-161`) |
| WhatsApp webhook | verify token required in compose (`docker-compose.yml:148`) |

Compose requires `${SECRET_KEY:?}`, `${JWT_SECRET_KEY:?}`, `${PII_ENCRYPTION_KEY:?}` (`docker-compose.yml:86-106`).

## 8. Exposure Findings

### F-001 — OpenAPI open without DOCS_API_KEY (P1)

```343:345:backend/app/main.py
            if not DOCS_API_KEY:
                return
```

**Risk:** Full API surface scannable in production.  
**Fix:** Fail closed or disable docs routes when key unset in prod.

### F-002 — /metrics open without METRICS_API_KEY (P1)

```54:58:backend/app/main.py
def metrics_access_allowed(authorization_header: str, api_key: str) -> bool:
    if not api_key:
        return True
```

Combined with tenant-exempt public list (`tenant.py:31`) and tenant-labeled series comment (`main.py:788-794`).

**Fix:** Require `METRICS_API_KEY` in prod; scrape via internal network only.

### F-003 — WebSocket token in URL (P1)

```876:877:backend/app/main.py
        tenant_id: Optional[int] = Query(default=None),
        token: Optional[str] = Query(default=None),
```

Comment at `main.py:825-828` correctly warns against query tokens for SSE, but WS still accepts `?token=`.

**Fix:** Require `Sec-WebSocket-Protocol` bearer or post-connect auth message.

### F-004 — Mock ad data default in dev compose (P1)

```103:103:docker-compose.yml
      - USE_MOCK_AD_DATA=${USE_MOCK_AD_DATA:-true}
```

Mitigated by `enforce_production_safety` if `APP_ENV=production`, but mis-set `APP_ENV` with dev compose file is catastrophic.

### F-010 — .env.example conflict (P2)

| File | USE_MOCK_AD_DATA | DB password example |
|------|------------------|---------------------|
| `backend/.env.example:39` | `true` | `stratum:password` |
| `.env.example:23` | not listed (root) | `change-me-in-production` |
| `config.py:122-125` | default `False` | warns on `password` |

`needs_human_review: true`

## 9. Positive Controls

- bcrypt + JWT best practices
- Constant-time API key compare (`security.py:381-382`)
- Email/phone masking for logs (`security.py:336-367`)
- gitleaks in CI (`ci.yml:613-641`)
- Bandit + pip-audit gates (`ci.yml:373-385`)
- Production CORS localhost rejection (`config.py:567-577`)

## 10. Searches Run

```
grep "DOCS_API_KEY|METRICS_API_KEY" backend/app/main.py  → found
grep "construct_event" stripe_webhook.py                 → found
grep "PUBLIC_ENDPOINTS" tenant.py                        → 25-51
glob backend/tests/**/test_security*.py                  → test_security.py, test_core_security_extras.py
glob backend/tests/**/test_csrf*.py                      → test_csrf_middleware.py
```
