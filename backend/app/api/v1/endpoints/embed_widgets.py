# =============================================================================
# Stratum AI - Embed Widgets API Endpoints
# =============================================================================
"""
API endpoints for managing embeddable widgets.

Endpoints:
- Widget CRUD (create, read, update, delete)
- Token management (create, refresh, revoke)
- Domain whitelist management
- Embed code generation
- Public widget data endpoint (for embedding)
"""

from datetime import UTC, datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.feature_gate import get_current_tier
from app.core.tiers import Feature, SubscriptionTier, get_tier_limit, has_feature
from app.db.session import get_db
from app.models import Campaign
from app.models.embed_widgets import (
    BrandingLevel,
    EmbedToken,
    EmbedWidget,
    WidgetType,
)
from app.schemas.embed_widgets import (
    DomainWhitelistCreate,
    DomainWhitelistResponse,
    EmbedCodeResponse,
    TokenCreate,
    TokenCreateResponse,
    TokenRefresh,
    TokenRefreshResponse,
    TokenResponse,
    WidgetCreate,
    WidgetResponse,
    WidgetType as WidgetTypeEnum,
    WidgetUpdate,
)
from app.services.embed_widgets import (
    EmbedSecurityService,
    EmbedTokenService,
    EmbedWidgetService,
)

router = APIRouter(prefix="/embed-widgets", tags=["embed-widgets"])


# =============================================================================
# Dependencies
# =============================================================================


def get_widget_service(db: AsyncSession = Depends(get_db)) -> EmbedWidgetService:
    return EmbedWidgetService(db)


def get_token_service(db: AsyncSession = Depends(get_db)) -> EmbedTokenService:
    return EmbedTokenService(db)


def get_security_service() -> EmbedSecurityService:
    if not settings.embed_signing_key or len(settings.embed_signing_key) < 32:
        raise HTTPException(
            status_code=503,
            detail="Embed widget service not configured (EMBED_SIGNING_KEY required)",
        )
    return EmbedSecurityService(settings.embed_signing_key)


def get_tenant_id(request: Request) -> int:
    """Extract tenant_id from request state (set by tenant middleware)."""
    tenant_id = getattr(request.state, "tenant_id", None)
    if tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Tenant context not found. Authenticate first.",
        )
    return int(tenant_id)


# =============================================================================
# Widget Endpoints
# =============================================================================


@router.post("/widgets", response_model=WidgetResponse, status_code=status.HTTP_201_CREATED)
async def create_widget(
    data: WidgetCreate,
    tenant_id: int = Depends(get_tenant_id),
    service: EmbedWidgetService = Depends(get_widget_service),
):
    """
    Create a new embed widget.

    Branding level is automatically determined by subscription tier:
    - Starter: Full Stratum branding
    - Professional: Minimal "Powered by Stratum" branding
    - Enterprise: No branding (white-label)
    """
    tier = get_current_tier()

    # Check feature access
    if not has_feature(tier, Feature.EMBED_WIDGETS_BASIC):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Embed widgets not available in your plan"
        )

    widget = service.create_widget(tenant_id, data, tier)
    return widget


@router.get("/widgets", response_model=list[WidgetResponse])
async def list_widgets(
    widget_type: Optional[WidgetTypeEnum] = None,
    is_active: Optional[bool] = None,
    tenant_id: int = Depends(get_tenant_id),
    service: EmbedWidgetService = Depends(get_widget_service),
):
    """List all widgets for the current tenant."""
    widgets = service.list_widgets(tenant_id, widget_type, is_active)
    return widgets


@router.get("/widgets/{widget_id}", response_model=WidgetResponse)
async def get_widget(
    widget_id: UUID,
    tenant_id: int = Depends(get_tenant_id),
    service: EmbedWidgetService = Depends(get_widget_service),
):
    """Get a specific widget by ID."""
    widget = service.get_widget(tenant_id, widget_id)
    if not widget:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not found")
    return widget


@router.patch("/widgets/{widget_id}", response_model=WidgetResponse)
async def update_widget(
    widget_id: UUID,
    data: WidgetUpdate,
    tenant_id: int = Depends(get_tenant_id),
    service: EmbedWidgetService = Depends(get_widget_service),
):
    """Update an existing widget."""
    tier = get_current_tier()
    widget = service.update_widget(tenant_id, widget_id, data, tier)
    return widget


@router.delete("/widgets/{widget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_widget(
    widget_id: UUID,
    tenant_id: int = Depends(get_tenant_id),
    service: EmbedWidgetService = Depends(get_widget_service),
):
    """Delete a widget and all associated tokens."""
    service.delete_widget(tenant_id, widget_id)


# =============================================================================
# Token Endpoints
# =============================================================================


@router.post(
    "/widgets/{widget_id}/tokens",
    response_model=TokenCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_token(
    widget_id: UUID,
    data: TokenCreate,
    tenant_id: int = Depends(get_tenant_id),
    service: EmbedTokenService = Depends(get_token_service),
):
    """
    Create a new embed token for a widget.

    IMPORTANT: The token value is only returned once at creation.
    Store it securely - it cannot be retrieved again.
    """
    tier = get_current_tier()
    token, plaintext_token, refresh_token = service.create_token(
        tenant_id=tenant_id,
        widget_id=widget_id,
        allowed_domains=data.allowed_domains,
        tier=tier,
        expires_in_days=data.expires_in_days,
    )

    return TokenCreateResponse(
        id=token.id,
        token=plaintext_token,
        refresh_token=refresh_token,
        token_prefix=token.token_prefix,
        allowed_domains=token.allowed_domains,
        expires_at=token.expires_at,
        rate_limit_per_minute=token.rate_limit_per_minute,
    )


@router.get("/widgets/{widget_id}/tokens", response_model=list[TokenResponse])
async def list_tokens(
    widget_id: UUID,
    tenant_id: int = Depends(get_tenant_id),
    db: AsyncSession = Depends(get_db),
):
    """List all tokens for a widget (without actual token values)."""
    result = await db.execute(
        select(EmbedToken)
        .where(
            EmbedToken.widget_id == widget_id,
            EmbedToken.tenant_id == tenant_id,
        )
        .order_by(EmbedToken.created_at.desc()).limit(1000)
    )
    tokens = result.scalars().all()

    return tokens


@router.post("/tokens/{token_id}/refresh", response_model=TokenRefreshResponse)
async def refresh_token(
    token_id: UUID,
    data: TokenRefresh,
    service: EmbedTokenService = Depends(get_token_service),
):
    """
    Refresh an embed token using the refresh token.

    This rotates both the main token and refresh token for security.
    """
    new_token, new_refresh, expires_at = service.refresh_token(token_id, data.refresh_token)

    return TokenRefreshResponse(
        token=new_token,
        refresh_token=new_refresh,
        expires_at=expires_at,
    )


@router.delete("/tokens/{token_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_token(
    token_id: UUID,
    tenant_id: int = Depends(get_tenant_id),
    service: EmbedTokenService = Depends(get_token_service),
):
    """Revoke an embed token."""
    service.revoke_token(tenant_id, token_id)


# =============================================================================
# Domain Whitelist Endpoints
# =============================================================================


@router.post(
    "/domains", response_model=DomainWhitelistResponse, status_code=status.HTTP_201_CREATED
)
async def add_domain(
    data: DomainWhitelistCreate,
    tenant_id: int = Depends(get_tenant_id),
    service: EmbedWidgetService = Depends(get_widget_service),
):
    """
    Add a domain to the whitelist.

    Domains must be whitelisted before they can be used with tokens.
    Supports wildcards like *.example.com
    """
    tier = get_current_tier()
    domain = service.add_domain_to_whitelist(
        tenant_id=tenant_id,
        domain_pattern=data.domain_pattern,
        description=data.description,
        tier=tier,
    )
    return domain


@router.get("/domains", response_model=list[DomainWhitelistResponse])
async def list_domains(
    tenant_id: int = Depends(get_tenant_id),
    service: EmbedWidgetService = Depends(get_widget_service),
):
    """List all whitelisted domains."""
    domains = service.list_whitelisted_domains(tenant_id)
    return domains


@router.delete("/domains/{domain_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_domain(
    domain_id: UUID,
    tenant_id: int = Depends(get_tenant_id),
    service: EmbedWidgetService = Depends(get_widget_service),
):
    """Remove a domain from the whitelist."""
    service.remove_domain_from_whitelist(tenant_id, domain_id)


# =============================================================================
# Embed Code Generation
# =============================================================================


@router.get("/widgets/{widget_id}/embed-code", response_model=EmbedCodeResponse)
async def get_embed_code(
    widget_id: UUID,
    token_id: UUID = Query(..., description="Token ID to use for the embed"),
    tenant_id: int = Depends(get_tenant_id),
    service: EmbedWidgetService = Depends(get_widget_service),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate embed code snippets for a widget.

    Returns both iframe and script embed options.
    """
    widget = service.get_widget(tenant_id, widget_id)
    if not widget:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Widget not found")

    # Get token
    result = await db.execute(
        select(EmbedToken).where(
            EmbedToken.id == token_id,
            EmbedToken.widget_id == widget_id,
        )
    )
    token = result.scalar_one_or_none()

    if not token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found")

    # Note: We use the token prefix for the embed code, not the full token
    # The full token was given at creation and should be stored by the user
    base_url = getattr(settings, "BASE_URL", "https://app.stratum.ai")

    codes = service.generate_embed_code(
        widget=widget,
        token=token.token_prefix if hasattr(token, 'token_prefix') else str(token.id),
        base_url=base_url,
    )

    return EmbedCodeResponse(
        widget_id=widget_id,
        iframe_code=codes["iframe_code"],
        script_code=codes["script_code"],
        preview_url=codes["preview_url"],
        documentation_url=codes["documentation_url"],
    )


# =============================================================================
# Tier Information
# =============================================================================


@router.get("/tier-info")
async def get_embed_tier_info():
    """
    Get embed widget limits and features for current tier.
    """
    tier = get_current_tier()

    return {
        "tier": tier.value,
        "branding_level": _get_branding_level(tier),
        "limits": {
            "max_widgets": get_tier_limit(tier, "max_embed_widgets"),
            "max_domains": get_tier_limit(tier, "max_embed_domains"),
        },
        "features": {
            "basic_widgets": has_feature(tier, Feature.EMBED_WIDGETS_BASIC),
            "minimal_branding": has_feature(tier, Feature.EMBED_WIDGETS_MINIMAL),
            "white_label": has_feature(tier, Feature.EMBED_WIDGETS_WHITELABEL),
        },
    }


def _get_branding_level(tier: SubscriptionTier) -> str:
    if has_feature(tier, Feature.EMBED_WIDGETS_WHITELABEL):
        return BrandingLevel.NONE.value
    elif has_feature(tier, Feature.EMBED_WIDGETS_MINIMAL):
        return BrandingLevel.MINIMAL.value
    else:
        return BrandingLevel.FULL.value


# =============================================================================
# Public Embed Endpoint (No Auth Required)
# =============================================================================

# This would be in a separate router for public access
public_router = APIRouter(prefix="/embed/v1", tags=["embed-public"])


@public_router.get("/widget/{widget_id}")
async def get_widget_data(
    widget_id: UUID,
    token: str = Query(..., description="Embed token"),
    request: Request = None,
    db: AsyncSession = Depends(get_db),
):
    """
    Public endpoint to fetch widget data for embedding.

    This endpoint:
    1. Validates the token
    2. Checks origin against allowed domains
    3. Returns widget data with appropriate security headers
    """
    token_service = EmbedTokenService(db)
    security_service = get_security_service()

    # Validate request
    request_info = security_service.validate_embed_request(request)

    if not request_info["token"]:
        request_info["token"] = token

    # Validate token and get widget
    try:
        db_token, widget = token_service.validate_token(
            token=request_info["token"],
            origin=request_info["origin"],
        )
    except HTTPException:
        raise

    # Get widget data based on type
    widget_data = await _get_widget_data(widget, db)

    # Create secure response with headers
    return security_service.create_embed_response(
        data={
            "widget_type": widget.widget_type,
            "branding_level": widget.branding_level,
            "config": {
                "size": widget.widget_size,
                "custom_width": widget.custom_width,
                "custom_height": widget.custom_height,
                "custom_logo_url": widget.custom_logo_url,
                "custom_accent_color": widget.custom_accent_color,
                "custom_background_color": widget.custom_background_color,
                "custom_text_color": widget.custom_text_color,
                "refresh_interval": widget.refresh_interval_seconds,
            },
            "data": widget_data,
        },
        token_id=str(db_token.id),
        allowed_domains=db_token.allowed_domains,
        widget_type=widget.widget_type,
        origin=request_info["origin"],
    )


async def _get_widget_data(widget: EmbedWidget, db: AsyncSession) -> dict:
    """
    Fetch actual widget data based on widget type.

    Queries real campaign and platform data from the database.
    Returns empty/minimal responses when no data is available.
    """
    widget_type = widget.widget_type
    tenant_id = widget.tenant_id

    # Fetch active campaigns for the tenant
    result = await db.execute(
        select(Campaign).where(
            Campaign.tenant_id == tenant_id,
            Campaign.status == "active",
        )
    )
    campaigns = result.scalars().all()

    if widget_type == WidgetType.SIGNAL_HEALTH.value:
        if not campaigns:
            return {
                "overall_score": 0,
                "status": "unknown",
                "platforms": {},
                "last_updated": datetime.now(UTC).isoformat(),
            }
        # Compute per-platform scores from campaign CTR/ROAS
        platform_scores: dict[str, list[float]] = {}
        for c in campaigns:
            plat = c.platform.value if hasattr(c.platform, "value") else str(c.platform)
            score = 0.0
            if c.roas is not None and c.roas > 0:
                score += min(50, c.roas * 10)
            if c.ctr is not None and c.ctr > 0:
                score += min(50, c.ctr * 5)
            platform_scores.setdefault(plat, []).append(score)
        avg_platforms = {
            plat: round(sum(scores) / len(scores), 1)
            for plat, scores in platform_scores.items()
        }
        overall = round(
            sum(avg_platforms.values()) / len(avg_platforms), 1
        ) if avg_platforms else 0
        status = (
            "healthy" if overall >= 70 else "at_risk" if overall >= 40 else "critical"
        )
        return {
            "overall_score": overall,
            "status": status,
            "platforms": avg_platforms,
            "last_updated": datetime.now(UTC).isoformat(),
        }

    elif widget_type == WidgetType.ROAS_DISPLAY.value:
        total_spend = sum(c.total_spend_cents or 0 for c in campaigns)
        total_revenue = sum(c.revenue_cents or 0 for c in campaigns)
        blended_roas = round(total_revenue / total_spend, 2) if total_spend > 0 else 0
        return {
            "blended_roas": blended_roas,
            "trend": "neutral",
            "trend_percentage": 0,
            "period": "Last 7 days",
            "last_updated": datetime.now(UTC).isoformat(),
        }

    elif widget_type == WidgetType.TRUST_GATE_STATUS.value:
        # Check data freshness from most recent campaign sync
        latest_sync = max(
            (c.last_synced_at for c in campaigns if c.last_synced_at),
            default=None,
        )
        pending_actions = sum(
            1 for c in campaigns
            if c.roas is not None and c.roas < 1.0
        )
        return {
            "status": "pass" if pending_actions == 0 else "review",
            "signal_health": None,
            "automation_mode": "normal",
            "pending_actions": pending_actions,
            "last_updated": latest_sync.isoformat() if latest_sync else datetime.now(UTC).isoformat(),
        }

    elif widget_type == WidgetType.SPEND_TRACKER.value:
        total_spend = sum(c.total_spend_cents or 0 for c in campaigns) / 100
        total_budget = sum(c.daily_budget_cents or 0 for c in campaigns) / 100
        utilization = round(total_spend / total_budget * 100, 1) if total_budget > 0 else 0
        return {
            "total_spend": total_spend,
            "budget": total_budget,
            "utilization_percentage": utilization,
            "currency": campaigns[0].currency if campaigns else "USD",
            "period": "This month",
            "last_updated": datetime.now(UTC).isoformat(),
        }

    elif widget_type == WidgetType.ANOMALY_ALERT.value:
        anomalies = []
        for c in campaigns:
            if c.roas is not None and c.roas < 1.0:
                anomalies.append(f"Low ROAS on {c.name}")
            if c.ctr is not None and c.ctr < 0.5:
                anomalies.append(f"Low CTR on {c.name}")
        return {
            "has_anomalies": len(anomalies) > 0,
            "anomaly_count": len(anomalies),
            "severity": "high" if any(c.roas is not None and c.roas < 0.5 for c in campaigns) else "medium" if anomalies else "none",
            "most_recent": anomalies[0] if anomalies else None,
            "last_updated": datetime.now(UTC).isoformat(),
        }

    elif widget_type == WidgetType.CAMPAIGN_PERFORMANCE.value:
        top_campaigns = sorted(
            campaigns,
            key=lambda c: c.roas or 0,
            reverse=True,
        )[:5]
        return {
            "campaigns": [
                {
                    "name": c.name,
                    "roas": c.roas or 0,
                    "spend": (c.total_spend_cents or 0) / 100,
                    "status": c.status.value if hasattr(c.status, "value") else str(c.status),
                }
                for c in top_campaigns
            ],
            "total_campaigns": len(campaigns),
            "top_performer": top_campaigns[0].name if top_campaigns else None,
            "last_updated": datetime.now(UTC).isoformat(),
        }

    return {}
