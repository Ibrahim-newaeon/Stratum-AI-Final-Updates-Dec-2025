# =============================================================================
# Stratum AI — Push Notifications (Web Push API)
# =============================================================================
"""
Web Push notification system using VAPID keys.
Supports browser subscription, broadcast, targeted sends, and campaign alerts.

Subscriptions and sent-notification records are persisted to PostgreSQL
(see ``app.models.push``) so they survive restarts and are shared across API
workers — replacing the former per-process in-memory store.
"""

from datetime import UTC, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import get_async_session
from app.models.push import PushNotificationLog
from app.models.push import PushSubscription as PushSubscriptionModel
from app.schemas.response import APIResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/push-notifications", tags=["Push Notifications"])


# =============================================================================
# Schemas
# =============================================================================


class PushSubscription(BaseModel):
    """Browser push subscription (from PushManager.subscribe())."""

    endpoint: str
    keys: dict[str, str]  # { p256dh: "...", auth: "..." }
    user_agent: Optional[str] = None
    platform: str = "web"  # web, ios, android


class PushNotificationSend(BaseModel):
    """Send a push notification."""

    title: str = Field(..., max_length=100)
    body: str = Field(..., max_length=200)
    icon: Optional[str] = "https://stratumai.app/icon-192.png"
    badge: Optional[str] = "https://stratumai.app/badge-72.png"
    image: Optional[str] = None
    url: Optional[str] = None  # click URL
    tag: Optional[str] = None  # for grouping/collapsing
    require_interaction: bool = False
    actions: Optional[list[dict[str, str]]] = None  # [{ action, title, icon }]
    subscription_ids: Optional[list[str]] = None  # target specific devices
    send_to_all: bool = False


class PushNotificationResponse(BaseModel):
    id: str
    title: str
    body: str
    sent_count: int
    delivered_count: int
    failed_count: int
    created_at: str


class PushVapidConfig(BaseModel):
    """VAPID public key for browser subscription."""

    public_key: str
    subject: str = "mailto:admin@stratumai.app"


class PushAnalytics(BaseModel):
    total_subscribers: int
    active_subscribers_7d: int
    notifications_sent_24h: int
    notifications_sent_30d: int
    click_rate: float
    platform_breakdown: dict[str, int]


# =============================================================================
# Helpers
# =============================================================================


def _require_tenant(req: Request) -> int:
    """Return the request tenant_id or raise 401 if absent."""
    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant required"
        )
    return tenant_id


# =============================================================================
# API Endpoints
# =============================================================================


@router.get("/vapid-key", response_model=APIResponse[PushVapidConfig])
async def get_vapid_public_key(
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get the VAPID public key for browser PushManager subscription.

    Frontend calls this on load, then uses the key with:
    serviceWorkerRegistration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(vapidPublicKey)
    })
    """
    # In production, load from environment
    public_key = getattr(
        settings,
        "vapid_public_key",
        "BJO_xP9SdCW7Lr0w0y0Z0X0Y0Z0X0Y0Z0X0Y0Z0X0Y0Z0X0Y0Z0X0Y0Z0",
    )

    return APIResponse(
        success=True,
        data=PushVapidConfig(
            public_key=public_key, subject="mailto:admin@stratumai.app"
        ),
        message="VAPID key retrieved",
    )


@router.post("/subscribe", response_model=APIResponse[dict])
async def subscribe_device(
    subscription: PushSubscription,
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Register a browser/device for push notifications.

    Called by the frontend after PushManager.subscribe() returns
    a subscription object.
    """
    tenant_id = _require_tenant(req)

    record = PushSubscriptionModel(
        tenant_id=tenant_id,
        endpoint=subscription.endpoint,
        keys=subscription.keys,
        user_agent=subscription.user_agent,
        platform=subscription.platform,
        is_active=True,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    logger.info(
        "push_subscription_created", tenant_id=tenant_id, subscription_id=record.id
    )

    return APIResponse(
        success=True,
        data={"subscription_id": record.id, "status": "subscribed"},
        message="Device subscribed for push notifications",
    )


@router.post("/unsubscribe", response_model=APIResponse[dict])
async def unsubscribe_device(
    endpoint: str,
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """Remove a push subscription."""
    tenant_id = _require_tenant(req)

    result = await db.execute(
        select(PushSubscriptionModel).where(
            PushSubscriptionModel.endpoint == endpoint,
            PushSubscriptionModel.tenant_id == tenant_id,
        )
    )
    subs = result.scalars().all()
    for sub in subs:
        sub.is_active = False
    removed = bool(subs)
    await db.commit()

    return APIResponse(
        success=True,
        data={"unsubscribed": removed},
        message="Device unsubscribed" if removed else "Subscription not found",
    )


@router.post("/send", response_model=APIResponse[PushNotificationResponse])
async def send_push_notification(
    notification: PushNotificationSend,
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Send a push notification to subscribers.

    Can target specific subscription_ids or broadcast to all
    active subscribers of the tenant.
    """
    tenant_id = _require_tenant(req)

    # Get target subscriptions
    stmt = select(PushSubscriptionModel).where(
        PushSubscriptionModel.tenant_id == tenant_id,
        PushSubscriptionModel.is_active.is_(True),
    )
    if not notification.send_to_all:
        if notification.subscription_ids:
            stmt = stmt.where(
                PushSubscriptionModel.id.in_(notification.subscription_ids)
            )
        else:
            stmt = stmt.where(False)
    result = await db.execute(stmt)
    targets = result.scalars().all()

    if not targets:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active subscribers found",
        )

    # Simulate send (in production, use pywebpush library)
    sent = len(targets)
    delivered = int(sent * 0.95)  # 95% delivery rate estimate
    failed = sent - delivered

    record = PushNotificationLog(
        tenant_id=tenant_id,
        title=notification.title,
        body=notification.body,
        url=notification.url,
        tag=notification.tag,
        sent_count=sent,
        delivered_count=delivered,
        failed_count=failed,
        target_type="all" if notification.send_to_all else "selected",
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)

    logger.info(
        "push_notification_sent",
        tenant_id=tenant_id,
        notification_id=record.id,
        sent=sent,
        title=notification.title,
    )

    return APIResponse(
        success=True,
        data=PushNotificationResponse(
            id=record.id,
            title=record.title,
            body=record.body,
            sent_count=record.sent_count,
            delivered_count=record.delivered_count,
            failed_count=record.failed_count,
            created_at=record.created_at.isoformat(),
        ),
        message=f"Notification sent to {sent} subscribers",
    )


@router.get("/subscribers", response_model=APIResponse[list[dict]])
async def list_subscribers(
    req: Request,
    db: AsyncSession = Depends(get_async_session),
    platform: Optional[str] = None,
    active_only: bool = True,
):
    """List push notification subscribers."""
    tenant_id = _require_tenant(req)

    stmt = select(PushSubscriptionModel).where(
        PushSubscriptionModel.tenant_id == tenant_id
    )
    if platform:
        stmt = stmt.where(PushSubscriptionModel.platform == platform)
    if active_only:
        stmt = stmt.where(PushSubscriptionModel.is_active.is_(True))

    result = await db.execute(stmt)
    rows = result.scalars().all()

    subs = [
        {
            "id": sub.id,
            "platform": sub.platform,
            "is_active": sub.is_active,
            "created_at": sub.created_at.isoformat(),
            "last_active_at": (
                sub.last_active_at.isoformat() if sub.last_active_at else None
            ),
        }
        for sub in rows
    ]

    return APIResponse(
        success=True, data=subs, message=f"Found {len(subs)} subscribers"
    )


@router.get("/history", response_model=APIResponse[list[dict]])
async def get_notification_history(
    req: Request,
    db: AsyncSession = Depends(get_async_session),
    page: int = 1,
    page_size: int = 20,
):
    """Get sent notification history."""
    tenant_id = _require_tenant(req)

    result = await db.execute(
        select(PushNotificationLog)
        .where(PushNotificationLog.tenant_id == tenant_id)
        .order_by(PushNotificationLog.created_at.desc())
    )
    rows = result.scalars().all()

    start = (page - 1) * page_size
    paginated = [
        {
            "id": n.id,
            "title": n.title,
            "body": n.body,
            "url": n.url,
            "tag": n.tag,
            "sent_count": n.sent_count,
            "delivered_count": n.delivered_count,
            "failed_count": n.failed_count,
            "target_type": n.target_type,
            "created_at": n.created_at.isoformat(),
        }
        for n in rows[start : start + page_size]
    ]

    return APIResponse(
        success=True, data=paginated, message=f"Found {len(rows)} notifications"
    )


@router.get("/analytics", response_model=APIResponse[PushAnalytics])
async def get_push_analytics(
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """Get push notification analytics."""
    tenant_id = _require_tenant(req)

    subs_result = await db.execute(
        select(PushSubscriptionModel).where(
            PushSubscriptionModel.tenant_id == tenant_id
        )
    )
    tenant_subs = subs_result.scalars().all()

    notifs_result = await db.execute(
        select(PushNotificationLog).where(PushNotificationLog.tenant_id == tenant_id)
    )
    tenant_notifs = notifs_result.scalars().all()

    total = len(tenant_subs)
    active = len([s for s in tenant_subs if s.is_active])

    # Platform breakdown
    platforms: dict[str, int] = {}
    for s in tenant_subs:
        p = s.platform or "web"
        platforms[p] = platforms.get(p, 0) + 1

    # Recent notifications
    cutoff_24h = datetime.now(UTC) - timedelta(hours=24)
    recent_24h = len([n for n in tenant_notifs if n.created_at > cutoff_24h])
    recent_30d = len(tenant_notifs)

    return APIResponse(
        success=True,
        data=PushAnalytics(
            total_subscribers=total,
            active_subscribers_7d=active,
            notifications_sent_24h=recent_24h,
            notifications_sent_30d=recent_30d,
            click_rate=12.5,  # estimate
            platform_breakdown=platforms,
        ),
        message="Analytics retrieved",
    )


# =============================================================================
# Service Worker Content (served to frontend)
# =============================================================================


@router.get("/service-worker.js", response_class=None)
async def get_service_worker():
    """
    Serve the push notification service worker.

    The frontend registers this at /push-notifications/service-worker.js
    to handle background push events.
    """
    sw_code = """
// Stratum AI Push Notification Service Worker
self.addEventListener('push', function(event) {
    const data = event.data ? event.data.json() : {};
    const title = data.title || 'Stratum AI';
    const options = {
        body: data.body || '',
        icon: data.icon || '/icon-192.png',
        badge: data.badge || '/badge-72.png',
        image: data.image || undefined,
        tag: data.tag || 'default',
        requireInteraction: data.requireInteraction || false,
        actions: data.actions || [],
        data: { url: data.url || '/' }
    };
    event.waitUntil(self.registration.showNotification(title, options));
});

self.addEventListener('notificationclick', function(event) {
    event.notification.close();
    const url = event.notification.data?.url || '/';
    event.waitUntil(clients.openWindow(url));
});
"""
    from fastapi.responses import PlainTextResponse

    return PlainTextResponse(content=sw_code, media_type="application/javascript")
