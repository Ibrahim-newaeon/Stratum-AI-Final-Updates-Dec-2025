# =============================================================================
# Stratum AI - Daily Scoring Tasks
# =============================================================================
"""
Background tasks for daily score calculations (scaling, health, etc.).
"""

from datetime import datetime, timezone

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy import select

from app.db.session import SyncSessionLocal
from app.models import Campaign, Tenant
from app.workers.tasks.helpers import publish_event

logger = get_task_logger(__name__)


@shared_task
def calculate_daily_scores():
    """
    Calculate daily performance scores for all campaigns.
    Scheduled daily by Celery beat.

    Calculates:
    - Scaling scores (scale/watch/fix recommendations)
    - Health scores (0-100 composite)
    - Signal health for trust engine
    """
    logger.info("Starting daily score calculations")

    with SyncSessionLocal() as db:
        tenants = (
            db.execute(select(Tenant).where(Tenant.is_deleted == False))
            .scalars()
            .all()
        )

        total_scored = 0
        for tenant in tenants:
            campaigns = (
                db.execute(
                    select(Campaign).where(
                        Campaign.tenant_id == tenant.id,
                        Campaign.is_deleted == False,
                        Campaign.status.in_(["active", "paused"]),
                    )
                )
                .scalars()
                .all()
            )

            for campaign in campaigns:
                try:
                    # Calculate scaling score
                    from app.analytics.logic.scoring import calculate_scaling_score

                    scaling = calculate_scaling_score(
                        campaign_id=campaign.id,
                        tenant_id=tenant.id,
                    )
                    campaign.scaling_score = scaling.get("score")
                    campaign.scaling_recommendation = scaling.get("recommendation")

                    # Calculate health score
                    from app.ml.roas_optimizer import ROASOptimizer

                    optimizer = ROASOptimizer(tenant.id)
                    health = optimizer.calculate_health_score(campaign.id)
                    campaign.health_score = health.get("score")

                    # Calculate signal health for trust engine
                    from app.analytics.logic.signal_health import calculate_signal_health

                    signal = calculate_signal_health(
                        campaign_id=campaign.id,
                        tenant_id=tenant.id,
                    )
                    campaign.signal_health = signal.get("score")
                    campaign.signal_health_status = signal.get("status")

                    total_scored += 1

                except Exception as e:
                    logger.error(f"Scoring failed for campaign {campaign.id}: {e}")

            # Commit per tenant to avoid long transactions
            db.commit()

            # Publish tenant scores updated event
            publish_event(
                tenant.id,
                "scores_updated",
                {
                    "campaigns_scored": len(campaigns),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

    logger.info(f"Calculated scores for {total_scored} campaigns")
    return {"campaigns_scored": total_scored}
