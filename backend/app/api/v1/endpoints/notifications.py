# =============================================================================
# Stratum AI - In-App Notifications Endpoints
# =============================================================================
"""
In-app notification management:
- List notifications
- Mark as read
- Delete notifications
- Get unread count
"""

from datetime import UTC, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_async_session
from app.models.settings import (
    Notification,
    NotificationCategory,
    NotificationType,
)
from app.schemas.response import APIResponse

router = APIRouter(prefix="/notifications", tags=["Notifications"])
logger = get_logger(__name__)


# =============================================================================
# Pydantic Schemas
# =============================================================================


class NotificationResponse(BaseModel):
    """Notification response."""

    id: int
    title: str
    message: str
    type: str
    category: str
    is_read: bool
    read_at: Optional[datetime]
    action_url: Optional[str]
    action_label: Optional[str]
    metadata: Optional[dict]
    created_at: datetime


class NotificationCountResponse(BaseModel):
    """Unread notification count."""

    unread_count: int
    total_count: int


class NotificationCreateRequest(BaseModel):
    """Request to create a notification (admin/system use)."""

    title: str = Field(..., min_length=1, max_length=255)
    message: str = Field(..., min_length=1)
    type: str = Field(default="info")
    category: str = Field(default="system")
    user_id: Optional[int] = Field(default=None, description="Specific user, or null for broadcast")
    action_url: Optional[str] = None
    action_label: Optional[str] = None
    metadata: Optional[dict] = None


class MarkReadRequest(BaseModel):
    """Request to mark notifications as read."""

    notification_ids: Optional[list[int]] = Field(
        default=None, description="Specific IDs, or null for all"
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=APIResponse[list[NotificationResponse]])
async def list_notifications(
    request: Request,
    unread_only: bool = False,
    category: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[list[NotificationResponse]]:
    """
    List notifications for the current user.
    """
    user_id = getattr(request.state, "user_id", None)
    tenant_id = getattr(request.state, "tenant_id", None)

    if not user_id or not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    # Build query - user's notifications + tenant broadcasts
    conditions = [
        Notification.tenant_id == tenant_id,
        ((Notification.user_id == user_id) | (Notification.user_id.is_(None))),
    ]

    if unread_only:
        conditions.append(Notification.is_read == False)

    if category:
        try:
            cat = NotificationCategory(category)
            conditions.append(Notification.category == cat)
        except ValueError:
            pass

    # Filter out expired notifications
    conditions.append(
        (Notification.expires_at.is_(None)) | (Notification.expires_at > datetime.now(UTC))
    )

    result = await db.execute(
        select(Notification)
        .where(and_(*conditions))
        .order_by(desc(Notification.created_at))
        .limit(limit)
        .offset(offset)
    )
    notifications = result.scalars().all()

    return APIResponse(
        success=True,
        data=[
            NotificationResponse(
                id=n.id,
                title=n.title,
                message=n.message,
                type=n.type.value,
                category=n.category.value,
                is_read=n.is_read,
                read_at=n.read_at,
                action_url=n.action_url,
                action_label=n.action_label,
                metadata=n.extra_data,
                created_at=n.created_at,
            )
            for n in notifications
        ],
    )


@router.get("/count", response_model=APIResponse[NotificationCountResponse])
async def get_notification_count(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[NotificationCountResponse]:
    """
    Get notification counts for the current user.
    """
    user_id = getattr(request.state, "user_id", None)
    tenant_id = getattr(request.state, "tenant_id", None)

    if not user_id or not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    base_conditions = [
        Notification.tenant_id == tenant_id,
        ((Notification.user_id == user_id) | (Notification.user_id.is_(None))),
        (Notification.expires_at.is_(None)) | (Notification.expires_at > datetime.now(UTC)),
    ]

    # Total count
    total_result = await db.execute(
        select(func.count(Notification.id)).where(and_(*base_conditions))
    )
    total_count = total_result.scalar() or 0

    # Unread count
    unread_result = await db.execute(
        select(func.count(Notification.id)).where(
            and_(*base_conditions, Notification.is_read == False)
        )
    )
    unread_count = unread_result.scalar() or 0

    return APIResponse(
        success=True,
        data=NotificationCountResponse(
            unread_count=unread_count,
            total_count=total_count,
        ),
    )


@router.post("/mark-read", response_model=APIResponse[dict])
async def mark_notifications_read(
    request: Request,
    body: MarkReadRequest,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[dict]:
    """
    Mark notifications as read.
    """
    user_id = getattr(request.state, "user_id", None)
    tenant_id = getattr(request.state, "tenant_id", None)

    if not user_id or not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    now = datetime.now(UTC)

    conditions = [
        Notification.tenant_id == tenant_id,
        ((Notification.user_id == user_id) | (Notification.user_id.is_(None))),
        Notification.is_read == False,
    ]

    if body.notification_ids:
        conditions.append(Notification.id.in_(body.notification_ids))

    result = await db.execute(
        update(Notification)
        .where(and_(*conditions))
        .values(is_read=True, read_at=now)
        .returning(Notification.id)
    )
    updated_ids = result.scalars().all()
    await db.commit()

    return APIResponse(
        success=True,
        data={"marked_read": len(updated_ids)},
        message=f"{len(updated_ids)} notification(s) marked as read",
    )


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    request: Request,
    notification_id: int,
    db: AsyncSession = Depends(get_async_session),
) -> None:
    """
    Delete a notification.
    """
    user_id = getattr(request.state, "user_id", None)
    tenant_id = getattr(request.state, "tenant_id", None)

    if not user_id or not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    result = await db.execute(
        select(Notification).where(
            and_(
                Notification.id == notification_id,
                Notification.tenant_id == tenant_id,
                ((Notification.user_id == user_id) | (Notification.user_id.is_(None))),
            )
        )
    )
    notification = result.scalar_one_or_none()

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found",
        )

    await db.delete(notification)
    await db.commit()


@router.post(
    "", response_model=APIResponse[NotificationResponse], status_code=status.HTTP_201_CREATED
)
async def create_notification(
    request: Request,
    body: NotificationCreateRequest,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[NotificationResponse]:
    """
    Create a new notification (admin/system use).
    """
    user_id = getattr(request.state, "user_id", None)
    tenant_id = getattr(request.state, "tenant_id", None)

    if not user_id or not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    # TODO: Add admin role check here if needed

    try:
        notif_type = NotificationType(body.type)
    except ValueError:
        notif_type = NotificationType.INFO

    try:
        notif_category = NotificationCategory(body.category)
    except ValueError:
        notif_category = NotificationCategory.SYSTEM

    notification = Notification(
        tenant_id=tenant_id,
        user_id=body.user_id,
        title=body.title,
        message=body.message,
        type=notif_type,
        category=notif_category,
        action_url=body.action_url,
        action_label=body.action_label,
        extra_data=body.metadata,
    )

    db.add(notification)
    await db.commit()
    await db.refresh(notification)

    logger.info(f"Notification created: {notification.id}")

    return APIResponse(
        success=True,
        data=NotificationResponse(
            id=notification.id,
            title=notification.title,
            message=notification.message,
            type=notification.type.value,
            category=notification.category.value,
            is_read=notification.is_read,
            read_at=notification.read_at,
            action_url=notification.action_url,
            action_label=notification.action_label,
            metadata=notification.extra_data,
            created_at=notification.created_at,
        ),
    )
