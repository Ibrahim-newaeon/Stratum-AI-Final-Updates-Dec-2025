# =============================================================================
# Stratum AI - Creative Fatigue Tasks
# =============================================================================
"""
Background tasks for creative fatigue analysis and alerting.
"""

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy import select

from app.db.session import SyncSessionLocal
from app.models import CreativeAsset, Tenant
from app.workers.tasks.helpers import publish_event

logger = get_task_logger(__name__)


@shared_task
def calculate_all_fatigue_scores():
    """
    Calculate creative fatigue scores for all active creatives.
    Scheduled daily by Celery beat.
    """
    logger.info("Starting creative fatigue calculation")

    with SyncSessionLocal() as db:
        tenants = (
            db.execute(select(Tenant).where(Tenant.is_deleted == False))
            .scalars()
            .all()
        )

        total_updated = 0
        alerts_sent = 0

        for tenant in tenants:
            assets = (
                db.execute(
                    select(CreativeAsset).where(
                        CreativeAsset.tenant_id == tenant.id,
                        CreativeAsset.is_deleted == False,
                        CreativeAsset.is_active == True,
                    )
                )
                .scalars()
                .all()
            )

            for asset in assets:
                try:
                    # Calculate fatigue score using the analytics logic
                    from app.analytics.logic.fatigue import calculate_fatigue_score

                    score = calculate_fatigue_score(
                        asset_id=asset.id,
                        tenant_id=tenant.id,
                    )

                    # Update asset with new fatigue score
                    asset.fatigue_score = score["score"]
                    asset.fatigue_status = score["status"]
                    total_updated += 1

                    # Send alert if creative needs refresh
                    if score["status"] == "REFRESH":
                        publish_event(
                            tenant.id,
                            "creative_fatigue_alert",
                            {
                                "asset_id": asset.id,
                                "asset_name": asset.name,
                                "fatigue_score": score["score"],
                            },
                        )
                        alerts_sent += 1

                except Exception as e:
                    logger.error(f"Fatigue calc failed for asset {asset.id}: {e}")

        db.commit()

    logger.info(f"Updated {total_updated} fatigue scores, sent {alerts_sent} alerts")
    return {"updated": total_updated, "alerts": alerts_sent}
