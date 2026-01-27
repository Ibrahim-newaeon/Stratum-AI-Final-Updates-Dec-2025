# =============================================================================
# Stratum AI - Webhooks Management Endpoints
# =============================================================================
"""
CRUD operations for webhooks:
- Create webhook endpoints
- List webhooks
- Update webhook configuration
- Test webhooks
- View delivery history
- Delete webhooks
"""

import secrets
from datetime import UTC, datetime
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_async_session
from app.models.settings import (
    Webhook,
    WebhookDelivery,
    WebhookStatus,
)
from app.schemas.response import APIResponse

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])
logger = get_logger(__name__)


# =============================================================================
# Pydantic Schemas
# =============================================================================


class WebhookCreateRequest(BaseModel):
    """Request to create a new webhook."""

    name: str = Field(..., min_length=1, max_length=255)
    url: str = Field(..., description="Webhook endpoint URL")
    events: list[str] = Field(..., min_length=1, description="Events to subscribe to")
    headers: Optional[dict] = Field(default=None, description="Custom headers to include")


class WebhookUpdateRequest(BaseModel):
    """Request to update a webhook."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    url: Optional[str] = None
    events: Optional[list[str]] = None
    headers: Optional[dict] = None
    status: Optional[str] = None


class WebhookResponse(BaseModel):
    """Webhook response."""

    id: int
    name: str
    url: str
    events: list[str]
    status: str
    headers: Optional[dict]
    failure_count: int
    last_triggered_at: Optional[datetime]
    last_success_at: Optional[datetime]
    last_failure_at: Optional[datetime]
    last_failure_reason: Optional[str]
    created_at: datetime
    updated_at: datetime


class WebhookDeliveryResponse(BaseModel):
    """Webhook delivery log entry."""

    id: int
    event_type: str
    payload: dict
    success: bool
    status_code: Optional[int]
    response_body: Optional[str]
    error_message: Optional[str]
    duration_ms: Optional[int]
    created_at: datetime


class WebhookTestResponse(BaseModel):
    """Response from testing a webhook."""

    success: bool
    status_code: Optional[int]
    response_body: Optional[str]
    error_message: Optional[str]
    duration_ms: int


class WebhookEventTypesResponse(BaseModel):
    """Available webhook event types."""

    event_types: list[dict]


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/event-types", response_model=APIResponse[WebhookEventTypesResponse])
async def get_event_types() -> APIResponse[WebhookEventTypesResponse]:
    """
    Get available webhook event types.
    """
    event_types = [
        {
            "id": "campaign.updated",
            "label": "Campaign Updated",
            "description": "When campaign settings change",
        },
        {
            "id": "campaign.paused",
            "label": "Campaign Paused",
            "description": "When a campaign is paused",
        },
        {
            "id": "alert.triggered",
            "label": "Alert Triggered",
            "description": "When performance alerts fire",
        },
        {
            "id": "budget.depleted",
            "label": "Budget Depleted",
            "description": "When daily budget runs out",
        },
        {
            "id": "sync.completed",
            "label": "Sync Completed",
            "description": "When data sync finishes",
        },
        {
            "id": "anomaly.detected",
            "label": "Anomaly Detected",
            "description": "When unusual patterns found",
        },
        {
            "id": "trust_gate.pass",
            "label": "Trust Gate Pass",
            "description": "When automation passes trust gate",
        },
        {
            "id": "trust_gate.hold",
            "label": "Trust Gate Hold",
            "description": "When automation is on hold",
        },
        {
            "id": "trust_gate.block",
            "label": "Trust Gate Block",
            "description": "When automation is blocked",
        },
    ]
    return APIResponse(success=True, data=WebhookEventTypesResponse(event_types=event_types))


@router.get("", response_model=APIResponse[list[WebhookResponse]])
async def list_webhooks(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[list[WebhookResponse]]:
    """
    List all webhooks for the current tenant.
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    result = await db.execute(
        select(Webhook).where(Webhook.tenant_id == tenant_id).order_by(Webhook.created_at.desc())
    )
    webhooks = result.scalars().all()

    return APIResponse(
        success=True,
        data=[
            WebhookResponse(
                id=wh.id,
                name=wh.name,
                url=wh.url,
                events=wh.events or [],
                status=wh.status.value,
                headers=wh.headers,
                failure_count=wh.failure_count,
                last_triggered_at=wh.last_triggered_at,
                last_success_at=wh.last_success_at,
                last_failure_at=wh.last_failure_at,
                last_failure_reason=wh.last_failure_reason,
                created_at=wh.created_at,
                updated_at=wh.updated_at,
            )
            for wh in webhooks
        ],
    )


@router.get("/{webhook_id}", response_model=APIResponse[WebhookResponse])
async def get_webhook(
    request: Request,
    webhook_id: int,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[WebhookResponse]:
    """
    Get a specific webhook.
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    result = await db.execute(
        select(Webhook).where(and_(Webhook.id == webhook_id, Webhook.tenant_id == tenant_id))
    )
    webhook = result.scalar_one_or_none()

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    return APIResponse(
        success=True,
        data=WebhookResponse(
            id=webhook.id,
            name=webhook.name,
            url=webhook.url,
            events=webhook.events or [],
            status=webhook.status.value,
            headers=webhook.headers,
            failure_count=webhook.failure_count,
            last_triggered_at=webhook.last_triggered_at,
            last_success_at=webhook.last_success_at,
            last_failure_at=webhook.last_failure_at,
            last_failure_reason=webhook.last_failure_reason,
            created_at=webhook.created_at,
            updated_at=webhook.updated_at,
        ),
    )


@router.post("", response_model=APIResponse[WebhookResponse], status_code=status.HTTP_201_CREATED)
async def create_webhook(
    request: Request,
    body: WebhookCreateRequest,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[WebhookResponse]:
    """
    Create a new webhook endpoint.
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    # Check webhook limit (max 20 per tenant)
    result = await db.execute(select(Webhook).where(Webhook.tenant_id == tenant_id))
    if len(result.scalars().all()) >= 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum of 20 webhooks allowed per tenant",
        )

    # Generate signing secret
    signing_secret = secrets.token_urlsafe(32)

    webhook = Webhook(
        tenant_id=tenant_id,
        name=body.name,
        url=body.url,
        events=body.events,
        headers=body.headers,
        secret=signing_secret,
        status=WebhookStatus.ACTIVE,
    )

    db.add(webhook)
    await db.commit()
    await db.refresh(webhook)

    logger.info(f"Webhook created: {webhook.id} for tenant {tenant_id}")

    return APIResponse(
        success=True,
        data=WebhookResponse(
            id=webhook.id,
            name=webhook.name,
            url=webhook.url,
            events=webhook.events or [],
            status=webhook.status.value,
            headers=webhook.headers,
            failure_count=webhook.failure_count,
            last_triggered_at=webhook.last_triggered_at,
            last_success_at=webhook.last_success_at,
            last_failure_at=webhook.last_failure_at,
            last_failure_reason=webhook.last_failure_reason,
            created_at=webhook.created_at,
            updated_at=webhook.updated_at,
        ),
        message="Webhook created successfully",
    )


@router.patch("/{webhook_id}", response_model=APIResponse[WebhookResponse])
async def update_webhook(
    request: Request,
    webhook_id: int,
    body: WebhookUpdateRequest,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[WebhookResponse]:
    """
    Update a webhook.
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    result = await db.execute(
        select(Webhook).where(and_(Webhook.id == webhook_id, Webhook.tenant_id == tenant_id))
    )
    webhook = result.scalar_one_or_none()

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    # Update fields
    if body.name is not None:
        webhook.name = body.name
    if body.url is not None:
        webhook.url = body.url
    if body.events is not None:
        webhook.events = body.events
    if body.headers is not None:
        webhook.headers = body.headers
    if body.status is not None:
        webhook.status = WebhookStatus(body.status)
        # Reset failure count when reactivating
        if body.status == "active":
            webhook.failure_count = 0

    await db.commit()
    await db.refresh(webhook)

    return APIResponse(
        success=True,
        data=WebhookResponse(
            id=webhook.id,
            name=webhook.name,
            url=webhook.url,
            events=webhook.events or [],
            status=webhook.status.value,
            headers=webhook.headers,
            failure_count=webhook.failure_count,
            last_triggered_at=webhook.last_triggered_at,
            last_success_at=webhook.last_success_at,
            last_failure_at=webhook.last_failure_at,
            last_failure_reason=webhook.last_failure_reason,
            created_at=webhook.created_at,
            updated_at=webhook.updated_at,
        ),
    )


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    request: Request,
    webhook_id: int,
    db: AsyncSession = Depends(get_async_session),
) -> None:
    """
    Delete a webhook.
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    result = await db.execute(
        select(Webhook).where(and_(Webhook.id == webhook_id, Webhook.tenant_id == tenant_id))
    )
    webhook = result.scalar_one_or_none()

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    await db.delete(webhook)
    await db.commit()

    logger.info(f"Webhook deleted: {webhook_id}")


@router.post("/{webhook_id}/test", response_model=APIResponse[WebhookTestResponse])
async def test_webhook(
    request: Request,
    webhook_id: int,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[WebhookTestResponse]:
    """
    Send a test event to a webhook endpoint.
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    result = await db.execute(
        select(Webhook).where(and_(Webhook.id == webhook_id, Webhook.tenant_id == tenant_id))
    )
    webhook = result.scalar_one_or_none()

    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    # Send test payload
    test_payload = {
        "event": "test",
        "timestamp": datetime.now(UTC).isoformat(),
        "data": {
            "message": "This is a test webhook from Stratum AI",
            "webhook_id": webhook_id,
        },
    }

    start_time = datetime.now(UTC)
    success = False
    status_code = None
    response_body = None
    error_message = None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            headers = {"Content-Type": "application/json", "X-Stratum-Event": "test"}
            if webhook.headers:
                headers.update(webhook.headers)

            response = await client.post(webhook.url, json=test_payload, headers=headers)
            status_code = response.status_code
            response_body = response.text[:1000] if response.text else None
            success = 200 <= response.status_code < 300
    except httpx.TimeoutException:
        error_message = "Request timed out"
    except httpx.RequestError as e:
        error_message = str(e)
    except Exception as e:
        error_message = f"Unexpected error: {e!s}"

    duration_ms = int((datetime.now(UTC) - start_time).total_seconds() * 1000)

    # Update webhook test status
    webhook.last_triggered_at = datetime.now(UTC)
    if success:
        webhook.last_success_at = datetime.now(UTC)
    else:
        webhook.last_failure_at = datetime.now(UTC)
        webhook.last_failure_reason = error_message

    await db.commit()

    return APIResponse(
        success=True,
        data=WebhookTestResponse(
            success=success,
            status_code=status_code,
            response_body=response_body,
            error_message=error_message,
            duration_ms=duration_ms,
        ),
    )


@router.get("/{webhook_id}/deliveries", response_model=APIResponse[list[WebhookDeliveryResponse]])
async def get_webhook_deliveries(
    request: Request,
    webhook_id: int,
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[list[WebhookDeliveryResponse]]:
    """
    Get delivery history for a webhook.
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    # Verify webhook belongs to tenant
    result = await db.execute(
        select(Webhook).where(and_(Webhook.id == webhook_id, Webhook.tenant_id == tenant_id))
    )
    if not result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    # Get deliveries
    result = await db.execute(
        select(WebhookDelivery)
        .where(WebhookDelivery.webhook_id == webhook_id)
        .order_by(desc(WebhookDelivery.created_at))
        .limit(limit)
        .offset(offset)
    )
    deliveries = result.scalars().all()

    return APIResponse(
        success=True,
        data=[
            WebhookDeliveryResponse(
                id=d.id,
                event_type=d.event_type,
                payload=d.payload,
                success=d.success,
                status_code=d.status_code,
                response_body=d.response_body,
                error_message=d.error_message,
                duration_ms=d.duration_ms,
                created_at=d.created_at,
            )
            for d in deliveries
        ],
    )
