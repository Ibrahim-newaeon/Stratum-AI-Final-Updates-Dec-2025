# =============================================================================
# Stratum AI - Competitor Intelligence Tasks
# =============================================================================
"""
Background tasks for fetching and analyzing competitor data.
"""

import asyncio
from datetime import UTC, datetime
from typing import Any

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy import select

from app.core.config import settings
from app.db.session import SyncSessionLocal
from app.models import CompetitorBenchmark, Tenant
from app.services.competitor_scraper import scan_competitor
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

        # Real scan: website scrape (social links, meta) + Meta Ad Library
        # (active-ad count / creatives, if a Graph token is configured). The
        # scraper is pure HTTP — no app DB — so running it via asyncio.run from
        # this sync task is safe (no shared async engine / event-loop reuse).
        try:
            scan = asyncio.run(
                scan_competitor(
                    domain=competitor.domain,
                    name=competitor.name or competitor.domain,
                    country="SA",
                    access_token=settings.meta_access_token,
                )
            )
        except Exception as e:
            logger.error(f"Competitor scan failed for {competitor_id}: {e}")
            competitor.fetch_error = str(e)[:500]
            competitor.last_fetched_at = datetime.now(UTC)
            db.commit()
            raise  # let autoretry handle transient failures

        _apply_scan_result(competitor, scan)
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

        logger.info(
            f"Competitor {competitor_id} data updated (source={competitor.data_source})"
        )
        return {"status": "success", "competitor_id": competitor_id}


# Explicit name: this module was split out of the old app/workers/tasks.py;
# without it the auto-generated name gains the submodule segment and the
# beat schedule's task reference silently dispatches to nothing.
@shared_task(name="app.workers.tasks.refresh_all_competitors")
def refresh_all_competitors():
    """
    Refresh data for all competitor benchmarks.
    Scheduled weekly by Celery beat.
    """
    logger.info("Starting refresh for all competitors")

    with SyncSessionLocal() as db:
        # Get all active tenants
        tenants = (
            db.execute(select(Tenant).where(Tenant.is_deleted == False)).scalars().all()
        )

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


def _apply_scan_result(competitor: CompetitorBenchmark, scan: dict[str, Any]) -> None:
    """
    Map a ``scan_competitor`` result onto a CompetitorBenchmark.

    Only genuinely sourced fields are written. Metrics we cannot obtain without
    a paid ad-intelligence provider (estimated traffic, ad spend, share of
    voice, keyword counts) are deliberately left untouched — honest null rather
    than the fabricated random numbers this used to write.
    """
    ad = scan.get("ad_library") or {}
    ad_error = ad.get("error")

    competitor.social_links = scan.get("social_links")
    competitor.meta_title = scan.get("meta_title")
    competitor.meta_description = scan.get("meta_description")

    # Active-ad count is only known when the Ad Library query actually ran; a
    # token/API error means "unknown", not zero.
    competitor.ad_creatives_count = None if ad_error else ad.get("ad_count")

    platforms = sorted(
        {p for a in (ad.get("ads") or []) for p in (a.get("platforms") or [])}
    )
    competitor.detected_ad_platforms = platforms or None

    if ad.get("has_ads") and not ad_error:
        competitor.data_source = "meta_ad_library"
    elif scan.get("scrape_error"):
        competitor.data_source = "unavailable"
    else:
        competitor.data_source = "website_scrape"

    competitor.fetch_error = scan.get("scrape_error")

    # Append a timestamped snapshot; keep the last 30.
    history = list(competitor.metrics_history or [])
    history.append(
        {
            "scanned_at": scan.get("scanned_at"),
            "active_ads": None if ad_error else ad.get("ad_count"),
            "has_ads": ad.get("has_ads"),
            "source": competitor.data_source,
        }
    )
    competitor.metrics_history = history[-30:]
