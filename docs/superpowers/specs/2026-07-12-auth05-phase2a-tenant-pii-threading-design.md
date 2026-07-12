# AUTH-05 Phase 2, Slice A — Thread `tenant_id` through User-PII call sites

**Date:** 2026-07-12
**Status:** Approved (design)
**Depends on:** AUTH-05 Phase 1 (per-tenant DEKs, dual-read) — merged in #599.

## Problem

Phase 1 shipped real per-tenant data-encryption keys (DEKs) with envelope
encryption and dual-read decryption, but **no call site threads `tenant_id`**.
`encrypt_pii(plaintext)` / `decrypt_pii(ciphertext)` are always called with
`tenant_id=None`, so every PII write still uses the legacy global-derived key
(`_get_fernet_key(None)`). The per-tenant DEKs are provisioned but unused for
writes. A leaked master `pii_encryption_key` therefore still exposes every
tenant's newly-written PII — the exact risk Phase 1 set out to remove.

This slice makes per-tenant keys real for the **highest-value PII** (user
names, emails, phones, MFA/TOTP secrets) by threading `tenant_id` through the
call sites where it is directly and unambiguously available.

## Non-goals (deferred to later slices)

- CRM client call sites (`hubspot_client.py`, `zoho_client.py`,
  `pipedrive_client.py` — ~20 sites).
- The `encrypt_token()` / `decrypt_token()` OAuth-credential wrapper
  (`services/encryption.py`) and its callers.
- The single `EncryptedString` SQLAlchemy `TypeDecorator` column
  (`settings.webhook_url`) — a type decorator only sees one column value, not
  the row's `tenant_id`, and needs a context mechanism (own slice).
- Misc sites: `superadmin.py`, `stripe_webhook.py`, `cms.py`, `payments.py`,
  `autopilot.py`, `oauth/base.py`, `auth/deps.py`, `audience_sync.py`,
  `tenant/provisioning.py`, `db/types.py`.
- KEK rotation.
- Self-serve registration inline DEK provisioning.
- **Active re-encryption** of at-rest legacy ciphertext (see Re-encryption).

## In-scope call sites (~25)

| File | Calls | PII |
| --- | --- | --- |
| `api/v1/endpoints/auth.py` | 7 | email, full_name (register, verify, reset, resend) |
| `api/v1/endpoints/users.py` | 7 | full_name, email, phone (self-update, invite, admin update) |
| `services/mfa_service.py` | 4 | TOTP secret (enroll, verify, disable, status) |
| `api/v1/endpoints/clients.py` | 4 | assigned-user email/full_name, client create |
| `api/v1/endpoints/gdpr.py` | 3 | email, full_name, phone (data export) |

Exact line numbers are enumerated in the implementation plan, not here (they
drift as the files change).

## Key design decisions

### 1. `tenant_id` is sourced from data, never from the request

The one real hazard is encrypting under the **wrong** tenant's DEK. To make
that structurally impossible, `tenant_id` is always read from the persisted
row or the authenticated principal, never from a request body:

- A call operating on a loaded `user` row → `user.tenant_id`.
  e.g. `decrypt_pii(user.full_name, user.tenant_id)`.
- A create/update flow → the target user's tenant: `current_user.tenant_id`,
  or, at registration, the `tenant_id` assigned to the new user immediately
  before the encrypt call.

### 2. Email is safe to thread

User lookup is by `email_hash` (`hash_pii_for_lookup`, a global deterministic
SHA-256), never by decrypting the stored email. So the encrypted `email`
column is only ever decrypted when the row — and thus `tenant_id` — is already
in hand. Threading `tenant_id` into email encrypt/decrypt cannot break login,
password reset, or resend-verification, all of which match on `email_hash`.

At registration (`auth.py:906`, `users.py:311`), `tenant_id` is threaded from
the tenant assigned to the new user. If that tenant's DEK is not yet cached,
`encrypt_pii` falls back to the global key — safe, and dual-read upgrades it on
the next write.

### 3. Re-encryption is passive-only

No active migration in this slice. Once `tenant_id` is threaded, any update to
a field rewrites it under the tenant's DEK automatically (passive
re-encryption). Rows that are never re-written stay on the global key and
continue to decrypt via dual-read — correct, just not yet upgraded. Active
backfill (`reencrypt_tenant_pii`) is explicitly deferred.

### 4. Fallback safety is unchanged

- `encrypt_pii(x, tid)` with an un-provisioned/uncached DEK → global key.
  Safe; dual-read decrypts.
- `decrypt_pii(x, tid)` → tries the tenant DEK, then the global key. Legacy
  global-key ciphertext still decrypts after threading.

## Testing

Unit tests (extend `tests/unit/test_pii_keys.py` / `test_security*.py`):

1. **Round-trip under DEK** — with a provisioned tenant DEK cached,
   `decrypt_pii(encrypt_pii(x, tid), tid) == x`, and the ciphertext does NOT
   decrypt under the global key alone.
2. **Dual-read of legacy** — ciphertext produced with the global key
   (`tenant_id=None`) still decrypts via `decrypt_pii(x, tid)`.
3. **Cross-tenant fails closed** — ciphertext encrypted under tenant A's DEK
   does not decrypt under tenant B (`decrypt_pii` raises `ValueError`, and
   never returns the ciphertext).
4. **Passive re-encryption** — a value written under the global key, then
   re-encrypted with `tid`, is thereafter DEK-decryptable.

Integration (extend existing auth/users/mfa suites):

5. MFA enroll→verify round-trips with per-tenant TOTP secret encryption.
6. User self-update / admin-update / invite persist and read back PII
   correctly under the tenant DEK.
7. GDPR export returns correctly decrypted PII for a provisioned tenant.
8. Login / password-reset / resend-verification (email_hash paths) are
   unaffected — regression guard.

## Risks & mitigations

| Risk | Mitigation |
| --- | --- |
| Wrong `tenant_id` → cross-tenant DEK | Source only from row / `current_user`, never request body (§1). Cross-tenant decrypt test (§Testing.3). |
| Provisioning race at registration | Global fallback + dual-read make it safe; passive upgrade later. |
| Missed a call site in a threaded file | Plan enumerates every site per file; grep audit confirms zero un-threaded `encrypt_pii`/`decrypt_pii` remain in the 5 in-scope files. |
| Behavior change breaks existing tests | Round-trip is preserved for provisioned and unprovisioned tenants; regression tests on email_hash auth paths. |

## Rollout

Behavior-preserving and dual-read-backed, so it ships as a normal PR to `main`
(auto-deploys to Railway). No migration, no data backfill, no env changes.
