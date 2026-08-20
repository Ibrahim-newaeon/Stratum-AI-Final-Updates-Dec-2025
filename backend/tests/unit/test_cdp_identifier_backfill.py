# =============================================================================
# Stratum AI - CDP identifier encryption backfill [CDP-04]
# =============================================================================
"""Migration 064 widened ``cdp_profile_identifiers.identifier_value`` so new
writes could hold ciphertext, and deliberately left the existing rows alone.
Nothing has rewritten them since: identifier rows are touched to bump
``last_seen_at``, which does not go through ``set_identifier_value``. Every
profile identified before 064 therefore still has its raw email or phone number
sitting in plaintext on disk.

This backfill closes that. The assertions here pin the two ways it can appear
to work while doing the wrong thing:

* ``encrypt_pii`` falls back to the legacy global-derived key whenever the
  tenant's DEK is not in the cache, and returns successfully. A script that
  does not warm the cache first would put every tenant's identifiers under one
  shared key, report a full success, and still decrypt correctly afterwards --
  because ``decrypt_pii`` dual-reads. The isolation CDP-04 exists to create
  would be silently absent.
* Re-running over an already-encrypted row must not encrypt it twice. Double
  encryption is not detectable by reading the column back; it decrypts to
  ciphertext rather than to an email address.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet

from app.core import pii_keys
from app.core.security import decrypt_pii, encrypt_pii
from app.models.cdp import CDPProfileIdentifier

pytestmark = pytest.mark.unit

BACKEND_DIR = Path(__file__).resolve().parents[2]
SCRIPT_PATH = BACKEND_DIR / "scripts" / "backfill_cdp_identifiers.py"

TENANT_ID = 42


def load_script():
    """Import the backfill script by path -- ``scripts/`` is not a package."""
    if "backfill_cdp_identifiers" in sys.modules:
        return sys.modules["backfill_cdp_identifiers"]
    spec = importlib.util.spec_from_file_location(
        "backfill_cdp_identifiers", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# =============================================================================
# Test doubles
# =============================================================================
class _ScalarResult:
    def __init__(self, rows: list[Any]) -> None:
        self._rows = rows

    def scalars(self) -> _ScalarResult:
        return self

    def all(self) -> list[Any]:
        return self._rows

    def scalar(self):
        return self._rows[0] if self._rows else None

    def scalar_one(self):
        return self._rows[0]


class FakeSession:
    """Serves canned pages of ORM rows and records commits.

    The script paginates by primary key, so it keeps querying until a page
    comes back short. Pages are popped in order and an empty list is served
    once they run out.
    """

    def __init__(self, pages: list[list[Any]]) -> None:
        self._pages = list(pages)
        self.commits = 0

    async def execute(self, statement, *args, **kwargs):  # noqa: ANN001
        page = self._pages.pop(0) if self._pages else []
        return _ScalarResult(page)

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        pass


def make_row(value: str | None, tenant_id: int = TENANT_ID) -> CDPProfileIdentifier:
    """A row holding ``value`` in the encrypted column verbatim.

    Assigning the private attribute is what a pre-064 row looks like when it is
    loaded: whatever bytes are in the column, with no encryption applied.
    """
    row = CDPProfileIdentifier()
    row.id = uuid4()
    row.tenant_id = tenant_id
    row.profile_id = uuid4()
    row.identifier_type = "email"
    row.identifier_hash = "a" * 64
    row._identifier_value_encrypted = value
    return row


@pytest.fixture(autouse=True)
def _clean_dek_cache():
    pii_keys._clear_cache()
    yield
    pii_keys._clear_cache()


# =============================================================================
# Encryption
# =============================================================================
@pytest.mark.asyncio
async def test_plaintext_row_is_encrypted_under_the_tenant_dek():
    """The whole point: a pre-064 plaintext identifier ends up as ciphertext
    that only this tenant's DEK can read."""
    script = load_script()
    pii_keys._DEK_CACHE[TENANT_ID] = Fernet.generate_key()

    row = make_row("user@example.com")
    session = FakeSession([[row]])

    stats = await script.backfill_tenant(session, TENANT_ID, batch_size=100)

    stored = row._identifier_value_encrypted
    assert stored != "user@example.com", "row was left in plaintext"
    assert decrypt_pii(stored, TENANT_ID) == "user@example.com"
    assert stats.encrypted == 1


@pytest.mark.asyncio
async def test_refuses_to_run_when_the_tenant_has_no_dek():
    """The failure this script exists to avoid.

    With no DEK cached, ``encrypt_pii`` silently derives the legacy global key
    and succeeds. Every tenant's identifiers would land under one shared key,
    the run would report success, and ``decrypt_pii``'s dual-read would keep
    returning the right plaintext -- so nothing downstream would ever notice
    that per-tenant isolation had not happened.
    """
    script = load_script()
    assert pii_keys.get_cached_dek(TENANT_ID) is None

    row = make_row("user@example.com")
    session = FakeSession([[row]])

    with pytest.raises(script.MissingTenantDEK):
        await script.backfill_tenant(session, TENANT_ID, batch_size=100)

    assert row._identifier_value_encrypted == "user@example.com"
    assert session.commits == 0


@pytest.mark.asyncio
async def test_already_encrypted_row_is_not_encrypted_twice():
    """Idempotence, and it has to be real: a resumed or repeated run passes
    over rows the previous run finished. Double encryption survives every
    obvious check -- the column still looks like ciphertext -- and only shows
    up when a profile renders a Fernet token where an email should be."""
    script = load_script()
    pii_keys._DEK_CACHE[TENANT_ID] = Fernet.generate_key()

    ciphertext = encrypt_pii("user@example.com", TENANT_ID)
    row = make_row(ciphertext)
    session = FakeSession([[row]])

    stats = await script.backfill_tenant(session, TENANT_ID, batch_size=100)

    assert row._identifier_value_encrypted == ciphertext
    assert decrypt_pii(row._identifier_value_encrypted, TENANT_ID) == "user@example.com"
    assert stats.already_encrypted == 1
    assert stats.encrypted == 0


@pytest.mark.asyncio
async def test_identifier_hash_is_never_rewritten():
    """The hash is the lookup key in every read path and in audience sync, and
    it is SHA-256 of the plaintext. Encrypting the value must not touch it, or
    identity resolution stops finding the profile it just encrypted."""
    script = load_script()
    pii_keys._DEK_CACHE[TENANT_ID] = Fernet.generate_key()

    row = make_row("user@example.com")
    original_hash = row.identifier_hash
    session = FakeSession([[row]])

    await script.backfill_tenant(session, TENANT_ID, batch_size=100)

    assert row.identifier_hash == original_hash


@pytest.mark.asyncio
async def test_null_value_is_left_null():
    """``identifier_value`` is nullable and ``set_identifier_value(None)``
    stores None -- but encrypting the empty string would store "" instead,
    turning "no identifier recorded" into "an identifier that is blank"."""
    script = load_script()
    pii_keys._DEK_CACHE[TENANT_ID] = Fernet.generate_key()

    row = make_row(None)
    session = FakeSession([[row]])

    stats = await script.backfill_tenant(session, TENANT_ID, batch_size=100)

    assert row._identifier_value_encrypted is None
    assert stats.empty == 1
    assert stats.encrypted == 0


@pytest.mark.asyncio
async def test_dry_run_counts_without_writing_or_committing():
    """Operators need the row count before they authorise a run that rewrites
    production PII with no plaintext copy retained."""
    script = load_script()
    pii_keys._DEK_CACHE[TENANT_ID] = Fernet.generate_key()

    row = make_row("user@example.com")
    session = FakeSession([[row]])

    stats = await script.backfill_tenant(
        session, TENANT_ID, batch_size=100, dry_run=True
    )

    assert stats.encrypted == 1, "dry run should still report what it would do"
    assert row._identifier_value_encrypted == "user@example.com"
    assert session.commits == 0


@pytest.mark.asyncio
async def test_each_batch_commits_so_an_interrupted_run_keeps_its_work():
    """The knowledge-graph backfill shipped once with no commit at all and
    reported success. A single commit at the end has the same failure shape:
    a run killed at hour three would have written nothing."""
    script = load_script()
    pii_keys._DEK_CACHE[TENANT_ID] = Fernet.generate_key()

    pages = [[make_row("one@example.com")], [make_row("two@example.com")], []]
    session = FakeSession(pages)

    await script.backfill_tenant(session, TENANT_ID, batch_size=1)

    assert session.commits == 2


@pytest.mark.asyncio
async def test_run_warms_the_dek_cache_before_backfilling(monkeypatch):
    """The guard is only safe if the normal path satisfies it.

    ``_DEK_CACHE`` is populated at API startup, and this script is not the API
    -- it starts with an empty cache. If ``run`` did not load the DEKs first,
    every real invocation would raise MissingTenantDEK, and the obvious "fix"
    would be to delete the guard that stops the global-key fallback.
    """
    script = load_script()
    calls: list[str] = []

    class _SessionCtx:
        async def __aenter__(self):
            return FakeSession([])

        async def __aexit__(self, *exc):
            return False

    async def fake_load_all(session):
        calls.append("warmed")
        return 1

    async def fake_resolve(session, tenants):
        return [TENANT_ID]

    async def fake_backfill(session, tenant_id, batch_size=500, dry_run=False):
        calls.append("backfilled")
        return script.TenantStats(scanned=1, encrypted=1)

    monkeypatch.setattr(script, "AsyncSessionLocal", lambda: _SessionCtx())
    monkeypatch.setattr(script, "load_all_tenant_deks", fake_load_all)
    monkeypatch.setattr(script, "resolve_tenant_ids", fake_resolve)
    monkeypatch.setattr(script, "backfill_tenant", fake_backfill)

    args = script.build_parser().parse_args(["--tenant", str(TENANT_ID)])
    exit_code = await script.run(args)

    assert calls == ["warmed", "backfilled"]
    assert exit_code == 0
