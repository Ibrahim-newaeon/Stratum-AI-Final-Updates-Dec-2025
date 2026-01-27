# =============================================================================
# Stratum AI - Forecasting Tasks
# =============================================================================
"""
Background tasks for ML-based forecasting and predictions.
"""

from typing import List, Optional

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy import select

from app.db.session import SyncSessionLocal
from app.models import Campaign, Tenant

logger = get_task_logger(__name__)


@shared_task
def generate_forecast(tenant_id: int, campaign_ids: Optional[List[int]] = None):
    """
    Generate forecast for specified campaigns or all campaigns.

    Args:
        tenant_id: Tenant ID for isolation
        campaign_ids: Optional list of campaign IDs (all if None)
    """
    logger.info(f"Generating forecast for tenant {tenant_id}")

    with SyncSessionLocal() as db:
        query = select(Campaign).where(
            Campaign.tenant_id == tenant_id,
            Campaign.is_deleted == False,
        )

        if campaign_ids:
            query = query.where(Campaign.id.in_(campaign_ids))

        campaigns = db.execute(query).scalars().all()

        forecasts = []
        for campaign in campaigns:
            try:
                # Use the pacing forecaster service
                from app.services.pacing.forecasting import PacingForecaster

                forecaster = PacingForecaster(tenant_id)
                forecast = forecaster.generate_campaign_forecast(campaign.id)
                forecasts.append(
                    {
                        "campaign_id": campaign.id,
                        "forecast": forecast,
                    }
                )
            except Exception as e:
                logger.error(f"Forecast failed for campaign {campaign.id}: {e}")

    logger.info(f"Generated {len(forecasts)} forecasts")
    return {"forecasts_generated": len(forecasts)}


@shared_task
def generate_daily_forecasts():
    """
    Generate daily forecasts for all active campaigns.
    Scheduled daily by Celery beat.
    """
    logger.info("Starting daily forecast generation")

    with SyncSessionLocal() as db:
        tenants = (
            db.execute(select(Tenant).where(Tenant.is_deleted == False))
            .scalars()
            .all()
        )

        task_count = 0
        for tenant in tenants:
            generate_forecast.delay(tenant.id)
            task_count += 1

    logger.info(f"Queued {task_count} forecast tasks")
    return {"tasks_queued": task_count}
