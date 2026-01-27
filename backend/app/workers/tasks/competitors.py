# =============================================================================
# Stratum AI - Competitor Intelligence Tasks
# =============================================================================
"""
Background tasks for fetching and analyzing competitor data.
"""

from datetime import UTC, datetime

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy import select

from app.db.session import SyncSessionLocal
from app.models import CompetitorBenchmark, Tenant
from app.workers.tasks.helpers import publish_event

logger = get_task_logger(__name__)


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def fetch_competitor_data(self, tenant_id: int, competitor_id: int):
    """
    Fetch latest data for a competitor benchmark.

    Args:
        tenant_id: Tenant ID for isolation
        competitor_id: CompetitorBenchmark ID
    """
    logger.info(f"Fetching competitor {competitor_id} for tenant {tenant_id}")

    with SyncSessionLocal() as db:
        competitor = db.execute(
            select(CompetitorBenchmark).where(
                CompetitorBenchmark.id == competitor_id,
                CompetitorBenchmark.tenant_id == tenant_id,
            )
        ).scalar_one_or_none()

        if not competitor:
            logger.warning(f"Competitor {competitor_id} not found")
            return {"status": "not_found"}

        try:
            # In production, integrate with ad intelligence APIs
            # (SimilarWeb, SEMrush, SpyFu, etc.)
            # For now, use mock data
            import random

            competitor.estimated_monthly_spend_cents = random.randint(100000, 10000000)
            competitor.estimated_impressions = random.randint(100000, 50000000)
            competitor.estimated_ctr = round(random.uniform(0.5, 3.0), 2)
            competitor.top_keywords = [
                "marketing automation",
                "ad platform",
                "campaign management",
            ]
            competitor.last_fetched_at = datetime.now(UTC)

            db.commit()

            publish_event(
                tenant_id,
                "competitor_updated",
                {
                    "competitor_id": competitor_id,
                    "competitor_name": competitor.name,
                },
            )

            logger.info(f"Competitor {competitor_id} data updated")
            return {"status": "success", "competitor_id": competitor_id}

        except Exception as e:
            logger.error(f"Failed to fetch competitor data: {e}")
            raise


@shared_task
def refresh_all_competitors():
    """
    Refresh data for all competitor benchmarks.
    Scheduled weekly by Celery beat.
    """
    logger.info("Starting refresh for all competitors")

    with SyncSessionLocal() as db:
        # Get all active tenants
        tenants = db.execute(select(Tenant).where(Tenant.is_deleted == False)).scalars().all()

        task_count = 0
        for tenant in tenants:
            competitors = (
                db.execute(
                    select(CompetitorBenchmark).where(
                        CompetitorBenchmark.tenant_id == tenant.id,
                        CompetitorBenchmark.is_active == True,
                    )
                )
                .scalars()
                .all()
            )

            for competitor in competitors:
                fetch_competitor_data.delay(tenant.id, competitor.id)
                task_count += 1

    logger.info(f"Queued {task_count} competitor refresh tasks")
    return {"tasks_queued": task_count}
