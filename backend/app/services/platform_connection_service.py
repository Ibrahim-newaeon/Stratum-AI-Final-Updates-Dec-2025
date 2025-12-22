# =============================================================================
# Stratum AI - Platform Connection Service
# =============================================================================
"""
Service for managing ad platform connections.
Handles connection, credential storage, and data syncing.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import (
    AdPlatform,
    Campaign,
    CampaignMetric,
    CampaignStatus,
    ConnectionStatus,
    PlatformConnection,
)
from app.services.credential_service import get_credential_service
from app.services.meta_ads_client import MetaAdsClient, MetaAPIError, map_meta_status

logger = get_logger(__name__)


class PlatformConnectionService:
    """
    Manages platform connections and data synchronization.

    Features:
    - Persistent credential storage (encrypted)
    - Connection testing
    - Campaign data sync
    - Multi-platform support
    """

    def __init__(self, db: AsyncSession, tenant_id: int):
        """
        Initialize the service.

        Args:
            db: Database session
            tenant_id: Current tenant ID
        """
        self.db = db
        self.tenant_id = tenant_id
        self.credential_service = get_credential_service()

    # =========================================================================
    # Connection Management
    # =========================================================================

    async def get_connections(self) -> List[PlatformConnection]:
        """Get all platform connections for the tenant."""
        result = await self.db.execute(
            select(PlatformConnection).where(
                PlatformConnection.tenant_id == self.tenant_id
            )
        )
        return list(result.scalars().all())

    async def get_connection(self, platform: AdPlatform) -> Optional[PlatformConnection]:
        """Get a specific platform connection."""
        result = await self.db.execute(
            select(PlatformConnection).where(
                PlatformConnection.tenant_id == self.tenant_id,
                PlatformConnection.platform == platform,
            )
        )
        return result.scalar_one_or_none()

    async def connect_platform(
        self,
        platform: AdPlatform,
        credentials: Dict[str, str],
    ) -> Dict[str, Any]:
        """
        Connect to a platform with credentials.

        Args:
            platform: Platform to connect
            credentials: Platform-specific credentials

        Returns:
            Connection result with status and details
        """
        # Test the connection first
        test_result = await self._test_platform_connection(platform, credentials)

        if not test_result["success"]:
            return {
                "success": False,
                "status": ConnectionStatus.ERROR,
                "error": test_result.get("error", "Connection test failed"),
            }

        # Encrypt credentials
        encrypted_creds = self.credential_service.encrypt(credentials, self.tenant_id)

        # Check for existing connection
        existing = await self.get_connection(platform)

        if existing:
            # Update existing
            existing.credentials_encrypted = encrypted_creds
            existing.status = ConnectionStatus.CONNECTED
            existing.connected_at = datetime.now(timezone.utc)
            existing.last_tested_at = datetime.now(timezone.utc)
            existing.error_message = None
            existing.error_count = 0
            existing.account_id = test_result.get("account_id")
            existing.account_name = test_result.get("account_name")
        else:
            # Create new connection
            connection = PlatformConnection(
                tenant_id=self.tenant_id,
                platform=platform,
                credentials_encrypted=encrypted_creds,
                status=ConnectionStatus.CONNECTED,
                connected_at=datetime.now(timezone.utc),
                last_tested_at=datetime.now(timezone.utc),
                account_id=test_result.get("account_id"),
                account_name=test_result.get("account_name"),
            )
            self.db.add(connection)

        await self.db.commit()

        return {
            "success": True,
            "status": ConnectionStatus.CONNECTED,
            "platform": platform.value,
            "account_id": test_result.get("account_id"),
            "account_name": test_result.get("account_name"),
            "details": test_result.get("details", {}),
        }

    async def disconnect_platform(self, platform: AdPlatform) -> Dict[str, Any]:
        """
        Disconnect from a platform.

        Args:
            platform: Platform to disconnect

        Returns:
            Disconnect result
        """
        connection = await self.get_connection(platform)

        if not connection:
            return {
                "success": False,
                "error": "Platform not connected",
            }

        # Update status (keep record for audit trail)
        connection.status = ConnectionStatus.DISCONNECTED
        connection.credentials_encrypted = ""  # Clear credentials
        connection.error_message = None

        await self.db.commit()

        return {
            "success": True,
            "platform": platform.value,
            "message": "Platform disconnected successfully",
        }

    async def test_connection(self, platform: AdPlatform) -> Dict[str, Any]:
        """
        Test an existing platform connection.

        Args:
            platform: Platform to test

        Returns:
            Test result
        """
        connection = await self.get_connection(platform)

        if not connection or connection.status == ConnectionStatus.DISCONNECTED:
            return {
                "success": False,
                "error": "Platform not connected",
            }

        # Decrypt credentials
        try:
            credentials = self.credential_service.decrypt(
                connection.credentials_encrypted, self.tenant_id
            )
        except ValueError as e:
            connection.status = ConnectionStatus.ERROR
            connection.error_message = str(e)
            await self.db.commit()
            return {
                "success": False,
                "error": "Failed to decrypt credentials",
            }

        # Test connection
        result = await self._test_platform_connection(platform, credentials)

        # Update connection status
        connection.last_tested_at = datetime.now(timezone.utc)
        if result["success"]:
            connection.status = ConnectionStatus.CONNECTED
            connection.error_message = None
            connection.error_count = 0
        else:
            connection.status = ConnectionStatus.ERROR
            connection.error_message = result.get("error")
            connection.error_count += 1

        await self.db.commit()

        return result

    async def get_connection_status(self) -> Dict[str, Any]:
        """Get status of all platform connections."""
        connections = await self.get_connections()

        status = {}
        for conn in connections:
            status[conn.platform.value] = {
                "status": conn.status.value,
                "connected_at": conn.connected_at.isoformat() if conn.connected_at else None,
                "last_tested_at": conn.last_tested_at.isoformat() if conn.last_tested_at else None,
                "last_sync_at": conn.last_sync_at.isoformat() if conn.last_sync_at else None,
                "account_id": conn.account_id,
                "account_name": conn.account_name,
                "error_message": conn.error_message if conn.status == ConnectionStatus.ERROR else None,
                "sync_enabled": conn.sync_enabled,
            }

        return status

    # =========================================================================
    # Platform-Specific Testing
    # =========================================================================

    async def _test_platform_connection(
        self,
        platform: AdPlatform,
        credentials: Dict[str, str],
    ) -> Dict[str, Any]:
        """Test platform connection based on platform type."""

        if platform == AdPlatform.META:
            return await self._test_meta_connection(credentials)
        elif platform == AdPlatform.GOOGLE:
            return await self._test_google_connection(credentials)
        elif platform == AdPlatform.TIKTOK:
            return await self._test_tiktok_connection(credentials)
        elif platform == AdPlatform.SNAPCHAT:
            return await self._test_snapchat_connection(credentials)
        elif platform == AdPlatform.LINKEDIN:
            return await self._test_linkedin_connection(credentials)
        else:
            return {"success": False, "error": f"Unsupported platform: {platform}"}

    async def _test_meta_connection(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Test Meta/Facebook connection."""
        access_token = credentials.get("access_token")
        if not access_token:
            return {"success": False, "error": "Missing access_token"}

        async with MetaAdsClient(access_token) as client:
            result = await client.test_connection()

            if result["success"]:
                # Get first ad account info
                accounts = result.get("ad_accounts", [])
                first_account = accounts[0] if accounts else {}

                return {
                    "success": True,
                    "account_id": first_account.get("id"),
                    "account_name": first_account.get("name"),
                    "details": {
                        "user_name": result.get("user_name"),
                        "ad_accounts_count": result.get("ad_accounts_count"),
                    },
                }
            else:
                return {
                    "success": False,
                    "error": result.get("error", "Connection failed"),
                }

    async def _test_google_connection(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Test Google Ads connection (placeholder)."""
        # TODO: Implement real Google Ads API test
        customer_id = credentials.get("customer_id", "").replace("-", "")
        if not customer_id or not credentials.get("api_key"):
            return {"success": False, "error": "Missing required credentials"}

        return {
            "success": True,
            "account_id": customer_id,
            "account_name": f"Google Ads {customer_id}",
            "details": {"validated": True},
        }

    async def _test_tiktok_connection(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Test TikTok connection (placeholder)."""
        # TODO: Implement real TikTok API test
        pixel_code = credentials.get("pixel_code")
        if not pixel_code or not credentials.get("access_token"):
            return {"success": False, "error": "Missing required credentials"}

        return {
            "success": True,
            "account_id": pixel_code,
            "account_name": f"TikTok Pixel {pixel_code}",
            "details": {"validated": True},
        }

    async def _test_snapchat_connection(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Test Snapchat connection (placeholder)."""
        pixel_id = credentials.get("pixel_id")
        if not pixel_id or not credentials.get("access_token"):
            return {"success": False, "error": "Missing required credentials"}

        return {
            "success": True,
            "account_id": pixel_id,
            "account_name": f"Snapchat Pixel {pixel_id}",
            "details": {"validated": True},
        }

    async def _test_linkedin_connection(self, credentials: Dict[str, str]) -> Dict[str, Any]:
        """Test LinkedIn connection (placeholder)."""
        conversion_id = credentials.get("conversion_id")
        if not conversion_id or not credentials.get("access_token"):
            return {"success": False, "error": "Missing required credentials"}

        return {
            "success": True,
            "account_id": conversion_id,
            "account_name": f"LinkedIn Conversion {conversion_id}",
            "details": {"validated": True},
        }

    # =========================================================================
    # Campaign Data Sync
    # =========================================================================

    async def sync_campaigns(
        self,
        platform: Optional[AdPlatform] = None,
        days_back: int = 90,
    ) -> Dict[str, Any]:
        """
        Sync campaign data from connected platforms.

        Args:
            platform: Specific platform to sync (None = all)
            days_back: Number of days of historical data to fetch

        Returns:
            Sync results
        """
        connections = await self.get_connections()

        if platform:
            connections = [c for c in connections if c.platform == platform]

        results = {}
        for conn in connections:
            if conn.status != ConnectionStatus.CONNECTED:
                results[conn.platform.value] = {
                    "success": False,
                    "error": "Platform not connected",
                }
                continue

            try:
                # Decrypt credentials
                credentials = self.credential_service.decrypt(
                    conn.credentials_encrypted, self.tenant_id
                )

                # Sync based on platform
                if conn.platform == AdPlatform.META:
                    result = await self._sync_meta_campaigns(credentials, days_back)
                else:
                    # Other platforms not yet implemented
                    result = {
                        "success": False,
                        "error": f"Sync not implemented for {conn.platform.value}",
                    }

                # Update last sync time
                if result["success"]:
                    conn.last_sync_at = datetime.now(timezone.utc)
                    conn.error_message = None
                else:
                    conn.error_message = result.get("error")

                results[conn.platform.value] = result

            except Exception as e:
                logger.error(f"Sync error for {conn.platform}: {e}")
                results[conn.platform.value] = {
                    "success": False,
                    "error": str(e),
                }

        await self.db.commit()
        return results

    async def _sync_meta_campaigns(
        self,
        credentials: Dict[str, str],
        days_back: int,
    ) -> Dict[str, Any]:
        """Sync campaigns from Meta/Facebook."""
        from datetime import date, timedelta

        access_token = credentials.get("access_token")
        if not access_token:
            return {"success": False, "error": "Missing access_token"}

        async with MetaAdsClient(access_token) as client:
            try:
                # Get ad accounts
                accounts = await client.get_ad_accounts()

                if not accounts:
                    return {"success": False, "error": "No ad accounts found"}

                campaigns_synced = 0
                metrics_synced = 0
                errors = []

                # Sync each ad account
                for account in accounts:
                    account_id = account["id"]

                    try:
                        # Get campaigns
                        campaigns = await client.get_campaigns(account_id)

                        for meta_campaign in campaigns:
                            # Create or update campaign in database
                            campaign = await self._upsert_campaign(meta_campaign, account)

                            # Get insights for the campaign
                            date_end = date.today()
                            date_start = date_end - timedelta(days=days_back)

                            insights = await client.get_campaign_insights(
                                meta_campaign.id,
                                date_start,
                                date_end,
                                time_increment=1,  # Daily
                            )

                            # Store daily metrics
                            for insight in insights:
                                await self._upsert_metric(campaign.id, insight)
                                metrics_synced += 1

                            campaigns_synced += 1

                    except MetaAPIError as e:
                        errors.append(f"Account {account_id}: {e}")
                        logger.warning(f"Error syncing account {account_id}: {e}")

                await self.db.commit()

                return {
                    "success": True,
                    "campaigns_synced": campaigns_synced,
                    "metrics_synced": metrics_synced,
                    "accounts_synced": len(accounts),
                    "errors": errors if errors else None,
                }

            except MetaAPIError as e:
                return {"success": False, "error": str(e)}

    async def _upsert_campaign(self, meta_campaign, account: Dict) -> Campaign:
        """Create or update a campaign from Meta data."""
        # Check for existing campaign
        result = await self.db.execute(
            select(Campaign).where(
                Campaign.tenant_id == self.tenant_id,
                Campaign.platform == AdPlatform.META,
                Campaign.external_id == meta_campaign.id,
            )
        )
        campaign = result.scalar_one_or_none()

        if campaign:
            # Update existing
            campaign.name = meta_campaign.name
            campaign.status = map_meta_status(meta_campaign.status)
            campaign.objective = meta_campaign.objective
            campaign.daily_budget_cents = meta_campaign.daily_budget
            campaign.lifetime_budget_cents = meta_campaign.lifetime_budget
            campaign.last_synced_at = datetime.now(timezone.utc)
        else:
            # Create new
            campaign = Campaign(
                tenant_id=self.tenant_id,
                platform=AdPlatform.META,
                external_id=meta_campaign.id,
                account_id=account["id"],
                name=meta_campaign.name,
                status=map_meta_status(meta_campaign.status),
                objective=meta_campaign.objective,
                daily_budget_cents=meta_campaign.daily_budget,
                lifetime_budget_cents=meta_campaign.lifetime_budget,
                currency=account.get("currency", "USD"),
                start_date=meta_campaign.start_time.date() if meta_campaign.start_time else None,
                end_date=meta_campaign.stop_time.date() if meta_campaign.stop_time else None,
                last_synced_at=datetime.now(timezone.utc),
            )
            self.db.add(campaign)
            await self.db.flush()  # Get the ID

        return campaign

    async def _upsert_metric(self, campaign_id: int, insight) -> CampaignMetric:
        """Create or update a daily metric from Meta insights."""
        # Check for existing metric
        result = await self.db.execute(
            select(CampaignMetric).where(
                CampaignMetric.tenant_id == self.tenant_id,
                CampaignMetric.campaign_id == campaign_id,
                CampaignMetric.date == insight.date_start,
            )
        )
        metric = result.scalar_one_or_none()

        # Convert spend to cents
        spend_cents = int(insight.spend * 100)
        revenue_cents = int(insight.conversion_value * 100)

        if metric:
            # Update existing
            metric.impressions = insight.impressions
            metric.clicks = insight.clicks
            metric.conversions = insight.conversions
            metric.spend_cents = spend_cents
            metric.revenue_cents = revenue_cents
        else:
            # Create new
            metric = CampaignMetric(
                tenant_id=self.tenant_id,
                campaign_id=campaign_id,
                date=insight.date_start,
                impressions=insight.impressions,
                clicks=insight.clicks,
                conversions=insight.conversions,
                spend_cents=spend_cents,
                revenue_cents=revenue_cents,
            )
            self.db.add(metric)

        return metric


# =============================================================================
# Factory Function
# =============================================================================
def get_platform_connection_service(
    db: AsyncSession,
    tenant_id: int,
) -> PlatformConnectionService:
    """Create a platform connection service instance."""
    return PlatformConnectionService(db, tenant_id)
