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
    CDPProfile,
    CDPSegment,
    CDPSegmentMembership,
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
            next_sync_at=datetime.now(UTC) + timedelta(hours=sync_interval_hours)
            if auto_sync
            else None,
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
            await self.db.flush()
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
            await self.db.flush()
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
                    await connector.delete_audience(platform_audience.platform_audience_id)
            except Exception as e:
                self.logger.warning(
                    "platform_audience_delete_failed",
                    error=str(e),
                    platform_audience_id=str(platform_audience_id),
                )

        await self.db.delete(platform_audience)
        await self.db.flush()

        return True

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

        # Get segment profiles
        profiles = await self._get_segment_profiles(segment.id)
        users = await self._profiles_to_audience_users(profiles)

        sync_job.profiles_total = len(users)

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
            result = await connector.add_users(platform_audience.platform_audience_id, users)

        elif operation == SyncOperation.REPLACE:
            if not platform_audience.platform_audience_id:
                raise ValueError("No platform audience ID for replace operation")
            result = await connector.replace_audience(platform_audience.platform_audience_id, users)

        elif operation == SyncOperation.DELETE:
            if not platform_audience.platform_audience_id:
                raise ValueError("No platform audience ID for delete operation")
            result = await connector.delete_audience(platform_audience.platform_audience_id)

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
        query = select(PlatformAudience).where(PlatformAudience.tenant_id == self.tenant_id)

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
        count_result = await self.db.execute(count_query)
        total = count_result.scalar() or 0

        # Get results
        result = await self.db.execute(
            query.order_by(PlatformAudience.created_at.desc()).offset(offset).limit(limit)
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

    async def _get_platform_audience(self, audience_id: UUID) -> Optional[PlatformAudience]:
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

    async def _get_segment_profiles(
        self,
        segment_id: UUID,
        limit: int = 1000000,
        batch_size: int = 1000,
    ) -> list[CDPProfile]:
        """Get all profiles in a segment using batched fetching to avoid OOM.

        Fetches profiles in batches of `batch_size` to keep memory usage
        bounded, up to `limit` total profiles.
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
            access_token=credentials.access_token, ad_account_id=credentials.ad_account_id, **kwargs
        )
