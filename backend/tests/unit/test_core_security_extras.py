# =============================================================================
# Stratum AI - Security (Redis & auth-flow paths) Unit Tests
# =============================================================================
"""Unit tests for the Redis-backed and auth-flow paths of
``app.core.security``.

Complements ``test_security.py`` (crypto / hashing / JWT signing). Covers:

- token blacklist (``blacklist_token`` / ``is_token_blacklisted``)
- login rate limiting (``check_login_rate_limit`` / ``record_failed_login``
  / ``clear_login_attempts``)
- ``get_redis_pool`` caching and creation
- ``decode_token`` failure branches (expired, garbage)
- ``require_permission`` (superadmin bypass / missing / granted)
- ``anonymize_pii``

The autouse ``_fake_security_redis`` fixture in ``tests/unit/conftest.py``
already swaps ``get_redis_pool`` for a benign fake and resets the module
globals before each test; the ``fake_redis`` fixture here layers an
assertable fake on top of it.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

import app.core.security as security

# Captured at import time, before the autouse conftest fixture monkeypatches
# the module attribute — this is the real implementation.
from app.core.security import (
    LOGIN_ATTEMPT_PREFIX,
    LOGIN_ATTEMPT_WINDOW_SECONDS,
    LOGIN_LOCKOUT_PREFIX,
    LOGIN_LOCKOUT_SECONDS,
    MAX_LOGIN_ATTEMPTS,
    TOKEN_BLACKLIST_PREFIX,
    _get_pii_salt,
    anonymize_pii,
    blacklist_token,
    check_login_rate_limit,
    clear_login_attempts,
    create_access_token,
    create_refresh_token,
    decode_token,
    decrypt_pii,
    encrypt_pii,
    get_password_hash,
)
from app.core.security import get_redis_pool as _real_get_redis_pool
from app.core.security import (
    is_token_blacklisted,
    record_failed_login,
    require_permission,
    verify_password,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def fake_redis(monkeypatch: pytest.MonkeyPatch) -> AsyncMock:
    """Assertable fake Redis client wired into security.get_redis_pool."""
    fake = AsyncMock()
    fake.setex = AsyncMock()
    fake.exists = AsyncMock(return_value=0)
    fake.ttl = AsyncMock(return_value=-2)
    fake.incr = AsyncMock(return_value=1)
    fake.expire = AsyncMock()
    fake.delete = AsyncMock()

    async def _pool() -> AsyncMock:
        return fake

    monkeypatch.setattr(security, "get_redis_pool", _pool)
    return fake


# =============================================================================
# Token blacklist
# =============================================================================


class TestBlacklistToken:
    async def test_missing_exp_is_a_noop(self, fake_redis: AsyncMock) -> None:
        """A payload without 'exp' cannot be blacklisted."""
        await blacklist_token("token", {"sub": "1"})
        fake_redis.setex.assert_not_awaited()

    async def test_already_expired_token_is_a_noop(self, fake_redis: AsyncMock) -> None:
        """A token past its expiry needs no blacklist entry."""
        past = datetime.now(timezone.utc).timestamp() - 100
        await blacklist_token("token", {"exp": past})
        fake_redis.setex.assert_not_awaited()

    async def test_blacklists_with_jti_and_token_ttl(
        self, fake_redis: AsyncMock
    ) -> None:
        """The entry is keyed by jti and expires when the token would."""
        exp = datetime.now(timezone.utc).timestamp() + 3600
        await blacklist_token("token", {"exp": exp, "jti": "unique-jti"})

        fake_redis.setex.assert_awaited_once()
        key, ttl, value = fake_redis.setex.await_args.args
        assert key == f"{TOKEN_BLACKLIST_PREFIX}unique-jti"
        assert 3590 <= ttl <= 3600
        assert value == "1"

    async def test_falls_back_to_token_suffix_without_jti(
        self, fake_redis: AsyncMock
    ) -> None:
        """Without a jti, the last 32 chars of the raw token key the entry."""
        token = "x" * 40 + "SUFFIX" * 4  # last 32 chars are deterministic
        exp = datetime.now(timezone.utc).timestamp() + 60
        await blacklist_token(token, {"exp": exp})

        key = fake_redis.setex.await_args.args[0]
        assert key == f"{TOKEN_BLACKLIST_PREFIX}{token[-32:]}"


class TestIsTokenBlacklisted:
    async def test_returns_true_when_entry_exists(self, fake_redis: AsyncMock) -> None:
        """An existing blacklist key means the token is revoked."""
        fake_redis.exists.return_value = 1
        assert await is_token_blacklisted({"jti": "j1"}, "token") is True

    async def test_returns_false_when_entry_missing(
        self, fake_redis: AsyncMock
    ) -> None:
        """No blacklist key means the token is still valid."""
        fake_redis.exists.return_value = 0
        assert await is_token_blacklisted({"jti": "j1"}, "token") is False

    async def test_redis_outage_reraises_connection_error(
        self, fake_redis: AsyncMock
    ) -> None:
        """Redis being unreachable must surface, not silently allow tokens."""
        fake_redis.exists.side_effect = ConnectionError("down")

        with pytest.raises(ConnectionError, match="Redis unavailable"):
            await is_token_blacklisted({"jti": "j1"}, "token")


# =============================================================================
# Login rate limiting
# =============================================================================


class TestLoginRateLimit:
    async def test_active_lockout_blocks_login(self, fake_redis: AsyncMock) -> None:
        """A positive lockout TTL blocks logins and reports the wait."""
        fake_redis.ttl.return_value = 120
        allowed, remaining = await check_login_rate_limit("hash1")
        assert allowed is False
        assert remaining == 120

    async def test_no_lockout_allows_login(self, fake_redis: AsyncMock) -> None:
        """A missing lockout key (-2 TTL) allows the attempt."""
        fake_redis.ttl.return_value = -2
        allowed, remaining = await check_login_rate_limit("hash1")
        assert allowed is True
        assert remaining == 0

    async def test_first_failed_attempt_sets_window(
        self, fake_redis: AsyncMock
    ) -> None:
        """The first failure opens the attempt window without a lockout."""
        fake_redis.incr.return_value = 1

        attempts = await record_failed_login("hash1")

        assert attempts == 1
        fake_redis.expire.assert_awaited_once_with(
            f"{LOGIN_ATTEMPT_PREFIX}hash1", LOGIN_ATTEMPT_WINDOW_SECONDS
        )
        fake_redis.setex.assert_not_awaited()

    async def test_max_attempts_sets_lockout_and_resets_counter(
        self, fake_redis: AsyncMock
    ) -> None:
        """Hitting MAX_LOGIN_ATTEMPTS locks the account and clears attempts."""
        fake_redis.incr.return_value = MAX_LOGIN_ATTEMPTS

        attempts = await record_failed_login("hash1")

        assert attempts == MAX_LOGIN_ATTEMPTS
        fake_redis.setex.assert_awaited_once_with(
            f"{LOGIN_LOCKOUT_PREFIX}hash1", LOGIN_LOCKOUT_SECONDS, "1"
        )
        fake_redis.delete.assert_awaited_once_with(f"{LOGIN_ATTEMPT_PREFIX}hash1")
        fake_redis.expire.assert_not_awaited()

    async def test_clear_login_attempts_deletes_key(
        self, fake_redis: AsyncMock
    ) -> None:
        """A successful login wipes the failed-attempt counter."""
        await clear_login_attempts("hash1")
        fake_redis.delete.assert_awaited_once_with(f"{LOGIN_ATTEMPT_PREFIX}hash1")


# =============================================================================
# get_redis_pool
# =============================================================================


class TestGetRedisPool:
    async def test_returns_cached_pool(self) -> None:
        """An existing pool is returned without touching the factory."""
        sentinel = object()
        security._redis_pool = sentinel
        try:
            assert await _real_get_redis_pool() is sentinel
        finally:
            security._redis_pool = None

    async def test_creates_pool_once_under_lock(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """The pool is created lazily and reused on subsequent calls."""
        created = AsyncMock()
        from_url = MagicMock(return_value=created)
        monkeypatch.setattr(security, "aioredis", SimpleNamespace(from_url=from_url))
        security._redis_pool = None
        security._redis_pool_lock = None
        try:
            first = await _real_get_redis_pool()
            second = await _real_get_redis_pool()

            assert first is created
            assert second is created
            from_url.assert_called_once()
        finally:
            security._redis_pool = None
            security._redis_pool_lock = None

    async def test_get_redis_lock_is_created_once(self) -> None:
        """The asyncio lock is lazily created once and then reused."""
        security._redis_pool_lock = None
        try:
            first = security._get_redis_lock()
            second = security._get_redis_lock()
            assert first is second
        finally:
            security._redis_pool_lock = None


# =============================================================================
# Password hashing
# =============================================================================


class TestPasswordHashing:
    """Exercises the truncation wrapper around passlib.

    The bcrypt backend fails to load under the coverage tracer in this
    environment (passlib 1.7.4 + bcrypt 4.x backend detection), so these
    tests swap in passlib's pure-Python md5_crypt scheme — the code under
    test is our wrapper logic, not the bcrypt algorithm itself.
    """

    @pytest.fixture(autouse=True)
    def _pure_python_hasher(self, monkeypatch: pytest.MonkeyPatch) -> None:
        from passlib.context import CryptContext

        monkeypatch.setattr(
            security, "pwd_context", CryptContext(schemes=["md5_crypt"])
        )

    def test_hash_and_verify_round_trip(self) -> None:
        """A hashed password verifies against the original, not others."""
        hashed = get_password_hash("s3cret-Passw0rd!")
        assert hashed != "s3cret-Passw0rd!"
        assert verify_password("s3cret-Passw0rd!", hashed) is True
        assert verify_password("wrong-password", hashed) is False

    def test_long_multibyte_password_is_truncated_safely(self) -> None:
        """Passwords over bcrypt's 72-byte cap hash and verify without error."""
        long_password = "п" * 100  # 200 bytes of UTF-8
        hashed = get_password_hash(long_password)
        assert verify_password(long_password, hashed) is True

    def test_truncate_helper_respects_multibyte_boundaries(self) -> None:
        """Truncation caps at 72 bytes without splitting a multi-byte char."""
        truncated = security._truncate_for_bcrypt("п" * 100)
        assert truncated == "п" * 36  # 72 bytes // 2 bytes per char
        assert len(truncated.encode("utf-8")) <= 72


# =============================================================================
# Token creation branches
# =============================================================================


class TestTokenCreation:
    def test_access_token_carries_additional_claims(self) -> None:
        """additional_claims are merged into the encoded payload."""
        token = create_access_token(subject=1, additional_claims={"tenant_id": 5})
        payload = decode_token(token)
        assert payload is not None
        assert payload["tenant_id"] == 5
        assert payload["type"] == "access"

    def test_refresh_token_has_type_and_jti(self) -> None:
        """Refresh tokens carry a revocable jti and the refresh type."""
        payload = decode_token(create_refresh_token(subject=7))
        assert payload is not None
        assert payload["sub"] == "7"
        assert payload["type"] == "refresh"
        assert payload["jti"]

    def test_refresh_token_honours_custom_expiry(self) -> None:
        """A custom expires_delta drives the exp claim."""
        payload = decode_token(
            create_refresh_token(subject=7, expires_delta=timedelta(minutes=5))
        )
        assert payload is not None
        expected = datetime.now(timezone.utc) + timedelta(minutes=5)
        assert abs(payload["exp"] - expected.timestamp()) < 10


# =============================================================================
# Per-tenant PII encryption
# =============================================================================


class TestTenantScopedPii:
    def test_per_tenant_salts_differ(self) -> None:
        """Each tenant derives a distinct salt (and from the global one)."""
        assert _get_pii_salt(1) != _get_pii_salt(2)
        assert _get_pii_salt(1) != _get_pii_salt()

    def test_tenant_scoped_round_trip(self) -> None:
        """Data encrypted for a tenant decrypts only with that tenant's key."""
        ciphertext = encrypt_pii("user@example.com", tenant_id=1)
        assert decrypt_pii(ciphertext, tenant_id=1) == "user@example.com"
        with pytest.raises(ValueError, match="PII decryption failed"):
            decrypt_pii(ciphertext, tenant_id=2)

    def test_empty_values_short_circuit(self) -> None:
        """Empty input encrypts/decrypts to the empty string."""
        assert encrypt_pii("") == ""
        assert decrypt_pii("") == ""


# =============================================================================
# decode_token failure branches
# =============================================================================


class TestDecodeTokenFailures:
    def test_expired_token_returns_none(self) -> None:
        """An expired signature decodes to None, never raises."""
        token = create_access_token(subject=1, expires_delta=timedelta(seconds=-10))
        assert decode_token(token) is None

    def test_garbage_token_returns_none(self) -> None:
        """Structurally invalid tokens decode to None."""
        assert decode_token("not.a.token") is None
        assert decode_token("") is None


# =============================================================================
# require_permission
# =============================================================================


def _perm_request(role: Any = None, permissions: Any = None) -> SimpleNamespace:
    """Fake request carrying auth-middleware state."""
    return SimpleNamespace(
        state=SimpleNamespace(role=role, permissions=permissions or [])
    )


class TestRequirePermission:
    async def test_superadmin_bypasses_permission_check(self) -> None:
        """Superadmins are allowed regardless of explicit permissions."""
        checker = require_permission("CAMPAIGN_APPROVE").dependency
        assert await checker(_perm_request(role="superadmin")) is True

    async def test_missing_permission_raises_403(self) -> None:
        """A user without the permission gets a 403 naming it."""
        checker = require_permission("CAMPAIGN_APPROVE").dependency
        with pytest.raises(HTTPException) as exc:
            await checker(_perm_request(role="admin", permissions=["OTHER"]))
        assert exc.value.status_code == 403
        assert "CAMPAIGN_APPROVE" in exc.value.detail

    async def test_granted_permission_allows(self) -> None:
        """A user holding the permission passes."""
        checker = require_permission("CAMPAIGN_APPROVE").dependency
        result = await checker(
            _perm_request(role="admin", permissions=["CAMPAIGN_APPROVE"])
        )
        assert result is True


# =============================================================================
# anonymize_pii
# =============================================================================


class TestAnonymizePii:
    def test_output_is_prefixed_and_random(self) -> None:
        """Anonymized values are prefixed, non-reversible, and unique."""
        original = "user@example.com"
        first = anonymize_pii(original)
        second = anonymize_pii(original)

        assert first.startswith("ANONYMIZED_")
        assert original not in first
        assert first != second  # random suffix per call
