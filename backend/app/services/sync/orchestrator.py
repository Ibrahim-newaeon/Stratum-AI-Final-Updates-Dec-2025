# =============================================================================
# Stratum AI - Platform Sync Orchestrator
# =============================================================================
"""
Coordinates campaign sync across Meta and TikTok.

Responsibilities:
1. Load TenantPlatformConnection + enabled TenantAdAccount records
2. Decrypt and refresh tokens as needed
3. Delegate to platform-specific sync services
4. Upsert Campaign and CampaignMetric rows
5. Recalculate aggregate metrics
6. Update last_synced_at

Respects settings.use_mock_ad_data — skips real API calls when True.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from typing import Optional

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.base_models import AdPlatform, Campaign, CampaignMetric, CampaignStatus
from app.core.config import settings
from app.core.logging import get_logger
from app.models.campaign_builder import (
    ConnectionStatus,
    TenantAdAccount,
    TenantPlatformConnection,
)
from app.services.oauth import get_oauth_service
from app.services.sync.meta_sync import MetaCampaignSyncService, TokenExpiredError
from app.services.sync.tiktok_sync import TikTokCampaignSyncService

logger = get_logger(__name__)


@dataclass
class SyncResult:
    """Result of a platform sync operation."""

    platform: str
    tenant_id: int
    campaigns_synced: int = 0
    metrics_upserted: int = 0
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0


class PlatformSyncOrchestrator:
    """Orchestrates campaign data sync from ad platforms."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self._meta_sync = MetaCampaignSyncService()
        self._tiktok_sync = TikTokCampaignSyncService()

    async def sync_platform(
        self,
        tenant_id: int,
        platform: AdPlatform,
        days_back: int = 30,
    ) -> SyncResult:
        """
        Sync all campaigns and metrics for a tenant+platform.

        Args:
            tenant_id: Tenant to sync for
            platform: Which ad platform to sync
            days_back: How many days of historical metrics to fetch
        """
        t0 = time.monotonic()
        result = SyncResult(platform=platform.value, tenant_id=tenant_id)

        if settings.use_mock_ad_data:
            logger.info("sync_skipped_mock_mode", tenant=tenant_id, platform=platform.value)
            return result

        # 1. Load connection (or fall back to env vars)
        conn = await self._load_connection(tenant_id, platform)

        access_token: Optional[str] = None
        account_ids: list[str] = []

        if conn:
            # 2a. Decrypt + refresh token from DB
            access_token = await self._get_valid_token(conn, platform)
            if not access_token:
                result.errors.append("Failed to obtain valid access token")
                return result
            # 3a. Load enabled ad accounts from DB
            accounts = await self._load_ad_accounts(conn)
            account_ids = [a.platform_account_id for a in accounts]
        else:
            # 2b. Fall back to environment variable tokens
            access_token, account_ids = self._get_env_credentials(platform)
            if not access_token:
                result.errors.append(f"No active connection or env credentials for {platform.value}")
                return result
            logger.info("sync_using_env_credentials", platform=platform.value, accounts=len(account_ids))

        if not account_ids:
            result.errors.append("No ad accounts configured")
            return result

        # 4. Sync each account
        date_end = datetime.now(UTC).date()
        date_start = date_end - timedelta(days=days_back)

        for acct_id in account_ids:
            try:
                if platform == AdPlatform.META:
                    synced, metrics = await self._sync_meta_account(
                        tenant_id, access_token, acct_id, date_start, date_end
                    )
                elif platform == AdPlatform.TIKTOK:
                    synced, metrics = await self._sync_tiktok_account(
                        tenant_id, access_token, acct_id, date_start, date_end
                    )
                else:
                    continue
                result.campaigns_synced += synced
                result.metrics_upserted += metrics
            except TokenExpiredError:
                if conn:
                    access_token = await self._refresh_token(conn, platform)
                    if not access_token:
                        result.errors.append("Token expired and refresh failed")
                        break
                    try:
                        if platform == AdPlatform.META:
                            synced, metrics = await self._sync_meta_account(
                                tenant_id, access_token, acct_id, date_start, date_end
                            )
                        elif platform == AdPlatform.TIKTOK:
                            synced, metrics = await self._sync_tiktok_account(
                                tenant_id, access_token, acct_id, date_start, date_end
                            )
                        else:
                            continue
                        result.campaigns_synced += synced
                        result.metrics_upserted += metrics
                    except Exception as e:
                        result.errors.append(f"Account {acct_id}: {e}")
                else:
                    result.errors.append(f"Token expired for {acct_id} and no DB connection to refresh")
                    break
            except Exception as e:
                logger.error("sync_account_error", account=acct_id, error=str(e))
                result.errors.append(f"Account {acct_id}: {e}")

        # 5. Update connection last sync time
        if conn:
            conn.last_refreshed_at = datetime.now(UTC)
        await self.db.commit()

        result.duration_seconds = round(time.monotonic() - t0, 2)
        logger.info(
            "sync_completed",
            tenant=tenant_id,
            platform=platform.value,
            campaigns=result.campaigns_synced,
            metrics=result.metrics_upserted,
            errors=len(result.errors),
            duration=result.duration_seconds,
        )
        return result

    # ------------------------------------------------------------------
    # Environment variable fallback
    # ------------------------------------------------------------------

    @staticmethod
    def _get_env_credentials(platform: AdPlatform) -> tuple[Optional[str], list[str]]:
        """Get access token and account IDs from environment variables."""
        if platform == AdPlatform.META:
            token = os.getenv("META_ACCESS_TOKEN")
            accounts_str = os.getenv("META_AD_ACCOUNT_IDS", "")
            account_ids = [a.strip() for a in accounts_str.split(",") if a.strip()]
            # Meta API expects act_ prefix
            account_ids = [f"act_{a}" if not a.startswith("act_") else a for a in account_ids]
            return token, account_ids
        elif platform == AdPlatform.TIKTOK:
            token = os.getenv("TIKTOK_ACCESS_TOKEN")
            # TikTok uses advertiser_id
            advertiser_id = os.getenv("TIKTOK_ADVERTISER_ID", "")
            account_ids = [advertiser_id] if advertiser_id else []
            return token, account_ids
        return None, []

    # ------------------------------------------------------------------
    # Account-level sync
    # ------------------------------------------------------------------

    async def _sync_account(
        self,
        tenant_id: int,
        platform: AdPlatform,
        access_token: str,
        account: TenantAdAccount,
        date_start: date,
        date_end: date,
    ) -> tuple[int, int]:
        """Sync campaigns + metrics for one ad account. Returns (campaigns, metrics)."""
        account_id = account.platform_account_id
        campaigns_synced = 0
        metrics_upserted = 0

        if platform == AdPlatform.META:
            campaigns_synced, metrics_upserted = await self._sync_meta_account(
                tenant_id, access_token, account_id, date_start, date_end
            )
        elif platform == AdPlatform.TIKTOK:
            campaigns_synced, metrics_upserted = await self._sync_tiktok_account(
                tenant_id, access_token, account_id, date_start, date_end
            )

        # Update account sync timestamp
        account.last_synced_at = datetime.now(UTC)
        account.sync_error = None
        return campaigns_synced, metrics_upserted

    async def _sync_meta_account(
        self,
        tenant_id: int,
        access_token: str,
        account_id: str,
        date_start: date,
        date_end: date,
    ) -> tuple[int, int]:
        # Fetch campaigns
        raw_campaigns = await self._meta_sync.fetch_campaigns(access_token, account_id)
        campaigns_synced = 0
        metrics_upserted = 0

        for mc in raw_campaigns:
            campaign = await self._upsert_campaign(
                tenant_id=tenant_id,
                platform=AdPlatform.META,
                external_id=mc.external_id,
                account_id=account_id,
                name=mc.name,
                status=mc.status,
                objective=mc.objective,
                daily_budget_cents=mc.daily_budget_cents,
                lifetime_budget_cents=mc.lifetime_budget_cents,
                start_date=mc.start_time,
                end_date=mc.stop_time,
                raw_data=mc.raw,
            )
            campaigns_synced += 1

            # Fetch insights for this campaign
            try:
                insights = await self._meta_sync.fetch_campaign_insights(
                    access_token, mc.external_id, date_start, date_end
                )
                for row in insights:
                    await self._upsert_metric(
                        tenant_id=tenant_id,
                        campaign_id=campaign.id,
                        metric_date=row.date,
                        spend_cents=row.spend_cents,
                        impressions=row.impressions,
                        clicks=row.clicks,
                        conversions=row.conversions,
                        revenue_cents=row.revenue_cents,
                        video_views=row.video_views,
                    )
                    metrics_upserted += 1
            except Exception as e:
                logger.warning("meta_insights_error", campaign=mc.external_id, error=str(e))

            # Recalculate aggregates on the campaign
            await self._recalculate_campaign_aggregates(campaign)

        await self.db.commit()
        return campaigns_synced, metrics_upserted

    async def _sync_tiktok_account(
        self,
        tenant_id: int,
        access_token: str,
        advertiser_id: str,
        date_start: date,
        date_end: date,
    ) -> tuple[int, int]:
        # Fetch campaigns
        raw_campaigns = await self._tiktok_sync.fetch_campaigns(access_token, advertiser_id)
        campaigns_synced = 0
        metrics_upserted = 0

        campaign_map: dict[str, Campaign] = {}
        campaign_ids: list[str] = []

        for tc in raw_campaigns:
            campaign = await self._upsert_campaign(
                tenant_id=tenant_id,
                platform=AdPlatform.TIKTOK,
                external_id=tc.external_id,
                account_id=advertiser_id,
                name=tc.name,
                status=tc.status,
                objective=tc.objective,
                daily_budget_cents=tc.daily_budget_cents,
                lifetime_budget_cents=tc.lifetime_budget_cents,
                raw_data=tc.raw,
            )
            campaign_map[tc.external_id] = campaign
            campaign_ids.append(tc.external_id)
            campaigns_synced += 1

        # Fetch reports for all campaigns in one call
        if campaign_ids:
            try:
                reports = await self._tiktok_sync.fetch_campaign_reports(
                    access_token, advertiser_id, campaign_ids, date_start, date_end
                )
                for row in reports:
                    campaign = campaign_map.get(row.campaign_id)
                    if not campaign:
                        continue
                    await self._upsert_metric(
                        tenant_id=tenant_id,
                        campaign_id=campaign.id,
                        metric_date=row.date,
                        spend_cents=row.spend_cents,
                        impressions=row.impressions,
                        clicks=row.clicks,
                        conversions=row.conversions,
                        revenue_cents=row.revenue_cents,
                    )
                    metrics_upserted += 1
            except Exception as e:
                logger.warning("tiktok_reports_error", advertiser=advertiser_id, error=str(e))

        # Recalculate aggregates
        for campaign in campaign_map.values():
            await self._recalculate_campaign_aggregates(campaign)

        await self.db.commit()
        return campaigns_synced, metrics_upserted

    # ------------------------------------------------------------------
    # DB helpers
    # ------------------------------------------------------------------

    async def _upsert_campaign(
        self,
        tenant_id: int,
        platform: AdPlatform,
        external_id: str,
        account_id: str,
        name: str,
        status: CampaignStatus,
        objective: Optional[str] = None,
        daily_budget_cents: Optional[int] = None,
        lifetime_budget_cents: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        raw_data: Optional[dict] = None,
    ) -> Campaign:
        """Insert or update a campaign by tenant+platform+external_id."""
        result = await self.db.execute(
            select(Campaign).where(
                and_(
                    Campaign.tenant_id == tenant_id,
                    Campaign.platform == platform,
                    Campaign.external_id == external_id,
                )
            )
        )
        campaign = result.scalar_one_or_none()

        now = datetime.now(UTC)

        if campaign:
            campaign.name = name
            campaign.status = status
            campaign.objective = objective
            campaign.account_id = account_id
            if daily_budget_cents is not None:
                campaign.daily_budget_cents = daily_budget_cents
            if lifetime_budget_cents is not None:
                campaign.lifetime_budget_cents = lifetime_budget_cents
            if start_date:
                campaign.start_date = start_date.date() if isinstance(start_date, datetime) else start_date
            if end_date:
                campaign.end_date = end_date.date() if isinstance(end_date, datetime) else end_date
            campaign.raw_data = raw_data
            campaign.last_synced_at = now
            campaign.sync_error = None
        else:
            campaign = Campaign(
                tenant_id=tenant_id,
                platform=platform,
                external_id=external_id,
                account_id=account_id,
                name=name,
                status=status,
                objective=objective,
                daily_budget_cents=daily_budget_cents,
                lifetime_budget_cents=lifetime_budget_cents,
                start_date=start_date.date() if isinstance(start_date, datetime) else start_date,
                end_date=end_date.date() if isinstance(end_date, datetime) else end_date,
                raw_data=raw_data,
                last_synced_at=now,
            )
            self.db.add(campaign)
            await self.db.flush()

        return campaign

    async def _upsert_metric(
        self,
        tenant_id: int,
        campaign_id: int,
        metric_date: date,
        spend_cents: int = 0,
        impressions: int = 0,
        clicks: int = 0,
        conversions: int = 0,
        revenue_cents: int = 0,
        video_views: Optional[int] = None,
    ) -> None:
        """Insert or update a daily metric row."""
        result = await self.db.execute(
            select(CampaignMetric).where(
                and_(
                    CampaignMetric.campaign_id == campaign_id,
                    CampaignMetric.date == metric_date,
                )
            )
        )
        metric = result.scalar_one_or_none()

        if metric:
            metric.spend_cents = spend_cents
            metric.impressions = impressions
            metric.clicks = clicks
            metric.conversions = conversions
            metric.revenue_cents = revenue_cents
            if video_views is not None:
                metric.video_views = video_views
        else:
            metric = CampaignMetric(
                tenant_id=tenant_id,
                campaign_id=campaign_id,
                date=metric_date,
                spend_cents=spend_cents,
                impressions=impressions,
                clicks=clicks,
                conversions=conversions,
                revenue_cents=revenue_cents,
                video_views=video_views,
            )
            self.db.add(metric)

    async def _recalculate_campaign_aggregates(self, campaign: Campaign) -> None:
        """Sum all metric rows to update campaign-level aggregates."""
        result = await self.db.execute(
            select(
                func_sum(CampaignMetric.spend_cents),
                func_sum(CampaignMetric.impressions),
                func_sum(CampaignMetric.clicks),
                func_sum(CampaignMetric.conversions),
                func_sum(CampaignMetric.revenue_cents),
            ).where(CampaignMetric.campaign_id == campaign.id)
        )
        row = result.one_or_none()
        if row:
            campaign.total_spend_cents = row[0] or 0
            campaign.impressions = row[1] or 0
            campaign.clicks = row[2] or 0
            campaign.conversions = row[3] or 0
            campaign.revenue_cents = row[4] or 0
            campaign.calculate_metrics()

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------

    async def _load_connection(
        self, tenant_id: int, platform: AdPlatform
    ) -> Optional[TenantPlatformConnection]:
        result = await self.db.execute(
            select(TenantPlatformConnection).where(
                and_(
                    TenantPlatformConnection.tenant_id == tenant_id,
                    TenantPlatformConnection.platform == platform,
                    TenantPlatformConnection.status == ConnectionStatus.CONNECTED,
                )
            )
        )
        return result.scalar_one_or_none()

    async def _load_ad_accounts(
        self, connection: TenantPlatformConnection
    ) -> list[TenantAdAccount]:
        result = await self.db.execute(
            select(TenantAdAccount).where(
                and_(
                    TenantAdAccount.connection_id == connection.id,
                    TenantAdAccount.is_enabled == True,
                )
            )
        )
        return list(result.scalars().all())

    async def _get_valid_token(
        self,
        conn: TenantPlatformConnection,
        platform: AdPlatform,
    ) -> Optional[str]:
        """Decrypt access token, refreshing if expired."""
        try:
            oauth = get_oauth_service(platform.value)
            access_token = oauth.decrypt_token(conn.access_token_encrypted)
        except Exception as e:
            logger.error("token_decrypt_failed", error=str(e))
            return None

        # Check expiry
        if conn.token_expires_at and conn.token_expires_at <= datetime.now(UTC):
            return await self._refresh_token(conn, platform)

        return access_token

    async def _refresh_token(
        self,
        conn: TenantPlatformConnection,
        platform: AdPlatform,
    ) -> Optional[str]:
        """Attempt to refresh the access token."""
        if not conn.refresh_token_encrypted:
            logger.warning("no_refresh_token", platform=platform.value)
            conn.status = ConnectionStatus.EXPIRED
            return None

        try:
            oauth = get_oauth_service(platform.value)
            refresh_token = oauth.decrypt_token(conn.refresh_token_encrypted)
            new_tokens = await oauth.refresh_access_token(refresh_token)

            conn.access_token_encrypted = oauth.encrypt_token(new_tokens.access_token)
            if new_tokens.refresh_token:
                conn.refresh_token_encrypted = oauth.encrypt_token(new_tokens.refresh_token)
            conn.token_expires_at = new_tokens.expires_at
            conn.last_refreshed_at = datetime.now(UTC)
            conn.status = ConnectionStatus.CONNECTED
            conn.last_error = None
            conn.error_count = 0
            await self.db.commit()

            return new_tokens.access_token
        except Exception as e:
            logger.error("token_refresh_failed", platform=platform.value, error=str(e))
            conn.status = ConnectionStatus.EXPIRED
            conn.last_error = str(e)
            conn.error_count = (conn.error_count or 0) + 1
            await self.db.commit()
            return None


# Aliased import to avoid importing sqlalchemy.func at module level
from sqlalchemy import func as _sa_func  # noqa: E402

func_sum = _sa_func.sum
