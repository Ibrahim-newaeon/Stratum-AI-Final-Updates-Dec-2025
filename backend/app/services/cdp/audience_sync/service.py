# =============================================================================
# Stratum AI - Unified Audience Sync Service
# =============================================================================
"""
Main service for syncing CDP segments to ad platforms.

Orchestrates audience sync across all supported platforms:
- Meta (Facebook/Instagram)
- Google Ads
- TikTok
- Snapchat

Features:
- Segment-to-audience mapping
- Incremental and full sync support
- Sync job tracking and history
- Automatic retry with exponential backoff
"""

from datetime import UTC, datetime, timedelta
from typing import Any, Optional
from uuid import UUID

import httpx
import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.audience_sync import (
    AudienceSyncCredential,
    AudienceSyncJob,
    PlatformAudience,
    SyncOperation,
    SyncPlatform,
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

from .base import (
    AudienceConfig,
    AudienceSyncResult,
    AudienceUser,
    BaseAudienceConnector,
    IdentifierType,
    UserIdentifier,
)
from .google_connector import GoogleAudienceConnector
from .meta_connector import MetaAudienceConnector
from .snapchat_connector import SnapchatAudienceConnector
from .tiktok_connector import TikTokAudienceConnector

logger = structlog.get_logger()


# Consent types that authorise sending a profile's identifiers to an ad
# platform. ADS is the specific grant; ALL is the global one.
ADVERTISING_CONSENT_TYPES = (ConsentType.ADS.value, ConsentType.ALL.value)


class AudienceSyncService:
    """
    Unified service for syncing CDP segments to ad platforms.
    """

    CONNECTOR_CLASSES = {
        SyncPlatform.META.value: MetaAudienceConnector,
        SyncPlatform.GOOGLE.value: GoogleAudienceConnector,
        SyncPlatform.TIKTOK.value: TikTokAudienceConnector,
        SyncPlatform.SNAPCHAT.value: SnapchatAudienceConnector,
    }

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self.logger = logger.bind(tenant_id=tenant_id)

    # =========================================================================
    # Platform Audience Management
    # =========================================================================

    async def create_platform_audience(
        self,
        segment_id: UUID,
        platform: str,
        ad_account_id: str,
        audience_name: str,
        description: Optional[str] = None,
        auto_sync: bool = True,
        sync_interval_hours: int = 24,
    ) -> tuple[PlatformAudience, AudienceSyncJob]:
        """
        Create a platform audience linked to a CDP segment.
        Creates the audience on the platform and syncs initial users.
        """
        # Validate segment exists
        segment = await self._get_segment(segment_id)
        if not segment:
            raise ValueError(f"Segment {segment_id} not found")

        # Get credentials
        credentials = await self._get_credentials(platform, ad_account_id)
        if not credentials:
            raise ValueError(f"No credentials found for {platform}/{ad_account_id}")

        # Create platform audience record
        platform_audience = PlatformAudience(
            tenant_id=self.tenant_id,
            segment_id=segment_id,
            platform=platform,
            platform_audience_name=audience_name,
            ad_account_id=ad_account_id,
            description=description,
            auto_sync=auto_sync,
            sync_interval_hours=sync_interval_hours,
            next_sync_at=(
                datetime.now(UTC) + timedelta(hours=sync_interval_hours)
                if auto_sync
                else None
            ),
        )
        self.db.add(platform_audience)
        await self.db.flush()

        # Create initial sync job
        sync_job = AudienceSyncJob(
            tenant_id=self.tenant_id,
            platform_audience_id=platform_audience.id,
            operation=SyncOperation.CREATE.value,
            status=SyncStatus.PENDING.value,
            triggered_by="manual",
        )
        self.db.add(sync_job)
        await self.db.flush()

        # Execute the sync
        try:
            result = await self._execute_sync_job(
                sync_job,
                platform_audience,
                credentials,
                segment,
                operation=SyncOperation.CREATE,
            )

            # Update platform audience with result
            platform_audience.platform_audience_id = result.platform_audience_id
            platform_audience.last_sync_at = datetime.now(UTC)
            platform_audience.last_sync_status = sync_job.status
            platform_audience.platform_size = result.audience_size
            platform_audience.matched_size = result.matched_size
            platform_audience.match_rate = result.match_rate

            await self.db.flush()

        except Exception as e:
            sync_job.status = SyncStatus.FAILED.value
            sync_job.error_message = str(e)
            platform_audience.last_sync_status = SyncStatus.FAILED.value
            platform_audience.last_sync_error = str(e)
            # Commit (not just flush): the re-raise aborts the request and
            # get_async_session rolls back, which would erase this failure
            # record — sync history would show no trace of the attempt.
            await self.db.commit()
            raise

        return platform_audience, sync_job

    async def sync_platform_audience(
        self,
        platform_audience_id: UUID,
        operation: SyncOperation = SyncOperation.UPDATE,
        triggered_by: str = "manual",
        triggered_by_user_id: Optional[int] = None,
    ) -> AudienceSyncJob:
        """
        Sync a platform audience with current segment members.
        """
        # Get platform audience
        platform_audience = await self._get_platform_audience(platform_audience_id)
        if not platform_audience:
            raise ValueError(f"Platform audience {platform_audience_id} not found")

        # Get segment
        segment = await self._get_segment(platform_audience.segment_id)
        if not segment:
            raise ValueError(f"Segment {platform_audience.segment_id} not found")

        # Get credentials
        credentials = await self._get_credentials(
            platform_audience.platform,
            platform_audience.ad_account_id,
        )
        if not credentials:
            raise ValueError("No credentials found")

        # Create sync job
        sync_job = AudienceSyncJob(
            tenant_id=self.tenant_id,
            platform_audience_id=platform_audience_id,
            operation=operation.value,
            status=SyncStatus.PENDING.value,
            triggered_by=triggered_by,
            triggered_by_user_id=triggered_by_user_id,
        )
        self.db.add(sync_job)
        await self.db.flush()

        # Execute sync
        try:
            await self._execute_sync_job(
                sync_job,
                platform_audience,
                credentials,
                segment,
                operation=operation,
            )

            # Update platform audience
            platform_audience.last_sync_at = datetime.now(UTC)
            platform_audience.last_sync_status = sync_job.status

            if platform_audience.auto_sync:
                platform_audience.next_sync_at = datetime.now(UTC) + timedelta(
                    hours=platform_audience.sync_interval_hours
                )

            await self.db.flush()

        except Exception as e:
            sync_job.status = SyncStatus.FAILED.value
            sync_job.error_message = str(e)
            platform_audience.last_sync_status = SyncStatus.FAILED.value
            platform_audience.last_sync_error = str(e)
            # Commit (not just flush): the re-raise aborts the request and
            # get_async_session rolls back, which would erase this failure
            # record — sync history would show no trace of the attempt.
            await self.db.commit()
            raise

        return sync_job

    async def delete_platform_audience(
        self,
        platform_audience_id: UUID,
        delete_from_platform: bool = True,
    ) -> bool:
        """
        Delete a platform audience mapping.
        Optionally deletes the audience from the platform.
        """
        platform_audience = await self._get_platform_audience(platform_audience_id)
        if not platform_audience:
            return False

        if delete_from_platform and platform_audience.platform_audience_id:
            try:
                credentials = await self._get_credentials(
                    platform_audience.platform,
                    platform_audience.ad_account_id,
                )
                if credentials:
                    connector = self._get_connector(
                        platform_audience.platform,
                        credentials,
                    )
                    await connector.delete_audience(
                        platform_audience.platform_audience_id
                    )
            except (httpx.HTTPError, ConnectionError, TimeoutError, OSError) as e:
                self.logger.warning(
                    "platform_audience_delete_failed",
                    error=str(e),
                    platform_audience_id=str(platform_audience_id),
                )

        await self.db.delete(platform_audience)
        await self.db.flush()

        return True

    # =========================================================================
    # Erasure Propagation (GDPR Art. 17)
    # =========================================================================

    async def erase_profile_from_platforms(
        self,
        profile_id: UUID,
    ) -> list[dict[str, Any]]:
        """Remove one profile's identifiers from every platform audience.

        Erasing a profile locally does not erase it from Meta, Google, TikTok
        or Snapchat: the hashed email was uploaded to a custom audience and
        stays there until it is explicitly removed. Art. 17(2) requires telling
        the recipients, and ``remove_users`` — implemented by all four
        connectors — is how. It was never called from anywhere until now.

        Every audience for the tenant is attempted, not just those whose
        segment the profile currently belongs to. Membership is deleted as part
        of erasure, and ``add_users`` syncs never remove a profile that left a
        segment, so a stale upload is exactly the case that needs cleaning.
        Removing a hash that is not present is a no-op on all four platforms,
        so the extra calls are safe.

        This is best-effort by design and never raises: local erasure must
        complete even when a platform is down or a credential has expired. The
        per-audience outcome is returned so the caller can record it — an
        unrecorded failure here is an invisible compliance breach.

        Must be called BEFORE the local rows are deleted; it reads the
        profile's identifier hashes.
        """
        result = await self.db.execute(
            select(CDPProfileIdentifier).where(
                CDPProfileIdentifier.profile_id == profile_id,
                CDPProfileIdentifier.tenant_id == self.tenant_id,
            )
        )
        identifiers: list[UserIdentifier] = []
        for row in result.scalars().all():
            mapped = self._map_identifier_type(row.identifier_type)
            if mapped:
                identifiers.append(
                    UserIdentifier(
                        identifier_type=mapped,
                        hashed_value=row.identifier_hash,
                    )
                )

        if not identifiers:
            # Nothing was ever uploadable, so nothing can be on a platform.
            return []

        audiences_result = await self.db.execute(
            select(PlatformAudience).where(
                PlatformAudience.tenant_id == self.tenant_id,
                PlatformAudience.platform_audience_id.isnot(None),
            )
        )
        audiences = list(audiences_result.scalars().all())

        user = AudienceUser(profile_id=str(profile_id), identifiers=identifiers)
        outcomes: list[dict[str, Any]] = []

        for audience in audiences:
            outcome: dict[str, Any] = {
                "platform": audience.platform,
                "ad_account_id": audience.ad_account_id,
                "platform_audience_id": audience.platform_audience_id,
                "removed": False,
                "error": None,
            }
            try:
                credentials = await self._get_credentials(
                    audience.platform,
                    audience.ad_account_id,
                )
                if not credentials:
                    outcome["error"] = "no active credentials"
                else:
                    connector = self._get_connector(audience.platform, credentials)
                    removal = await connector.remove_users(
                        audience.platform_audience_id, [user]
                    )
                    outcome["removed"] = bool(removal.success)
                    if not removal.success:
                        outcome["error"] = removal.error_message or "platform rejected"
            except Exception as exc:
                # Deliberately broad: a connector bug, an auth error or a
                # network fault must not abort erasure of the other audiences,
                # nor of the local rows. Recorded, not swallowed.
                outcome["error"] = f"{type(exc).__name__}: {exc}"

            if not outcome["removed"]:
                self.logger.error(
                    "gdpr_platform_erasure_failed",
                    profile_id=str(profile_id),
                    platform=audience.platform,
                    platform_audience_id=audience.platform_audience_id,
                    error=outcome["error"],
                )

            outcomes.append(outcome)

        return outcomes

    # =========================================================================
    # Sync Job Execution
    # =========================================================================

    async def _execute_sync_job(
        self,
        sync_job: AudienceSyncJob,
        platform_audience: PlatformAudience,
        credentials: AudienceSyncCredential,
        segment: CDPSegment,
        operation: SyncOperation,
    ) -> AudienceSyncResult:
        """
        Execute a sync job against the platform.
        """
        sync_job.status = SyncStatus.PROCESSING.value
        sync_job.started_at = datetime.now(UTC)
        await self.db.flush()

        # Get connector
        connector = self._get_connector(platform_audience.platform, credentials)

        # Get segment profiles (consent-filtered — see _get_segment_profiles)
        profiles = await self._get_segment_profiles(segment.id)
        users = await self._profiles_to_audience_users(profiles)

        suppressed = await self._count_consent_suppressed(segment.id)

        sync_job.profiles_total = len(users)
        sync_job.profiles_suppressed = suppressed

        if suppressed:
            self.logger.info(
                "audience_sync_consent_suppressed",
                platform=platform_audience.platform,
                segment_id=str(segment.id),
                profiles_suppressed=suppressed,
                profiles_eligible=len(users),
            )

        # Execute operation
        result: AudienceSyncResult

        if operation == SyncOperation.CREATE:
            config = AudienceConfig(
                name=platform_audience.platform_audience_name,
                description=platform_audience.description,
            )
            result = await connector.create_audience(config, users)

        elif operation == SyncOperation.UPDATE:
            if not platform_audience.platform_audience_id:
                raise ValueError("No platform audience ID for update operation")
            result = await connector.add_users(
                platform_audience.platform_audience_id, users
            )

        elif operation == SyncOperation.REPLACE:
            if not platform_audience.platform_audience_id:
                raise ValueError("No platform audience ID for replace operation")
            result = await connector.replace_audience(
                platform_audience.platform_audience_id, users
            )

        elif operation == SyncOperation.DELETE:
            if not platform_audience.platform_audience_id:
                raise ValueError("No platform audience ID for delete operation")
            result = await connector.delete_audience(
                platform_audience.platform_audience_id
            )

        else:
            raise ValueError(f"Unknown operation: {operation}")

        # Update sync job with results
        sync_job.completed_at = datetime.now(UTC)
        sync_job.duration_ms = result.duration_ms
        sync_job.profiles_sent = result.users_sent
        sync_job.profiles_added = result.users_added
        sync_job.profiles_removed = result.users_removed
        sync_job.profiles_failed = result.users_failed
        sync_job.platform_response = result.platform_response

        if result.success:
            sync_job.status = SyncStatus.COMPLETED.value
        elif result.users_failed > 0 and result.users_added > 0:
            sync_job.status = SyncStatus.PARTIAL.value
            sync_job.error_message = result.error_message
        else:
            sync_job.status = SyncStatus.FAILED.value
            sync_job.error_message = result.error_message
            sync_job.error_details = result.error_details

        await self.db.flush()

        self.logger.info(
            "audience_sync_completed",
            platform=platform_audience.platform,
            operation=operation.value,
            status=sync_job.status,
            profiles_sent=sync_job.profiles_sent,
            profiles_added=sync_job.profiles_added,
            duration_ms=sync_job.duration_ms,
        )

        return result

    # =========================================================================
    # Query Methods
    # =========================================================================

    async def list_platform_audiences(
        self,
        segment_id: Optional[UUID] = None,
        platform: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[PlatformAudience], int]:
        """
        List platform audiences with optional filtering.
        """
        query = select(PlatformAudience).where(
            PlatformAudience.tenant_id == self.tenant_id
        )

        if segment_id:
            query = query.where(PlatformAudience.segment_id == segment_id)
        if platform:
            query = query.where(PlatformAudience.platform == platform)

        # Get total count
        count_query = select(func.count(PlatformAudience.id)).where(
            PlatformAudience.tenant_id == self.tenant_id
        )
        if segment_id:
            count_query = count_query.where(PlatformAudience.segment_id == segment_id)
        if platform:
            count_query = count_query.where(PlatformAudience.platform == platform)
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Get results
        result = await self.db.execute(
            query.order_by(PlatformAudience.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        audiences = list(result.scalars().all())

        return audiences, total

    async def get_sync_history(
        self,
        platform_audience_id: UUID,
        limit: int = 20,
    ) -> list[AudienceSyncJob]:
        """
        Get sync job history for a platform audience.
        """
        result = await self.db.execute(
            select(AudienceSyncJob)
            .where(
                AudienceSyncJob.platform_audience_id == platform_audience_id,
                AudienceSyncJob.tenant_id == self.tenant_id,
            )
            .order_by(AudienceSyncJob.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_connected_platforms(
        self,
    ) -> list[dict[str, Any]]:
        """
        Get list of platforms with active credentials.
        """
        result = await self.db.execute(
            select(AudienceSyncCredential).where(
                AudienceSyncCredential.tenant_id == self.tenant_id,
                AudienceSyncCredential.is_active == True,
            )
        )
        credentials = result.scalars().all()

        platforms = {}
        for cred in credentials:
            if cred.platform not in platforms:
                platforms[cred.platform] = {
                    "platform": cred.platform,
                    "ad_accounts": [],
                }
            platforms[cred.platform]["ad_accounts"].append(
                {
                    "ad_account_id": cred.ad_account_id,
                    "ad_account_name": cred.ad_account_name,
                }
            )

        return list(platforms.values())

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _get_segment(self, segment_id: UUID) -> Optional[CDPSegment]:
        """Get a CDP segment by ID."""
        result = await self.db.execute(
            select(CDPSegment).where(
                CDPSegment.id == segment_id,
                CDPSegment.tenant_id == self.tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def _get_platform_audience(
        self, audience_id: UUID
    ) -> Optional[PlatformAudience]:
        """Get a platform audience by ID."""
        result = await self.db.execute(
            select(PlatformAudience).where(
                PlatformAudience.id == audience_id,
                PlatformAudience.tenant_id == self.tenant_id,
            )
        )
        return result.scalar_one_or_none()

    async def _get_credentials(
        self,
        platform: str,
        ad_account_id: str,
    ) -> Optional[AudienceSyncCredential]:
        """Get credentials for a platform/ad account."""
        result = await self.db.execute(
            select(AudienceSyncCredential).where(
                AudienceSyncCredential.tenant_id == self.tenant_id,
                AudienceSyncCredential.platform == platform,
                AudienceSyncCredential.ad_account_id == ad_account_id,
                AudienceSyncCredential.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    def _advertising_consent_subquery(self):
        """Profile IDs that currently hold advertising consent for this tenant.

        Both conditions are required, not either: the ingest path sets
        ``granted=False`` *and* ``revoked_at`` on revocation, and clears
        ``revoked_at`` on re-grant, so a row failing either test is not a live
        grant. Checking both means a future writer that updates only one of
        them suppresses the profile rather than leaking it.
        """
        return select(CDPConsent.profile_id).where(
            CDPConsent.tenant_id == self.tenant_id,
            CDPConsent.consent_type.in_(ADVERTISING_CONSENT_TYPES),
            CDPConsent.granted.is_(True),
            CDPConsent.revoked_at.is_(None),
        )

    async def _count_consent_suppressed(self, segment_id: UUID) -> int:
        """Count segment members withheld from platform sync for lack of consent.

        Reported on the sync job so a tenant seeing 40 profiles pushed where
        they expected 10,000 can tell consent is the reason rather than a
        broken segment.
        """
        result = await self.db.execute(
            select(func.count())
            .select_from(CDPProfile)
            .join(CDPSegmentMembership)
            .where(
                CDPSegmentMembership.segment_id == segment_id,
                CDPSegmentMembership.is_active == True,
                CDPProfile.tenant_id == self.tenant_id,
                CDPProfile.id.notin_(self._advertising_consent_subquery()),
            )
        )
        return result.scalar() or 0

    async def _get_segment_profiles(
        self,
        segment_id: UUID,
        limit: int = 1000000,
        batch_size: int = 1000,
    ) -> list[CDPProfile]:
        """Get the syncable profiles in a segment, batched to avoid OOM.

        Fetches profiles in batches of `batch_size` to keep memory usage
        bounded, up to `limit` total profiles.

        Only profiles holding advertising consent are returned. Segment
        membership answers "who matches these rules"; it does not answer "whose
        email may we hand to Meta". Consent is recorded per profile in
        ``cdp_consents`` — with grant/revoke timestamps, consent text and
        version — and this is the one place in the codebase where honouring it
        is the difference between a lawful transfer and an unlawful one.

        Absence of consent is a refusal, not a maybe: GDPR consent is
        affirmative, so a profile with no ``cdp_consents`` row at all is
        withheld exactly like one that revoked. This means a tenant who has
        never populated consent syncs nothing, which is the correct behaviour
        and is surfaced through ``profiles_suppressed`` on the sync job rather
        than failing silently.
        """
        all_profiles: list[CDPProfile] = []
        offset = 0
        remaining = limit

        while remaining > 0:
            fetch_size = min(batch_size, remaining)
            result = await self.db.execute(
                select(CDPProfile)
                .join(CDPSegmentMembership)
                .where(
                    CDPSegmentMembership.segment_id == segment_id,
                    CDPSegmentMembership.is_active == True,
                    CDPProfile.tenant_id == self.tenant_id,
                    CDPProfile.id.in_(self._advertising_consent_subquery()),
                )
                .options(selectinload(CDPProfile.identifiers))
                .order_by(CDPProfile.id)
                .limit(fetch_size)
                .offset(offset)
            )
            batch = list(result.scalars().all())
            if not batch:
                break
            all_profiles.extend(batch)
            offset += len(batch)
            remaining -= len(batch)

        return all_profiles

    async def _profiles_to_audience_users(
        self,
        profiles: list[CDPProfile],
    ) -> list[AudienceUser]:
        """Convert CDP profiles to audience users."""
        users = []

        for profile in profiles:
            identifiers = []

            for pid in profile.identifiers:
                id_type = self._map_identifier_type(pid.identifier_type)
                if id_type:
                    identifiers.append(
                        UserIdentifier(
                            identifier_type=id_type,
                            hashed_value=pid.identifier_hash,
                        )
                    )

            if identifiers:
                users.append(
                    AudienceUser(
                        profile_id=str(profile.id),
                        identifiers=identifiers,
                    )
                )

        return users

    def _map_identifier_type(self, cdp_type: str) -> Optional[IdentifierType]:
        """Map CDP identifier type to audience sync identifier type."""
        mapping = {
            "email": IdentifierType.EMAIL,
            "phone": IdentifierType.PHONE,
            "device_id": IdentifierType.MOBILE_ADVERTISER_ID,
        }
        return mapping.get(cdp_type)

    def _get_connector(
        self,
        platform: str,
        credentials: AudienceSyncCredential,
    ) -> BaseAudienceConnector:
        """Get platform connector instance."""
        connector_class = self.CONNECTOR_CLASSES.get(platform)
        if not connector_class:
            raise ValueError(f"Unknown platform: {platform}")

        kwargs = {}
        if platform == SyncPlatform.GOOGLE.value:
            kwargs["developer_token"] = credentials.config.get("developer_token")
            kwargs["login_customer_id"] = credentials.config.get("login_customer_id")
        elif platform == SyncPlatform.META.value:
            kwargs["app_secret"] = credentials.config.get("app_secret")

        return connector_class(
            access_token=credentials.access_token,
            ad_account_id=credentials.ad_account_id,
            **kwargs,
        )
