# =============================================================================
# Stratum AI - Billing & Usage Tasks
# =============================================================================
"""
Background tasks for cost allocation and usage tracking.
"""

from datetime import datetime, timedelta, timezone

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy import select, func

from app.db.session import SyncSessionLocal
from app.models import Campaign, CampaignMetric, Tenant

logger = get_task_logger(__name__)


@shared_task
def calculate_cost_allocation():
    """
    Calculate cost allocation across campaigns and channels.
    Scheduled daily by Celery beat.
    """
    logger.info("Starting cost allocation calculation")

    with SyncSessionLocal() as db:
        tenants = (
            db.execute(select(Tenant).where(Tenant.is_deleted == False))
            .scalars()
            .all()
        )

        allocations = []
        for tenant in tenants:
            try:
                # Get yesterday's metrics
                yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date()

                metrics = (
                    db.execute(
                        select(CampaignMetric).where(
                            CampaignMetric.tenant_id == tenant.id,
                            CampaignMetric.date == yesterday,
                        )
                    )
                    .scalars()
                    .all()
                )

                # Calculate totals by platform
                platform_totals = {}
                for metric in metrics:
                    campaign = (
                        db.execute(
                            select(Campaign).where(Campaign.id == metric.campaign_id)
                        )
                        .scalar_one_or_none()
                    )
                    if campaign:
                        platform = campaign.platform
                        if platform not in platform_totals:
                            platform_totals[platform] = {
                                "spend_cents": 0,
                                "revenue_cents": 0,
                                "conversions": 0,
                            }
                        platform_totals[platform]["spend_cents"] += (
                            metric.spend_cents or 0
                        )
                        platform_totals[platform]["revenue_cents"] += (
                            metric.revenue_cents or 0
                        )
                        platform_totals[platform]["conversions"] += (
                            metric.conversions or 0
                        )

                allocations.append(
                    {
                        "tenant_id": tenant.id,
                        "date": str(yesterday),
                        "platforms": platform_totals,
                    }
                )

            except Exception as e:
                logger.error(f"Cost allocation failed for tenant {tenant.id}: {e}")

    logger.info(f"Calculated allocations for {len(allocations)} tenants")
    return {"allocations": len(allocations)}


@shared_task
def calculate_usage_rollup():
    """
    Calculate usage metrics for billing purposes.
    Scheduled daily by Celery beat.
    """
    logger.info("Starting usage rollup calculation")

    with SyncSessionLocal() as db:
        tenants = (
            db.execute(select(Tenant).where(Tenant.is_deleted == False))
            .scalars()
            .all()
        )

        rollups = []
        for tenant in tenants:
            try:
                # Count active campaigns
                active_campaigns = db.execute(
                    select(func.count(Campaign.id)).where(
                        Campaign.tenant_id == tenant.id,
                        Campaign.is_deleted == False,
                        Campaign.status == "active",
                    )
                ).scalar()

                # Calculate MTD spend
                month_start = datetime.now(timezone.utc).replace(day=1).date()
                mtd_spend = (
                    db.execute(
                        select(func.sum(CampaignMetric.spend_cents)).where(
                            CampaignMetric.tenant_id == tenant.id,
                            CampaignMetric.date >= month_start,
                        )
                    ).scalar()
                    or 0
                )

                rollup = {
                    "tenant_id": tenant.id,
                    "active_campaigns": active_campaigns,
                    "mtd_spend_cents": mtd_spend,
                    "plan": tenant.plan,
                    "calculated_at": datetime.now(timezone.utc).isoformat(),
                }
                rollups.append(rollup)

                # Update tenant usage metrics
                tenant.settings = tenant.settings or {}
                tenant.settings["last_usage_rollup"] = rollup

            except Exception as e:
                logger.error(f"Usage rollup failed for tenant {tenant.id}: {e}")

        db.commit()

    logger.info(f"Calculated usage for {len(rollups)} tenants")
    return {"rollups": len(rollups)}
