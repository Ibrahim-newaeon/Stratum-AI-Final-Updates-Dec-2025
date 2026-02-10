# =============================================================================
# Stratum AI - CMS Publishing Tasks
# =============================================================================
"""
Background tasks for CMS content publishing and scheduling.
"""

from datetime import UTC, datetime
from typing import Optional

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy import select

from app.db.session import SyncSessionLocal
from app.workers.tasks.helpers import publish_event

logger = get_task_logger(__name__)


@shared_task
def publish_scheduled_cms_posts():
    """
    Publish CMS posts that are scheduled for now or past.
    Scheduled every minute by Celery beat.
    """
    logger.info("Processing scheduled CMS posts")

    from app.models.cms import CMSPost, CMSPostStatus

    with SyncSessionLocal() as db:
        now = datetime.now(UTC)

        # Get posts scheduled for publishing
        posts = (
            db.execute(
                select(CMSPost).where(
                    CMSPost.status == CMSPostStatus.SCHEDULED,
                    CMSPost.scheduled_at <= now,
                )
            )
            .scalars()
            .all()
        )

        published_count = 0
        for post in posts:
            try:
                # Trigger individual publish task
                publish_cms_post.delay(str(post.id))
                published_count += 1
            except Exception as e:
                logger.error(f"Failed to queue post {post.id}: {e}")

    logger.info(f"Queued {published_count} posts for publishing")
    return {"queued": published_count}


@shared_task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    max_retries=3,
)
def publish_cms_post(self, post_id: str, published_by_id: Optional[int] = None):
    """
    Publish a CMS post.

    Args:
        post_id: Post ID to publish
        published_by_id: Optional user ID who triggered publish
    """
    logger.info(f"Publishing CMS post {post_id}")

    from app.models.cms import CMSPost, CMSPostStatus, CMSPostVersion

    with SyncSessionLocal() as db:
        post = db.execute(select(CMSPost).where(CMSPost.id == post_id)).scalar_one_or_none()

        if not post:
            logger.warning(f"Post {post_id} not found")
            return {"status": "not_found"}

        try:
            # Create version snapshot before publishing
            version = CMSPostVersion(
                post_id=post.id,
                tenant_id=post.tenant_id,
                title=post.title,
                content=post.content,
                metadata=post.metadata,
                version_number=post.version + 1,
                created_by_id=published_by_id,
                change_summary="Published",
            )
            db.add(version)

            # Update post status
            post.status = CMSPostStatus.PUBLISHED
            post.published_at = datetime.now(UTC)
            post.published_by_id = published_by_id
            post.version += 1

            db.commit()

            # Publish event for real-time updates
            publish_event(
                post.tenant_id,
                "cms_post_published",
                {
                    "post_id": post_id,
                    "title": post.title,
                    "slug": post.slug,
                },
            )

            # Trigger cache invalidation if CDN is configured
            _invalidate_cdn_cache(post)

            logger.info(f"Post {post_id} published successfully")
            return {
                "status": "published",
                "post_id": post_id,
                "version": post.version,
            }

        except Exception as e:
            logger.error(f"Failed to publish post {post_id}: {e}")
            raise


@shared_task
def create_cms_post_version(
    post_id: str,
    created_by_id: int,
    change_summary: Optional[str] = None,
):
    """
    Create a version snapshot of a CMS post.

    Args:
        post_id: Post ID to version
        created_by_id: User ID creating the version
        change_summary: Optional description of changes
    """
    logger.info(f"Creating version for CMS post {post_id}")

    from app.models.cms import CMSPost, CMSPostVersion

    with SyncSessionLocal() as db:
        post = db.execute(select(CMSPost).where(CMSPost.id == post_id)).scalar_one_or_none()

        if not post:
            logger.warning(f"Post {post_id} not found")
            return {"status": "not_found"}

        # Get current version count
        current_version = post.version or 0

        # Create version snapshot
        version = CMSPostVersion(
            post_id=post.id,
            tenant_id=post.tenant_id,
            title=post.title,
            content=post.content,
            metadata=post.metadata,
            version_number=current_version + 1,
            created_by_id=created_by_id,
            change_summary=change_summary or "Manual version",
        )
        db.add(version)

        # Update post version number
        post.version = current_version + 1

        db.commit()

        logger.info(f"Created version {version.version_number} for post {post_id}")
        return {
            "status": "created",
            "post_id": post_id,
            "version": version.version_number,
        }


def _invalidate_cdn_cache(post) -> None:
    """Invalidate CDN cache for a published post.

    Supports Cloudflare, CloudFront, and Fastly. Configured via
    CDN_PROVIDER, CDN_API_KEY, CDN_ZONE_ID, and CDN_BASE_URL env vars.
    Silently returns if no CDN provider is configured.
    """
    from app.core.config import settings

    if not settings.cdn_provider:
        return

    paths = [
        f"/blog/{post.slug}",
        f"/api/v1/cms/posts/{post.slug}",
        "/blog",
        "/sitemap.xml",
    ]

    try:
        if settings.cdn_provider == "cloudflare":
            _purge_cloudflare(paths, settings)
        elif settings.cdn_provider == "cloudfront":
            _purge_cloudfront(paths, settings)
        elif settings.cdn_provider == "fastly":
            _purge_fastly(paths, settings)

        logger.info(
            "CDN cache invalidated for post '%s' via %s (%d paths)",
            post.slug,
            settings.cdn_provider,
            len(paths),
        )
    except Exception as e:
        # Cache invalidation is best-effort; never fail the publish
        logger.warning("CDN cache invalidation failed for post '%s': %s", post.slug, e)


def _purge_cloudflare(paths: list[str], settings) -> None:
    """Purge cached files from Cloudflare by URL.

    Uses the Cloudflare Zone Purge API:
    POST /client/v4/zones/{zone_id}/purge_cache
    """
    import httpx

    if not settings.cdn_api_key or not settings.cdn_zone_id:
        logger.warning("Cloudflare purge skipped: CDN_API_KEY and CDN_ZONE_ID required")
        return

    base = (settings.cdn_base_url or "").rstrip("/")
    files = [f"{base}{path}" for path in paths] if base else paths

    url = f"https://api.cloudflare.com/client/v4/zones/{settings.cdn_zone_id}/purge_cache"
    with httpx.Client(timeout=10.0) as client:
        resp = client.post(
            url,
            headers={
                "Authorization": f"Bearer {settings.cdn_api_key}",
                "Content-Type": "application/json",
            },
            json={"files": files},
        )
        resp.raise_for_status()

    body = resp.json()
    if not body.get("success"):
        errors = body.get("errors", [])
        raise RuntimeError(f"Cloudflare purge failed: {errors}")


def _purge_cloudfront(paths: list[str], settings) -> None:
    """Create a CloudFront invalidation for the given paths.

    Uses boto3 to call CreateInvalidation on the configured distribution.
    """
    import boto3

    if not settings.cdn_zone_id:
        logger.warning("CloudFront purge skipped: CDN_ZONE_ID (distribution ID) required")
        return

    client = boto3.client("cloudfront")
    caller_ref = f"cms-{int(__import__('time').time())}"

    client.create_invalidation(
        DistributionId=settings.cdn_zone_id,
        InvalidationBatch={
            "Paths": {
                "Quantity": len(paths),
                "Items": paths,
            },
            "CallerReference": caller_ref,
        },
    )


def _purge_fastly(paths: list[str], settings) -> None:
    """Purge cached URLs from Fastly using their Purge API.

    Sends one POST per path to the single-URL purge endpoint.
    """
    import httpx

    if not settings.cdn_api_key:
        logger.warning("Fastly purge skipped: CDN_API_KEY required")
        return

    base = (settings.cdn_base_url or "").rstrip("/")
    if not base:
        logger.warning("Fastly purge skipped: CDN_BASE_URL required for full purge URLs")
        return

    headers = {
        "Fastly-Key": settings.cdn_api_key,
        "Accept": "application/json",
    }

    with httpx.Client(timeout=10.0) as client:
        for path in paths:
            purge_url = f"{base}{path}"
            resp = client.request("PURGE", purge_url, headers=headers)
            resp.raise_for_status()
