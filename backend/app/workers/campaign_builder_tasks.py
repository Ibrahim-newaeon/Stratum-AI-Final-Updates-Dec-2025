# =============================================================================
# Stratum AI - Campaign Builder Celery Tasks
# =============================================================================
"""
Background tasks for the Campaign Builder feature:
- sync_ad_accounts: Sync ad accounts from platform after OAuth
- refresh_tokens: Refresh OAuth tokens before expiry
- publish_campaign: Publish campaign draft to platform
- publish_retry: Retry failed publish attempts
- connector_health_check: Check platform API connectivity
"""

from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID
import logging

from celery import shared_task
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.campaign_builder import (
    TenantPlatformConnection, TenantAdAccount, CampaignDraft, CampaignPublishLog,
    AdPlatform, ConnectionStatus, DraftStatus, PublishResult
)

logger = logging.getLogger(__name__)


# =============================================================================
# Ad Account Sync Tasks
# =============================================================================

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_ad_accounts(self, tenant_id: int, platform: str):
    """
    Sync ad accounts from platform after OAuth authorization.
    Called after successful OAuth callback or manually triggered.
    """
    logger.info(f"Syncing ad accounts for tenant {tenant_id}, platform {platform}")

    with SessionLocal() as db:
        # Get connection
        connection = db.execute(
            select(TenantPlatformConnection).where(
                and_(
                    TenantPlatformConnection.tenant_id == tenant_id,
                    TenantPlatformConnection.platform == AdPlatform(platform),
                )
            )
        ).scalar_one_or_none()

        if not connection or connection.status != ConnectionStatus.CONNECTED:
            logger.warning(f"No active connection for tenant {tenant_id}, platform {platform}")
            return {"status": "skipped", "reason": "no active connection"}

        try:
            # Fetch ad accounts from platform API
            # In production: accounts = fetch_ad_accounts_from_platform(platform, connection.access_token_encrypted)

            # Mock data for development
            mock_accounts = [
                {
                    "id": f"act_{tenant_id}_{platform}_001",
                    "name": "Main Business Account",
                    "currency": "SAR",
                    "timezone": "Asia/Riyadh",
                    "status": "active",
                },
                {
                    "id": f"act_{tenant_id}_{platform}_002",
                    "name": "E-commerce Store",
                    "currency": "SAR",
                    "timezone": "Asia/Riyadh",
                    "status": "active",
                },
            ]

            synced_count = 0
            for account_data in mock_accounts:
                # Check if account exists
                existing = db.execute(
                    select(TenantAdAccount).where(
                        and_(
                            TenantAdAccount.tenant_id == tenant_id,
                            TenantAdAccount.platform == AdPlatform(platform),
                            TenantAdAccount.platform_account_id == account_data["id"],
                        )
                    )
                ).scalar_one_or_none()

                if existing:
                    # Update existing
                    existing.name = account_data["name"]
                    existing.currency = account_data["currency"]
                    existing.timezone = account_data["timezone"]
                    existing.account_status = account_data["status"]
                    existing.last_synced_at = datetime.now(timezone.utc)
                    existing.sync_error = None
                else:
                    # Create new
                    new_account = TenantAdAccount(
                        tenant_id=tenant_id,
                        connection_id=connection.id,
                        platform=AdPlatform(platform),
                        platform_account_id=account_data["id"],
                        name=account_data["name"],
                        currency=account_data["currency"],
                        timezone=account_data["timezone"],
                        account_status=account_data["status"],
                        is_enabled=False,  # Disabled by default
                        last_synced_at=datetime.now(timezone.utc),
                    )
                    db.add(new_account)

                synced_count += 1

            db.commit()
            logger.info(f"Synced {synced_count} ad accounts for tenant {tenant_id}, platform {platform}")

            return {"status": "success", "synced_count": synced_count}

        except Exception as e:
            logger.error(f"Error syncing ad accounts: {e}")
            connection.last_error = str(e)
            connection.error_count += 1
            db.commit()
            raise self.retry(exc=e)


@shared_task(bind=True)
def sync_all_ad_accounts(self):
    """
    Daily task to sync all ad accounts for all connected platforms.
    """
    logger.info("Starting daily ad accounts sync for all tenants")

    with SessionLocal() as db:
        # Get all active connections
        connections = db.execute(
            select(TenantPlatformConnection).where(
                TenantPlatformConnection.status == ConnectionStatus.CONNECTED
            )
        ).scalars().all()

        for conn in connections:
            sync_ad_accounts.delay(conn.tenant_id, conn.platform.value)

    return {"status": "triggered", "connections_count": len(connections)}


# =============================================================================
# Token Refresh Tasks
# =============================================================================

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def refresh_tokens(self, tenant_id: int, platform: str):
    """
    Refresh OAuth tokens for a platform connection.
    Called before token expiry to maintain connectivity.
    """
    logger.info(f"Refreshing tokens for tenant {tenant_id}, platform {platform}")

    with SessionLocal() as db:
        connection = db.execute(
            select(TenantPlatformConnection).where(
                and_(
                    TenantPlatformConnection.tenant_id == tenant_id,
                    TenantPlatformConnection.platform == AdPlatform(platform),
                )
            )
        ).scalar_one_or_none()

        if not connection:
            return {"status": "skipped", "reason": "connection not found"}

        try:
            # Refresh token via platform API
            # In production: new_tokens = refresh_oauth_token(platform, connection.refresh_token_encrypted)

            # Update connection
            connection.last_refreshed_at = datetime.now(timezone.utc)
            connection.token_expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
            connection.status = ConnectionStatus.CONNECTED
            connection.last_error = None
            connection.error_count = 0

            db.commit()
            logger.info(f"Token refreshed for tenant {tenant_id}, platform {platform}")

            return {"status": "success"}

        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            connection.status = ConnectionStatus.EXPIRED
            connection.last_error = str(e)
            connection.error_count += 1
            db.commit()
            raise self.retry(exc=e)


@shared_task(bind=True)
def refresh_expiring_tokens(self):
    """
    Scheduled task to refresh tokens expiring within 24 hours.
    """
    logger.info("Checking for expiring tokens")

    with SessionLocal() as db:
        expiry_threshold = datetime.now(timezone.utc) + timedelta(hours=24)

        connections = db.execute(
            select(TenantPlatformConnection).where(
                and_(
                    TenantPlatformConnection.status == ConnectionStatus.CONNECTED,
                    TenantPlatformConnection.token_expires_at <= expiry_threshold,
                )
            )
        ).scalars().all()

        for conn in connections:
            refresh_tokens.delay(conn.tenant_id, conn.platform.value)

    return {"status": "triggered", "connections_count": len(connections)}


# =============================================================================
# Campaign Publish Tasks
# =============================================================================

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def publish_campaign(self, draft_id: str, publish_log_id: str):
    """
    Publish a campaign draft to the platform.
    Called after approval and publish request.
    """
    logger.info(f"Publishing campaign draft {draft_id}")

    with SessionLocal() as db:
        draft = db.execute(
            select(CampaignDraft).where(CampaignDraft.id == UUID(draft_id))
        ).scalar_one_or_none()

        publish_log = db.execute(
            select(CampaignPublishLog).where(CampaignPublishLog.id == UUID(publish_log_id))
        ).scalar_one_or_none()

        if not draft or not publish_log:
            logger.error(f"Draft or publish log not found: {draft_id}, {publish_log_id}")
            return {"status": "error", "reason": "not found"}

        if draft.status != DraftStatus.PUBLISHING:
            return {"status": "skipped", "reason": f"invalid status: {draft.status}"}

        try:
            # Get ad account for credentials
            ad_account = db.execute(
                select(TenantAdAccount).where(TenantAdAccount.id == draft.ad_account_id)
            ).scalar_one_or_none()

            if not ad_account:
                raise Exception("Ad account not found")

            # Get connection for access token
            connection = db.execute(
                select(TenantPlatformConnection).where(
                    and_(
                        TenantPlatformConnection.tenant_id == draft.tenant_id,
                        TenantPlatformConnection.platform == draft.platform,
                    )
                )
            ).scalar_one_or_none()

            if not connection or connection.status != ConnectionStatus.CONNECTED:
                raise Exception("Platform not connected")

            # Publish to platform API
            # In production: result = publish_to_platform(draft.platform, connection, draft.draft_json)

            # Mock success
            platform_campaign_id = f"camp_{draft_id[:8]}"

            # Update draft
            draft.status = DraftStatus.PUBLISHED
            draft.platform_campaign_id = platform_campaign_id
            draft.published_at = datetime.now(timezone.utc)

            # Update publish log
            publish_log.result_status = PublishResult.SUCCESS
            publish_log.platform_campaign_id = platform_campaign_id
            publish_log.response_json = {"campaign_id": platform_campaign_id}

            db.commit()
            logger.info(f"Successfully published campaign {draft_id} as {platform_campaign_id}")

            return {"status": "success", "platform_campaign_id": platform_campaign_id}

        except Exception as e:
            logger.error(f"Error publishing campaign: {e}")

            # Update draft status
            draft.status = DraftStatus.FAILED

            # Update publish log
            publish_log.result_status = PublishResult.FAILURE
            publish_log.error_message = str(e)

            db.commit()
            raise self.retry(exc=e)


@shared_task(bind=True, max_retries=3, default_retry_delay=120)
def publish_retry(self, log_id: str):
    """
    Retry a failed publish attempt.
    """
    logger.info(f"Retrying publish for log {log_id}")

    with SessionLocal() as db:
        publish_log = db.execute(
            select(CampaignPublishLog).where(CampaignPublishLog.id == UUID(log_id))
        ).scalar_one_or_none()

        if not publish_log:
            return {"status": "error", "reason": "log not found"}

        if publish_log.result_status != PublishResult.FAILURE:
            return {"status": "skipped", "reason": "not a failed publish"}

        # Get the draft
        draft = db.execute(
            select(CampaignDraft).where(CampaignDraft.id == publish_log.draft_id)
        ).scalar_one_or_none()

        if not draft:
            return {"status": "error", "reason": "draft not found"}

        # Reset draft status to publishing
        draft.status = DraftStatus.PUBLISHING
        db.commit()

        # Trigger publish task
        publish_campaign.delay(str(draft.id), str(publish_log.id))

        return {"status": "triggered"}


# =============================================================================
# Health Check Tasks
# =============================================================================

@shared_task(bind=True)
def connector_health_check(self, tenant_id: Optional[int] = None):
    """
    Check platform API connectivity for tenant connections.
    Creates alerts for degraded connections.
    """
    logger.info(f"Running connector health check for tenant {tenant_id or 'all'}")

    with SessionLocal() as db:
        query = select(TenantPlatformConnection).where(
            TenantPlatformConnection.status == ConnectionStatus.CONNECTED
        )

        if tenant_id:
            query = query.where(TenantPlatformConnection.tenant_id == tenant_id)

        connections = db.execute(query).scalars().all()

        results = []
        for conn in connections:
            try:
                # Check API health
                # In production: healthy = check_platform_api_health(conn.platform, conn.access_token_encrypted)

                # Mock health check
                healthy = True

                if healthy:
                    conn.last_error = None
                    conn.error_count = 0
                    results.append({"tenant_id": conn.tenant_id, "platform": conn.platform.value, "healthy": True})
                else:
                    conn.error_count += 1
                    if conn.error_count >= 3:
                        conn.status = ConnectionStatus.ERROR
                    results.append({"tenant_id": conn.tenant_id, "platform": conn.platform.value, "healthy": False})

            except Exception as e:
                logger.error(f"Health check failed for connection {conn.id}: {e}")
                conn.last_error = str(e)
                conn.error_count += 1
                results.append({"tenant_id": conn.tenant_id, "platform": conn.platform.value, "healthy": False, "error": str(e)})

        db.commit()

    return {"status": "completed", "results": results}


# =============================================================================
# Scheduled Tasks Registration
# =============================================================================
# These should be added to celery_app.conf.beat_schedule in celery_app.py:
#
# "sync-all-ad-accounts": {
#     "task": "app.workers.campaign_builder_tasks.sync_all_ad_accounts",
#     "schedule": crontab(hour=2, minute=0),
#     "options": {"queue": "sync"},
# },
# "refresh-expiring-tokens": {
#     "task": "app.workers.campaign_builder_tasks.refresh_expiring_tokens",
#     "schedule": crontab(hour="*/6"),
#     "options": {"queue": "default"},
# },
# "connector-health-check": {
#     "task": "app.workers.campaign_builder_tasks.connector_health_check",
#     "schedule": crontab(minute="*/30"),
#     "options": {"queue": "default"},
# },
