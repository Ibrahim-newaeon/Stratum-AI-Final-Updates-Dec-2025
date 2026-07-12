# AUTH-05 Phase 2 Slice A — tenant_id PII Threading Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Thread `tenant_id` into the ~25 highest-value User-PII `encrypt_pii`/`decrypt_pii` call sites so per-tenant DEKs are actually used for the crown-jewel PII (names, emails, phones, MFA secrets).

**Architecture:** `encrypt_pii(plaintext, tenant_id)` / `decrypt_pii(ciphertext, tenant_id)` already exist and already do per-tenant-DEK-with-global-fallback (Phase 1, #599). This slice only changes *callers* to pass `tenant_id`, always sourced from a persisted row or the authenticated principal — never a request body. Behavior-preserving via dual-read; no migration, no env change.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy 2.0 async, pytest. Fernet (`cryptography`) for PII encryption.

## Global Constraints

- Use `datetime.now(timezone.utc)`, never `datetime.utcnow()`.
- `tenant_id` MUST come from a loaded row (`user.tenant_id`, `assigned_user.tenant_id`) or `current_user` / a just-flushed `tenant.id` — NEVER from a request/payload field.
- Behavior-preserving: existing tests for auth/users/mfa/clients/gdpr must stay green (dual-read guarantees legacy ciphertext still decrypts).
- Lint before commit: `python -m ruff check <files>`, `python -m black --check <files>`, `python -m isort --check-only <files>`. mypy is not in the prod image — `pip install -q mypy==2.1.0` first if type-checking.
- Local test recipe (Docker up): run in the api container, e.g.
  `docker exec stratum_api sh -c 'cd /app && python -m pytest tests/unit/test_pii_keys.py -q'`.
- No new dependencies. No schema migration.

---

### Task 1: Lock the cross-tenant safety contract (unit test)

The core functions already round-trip under a DEK, dual-read legacy ciphertext, and fall back to global (proven by existing `tests/unit/test_pii_keys.py`). The one un-covered property is the safety-critical one: ciphertext from tenant A must NOT decrypt under tenant B. Lock it before threading any caller.

**Files:**
- Test: `backend/tests/unit/test_pii_keys.py`

**Interfaces:**
- Consumes: `app.core.pii_keys._DEK_CACHE` (dict[int,bytes]), `pii_keys._clear_cache()`, `app.core.security.encrypt_pii(plaintext, tenant_id=None)`, `decrypt_pii(ciphertext, tenant_id=None)`.
- Produces: nothing new; asserts existing behavior.

- [ ] **Step 1: Write the failing test**

Add to `backend/tests/unit/test_pii_keys.py`:

```python
def test_cross_tenant_dek_fails_closed():
    """Ciphertext encrypted under tenant A's DEK must not decrypt under tenant B."""
    from cryptography.fernet import Fernet
    from app.core import pii_keys
    from app.core.security import decrypt_pii, encrypt_pii

    pii_keys._clear_cache()
    pii_keys._DEK_CACHE[101] = Fernet.generate_key()
    pii_keys._DEK_CACHE[202] = Fernet.generate_key()

    blob = encrypt_pii("secret@example.com", 101)
    # Correct tenant round-trips
    assert decrypt_pii(blob, 101) == "secret@example.com"
    # Wrong tenant fails closed (never returns ciphertext)
    with pytest.raises(ValueError):
        decrypt_pii(blob, 202)
    pii_keys._clear_cache()
```

Ensure `import pytest` is present at the top of the file (it already is).

- [ ] **Step 2: Run test to verify it passes (contract already holds)**

Run: `docker exec stratum_api sh -c 'cd /app && python -m pytest tests/unit/test_pii_keys.py::test_cross_tenant_dek_fails_closed -q'`
Expected: PASS. (If it FAILS, stop — the core dual-read is broken and threading is unsafe.)

- [ ] **Step 3: Run the whole pii_keys suite**

Run: `docker exec stratum_api sh -c 'cd /app && python -m pytest tests/unit/test_pii_keys.py -q'`
Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/unit/test_pii_keys.py
git commit -m "test(auth): lock cross-tenant PII decrypt fails closed [AUTH-05]"
```

---

### Task 2: Thread tenant_id in gdpr.py (3 sites — warm-up)

Simplest file: all three calls operate on a single loaded `user` in the data-export endpoint.

**Files:**
- Modify: `backend/app/api/v1/endpoints/gdpr.py:90-92`

**Interfaces:**
- Consumes: `decrypt_pii(ciphertext, tenant_id)`; a loaded `user` with `.tenant_id`.
- Produces: nothing new.

- [ ] **Step 1: Edit the three sites**

In `backend/app/api/v1/endpoints/gdpr.py`, change:

```python
            "email": decrypt_pii(user.email),
            "full_name": decrypt_pii(user.full_name) if user.full_name else None,
            "phone": decrypt_pii(user.phone) if user.phone else None,
```

to:

```python
            "email": decrypt_pii(user.email, user.tenant_id),
            "full_name": (
                decrypt_pii(user.full_name, user.tenant_id) if user.full_name else None
            ),
            "phone": decrypt_pii(user.phone, user.tenant_id) if user.phone else None,
```

- [ ] **Step 2: Grep-audit the file has zero un-threaded sites**

Run: `grep -nE '(encrypt_pii|decrypt_pii)\([^,)]*\)' backend/app/api/v1/endpoints/gdpr.py`
Expected: no output (every call now has a second argument).

- [ ] **Step 3: Lint**

Run: `cd backend && python -m ruff check app/api/v1/endpoints/gdpr.py && python -m black --check app/api/v1/endpoints/gdpr.py`
Expected: clean.

- [ ] **Step 4: Run any gdpr tests**

Run: `docker exec stratum_api sh -c 'cd /app && python -m pytest tests/ -q -k gdpr'`
Expected: PASS (or "no tests ran" — then rely on the Task 7 full run).

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/endpoints/gdpr.py
git commit -m "refactor(auth): thread tenant_id in gdpr PII export [AUTH-05]"
```

---

### Task 3: Thread tenant_id in mfa_service.py (+ mfa.py caller)

Three sites operate on a loaded `user`; one (`initiate_setup`) has only `user_id` and issues a bare `UPDATE`, so it takes a new `tenant_id` parameter passed by the endpoint (MFA is always self-service → `current_user.tenant_id` is the enrolling user's tenant).

**Files:**
- Modify: `backend/app/services/mfa_service.py` (`initiate_setup` signature + line 287; lines 338, 514, 546)
- Modify: `backend/app/api/v1/endpoints/mfa.py` (the `initiate_setup(...)` call)
- Test: `backend/tests/unit/test_mfa_service.py` (or the existing MFA test module)

**Interfaces:**
- Consumes: `encrypt_pii(plaintext, tenant_id)`, `decrypt_pii(ciphertext, tenant_id)`, loaded `user.tenant_id`.
- Produces: `MFAService.initiate_setup(self, user_id: int, email: str, tenant_id: int) -> TOTPSetupData` (added trailing param).

- [ ] **Step 1: Add tenant_id param to initiate_setup**

In `backend/app/services/mfa_service.py`, change the signature:

```python
    async def initiate_setup(self, user_id: int, email: str) -> TOTPSetupData:
```

to:

```python
    async def initiate_setup(
        self, user_id: int, email: str, tenant_id: int
    ) -> TOTPSetupData:
```

and its encrypt call (line ~287):

```python
        encrypted_secret = encrypt_pii(secret)
```

to:

```python
        encrypted_secret = encrypt_pii(secret, tenant_id)
```

- [ ] **Step 2: Thread the three loaded-user decrypt sites**

In the same file, each of these three has a loaded `user` in scope — add `, user.tenant_id`:

- line ~338 (`verify_and_enable`): `decrypt_pii(user.totp_secret)` → `decrypt_pii(user.totp_secret, user.tenant_id)`
- line ~514 (regenerate backup codes): `decrypt_pii(user.totp_secret)` → `decrypt_pii(user.totp_secret, user.tenant_id)`
- line ~546 (`_verify_code`, `user` is a parameter): `decrypt_pii(user.totp_secret)` → `decrypt_pii(user.totp_secret, user.tenant_id)`

- [ ] **Step 3: Update the endpoint caller**

In `backend/app/api/v1/endpoints/mfa.py`, find the `service.initiate_setup(...)` call and pass the tenant:

```python
        setup = await service.initiate_setup(current_user.id, <email_arg>)
```

becomes

```python
        setup = await service.initiate_setup(
            current_user.id, <email_arg>, current_user.tenant_id
        )
```

(Keep the existing `<email_arg>` exactly as it is; only append `current_user.tenant_id`.)

- [ ] **Step 4: Write/adjust an MFA round-trip test**

Add to the MFA unit test module (create `backend/tests/unit/test_mfa_tenant_key.py` if no suitable spot):

```python
import pytest
from cryptography.fernet import Fernet
from app.core import pii_keys
from app.core.security import decrypt_pii, encrypt_pii


def test_totp_secret_roundtrips_under_tenant_dek():
    pii_keys._clear_cache()
    pii_keys._DEK_CACHE[55] = Fernet.generate_key()
    enc = encrypt_pii("JBSWY3DPEHPK3PXP", 55)
    assert decrypt_pii(enc, 55) == "JBSWY3DPEHPK3PXP"
    # not decodable under the global key path (no DEK for tenant 999)
    with pytest.raises(ValueError):
        decrypt_pii(enc, 999)
    pii_keys._clear_cache()
```

- [ ] **Step 5: Run tests**

Run: `docker exec stratum_api sh -c 'cd /app && python -m pytest tests/unit/test_mfa_tenant_key.py -q && python -m pytest tests/ -q -k mfa'`
Expected: PASS.

- [ ] **Step 6: Grep-audit + lint**

Run: `grep -nE '(encrypt_pii|decrypt_pii)\([^,)]*\)' backend/app/services/mfa_service.py`
Expected: no output.
Run: `cd backend && python -m ruff check app/services/mfa_service.py app/api/v1/endpoints/mfa.py && python -m black --check app/services/mfa_service.py app/api/v1/endpoints/mfa.py`
Expected: clean.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/mfa_service.py backend/app/api/v1/endpoints/mfa.py backend/tests/unit/test_mfa_tenant_key.py
git commit -m "refactor(auth): thread tenant_id through MFA secret encryption [AUTH-05]"
```

---

### Task 4: Thread tenant_id in users.py (helper + callers + create/update)

The decrypt surface is centralized in `_safe_decrypt(value)` (9 callers), so add `tenant_id` there once and thread the row's tenant at each caller. Plus two encrypt sites in self-update, three in the invite flow, and one in admin-update.

**Files:**
- Modify: `backend/app/api/v1/endpoints/users.py` (helper at 39; callers 92-94, 163-165, 220-221, 370; encrypts 148-150, 307, 311, 315, 465)

**Interfaces:**
- Consumes: `decrypt_pii`, `encrypt_pii`, loaded rows `user`/`u`/`inviter` with `.tenant_id`, local `tenant_id`, `current_user.tenant_id`.
- Produces: `_safe_decrypt(value: Optional[str], tenant_id: Optional[int]) -> Optional[str]`.

- [ ] **Step 1: Add tenant_id to the helper**

Change:

```python
def _safe_decrypt(value: Optional[str]) -> Optional[str]:
    """Decrypt PII, returning the raw value if decryption fails."""
    if not value:
        return None
    try:
        return decrypt_pii(value)
    except (ValueError, TypeError, KeyError, OSError):
        # Value may be stored in plaintext or encrypted with a different key
        return value
```

to:

```python
def _safe_decrypt(value: Optional[str], tenant_id: Optional[int]) -> Optional[str]:
    """Decrypt PII, returning the raw value if decryption fails."""
    if not value:
        return None
    try:
        return decrypt_pii(value, tenant_id)
    except (ValueError, TypeError, KeyError, OSError):
        # Value may be stored in plaintext or encrypted with a different key
        return value
```

- [ ] **Step 2: Thread tenant_id at every `_safe_decrypt` caller**

Add the owning row's tenant to each call:

- lines 92-94 (`user`): `_safe_decrypt(user.email)` → `_safe_decrypt(user.email, user.tenant_id)`; same for `user.full_name`, `user.phone`.
- lines 163-165 (`user`): same pattern → `, user.tenant_id`.
- lines 220-221 (`u`): `_safe_decrypt(u.email)` → `_safe_decrypt(u.email, u.tenant_id)`; `_safe_decrypt(u.full_name)` → `, u.tenant_id`.
- line 370 (`inviter`): `_safe_decrypt(inviter.full_name)` → `_safe_decrypt(inviter.full_name, inviter.tenant_id)`.

- [ ] **Step 3: Thread the encrypt sites**

- Self-update (lines 148, 150) — this endpoint updates `current_user`; use `current_user.tenant_id`:

```python
    if "full_name" in update_dict and update_dict["full_name"]:
        update_dict["full_name"] = encrypt_pii(update_dict["full_name"], current_user.tenant_id)
    if "phone" in update_dict and update_dict["phone"]:
        update_dict["phone"] = encrypt_pii(update_dict["phone"], current_user.tenant_id)
```

(If the parameter is named differently than `current_user`, use that endpoint's authenticated-user variable — confirm by reading the function signature; it is the `Depends(get_current_user)` param.)

- Invite refresh, existing user (line 307), `user = existing_user` is in scope:

```python
            user.full_name = encrypt_pii(invite_data.full_name, user.tenant_id)
```

- Invite new user (lines 311, 315), local `tenant_id` is in scope:

```python
            email=encrypt_pii(invite_data.email.lower(), tenant_id),
            ...
            full_name=(
                encrypt_pii(invite_data.full_name, tenant_id) if invite_data.full_name else None
            ),
```

- Admin update (line 465), loaded `user`:

```python
        user.full_name = (
            encrypt_pii(update_data.full_name, user.tenant_id) if update_data.full_name else None
        )
```

- [ ] **Step 4: Grep-audit the file**

Run: `grep -nE '(encrypt_pii|decrypt_pii)\([^,)]*\)|_safe_decrypt\([^,)]*\)' backend/app/api/v1/endpoints/users.py`
Expected: no output (helper and all direct calls now take a tenant arg).

- [ ] **Step 5: Lint + run users tests**

Run: `cd backend && python -m ruff check app/api/v1/endpoints/users.py && python -m black --check app/api/v1/endpoints/users.py`
Run: `docker exec stratum_api sh -c 'cd /app && python -m pytest tests/ -q -k "users or invite"'`
Expected: clean + PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/api/v1/endpoints/users.py
git commit -m "refactor(auth): thread tenant_id through users PII (helper+CRUD) [AUTH-05]"
```

---

### Task 5: Thread tenant_id in auth.py (7 sites)

Two are in the registration flow (tenant just flushed → `tenant.id`); five operate on a loaded `user`.

**Files:**
- Modify: `backend/app/api/v1/endpoints/auth.py` (906, 910; 1357, 1563, 1658, 1664, 1766)

**Interfaces:**
- Consumes: `encrypt_pii`, `decrypt_pii`, a just-flushed `tenant.id`, loaded `user.tenant_id`.

- [ ] **Step 1: Registration sites (tenant.id available after `await db.flush()` at line 901)**

```python
        email=encrypt_pii(email_lower),
        ...
        full_name=(
            encrypt_pii(request_data.full_name) if request_data.full_name else None
        ),
```

→

```python
        email=encrypt_pii(email_lower, tenant.id),
        ...
        full_name=(
            encrypt_pii(request_data.full_name, tenant.id) if request_data.full_name else None
        ),
```

(Note: the new tenant's DEK is not provisioned in this path yet, so this correctly falls back to the global key and upgrades on next write — registration inline provisioning is a later slice. Threading `tenant.id` now is correct and harmless.)

- [ ] **Step 2: Loaded-user sites — add `, user.tenant_id`**

- line 1357 (`decrypt_pii(user.full_name)`) → `decrypt_pii(user.full_name, user.tenant_id)`
- line 1563 (`encrypt_pii(request_data.full_name.strip())`, in accept-invite where `user` is loaded) → `encrypt_pii(request_data.full_name.strip(), user.tenant_id)`
- line 1658 (`decrypt_pii(user.full_name)`) → `, user.tenant_id`
- line 1664 (`decrypt_pii(user.email)`) → `decrypt_pii(user.email, user.tenant_id)`
- line 1766 (`decrypt_pii(user.full_name)`) → `, user.tenant_id`

- [ ] **Step 3: Grep-audit + lint**

Run: `grep -nE '(encrypt_pii|decrypt_pii)\([^,)]*\)' backend/app/api/v1/endpoints/auth.py`
Expected: no output.
Run: `cd backend && python -m ruff check app/api/v1/endpoints/auth.py && python -m black --check app/api/v1/endpoints/auth.py`
Expected: clean.

- [ ] **Step 4: Run auth tests (regression guard — email_hash login paths must stay green)**

Run: `docker exec stratum_api sh -c 'cd /app && python -m pytest tests/ -q -k "auth or login or register or invite or password_reset"'`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/endpoints/auth.py
git commit -m "refactor(auth): thread tenant_id through auth PII (register/invite/email) [AUTH-05]"
```

---

### Task 6: Thread tenant_id in clients.py (4 sites)

Two decrypt an `assigned_user` (loaded via `user_map`); two encrypt a new `portal_user` with local `tenant_id` in scope.

**Files:**
- Modify: `backend/app/api/v1/endpoints/clients.py` (611, 613; 864, 867)

**Interfaces:**
- Consumes: `encrypt_pii`, `decrypt_pii`, `assigned_user.tenant_id`, local `tenant_id`.

- [ ] **Step 1: Assigned-user decrypt sites (611, 613)**

```python
                item.user_email = decrypt_pii(assigned_user.email)
                item.user_name = (
                    decrypt_pii(assigned_user.full_name)
                    if assigned_user.full_name
                    else None
```

→

```python
                item.user_email = decrypt_pii(assigned_user.email, assigned_user.tenant_id)
                item.user_name = (
                    decrypt_pii(assigned_user.full_name, assigned_user.tenant_id)
                    if assigned_user.full_name
                    else None
```

- [ ] **Step 2: Portal-user create sites (864, 867) — local `tenant_id` in scope**

```python
            email=encrypt_pii(payload.email),
            ...
            full_name=encrypt_pii(payload.full_name),
```

→

```python
            email=encrypt_pii(payload.email, tenant_id),
            ...
            full_name=encrypt_pii(payload.full_name, tenant_id),
```

- [ ] **Step 3: Grep-audit + lint**

Run: `grep -nE '(encrypt_pii|decrypt_pii)\([^,)]*\)' backend/app/api/v1/endpoints/clients.py`
Expected: no output.
Run: `cd backend && python -m ruff check app/api/v1/endpoints/clients.py && python -m black --check app/api/v1/endpoints/clients.py`
Expected: clean.

- [ ] **Step 4: Run clients tests**

Run: `docker exec stratum_api sh -c 'cd /app && python -m pytest tests/ -q -k client'`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/v1/endpoints/clients.py
git commit -m "refactor(auth): thread tenant_id through clients PII [AUTH-05]"
```

---

### Task 7: Cross-file audit + full verification

Confirm every in-scope site is threaded and nothing regressed.

**Files:** none modified (verification only).

- [ ] **Step 1: Audit all 5 in-scope files for any remaining single-arg call**

Run:

```bash
cd backend && grep -nE '(encrypt_pii|decrypt_pii)\([^,)]*\)|_safe_decrypt\([^,)]*\)' \
  app/api/v1/endpoints/auth.py app/api/v1/endpoints/users.py \
  app/services/mfa_service.py app/api/v1/endpoints/clients.py \
  app/api/v1/endpoints/gdpr.py
```

Expected: no output. (Any hit = a missed site; fix it in the owning task's file and re-commit.)

- [ ] **Step 2: Confirm out-of-scope files are untouched**

Run: `git diff --name-only main -- backend/app | sort`
Expected: only the 5 in-scope endpoint/service files (+ test files). CRM clients, `services/encryption.py`, `db/types.py`, superadmin/stripe/cms must NOT appear.

- [ ] **Step 3: Lint + type-check the changed set**

Run:

```bash
cd backend && pip install -q mypy==2.1.0
python -m ruff check app/api/v1/endpoints/auth.py app/api/v1/endpoints/users.py app/services/mfa_service.py app/api/v1/endpoints/clients.py app/api/v1/endpoints/gdpr.py app/api/v1/endpoints/mfa.py
python -m black --check app/api/v1/endpoints/auth.py app/api/v1/endpoints/users.py app/services/mfa_service.py app/api/v1/endpoints/clients.py app/api/v1/endpoints/gdpr.py app/api/v1/endpoints/mfa.py
python -m isort --check-only app/api/v1/endpoints/auth.py app/api/v1/endpoints/users.py app/services/mfa_service.py app/api/v1/endpoints/clients.py app/api/v1/endpoints/gdpr.py app/api/v1/endpoints/mfa.py
python -m mypy app/api/v1/endpoints/mfa.py app/services/mfa_service.py app/api/v1/endpoints/users.py --ignore-missing-imports --no-error-summary
```

Expected: all clean.

- [ ] **Step 4: Full unit + relevant integration run**

Run:

```bash
docker exec stratum_api sh -c 'cd /app && python -m pytest tests/unit/test_pii_keys.py tests/unit/test_mfa_tenant_key.py tests/unit/test_security.py -q'
docker exec stratum_api sh -c 'cd /app && export TEST_DATABASE_URL="${DATABASE_URL%/*}/stratum_ai_test" TEST_DATABASE_URL_SYNC="${DATABASE_URL_SYNC%/*}/stratum_ai_test"; python -m pytest tests/integration -q -k "auth or user or mfa or client or gdpr" -o asyncio_default_test_loop_scope=session -o asyncio_default_fixture_loop_scope=session'
```

Expected: PASS.

- [ ] **Step 5: Open PR**

```bash
git push -u origin feat/auth05-phase2a-tenant-pii-threading
gh pr create --base main --title 'refactor(auth): thread tenant_id through high-value PII sites, phase 2 slice A [AUTH-05]' --body-file - <<'BODY'
## AUTH-05 Phase 2, Slice A

Threads `tenant_id` through the ~25 highest-value User-PII encrypt/decrypt
sites (auth, users, mfa, clients, gdpr) so per-tenant DEKs (Phase 1, #599)
are actually used for names, emails, phones, and MFA secrets.

- `tenant_id` sourced only from loaded rows / `current_user` / just-flushed
  `tenant.id`, never from request bodies.
- Behavior-preserving via dual-read; no migration, no env change.
- Passive re-encryption only (fields upgrade to the DEK on next write).
- Deferred: CRM/OAuth-token/EncryptedString sites, KEK rotation,
  registration inline provisioning, active backfill.

Spec: docs/superpowers/specs/2026-07-12-auth05-phase2a-tenant-pii-threading-design.md

🤖 Generated with [Claude Code](https://claude.com/claude-code)
BODY
```

---

## Self-Review

**Spec coverage:**
- In-scope sites auth/users/mfa/clients/gdpr → Tasks 2-6. ✓
- `tenant_id` sourced from data not request → Global Constraints + each task's exact source. ✓
- Email threaded safely (email_hash lookup) → Task 5 (registration + `user.email`) with note. ✓
- Passive-only re-encryption → no active backfill task; noted in Task 5 registration. ✓
- Testing: round-trip, dual-read, cross-tenant fail, MFA round-trip → Task 1 + Task 3 + existing suites in Task 7. ✓
- Non-goals untouched → Task 7 Step 2 explicitly guards. ✓

**Placeholder scan:** every code step shows exact before/after. The only variable placeholders are `<email_arg>` (Task 3) and the "confirm `current_user` name" note (Task 4), each with explicit instruction to read the one adjacent line — acceptable because the exact token is local and unambiguous.

**Type consistency:** `_safe_decrypt(value, tenant_id)` defined in Task 4 Step 1 and used with that arity in Step 2. `initiate_setup(user_id, email, tenant_id)` defined in Task 3 Step 1 and called with that arity in Step 3. `encrypt_pii`/`decrypt_pii` second param is `tenant_id: int | None` per Phase 1 signature throughout. ✓
