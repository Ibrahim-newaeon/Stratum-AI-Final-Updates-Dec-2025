# =============================================================================
# Stratum AI - Slack Integration Endpoints
# =============================================================================
"""
Slack integration management:
- Configure Slack webhook
- Test connection
- Update notification preferences
- Send manual notifications
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.session import get_async_session
from app.models.settings import SlackIntegration
from app.services.notifications.slack_service import (
    SlackNotificationService,
    TrustGateStatus,
    AlertSeverity,
)
from app.schemas.response import APIResponse

router = APIRouter(prefix="/slack", tags=["Slack Integration"])
logger = get_logger(__name__)


# =============================================================================
# Pydantic Schemas
# =============================================================================

class SlackConfigRequest(BaseModel):
    """Request to configure Slack integration."""
    webhook_url: str = Field(..., description="Slack webhook URL")
    channel_name: Optional[str] = Field(None, max_length=100)
    notify_trust_gate: bool = Field(default=True)
    notify_anomalies: bool = Field(default=True)
    notify_signal_health: bool = Field(default=False)
    notify_daily_summary: bool = Field(default=True)


class SlackConfigResponse(BaseModel):
    """Slack integration configuration response."""
    id: int
    webhook_url_masked: str
    channel_name: Optional[str]
    notify_trust_gate: bool
    notify_anomalies: bool
    notify_signal_health: bool
    notify_daily_summary: bool
    is_active: bool
    last_test_at: Optional[datetime]
    last_test_success: Optional[bool]
    created_at: datetime
    updated_at: datetime


class SlackTestResponse(BaseModel):
    """Response from testing Slack connection."""
    success: bool
    message: str


class SlackNotifyRequest(BaseModel):
    """Request to send a manual Slack notification."""
    message: str = Field(..., min_length=1, max_length=3000)
    type: str = Field(default="info", description="info, warning, success, or error")


# =============================================================================
# Helper Functions
# =============================================================================

def mask_webhook_url(url: str) -> str:
    """Mask the webhook URL for display."""
    if not url:
        return ""
    # Show first part and mask the rest
    parts = url.split("/")
    if len(parts) > 4:
        return f"{'/'.join(parts[:4])}/{'*' * 20}"
    return url[:30] + "..." if len(url) > 30 else url


# =============================================================================
# Endpoints
# =============================================================================

@router.get("", response_model=APIResponse[Optional[SlackConfigResponse]])
async def get_slack_config(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[Optional[SlackConfigResponse]]:
    """
    Get Slack integration configuration for the current tenant.
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    result = await db.execute(
        select(SlackIntegration).where(SlackIntegration.tenant_id == tenant_id)
    )
    integration = result.scalar_one_or_none()

    if not integration:
        return APIResponse(success=True, data=None)

    return APIResponse(
        success=True,
        data=SlackConfigResponse(
            id=integration.id,
            webhook_url_masked=mask_webhook_url(integration.webhook_url),
            channel_name=integration.channel_name,
            notify_trust_gate=integration.notify_trust_gate,
            notify_anomalies=integration.notify_anomalies,
            notify_signal_health=integration.notify_signal_health,
            notify_daily_summary=integration.notify_daily_summary,
            is_active=integration.is_active,
            last_test_at=integration.last_test_at,
            last_test_success=integration.last_test_success,
            created_at=integration.created_at,
            updated_at=integration.updated_at,
        ),
    )


@router.post("", response_model=APIResponse[SlackConfigResponse])
async def configure_slack(
    request: Request,
    body: SlackConfigRequest,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[SlackConfigResponse]:
    """
    Configure or update Slack integration.
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    # Validate webhook URL format
    if not body.webhook_url.startswith("https://hooks.slack.com/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Slack webhook URL. Must start with https://hooks.slack.com/",
        )

    # Check for existing integration
    result = await db.execute(
        select(SlackIntegration).where(SlackIntegration.tenant_id == tenant_id)
    )
    integration = result.scalar_one_or_none()

    if integration:
        # Update existing
        integration.webhook_url = body.webhook_url
        integration.channel_name = body.channel_name
        integration.notify_trust_gate = body.notify_trust_gate
        integration.notify_anomalies = body.notify_anomalies
        integration.notify_signal_health = body.notify_signal_health
        integration.notify_daily_summary = body.notify_daily_summary
        integration.is_active = True
    else:
        # Create new
        integration = SlackIntegration(
            tenant_id=tenant_id,
            webhook_url=body.webhook_url,
            channel_name=body.channel_name,
            notify_trust_gate=body.notify_trust_gate,
            notify_anomalies=body.notify_anomalies,
            notify_signal_health=body.notify_signal_health,
            notify_daily_summary=body.notify_daily_summary,
            is_active=True,
        )
        db.add(integration)

    await db.commit()
    await db.refresh(integration)

    logger.info(f"Slack integration configured for tenant {tenant_id}")

    return APIResponse(
        success=True,
        data=SlackConfigResponse(
            id=integration.id,
            webhook_url_masked=mask_webhook_url(integration.webhook_url),
            channel_name=integration.channel_name,
            notify_trust_gate=integration.notify_trust_gate,
            notify_anomalies=integration.notify_anomalies,
            notify_signal_health=integration.notify_signal_health,
            notify_daily_summary=integration.notify_daily_summary,
            is_active=integration.is_active,
            last_test_at=integration.last_test_at,
            last_test_success=integration.last_test_success,
            created_at=integration.created_at,
            updated_at=integration.updated_at,
        ),
        message="Slack integration configured successfully",
    )


@router.post("/test", response_model=APIResponse[SlackTestResponse])
async def test_slack_connection(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[SlackTestResponse]:
    """
    Test the Slack webhook connection.
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    result = await db.execute(
        select(SlackIntegration).where(SlackIntegration.tenant_id == tenant_id)
    )
    integration = result.scalar_one_or_none()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slack integration not configured",
        )

    # Test the connection
    slack_service = SlackNotificationService(integration.webhook_url)
    try:
        success = await slack_service.test_connection()
        await slack_service.close()

        # Update test status
        integration.last_test_at = datetime.now(timezone.utc)
        integration.last_test_success = success
        await db.commit()

        if success:
            return APIResponse(
                success=True,
                data=SlackTestResponse(
                    success=True,
                    message="Connection test successful! Check your Slack channel.",
                ),
            )
        else:
            return APIResponse(
                success=True,
                data=SlackTestResponse(
                    success=False,
                    message="Connection test failed. Please check your webhook URL.",
                ),
            )
    except Exception as e:
        logger.error(f"Slack test failed: {e}")
        integration.last_test_at = datetime.now(timezone.utc)
        integration.last_test_success = False
        await db.commit()

        return APIResponse(
            success=True,
            data=SlackTestResponse(
                success=False,
                message=f"Connection test failed: {str(e)}",
            ),
        )


@router.post("/notify", response_model=APIResponse[SlackTestResponse])
async def send_slack_notification(
    request: Request,
    body: SlackNotifyRequest,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[SlackTestResponse]:
    """
    Send a manual notification to Slack.
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    result = await db.execute(
        select(SlackIntegration).where(
            SlackIntegration.tenant_id == tenant_id,
            SlackIntegration.is_active == True,
        )
    )
    integration = result.scalar_one_or_none()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slack integration not configured or not active",
        )

    # Map type to emoji
    emoji_map = {
        "info": "i",
        "warning": "warning",
        "success": "white_check_mark",
        "error": "x",
    }
    emoji = emoji_map.get(body.type, "speech_balloon")

    slack_service = SlackNotificationService(integration.webhook_url)
    try:
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f":{emoji}: {body.message}",
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Sent from Stratum AI at {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
                    }
                ]
            }
        ]

        success = await slack_service.send_message(
            text=body.message,
            blocks=blocks,
        )
        await slack_service.close()

        if success:
            return APIResponse(
                success=True,
                data=SlackTestResponse(
                    success=True,
                    message="Notification sent successfully",
                ),
            )
        else:
            return APIResponse(
                success=True,
                data=SlackTestResponse(
                    success=False,
                    message="Failed to send notification",
                ),
            )
    except Exception as e:
        logger.error(f"Slack notify failed: {e}")
        return APIResponse(
            success=True,
            data=SlackTestResponse(
                success=False,
                message=f"Failed to send notification: {str(e)}",
            ),
        )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_slack(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
) -> None:
    """
    Disconnect Slack integration.
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    result = await db.execute(
        select(SlackIntegration).where(SlackIntegration.tenant_id == tenant_id)
    )
    integration = result.scalar_one_or_none()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slack integration not found",
        )

    await db.delete(integration)
    await db.commit()

    logger.info(f"Slack integration disconnected for tenant {tenant_id}")


@router.patch("/toggle", response_model=APIResponse[SlackConfigResponse])
async def toggle_slack(
    request: Request,
    is_active: bool,
    db: AsyncSession = Depends(get_async_session),
) -> APIResponse[SlackConfigResponse]:
    """
    Enable or disable Slack integration.
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    result = await db.execute(
        select(SlackIntegration).where(SlackIntegration.tenant_id == tenant_id)
    )
    integration = result.scalar_one_or_none()

    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Slack integration not found",
        )

    integration.is_active = is_active
    await db.commit()
    await db.refresh(integration)

    return APIResponse(
        success=True,
        data=SlackConfigResponse(
            id=integration.id,
            webhook_url_masked=mask_webhook_url(integration.webhook_url),
            channel_name=integration.channel_name,
            notify_trust_gate=integration.notify_trust_gate,
            notify_anomalies=integration.notify_anomalies,
            notify_signal_health=integration.notify_signal_health,
            notify_daily_summary=integration.notify_daily_summary,
            is_active=integration.is_active,
            last_test_at=integration.last_test_at,
            last_test_success=integration.last_test_success,
            created_at=integration.created_at,
            updated_at=integration.updated_at,
        ),
        message=f"Slack integration {'enabled' if is_active else 'disabled'}",
    )
