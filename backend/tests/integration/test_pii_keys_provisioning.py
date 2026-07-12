# =============================================================================
# Stratum AI - Per-Tenant PII Key Provisioning (DB) [AUTH-05]
# =============================================================================
"""Integration coverage for the key-store DB paths: ensure_tenant_dek persists
+ caches a DEK, is idempotent, and load/initialize repopulate the cache."""

import pytest
from sqlalchemy import select

from app.core import pii_keys
from app.models.encryption import TenantEncryptionKey

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _clean_cache():
    pii_keys._clear_cache()
    yield
    pii_keys._clear_cache()


class TestProvisioning:
    @pytest.mark.asyncio
    async def test_ensure_provisions_persists_and_caches(
        self, db_session, test_tenant
    ):
        tid = test_tenant["id"]
        dek = await pii_keys.ensure_tenant_dek(tid, db_session)
        await db_session.commit()

        # Cached
        assert pii_keys.get_cached_dek(tid) == dek
        # Persisted (wrapped, not plaintext) and unwraps back to the same DEK
        row = (
            await db_session.execute(
                select(TenantEncryptionKey).where(
                    TenantEncryptionKey.tenant_id == tid
                )
            )
        ).scalar_one()
        assert row.wrapped_dek and dek.decode() not in row.wrapped_dek
        assert pii_keys.unwrap_dek(row.wrapped_dek) == dek

    @pytest.mark.asyncio
    async def test_ensure_is_idempotent(self, db_session, test_tenant):
        tid = test_tenant["id"]
        dek1 = await pii_keys.ensure_tenant_dek(tid, db_session)
        await db_session.commit()
        pii_keys._clear_cache()  # force a DB re-read rather than cache hit
        dek2 = await pii_keys.ensure_tenant_dek(tid, db_session)
        assert dek1 == dek2
        rows = (
            (
                await db_session.execute(
                    select(TenantEncryptionKey).where(
                        TenantEncryptionKey.tenant_id == tid
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(rows) == 1

    @pytest.mark.asyncio
    async def test_load_all_repopulates_cache(self, db_session, test_tenant):
        tid = test_tenant["id"]
        dek = await pii_keys.ensure_tenant_dek(tid, db_session)
        await db_session.commit()
        pii_keys._clear_cache()
        assert pii_keys.get_cached_dek(tid) is None

        loaded = await pii_keys.load_all_tenant_deks(db_session)
        assert loaded >= 1
        assert pii_keys.get_cached_dek(tid) == dek

    @pytest.mark.asyncio
    async def test_initialize_provisions_missing_tenant(
        self, db_session, test_tenant
    ):
        tid = test_tenant["id"]
        result = await pii_keys.initialize_pii_keys(db_session)
        assert result["loaded"] >= 0 and result["provisioned"] >= 0
        # After init, the test tenant has a cached DEK.
        assert pii_keys.get_cached_dek(tid) is not None
