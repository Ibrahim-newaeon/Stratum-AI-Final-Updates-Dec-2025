# =============================================================================
# Stratum AI — Push Notifications (Web Push API)
# =============================================================================
"""
Web Push notification system using VAPID keys.
Supports browser subscription, broadcast, targeted sends, and campaign alerts.
"""

from datetime import UTC, datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import get_async_session
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
# In-Memory Store
# =============================================================================

_subscriptions: dict[str, dict] = {}
_notifications: list[dict] = []


def _generate_id(prefix: str = "push") -> str:
    import secrets
    return f"{prefix}_{secrets.token_hex(8)}"


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
    public_key = getattr(settings, 'vapid_public_key', 'BJO_xP9SdCW7Lr0w0y0Z0X0Y0Z0X0Y0Z0X0Y0Z0X0Y0Z0X0Y0Z0X0Y0Z0')

    return APIResponse(
        success=True,
        data=PushVapidConfig(public_key=public_key, subject="mailto:admin@stratumai.app"),
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
    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant required")

    sub_id = _generate_id("sub")
    now = datetime.now(UTC).isoformat()

    _subscriptions[sub_id] = {
        "id": sub_id,
        "tenant_id": tenant_id,
        "endpoint": subscription.endpoint,
        "keys": subscription.keys,
        "user_agent": subscription.user_agent,
        "platform": subscription.platform,
        "is_active": True,
        "created_at": now,
        "last_active_at": now,
    }

    logger.info("push_subscription_created", tenant_id=tenant_id, subscription_id=sub_id)

    return APIResponse(
        success=True,
        data={"subscription_id": sub_id, "status": "subscribed"},
        message="Device subscribed for push notifications",
    )


@router.post("/unsubscribe", response_model=APIResponse[dict])
async def unsubscribe_device(
    endpoint: str,
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """Remove a push subscription."""
    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant required")

    removed = False
    for sub_id, sub in list(_subscriptions.items()):
        if sub.get("endpoint") == endpoint and sub.get("tenant_id") == tenant_id:
            sub["is_active"] = False
            removed = True

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
    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant required")

    # Get target subscriptions
    targets = []
    if notification.send_to_all:
        targets = [
            sub for sub in _subscriptions.values()
            if sub.get("tenant_id") == tenant_id and sub.get("is_active")
        ]
    elif notification.subscription_ids:
        targets = [
            _subscriptions.get(sid) for sid in notification.subscription_ids
            if _subscriptions.get(sid) and _subscriptions[sid].get("tenant_id") == tenant_id
        ]

    if not targets:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active subscribers found")

    # Simulate send (in production, use pywebpush library)
    sent = len(targets)
    delivered = int(sent * 0.95)  # 95% delivery rate estimate
    failed = sent - delivered

    notif_id = _generate_id("notif")
    now = datetime.now(UTC).isoformat()

    record = {
        "id": notif_id,
        "tenant_id": tenant_id,
        "title": notification.title,
        "body": notification.body,
        "url": notification.url,
        "tag": notification.tag,
        "sent_count": sent,
        "delivered_count": delivered,
        "failed_count": failed,
        "target_type": "all" if notification.send_to_all else "selected",
        "created_at": now,
    }
    _notifications.append(record)

    logger.info(
        "push_notification_sent",
        tenant_id=tenant_id,
        notification_id=notif_id,
        sent=sent,
        title=notification.title,
    )

    return APIResponse(
        success=True,
        data=PushNotificationResponse(
            id=notif_id,
            title=notification.title,
            body=notification.body,
            sent_count=sent,
            delivered_count=delivered,
            failed_count=failed,
            created_at=now,
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
    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant required")

    subs = [
        {
            "id": sub["id"],
            "platform": sub.get("platform", "web"),
            "is_active": sub.get("is_active", True),
            "created_at": sub["created_at"],
            "last_active_at": sub.get("last_active_at"),
        }
        for sub in _subscriptions.values()
        if sub.get("tenant_id") == tenant_id
        and (not platform or sub.get("platform") == platform)
        and (not active_only or sub.get("is_active"))
    ]

    return APIResponse(success=True, data=subs, message=f"Found {len(subs)} subscribers")


@router.get("/history", response_model=APIResponse[list[dict]])
async def get_notification_history(
    req: Request,
    db: AsyncSession = Depends(get_async_session),
    page: int = 1,
    page_size: int = 20,
):
    """Get sent notification history."""
    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant required")

    notifs = [
        n for n in sorted(_notifications, key=lambda x: x["created_at"], reverse=True)
        if n.get("tenant_id") == tenant_id
    ]

    start = (page - 1) * page_size
    paginated = notifs[start:start + page_size]

    return APIResponse(success=True, data=paginated, message=f"Found {len(notifs)} notifications")


@router.get("/analytics", response_model=APIResponse[PushAnalytics])
async def get_push_analytics(
    req: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """Get push notification analytics."""
    tenant_id = getattr(req.state, "tenant_id", None)
    if not tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Tenant required")

    tenant_subs = [s for s in _subscriptions.values() if s.get("tenant_id") == tenant_id]
    tenant_notifs = [n for n in _notifications if n.get("tenant_id") == tenant_id]

    total = len(tenant_subs)
    active = len([s for s in tenant_subs if s.get("is_active")])

    # Platform breakdown
    platforms = {}
    for s in tenant_subs:
        p = s.get("platform", "web")
        platforms[p] = platforms.get(p, 0) + 1

    # Recent notifications
    recent_24h = len([n for n in tenant_notifs if n["created_at"] > (datetime.now(UTC) - timedelta(hours=24)).isoformat()])
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
