# =============================================================================
# Stratum AI - API Key Authentication Tests
# =============================================================================
"""
Tests for inbound API-key authentication (P0-4).

Before this, `verify_api_key` had no production callers — a presented key
authenticated nothing. `get_api_key_principal` must now resolve a valid key
to a principal and reject missing / unknown / inactive / expired keys.
"""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.auth.api_key import (
    APIKeyPrincipal,
    get_api_key_principal,
    require_api_key_scope,
)


class _FakeResult:
    def __init__(self, record):
        self._record = record

    def scalar_one_or_none(self):
        return self._record


class _FakeDB:
    """Minimal async session stub returning a preset APIKey record."""

    def __init__(self, record):
        self._record = record
        self.committed = False

    async def execute(self, _query):
        return _FakeResult(self._record)

    async def commit(self):
        self.committed = True

    async def rollback(self):
        pass


def _key(**overrides):
    base = dict(
        id=11,
        tenant_id=7,
        user_id=3,
        scopes=["read"],
        is_active=True,
        expires_at=None,
        key_hash="deadbeef",
        last_used_at=None,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _request():
    return SimpleNamespace(state=SimpleNamespace())


async def test_valid_key_resolves_principal_and_sets_context():
    record = _key()
    db = _FakeDB(record)
    req = _request()

    principal = await get_api_key_principal(req, "strat_live_whatever", db)

    assert isinstance(principal, APIKeyPrincipal)
    assert principal.tenant_id == 7
    assert principal.user_id == 3
    assert principal.scopes == ["read"]
    # tenant context populated for downstream middleware
    assert req.state.tenant_id == 7
    assert req.state.user_id == 3
    # usage stamped
    assert record.last_used_at is not None
    assert db.committed is True


async def test_missing_key_rejected():
    with pytest.raises(HTTPException) as exc:
        await get_api_key_principal(_request(), None, _FakeDB(_key()))
    assert exc.value.status_code == 401


async def test_unknown_key_rejected():
    with pytest.raises(HTTPException) as exc:
        await get_api_key_principal(_request(), "nope", _FakeDB(None))
    assert exc.value.status_code == 401


async def test_inactive_key_rejected():
    with pytest.raises(HTTPException) as exc:
        await get_api_key_principal(_request(), "k", _FakeDB(_key(is_active=False)))
    assert exc.value.status_code == 401


async def test_expired_key_rejected():
    expired = _key(expires_at=datetime.now(timezone.utc) - timedelta(days=1))
    with pytest.raises(HTTPException) as exc:
        await get_api_key_principal(_request(), "k", _FakeDB(expired))
    assert exc.value.status_code == 401
    assert "expired" in exc.value.detail.lower()


async def test_scope_enforced():
    record = _key(scopes=["read"])
    checker = require_api_key_scope("write")
    principal = APIKeyPrincipal(record)
    with pytest.raises(HTTPException) as exc:
        await checker(principal)
    assert exc.value.status_code == 403


async def test_admin_scope_satisfies_any_requirement():
    record = _key(scopes=["admin"])
    checker = require_api_key_scope("write", "delete")
    principal = APIKeyPrincipal(record)
    assert await checker(principal) is principal
