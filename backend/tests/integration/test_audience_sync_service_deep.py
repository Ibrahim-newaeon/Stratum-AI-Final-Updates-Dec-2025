# =============================================================================
# Stratum AI - Audience Sync Service Deep Integration Tests (#342 Batch 5+6)
# =============================================================================
"""DB-backed integration tests for ``AudienceSyncService``.

Seeds real Postgres rows (tenant, CDP segment, profiles with hashed PII
identifiers, memberships, encrypted sync credentials) and drives the sync
orchestrator end-to-end with the Meta connector's HTTP respx-mocked at the
Graph API boundary. The unit suite (``tests/unit/test_audience_sync.py``)
covers the pure not-found/no-credentials guards with mocked sessions; this
file covers the orchestration bodies those mocks skip:

- ``create_platform_audience``: full create->upload->info flow, sync-job
  persistence, hashed payloads, failure recording (graceful and exception).
- ``sync_platform_audience``: update/replace/delete operations, partial
  failure accounting, next_sync_at scheduling, exception commit-persistence.
- ``delete_platform_audience``: platform deletion incl. connector failure
  tolerance and the no-credentials/no-platform-id skips.
- Query surfaces and the batched ``_get_segment_profiles`` helper.

Behavior corrected in #540 and asserted here:
- ``list_platform_audiences``: the count query now applies the ``platform``
  filter as well as ``segment_id``, so ``total`` matches the filtered rows.
  See ``test_list_by_platform_total_respects_platform_filter``.
"""

import hashlib
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
import pytest
import respx
from sqlalchemy import select

from app.models.audience_sync import (
    AudienceSyncCredential,
    AudienceSyncJob,
    PlatformAudience,
    SyncOperation,
    SyncStatus,
)
from app.models.cdp import (
    CDPConsent,
    CDPProfile,
    CDPProfileIdentifier,
    CDPSegment,
    CDPSegmentMembership,
    ConsentType,
)
from app.services.cdp.audience_sync.meta_connector import MetaAudienceConnector
from app.services.cdp.audience_sync.service import AudienceSyncService

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

GRAPH = "https://graph.facebook.com/v18.0"


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


# =============================================================================
# Seed helpers
# =============================================================================


async def _seed_segment(db, tenant_id, name="High Value") -> CDPSegment:
    segment = CDPSegment(tenant_id=tenant_id, name=name, rules={}, tags=[])
    db.add(segment)
    await db.flush()
    return segment


async def _seed_profile(
    db,
    tenant_id,
    segment,
    identifiers=(),
    membership_active=True,
    consent=ConsentType.ADS.value,
    consent_granted=True,
) -> CDPProfile:
    """Create a profile with identifiers, a segment membership, and consent.

    ``consent`` defaults to a granted ADS consent because that is the only
    state in which a profile is syncable — the tests that predate the consent
    gate are all about batching, ordering and tenant scoping, and would
    otherwise be asserting against an empty set. Pass ``consent=None`` for the
    no-record case or ``consent_granted=False`` for the revoked case.
    """
    profile = CDPProfile(tenant_id=tenant_id, profile_data={}, computed_traits={})
    db.add(profile)
    await db.flush()
    for identifier_type, raw in identifiers:
        db.add(
            CDPProfileIdentifier(
                tenant_id=tenant_id,
                profile_id=profile.id,
                identifier_type=identifier_type,
                identifier_value=raw,
                identifier_hash=_sha(raw),
            )
        )
    db.add(
        CDPSegmentMembership(
            tenant_id=tenant_id,
            segment_id=segment.id,
            profile_id=profile.id,
            is_active=membership_active,
        )
    )
    if consent is not None:
        now = datetime.now(UTC)
        db.add(
            CDPConsent(
                tenant_id=tenant_id,
                profile_id=profile.id,
                consent_type=consent,
                granted=consent_granted,
                granted_at=now if consent_granted else None,
                revoked_at=None if consent_granted else now,
                source="test",
            )
        )
    await db.flush()
    return profile


async def _seed_credential(
    db,
    tenant_id,
    platform="meta",
    ad_account_id="act_123",
    is_active=True,
    config=None,
) -> AudienceSyncCredential:
    cred = AudienceSyncCredential(
        tenant_id=tenant_id,
        platform=platform,
        ad_account_id=ad_account_id,
        ad_account_name=f"{platform} account",
        is_active=is_active,
        config=config if config is not None else {"app_secret": "shh"},
    )
    cred.set_access_token("tok-plain")
    db.add(cred)
    await db.flush()
    return cred


async def _seed_audience(
    db,
    tenant_id,
    segment,
    platform_audience_id="aud_ext_1",
    ad_account_id="act_123",
    **kwargs,
) -> PlatformAudience:
    audience = PlatformAudience(
        tenant_id=tenant_id,
        segment_id=segment.id,
        platform="meta",
        platform_audience_id=platform_audience_id,
        platform_audience_name="Synced Audience",
        ad_account_id=ad_account_id,
        platform_config={},
        **kwargs,
    )
    db.add(audience)
    await db.flush()
    return audience


async def _seed_second_tenant(db):
    from app.base_models import Tenant

    tenant = Tenant(
        name="Other Tenant",
        slug=f"other-{uuid4().hex[:8]}",
        plan="starter",
        max_users=5,
        max_campaigns=10,
    )
    db.add(tenant)
    await db.flush()
    return tenant


async def _get_jobs(db, platform_audience_id) -> list[AudienceSyncJob]:
    result = await db.execute(
        select(AudienceSyncJob).where(
            AudienceSyncJob.platform_audience_id == platform_audience_id
        )
    )
    return list(result.scalars().all())


@pytest.fixture
def svc(db_session, test_tenant) -> AudienceSyncService:
    return AudienceSyncService(db_session, test_tenant["id"])


# =============================================================================
# create_platform_audience
# =============================================================================


class TestCreatePlatformAudience:
    async def test_full_create_flow_persists_audience_and_job(
        self, db_session, test_tenant, svc
    ):
        tenant_id = test_tenant["id"]
        segment = await _seed_segment(db_session, tenant_id)
        await _seed_credential(db_session, tenant_id)

        # 3 syncable profiles + 1 unmapped identifier type + 1 inactive member
        await _seed_profile(
            db_session, tenant_id, segment, [("email", "user1@example.com")]
        )
        await _seed_profile(db_session, tenant_id, segment, [("phone", "+15551230001")])
        await _seed_profile(
            db_session, tenant_id, segment, [("device_id", "gaid-abc-123")]
        )
        await _seed_profile(db_session, tenant_id, segment, [("address", "1 Main St")])
        await _seed_profile(
            db_session,
            tenant_id,
            segment,
            [("email", "inactive@example.com")],
            membership_active=False,
        )

        with respx.mock:
            respx.post(f"{GRAPH}/act_123/customaudiences").mock(
                return_value=httpx.Response(200, json={"id": "aud_meta_1"})
            )
            users_route = respx.post(f"{GRAPH}/aud_meta_1/users").mock(
                return_value=httpx.Response(
                    200, json={"num_received": 3, "num_invalid_entries": 0}
                )
            )
            respx.get(f"{GRAPH}/aud_meta_1").mock(
                return_value=httpx.Response(200, json={"approximate_count": 250})
            )

            audience, job = await svc.create_platform_audience(
                segment_id=segment.id,
                platform="meta",
                ad_account_id="act_123",
                audience_name="VIP Buyers",
                description="Top spenders",
                sync_interval_hours=12,
            )

        # Platform audience updated with sync result
        assert audience.platform_audience_id == "aud_meta_1"
        assert audience.last_sync_status == SyncStatus.COMPLETED.value
        assert audience.platform_size == 250
        assert audience.last_sync_at is not None
        expected_next = datetime.now(UTC) + timedelta(hours=12)
        assert abs((audience.next_sync_at - expected_next).total_seconds()) < 300

        # Sync job persisted with metrics
        assert job.operation == SyncOperation.CREATE.value
        assert job.status == SyncStatus.COMPLETED.value
        assert job.triggered_by == "manual"
        assert job.profiles_total == 3  # unmapped + inactive excluded
        assert job.profiles_sent == 3
        assert job.profiles_added == 3
        assert job.started_at is not None and job.completed_at is not None

        # Uploaded payload carries SHA-256 hashes, never raw PII
        import json as _json

        payload = _json.loads(users_route.calls[0].request.content)
        rows = payload["payload"]["data"]
        assert [_sha("user1@example.com"), "", ""] in rows
        assert ["", _sha("+15551230001"), ""] in rows
        assert ["", "", _sha("gaid-abc-123")] in rows
        assert len(rows) == 3
        raw_blob = users_route.calls[0].request.content.decode()
        assert "user1@example.com" not in raw_blob

        # Row is queryable
        found = await db_session.execute(
            select(PlatformAudience).where(PlatformAudience.id == audience.id)
        )
        assert found.scalar_one() is audience

    async def test_create_segment_not_found(self, svc):
        with pytest.raises(ValueError, match="not found"):
            await svc.create_platform_audience(
                segment_id=uuid4(),
                platform="meta",
                ad_account_id="act_123",
                audience_name="X",
            )

    async def test_create_inactive_credential_rejected(
        self, db_session, test_tenant, svc
    ):
        segment = await _seed_segment(db_session, test_tenant["id"])
        await _seed_credential(db_session, test_tenant["id"], is_active=False)

        with pytest.raises(ValueError, match="No credentials"):
            await svc.create_platform_audience(
                segment_id=segment.id,
                platform="meta",
                ad_account_id="act_123",
                audience_name="X",
            )

    async def test_create_platform_failure_recorded_without_raise(
        self, db_session, test_tenant, svc
    ):
        """Connector-level failure (no id returned) marks job FAILED gracefully."""
        tenant_id = test_tenant["id"]
        segment = await _seed_segment(db_session, tenant_id)
        await _seed_credential(db_session, tenant_id)
        await _seed_profile(
            db_session, tenant_id, segment, [("email", "f1@example.com")]
        )

        with respx.mock:
            respx.post(f"{GRAPH}/act_123/customaudiences").mock(
                return_value=httpx.Response(200, json={})  # no "id"
            )

            audience, job = await svc.create_platform_audience(
                segment_id=segment.id,
                platform="meta",
                ad_account_id="act_123",
                audience_name="No ID",
            )

        assert job.status == SyncStatus.FAILED.value
        assert "No audience ID" in job.error_message
        assert audience.platform_audience_id is None
        assert audience.last_sync_status == SyncStatus.FAILED.value

    async def test_create_unexpected_exception_commits_failure_record(
        self, db_session, test_tenant, svc
    ):
        """Non-HTTP exceptions re-raise but the failure record is committed."""
        tenant_id = test_tenant["id"]
        segment = await _seed_segment(db_session, tenant_id)
        await _seed_credential(db_session, tenant_id)
        await _seed_profile(
            db_session, tenant_id, segment, [("email", "boom@example.com")]
        )

        with respx.mock:
            respx.post(f"{GRAPH}/act_123/customaudiences").mock(
                side_effect=RuntimeError("kaboom")
            )

            with pytest.raises(RuntimeError, match="kaboom"):
                await svc.create_platform_audience(
                    segment_id=segment.id,
                    platform="meta",
                    ad_account_id="act_123",
                    audience_name="Boom",
                )

        result = await db_session.execute(
            select(PlatformAudience).where(
                PlatformAudience.tenant_id == tenant_id,
                PlatformAudience.platform_audience_name == "Boom",
            )
        )
        audience = result.scalar_one()
        assert audience.last_sync_status == SyncStatus.FAILED.value
        assert "kaboom" in audience.last_sync_error
        jobs = await _get_jobs(db_session, audience.id)
        assert len(jobs) == 1
        assert jobs[0].status == SyncStatus.FAILED.value
        assert "kaboom" in jobs[0].error_message


# =============================================================================
# sync_platform_audience
# =============================================================================


class TestSyncPlatformAudience:
    async def test_update_happy_path_schedules_next_sync(
        self, db_session, test_tenant, svc
    ):
        tenant_id = test_tenant["id"]
        segment = await _seed_segment(db_session, tenant_id)
        await _seed_credential(db_session, tenant_id)
        audience = await _seed_audience(
            db_session, tenant_id, segment, auto_sync=True, sync_interval_hours=6
        )
        await _seed_profile(
            db_session, tenant_id, segment, [("email", "u-upd@example.com")]
        )

        with respx.mock:
            respx.post(f"{GRAPH}/aud_ext_1/users").mock(
                return_value=httpx.Response(200, json={"num_received": 1})
            )
            respx.get(f"{GRAPH}/aud_ext_1").mock(
                return_value=httpx.Response(200, json={"approximate_count": 10})
            )

            job = await svc.sync_platform_audience(
                audience.id,
                operation=SyncOperation.UPDATE,
                triggered_by="auto",
                triggered_by_user_id=42,
            )

        assert job.status == SyncStatus.COMPLETED.value
        assert job.operation == "update"
        assert job.triggered_by == "auto"
        assert job.triggered_by_user_id == 42
        assert job.profiles_sent == 1
        assert audience.last_sync_status == SyncStatus.COMPLETED.value
        expected_next = datetime.now(UTC) + timedelta(hours=6)
        assert abs((audience.next_sync_at - expected_next).total_seconds()) < 300

    async def test_update_partial_failure_accounting(
        self, db_session, test_tenant, svc, monkeypatch
    ):
        """Mid-batch HTTP failure with prior invalids => PARTIAL status."""
        monkeypatch.setattr(MetaAudienceConnector, "BATCH_SIZE", 2)
        tenant_id = test_tenant["id"]
        segment = await _seed_segment(db_session, tenant_id)
        await _seed_credential(db_session, tenant_id)
        audience = await _seed_audience(db_session, tenant_id, segment)
        for i in range(4):
            await _seed_profile(
                db_session, tenant_id, segment, [("email", f"part{i}@example.com")]
            )

        with respx.mock:
            respx.post(f"{GRAPH}/aud_ext_1/users").mock(
                side_effect=[
                    httpx.Response(
                        200, json={"num_received": 2, "num_invalid_entries": 1}
                    ),
                    httpx.Response(400, json={"error": {"message": "rate limited"}}),
                ]
            )

            job = await svc.sync_platform_audience(audience.id)

        assert job.status == SyncStatus.PARTIAL.value
        assert job.profiles_total == 4
        assert job.profiles_sent == 2
        assert job.profiles_added == 1
        assert job.profiles_failed == 1
        assert job.error_message == "rate limited"
        assert audience.last_sync_status == SyncStatus.PARTIAL.value

    async def test_update_without_platform_id_commits_failed_job(
        self, db_session, test_tenant, svc
    ):
        tenant_id = test_tenant["id"]
        segment = await _seed_segment(db_session, tenant_id)
        await _seed_credential(db_session, tenant_id)
        audience = await _seed_audience(
            db_session, tenant_id, segment, platform_audience_id=None
        )

        with pytest.raises(ValueError, match="No platform audience ID"):
            await svc.sync_platform_audience(audience.id)

        jobs = await _get_jobs(db_session, audience.id)
        assert len(jobs) == 1
        assert jobs[0].status == SyncStatus.FAILED.value
        assert "No platform audience ID" in jobs[0].error_message
        assert audience.last_sync_status == SyncStatus.FAILED.value
        assert "No platform audience ID" in audience.last_sync_error

    async def test_replace_operation(self, db_session, test_tenant, svc):
        tenant_id = test_tenant["id"]
        segment = await _seed_segment(db_session, tenant_id)
        await _seed_credential(db_session, tenant_id)
        audience = await _seed_audience(db_session, tenant_id, segment)
        for i in range(2):
            await _seed_profile(
                db_session, tenant_id, segment, [("email", f"rep{i}@example.com")]
            )

        with respx.mock:
            respx.post(f"{GRAPH}/aud_ext_1/usersreplace").mock(
                return_value=httpx.Response(200, json={"session_id": "s1"})
            )
            respx.post(f"{GRAPH}/aud_ext_1/users").mock(
                return_value=httpx.Response(200, json={})
            )

            job = await svc.sync_platform_audience(
                audience.id, operation=SyncOperation.REPLACE
            )

        assert job.status == SyncStatus.COMPLETED.value
        assert job.operation == "replace"
        assert job.profiles_sent == 2
        assert job.profiles_added == 2

    async def test_delete_operation(self, db_session, test_tenant, svc):
        tenant_id = test_tenant["id"]
        segment = await _seed_segment(db_session, tenant_id)
        await _seed_credential(db_session, tenant_id)
        audience = await _seed_audience(db_session, tenant_id, segment)

        with respx.mock:
            respx.delete(f"{GRAPH}/aud_ext_1").mock(
                return_value=httpx.Response(200, json={"success": True})
            )

            job = await svc.sync_platform_audience(
                audience.id, operation=SyncOperation.DELETE
            )

        assert job.status == SyncStatus.COMPLETED.value
        assert job.operation == "delete"

    async def test_empty_segment_syncs_zero_profiles(
        self, db_session, test_tenant, svc
    ):
        tenant_id = test_tenant["id"]
        segment = await _seed_segment(db_session, tenant_id)
        await _seed_credential(db_session, tenant_id)
        audience = await _seed_audience(db_session, tenant_id, segment, auto_sync=False)

        with respx.mock:
            # No user batches uploaded; only the audience-info lookup fires.
            respx.get(f"{GRAPH}/aud_ext_1").mock(
                return_value=httpx.Response(200, json={"approximate_count": 0})
            )

            job = await svc.sync_platform_audience(audience.id)

        assert job.status == SyncStatus.COMPLETED.value
        assert job.profiles_total == 0
        assert job.profiles_sent == 0
        # auto_sync=False -> no next sync scheduled
        assert audience.next_sync_at is None

    async def test_sync_audience_not_found(self, svc):
        with pytest.raises(ValueError, match="not found"):
            await svc.sync_platform_audience(uuid4())

    async def test_sync_segment_invisible_across_tenants(
        self, db_session, test_tenant, svc
    ):
        """Audience pointing at another tenant's segment fails the segment guard."""
        other = await _seed_second_tenant(db_session)
        foreign_segment = await _seed_segment(db_session, other.id)
        audience = await _seed_audience(db_session, test_tenant["id"], foreign_segment)

        with pytest.raises(ValueError, match=r"Segment .* not found"):
            await svc.sync_platform_audience(audience.id)

    async def test_sync_without_credentials(self, db_session, test_tenant, svc):
        tenant_id = test_tenant["id"]
        segment = await _seed_segment(db_session, tenant_id)
        audience = await _seed_audience(db_session, tenant_id, segment)

        with pytest.raises(ValueError, match="No credentials"):
            await svc.sync_platform_audience(audience.id)

    @pytest.mark.parametrize("operation", [SyncOperation.REPLACE, SyncOperation.DELETE])
    async def test_replace_and_delete_require_platform_id(
        self, db_session, test_tenant, svc, operation
    ):
        tenant_id = test_tenant["id"]
        segment = await _seed_segment(db_session, tenant_id)
        await _seed_credential(db_session, tenant_id)
        audience = await _seed_audience(
            db_session, tenant_id, segment, platform_audience_id=None
        )

        with pytest.raises(ValueError, match="No platform audience ID"):
            await svc.sync_platform_audience(audience.id, operation=operation)

        jobs = await _get_jobs(db_session, audience.id)
        assert len(jobs) == 1
        assert jobs[0].status == SyncStatus.FAILED.value
        assert jobs[0].operation == operation.value

    async def test_execute_sync_job_unknown_operation(
        self, db_session, test_tenant, svc
    ):
        tenant_id = test_tenant["id"]
        segment = await _seed_segment(db_session, tenant_id)
        credential = await _seed_credential(db_session, tenant_id)
        audience = await _seed_audience(db_session, tenant_id, segment)
        job = AudienceSyncJob(
            tenant_id=tenant_id,
            platform_audience_id=audience.id,
            operation="bogus",
            status=SyncStatus.PENDING.value,
            error_details={},
            platform_response={},
        )
        db_session.add(job)
        await db_session.flush()

        with pytest.raises(ValueError, match="Unknown operation"):
            await svc._execute_sync_job(
                job, audience, credential, segment, operation="bogus"
            )

    async def test_sync_cross_tenant_audience_not_visible(
        self, db_session, test_tenant, svc
    ):
        other = await _seed_second_tenant(db_session)
        other_segment = await _seed_segment(db_session, other.id)
        other_audience = await _seed_audience(db_session, other.id, other_segment)

        with pytest.raises(ValueError, match="not found"):
            await svc.sync_platform_audience(other_audience.id)


# =============================================================================
# delete_platform_audience
# =============================================================================


class TestDeletePlatformAudience:
    async def test_delete_with_platform_deletion(self, db_session, test_tenant, svc):
        tenant_id = test_tenant["id"]
        segment = await _seed_segment(db_session, tenant_id)
        await _seed_credential(db_session, tenant_id)
        audience = await _seed_audience(db_session, tenant_id, segment)

        with respx.mock:
            del_route = respx.delete(f"{GRAPH}/aud_ext_1").mock(
                return_value=httpx.Response(200, json={"success": True})
            )

            assert await svc.delete_platform_audience(audience.id) is True

        assert del_route.called
        result = await db_session.execute(
            select(PlatformAudience).where(PlatformAudience.id == audience.id)
        )
        assert result.scalar_one_or_none() is None

    async def test_delete_tolerates_platform_error(self, db_session, test_tenant, svc):
        tenant_id = test_tenant["id"]
        segment = await _seed_segment(db_session, tenant_id)
        await _seed_credential(db_session, tenant_id)
        audience = await _seed_audience(db_session, tenant_id, segment)

        with respx.mock:
            respx.delete(f"{GRAPH}/aud_ext_1").mock(
                side_effect=httpx.ConnectError("platform down")
            )

            assert await svc.delete_platform_audience(audience.id) is True

        result = await db_session.execute(
            select(PlatformAudience).where(PlatformAudience.id == audience.id)
        )
        assert result.scalar_one_or_none() is None

    async def test_delete_tolerates_connector_level_exception(
        self, db_session, test_tenant, svc, monkeypatch
    ):
        """A ConnectionError escaping the connector is swallowed by the service.

        Meta's connector catches transport errors internally, so the service's
        own except-branch is only reachable when the connector (or credential
        lookup) itself raises — simulated here at the connector method level.
        """

        async def _boom(self, audience_id):
            raise ConnectionError("connector meltdown")

        monkeypatch.setattr(MetaAudienceConnector, "delete_audience", _boom)
        tenant_id = test_tenant["id"]
        segment = await _seed_segment(db_session, tenant_id)
        await _seed_credential(db_session, tenant_id)
        audience = await _seed_audience(db_session, tenant_id, segment)

        assert await svc.delete_platform_audience(audience.id) is True

        result = await db_session.execute(
            select(PlatformAudience).where(PlatformAudience.id == audience.id)
        )
        assert result.scalar_one_or_none() is None

    async def test_delete_without_credentials_skips_platform_call(
        self, db_session, test_tenant, svc
    ):
        tenant_id = test_tenant["id"]
        segment = await _seed_segment(db_session, tenant_id)
        audience = await _seed_audience(db_session, tenant_id, segment)

        # No respx routes: any HTTP attempt would raise under respx.mock
        with respx.mock:
            assert await svc.delete_platform_audience(audience.id) is True

    async def test_delete_without_platform_id_skips_platform_call(
        self, db_session, test_tenant, svc
    ):
        tenant_id = test_tenant["id"]
        segment = await _seed_segment(db_session, tenant_id)
        await _seed_credential(db_session, tenant_id)
        audience = await _seed_audience(
            db_session, tenant_id, segment, platform_audience_id=None
        )

        with respx.mock:
            assert await svc.delete_platform_audience(audience.id) is True

    async def test_delete_local_only(self, db_session, test_tenant, svc):
        tenant_id = test_tenant["id"]
        segment = await _seed_segment(db_session, tenant_id)
        audience = await _seed_audience(db_session, tenant_id, segment)

        assert (
            await svc.delete_platform_audience(audience.id, delete_from_platform=False)
            is True
        )

    async def test_delete_not_found(self, svc):
        assert await svc.delete_platform_audience(uuid4()) is False


# =============================================================================
# Query surfaces
# =============================================================================


class TestQuerySurfaces:
    async def _seed_three_audiences(self, db, tenant_id):
        seg_a = await _seed_segment(db, tenant_id, name="Seg A")
        seg_b = await _seed_segment(db, tenant_id, name="Seg B")
        seg_c = await _seed_segment(db, tenant_id, name="Seg C")
        a1 = await _seed_audience(db, tenant_id, seg_a, platform_audience_id="m1")
        a2 = await _seed_audience(db, tenant_id, seg_b, platform_audience_id="m2")
        a3 = PlatformAudience(
            tenant_id=tenant_id,
            segment_id=seg_c.id,
            platform="google",
            platform_audience_name="G list",
            ad_account_id="goog_1",
            platform_config={},
        )
        db.add(a3)
        await db.flush()
        return seg_a, a1, a2, a3

    async def test_list_all_and_by_segment(self, db_session, test_tenant, svc):
        tenant_id = test_tenant["id"]
        seg_a, a1, _, _ = await self._seed_three_audiences(db_session, tenant_id)

        audiences, total = await svc.list_platform_audiences()
        assert total == 3
        assert len(audiences) == 3

        audiences, total = await svc.list_platform_audiences(segment_id=seg_a.id)
        assert total == 1
        assert audiences[0].id == a1.id

        # Pagination
        page, total = await svc.list_platform_audiences(limit=2, offset=2)
        assert total == 3
        assert len(page) == 1

    async def test_list_by_platform_total_respects_platform_filter(
        self, db_session, test_tenant, svc
    ):
        """The platform filter is now applied to the count query too, so
        ``total`` matches the filtered row set (service.py list_platform_audiences).
        Repro: seed 2 meta + 1 google, filter platform="meta" -> total 2.
        """
        tenant_id = test_tenant["id"]
        await self._seed_three_audiences(db_session, tenant_id)

        audiences, total = await svc.list_platform_audiences(platform="meta")
        assert len(audiences) == 2
        assert {a.platform for a in audiences} == {"meta"}
        assert total == 2  # count query now respects the platform filter

    async def test_list_excludes_other_tenants(self, db_session, test_tenant, svc):
        other = await _seed_second_tenant(db_session)
        other_seg = await _seed_segment(db_session, other.id)
        await _seed_audience(db_session, other.id, other_seg)

        audiences, total = await svc.list_platform_audiences()
        assert total == 0
        assert audiences == []

    async def test_sync_history_ordering_limit_and_tenant_scope(
        self, db_session, test_tenant, svc
    ):
        tenant_id = test_tenant["id"]
        segment = await _seed_segment(db_session, tenant_id)
        audience = await _seed_audience(db_session, tenant_id, segment)

        now = datetime.now(UTC)
        for i, op in enumerate(["create", "update", "replace"]):
            job = AudienceSyncJob(
                tenant_id=tenant_id,
                platform_audience_id=audience.id,
                operation=op,
                status=SyncStatus.COMPLETED.value,
                error_details={},
                platform_response={},
            )
            job.created_at = now - timedelta(minutes=10 - i)
            db_session.add(job)

        # Same audience id but a foreign tenant_id must be filtered out
        other = await _seed_second_tenant(db_session)
        foreign = AudienceSyncJob(
            tenant_id=other.id,
            platform_audience_id=audience.id,
            operation="update",
            status=SyncStatus.FAILED.value,
            error_details={},
            platform_response={},
        )
        db_session.add(foreign)
        await db_session.flush()

        jobs = await svc.get_sync_history(audience.id)
        assert len(jobs) == 3
        assert [j.operation for j in jobs] == ["replace", "update", "create"]

        limited = await svc.get_sync_history(audience.id, limit=2)
        assert len(limited) == 2

    async def test_connected_platforms_grouping(self, db_session, test_tenant, svc):
        tenant_id = test_tenant["id"]
        await _seed_credential(db_session, tenant_id, ad_account_id="act_1")
        await _seed_credential(db_session, tenant_id, ad_account_id="act_2")
        await _seed_credential(
            db_session, tenant_id, platform="google", ad_account_id="goog_1"
        )
        await _seed_credential(
            db_session, tenant_id, ad_account_id="act_dead", is_active=False
        )

        platforms = await svc.get_connected_platforms()
        assert len(platforms) == 2
        meta = next(p for p in platforms if p["platform"] == "meta")
        assert len(meta["ad_accounts"]) == 2
        assert {a["ad_account_id"] for a in meta["ad_accounts"]} == {"act_1", "act_2"}
        google = next(p for p in platforms if p["platform"] == "google")
        assert google["ad_accounts"] == [
            {"ad_account_id": "goog_1", "ad_account_name": "google account"}
        ]


# =============================================================================
# Consent gating (GDPR-01)
# =============================================================================


class TestConsentGate:
    """Only profiles holding advertising consent may leave for a platform.

    The consent record already existed and was already written on ingest; it
    was simply never read on the way out. These tests pin the four states that
    decide whether a person's hashed email is handed to Meta.
    """

    async def test_no_consent_record_is_withheld(self, db_session, test_tenant, svc):
        tenant_id = test_tenant["id"]
        segment = await _seed_segment(db_session, tenant_id)
        await _seed_profile(
            db_session,
            tenant_id,
            segment,
            [("email", "silent@example.com")],
            consent=None,
        )

        assert await svc._get_segment_profiles(segment.id) == []
        assert await svc._count_consent_suppressed(segment.id) == 1

    async def test_revoked_consent_is_withheld(self, db_session, test_tenant, svc):
        tenant_id = test_tenant["id"]
        segment = await _seed_segment(db_session, tenant_id)
        await _seed_profile(
            db_session,
            tenant_id,
            segment,
            [("email", "optout@example.com")],
            consent_granted=False,
        )

        assert await svc._get_segment_profiles(segment.id) == []
        assert await svc._count_consent_suppressed(segment.id) == 1

    async def test_ads_and_all_consent_both_permit_sync(
        self, db_session, test_tenant, svc
    ):
        tenant_id = test_tenant["id"]
        segment = await _seed_segment(db_session, tenant_id)
        ads = await _seed_profile(
            db_session,
            tenant_id,
            segment,
            [("email", "ads@example.com")],
            consent=ConsentType.ADS.value,
        )
        blanket = await _seed_profile(
            db_session,
            tenant_id,
            segment,
            [("email", "all@example.com")],
            consent=ConsentType.ALL.value,
        )

        fetched = await svc._get_segment_profiles(segment.id)
        assert {p.id for p in fetched} == {ads.id, blanket.id}
        assert await svc._count_consent_suppressed(segment.id) == 0

    async def test_unrelated_consent_type_does_not_permit_sync(
        self, db_session, test_tenant, svc
    ):
        """Consenting to analytics is not consenting to be sold to Meta."""
        tenant_id = test_tenant["id"]
        segment = await _seed_segment(db_session, tenant_id)
        await _seed_profile(
            db_session,
            tenant_id,
            segment,
            [("email", "analytics-only@example.com")],
            consent=ConsentType.ANALYTICS.value,
        )

        assert await svc._get_segment_profiles(segment.id) == []
        assert await svc._count_consent_suppressed(segment.id) == 1

    async def test_another_tenants_consent_does_not_leak(
        self, db_session, test_tenant, svc
    ):
        """The consent subquery is tenant-scoped, like every other CDP read."""
        tenant_id = test_tenant["id"]
        segment = await _seed_segment(db_session, tenant_id)
        profile = await _seed_profile(
            db_session,
            tenant_id,
            segment,
            [("email", "borrowed@example.com")],
            consent=None,
        )
        other = await _seed_second_tenant(db_session)
        db_session.add(
            CDPConsent(
                tenant_id=other.id,
                profile_id=profile.id,
                consent_type=ConsentType.ADS.value,
                granted=True,
                granted_at=datetime.now(UTC),
                source="test",
            )
        )
        await db_session.flush()

        assert await svc._get_segment_profiles(segment.id) == []

    async def test_suppressed_count_recorded_on_sync_job(
        self, db_session, test_tenant, svc
    ):
        tenant_id = test_tenant["id"]
        segment = await _seed_segment(db_session, tenant_id)
        await _seed_profile(
            db_session, tenant_id, segment, [("email", "yes@example.com")]
        )
        await _seed_profile(
            db_session,
            tenant_id,
            segment,
            [("email", "no@example.com")],
            consent=None,
        )
        audience = await _seed_audience(db_session, tenant_id, segment)
        await _seed_credential(db_session, tenant_id)

        with respx.mock:
            respx.post(f"{GRAPH}/aud_ext_1/users").mock(
                return_value=httpx.Response(200, json={"num_received": 1})
            )
            respx.get(f"{GRAPH}/aud_ext_1").mock(
                return_value=httpx.Response(200, json={"approximate_count": 10})
            )
            job = await svc.sync_platform_audience(
                audience.id, operation=SyncOperation.UPDATE
            )

        assert job.profiles_total == 1
        assert job.profiles_suppressed == 1


# =============================================================================
# Erasure propagation (GDPR-02)
# =============================================================================


class TestErasurePropagation:
    """Deleting a profile locally must also pull it out of the ad platforms.

    ``remove_users`` was implemented on all four connectors and called from
    nowhere, so an erased subject's hashed email lived on in Meta indefinitely.
    """

    async def test_removes_from_every_audience_and_reports_success(
        self, db_session, test_tenant, svc
    ):
        tenant_id = test_tenant["id"]
        segment = await _seed_segment(db_session, tenant_id)
        profile = await _seed_profile(
            db_session,
            tenant_id,
            segment,
            [("email", "erase@example.com"), ("phone", "+15550001111")],
        )
        first = await _seed_audience(db_session, tenant_id, segment)
        second = await _seed_audience(
            db_session, tenant_id, segment, platform_audience_id="aud_ext_2"
        )
        await _seed_credential(db_session, tenant_id)

        with respx.mock:
            for audience in (first, second):
                respx.delete(f"{GRAPH}/{audience.platform_audience_id}/users").mock(
                    return_value=httpx.Response(200, json={"num_received": 1})
                )
            outcomes = await svc.erase_profile_from_platforms(profile.id)

        assert len(outcomes) == 2
        assert all(o["removed"] for o in outcomes)
        assert {o["platform_audience_id"] for o in outcomes} == {
            "aud_ext_1",
            "aud_ext_2",
        }

    async def test_platform_failure_is_reported_not_raised(
        self, db_session, test_tenant, svc
    ):
        """A dead platform must not block the local erasure that follows."""
        tenant_id = test_tenant["id"]
        segment = await _seed_segment(db_session, tenant_id)
        profile = await _seed_profile(
            db_session, tenant_id, segment, [("email", "erase2@example.com")]
        )
        audience = await _seed_audience(db_session, tenant_id, segment)
        await _seed_credential(db_session, tenant_id)

        with respx.mock:
            respx.delete(f"{GRAPH}/{audience.platform_audience_id}/users").mock(
                return_value=httpx.Response(500, json={"error": "boom"})
            )
            outcomes = await svc.erase_profile_from_platforms(profile.id)

        assert len(outcomes) == 1
        assert outcomes[0]["removed"] is False
        assert outcomes[0]["error"]

    async def test_missing_credentials_reported_not_raised(
        self, db_session, test_tenant, svc
    ):
        tenant_id = test_tenant["id"]
        segment = await _seed_segment(db_session, tenant_id)
        profile = await _seed_profile(
            db_session, tenant_id, segment, [("email", "erase3@example.com")]
        )
        await _seed_audience(db_session, tenant_id, segment)

        outcomes = await svc.erase_profile_from_platforms(profile.id)

        assert outcomes == [
            {
                "platform": "meta",
                "ad_account_id": "act_123",
                "platform_audience_id": "aud_ext_1",
                "removed": False,
                "error": "no active credentials",
            }
        ]

    async def test_profile_with_no_syncable_identifiers_skips_platforms(
        self, db_session, test_tenant, svc
    ):
        """Nothing uploadable was ever sent, so there is nothing to recall."""
        tenant_id = test_tenant["id"]
        segment = await _seed_segment(db_session, tenant_id)
        profile = await _seed_profile(
            db_session, tenant_id, segment, [("address", "1 Main St")]
        )
        await _seed_audience(db_session, tenant_id, segment)
        await _seed_credential(db_session, tenant_id)

        assert await svc.erase_profile_from_platforms(profile.id) == []

    async def test_other_tenants_audiences_are_untouched(
        self, db_session, test_tenant, svc
    ):
        tenant_id = test_tenant["id"]
        segment = await _seed_segment(db_session, tenant_id)
        profile = await _seed_profile(
            db_session, tenant_id, segment, [("email", "erase4@example.com")]
        )
        other = await _seed_second_tenant(db_session)
        foreign_segment = await _seed_segment(db_session, other.id, name="Foreign")
        await _seed_audience(
            db_session,
            other.id,
            foreign_segment,
            platform_audience_id="aud_foreign",
        )

        assert await svc.erase_profile_from_platforms(profile.id) == []


# =============================================================================
# Profile-fetch and connector helpers
# =============================================================================


class TestHelpers:
    async def test_get_segment_profiles_batched_ordered_and_scoped(
        self, db_session, test_tenant, svc
    ):
        tenant_id = test_tenant["id"]
        segment = await _seed_segment(db_session, tenant_id)
        profiles = []
        for i in range(5):
            profiles.append(
                await _seed_profile(
                    db_session, tenant_id, segment, [("email", f"b{i}@example.com")]
                )
            )
        # Inactive membership excluded
        await _seed_profile(
            db_session,
            tenant_id,
            segment,
            [("email", "off@example.com")],
            membership_active=False,
        )
        # Cross-tenant profile attached to the same segment excluded
        other = await _seed_second_tenant(db_session)
        foreign_profile = CDPProfile(
            tenant_id=other.id, profile_data={}, computed_traits={}
        )
        db_session.add(foreign_profile)
        await db_session.flush()
        db_session.add(
            CDPSegmentMembership(
                tenant_id=other.id,
                segment_id=segment.id,
                profile_id=foreign_profile.id,
            )
        )
        await db_session.flush()

        fetched = await svc._get_segment_profiles(segment.id, batch_size=2)
        assert len(fetched) == 5
        assert {p.id for p in fetched} == {p.id for p in profiles}
        # Batched fetch keeps deterministic id ordering
        assert [p.id for p in fetched] == sorted(p.id for p in fetched)
        # Identifiers eager-loaded for downstream hashing
        assert fetched[0].identifiers[0].identifier_hash

        capped = await svc._get_segment_profiles(segment.id, limit=3, batch_size=2)
        assert len(capped) == 3

    async def test_profiles_to_audience_users_maps_types(
        self, db_session, test_tenant, svc
    ):
        tenant_id = test_tenant["id"]
        segment = await _seed_segment(db_session, tenant_id)
        await _seed_profile(
            db_session,
            tenant_id,
            segment,
            [
                ("email", "multi@example.com"),
                ("phone", "+15551239999"),
                ("address", "ignored"),
            ],
        )
        await _seed_profile(db_session, tenant_id, segment, [])  # no identifiers

        profiles = await svc._get_segment_profiles(segment.id)
        users = await svc._profiles_to_audience_users(profiles)

        assert len(users) == 1  # identifier-less profile dropped
        hashed = {
            (i.identifier_type.value, i.hashed_value) for i in users[0].identifiers
        }
        assert ("email", _sha("multi@example.com")) in hashed
        assert ("phone", _sha("+15551239999")) in hashed
        assert len(users[0].identifiers) == 2  # "address" type unmapped

    async def test_get_connector_platform_kwargs(self, db_session, test_tenant, svc):
        from app.services.cdp.audience_sync.google_connector import (
            GoogleAudienceConnector,
        )

        meta_cred = await _seed_credential(db_session, test_tenant["id"])
        meta_conn = svc._get_connector("meta", meta_cred)
        assert isinstance(meta_conn, MetaAudienceConnector)
        assert meta_conn.app_secret == "shh"
        assert meta_conn.access_token == "tok-plain"  # decrypted from Fernet

        google_cred = await _seed_credential(
            db_session,
            test_tenant["id"],
            platform="google",
            ad_account_id="goog_9",
            config={"developer_token": "dev-1", "login_customer_id": "cust-1"},
        )
        google_conn = svc._get_connector("google", google_cred)
        assert isinstance(google_conn, GoogleAudienceConnector)

        # Platforms without special kwargs take the plain constructor path
        tiktok_cred = await _seed_credential(
            db_session, test_tenant["id"], platform="tiktok", ad_account_id="tt_1"
        )
        tiktok_conn = svc._get_connector("tiktok", tiktok_cred)
        assert tiktok_conn.PLATFORM_NAME == "tiktok"

        with pytest.raises(ValueError, match="Unknown platform"):
            svc._get_connector("myspace", meta_cred)
