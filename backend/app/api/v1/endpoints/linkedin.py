# =============================================================================
# Stratum AI - LinkedIn Ads Integration Endpoints
# =============================================================================
"""
LinkedIn Marketing API integration endpoints.
Handles OAuth, campaign management, and analytics for LinkedIn Ads.
"""

from datetime import date, datetime, timedelta, timezone
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import get_async_session
from app.services.linkedin_client import (
    LinkedInAdsClient,
    LinkedInAPIError,
    get_linkedin_client,
)

logger = get_logger(__name__)
router = APIRouter()


# =============================================================================
# Pydantic Schemas
# =============================================================================
class LinkedInOAuthRequest(BaseModel):
    redirect_uri: str
    state: str


class LinkedInOAuthCallback(BaseModel):
    code: str
    state: str
    redirect_uri: str


class LinkedInCampaignCreate(BaseModel):
    account_id: str
    campaign_group_id: str
    name: str = Field(..., max_length=255)
    objective_type: str = Field(
        ...,
        description="BRAND_AWARENESS, ENGAGEMENT, VIDEO_VIEWS, LEAD_GENERATION, WEBSITE_VISITS, WEBSITE_CONVERSIONS, JOB_APPLICANTS"
    )
    daily_budget_amount: str = Field(..., description="Budget amount as string (e.g., '100.00')")
    daily_budget_currency: str = Field(default="USD")
    targeting: Dict[str, Any] = Field(default_factory=dict)
    status: str = Field(default="PAUSED")


class LinkedInCampaignUpdate(BaseModel):
    name: Optional[str] = None
    status: Optional[str] = None
    daily_budget_amount: Optional[str] = None
    daily_budget_currency: Optional[str] = None


class LinkedInCampaignGroupCreate(BaseModel):
    account_id: str
    name: str = Field(..., max_length=255)
    status: str = Field(default="ACTIVE")
    total_budget_amount: Optional[str] = None
    total_budget_currency: Optional[str] = Field(default="USD")


class LinkedInAnalyticsRequest(BaseModel):
    campaign_ids: List[str]
    start_date: date
    end_date: date
    time_granularity: str = Field(default="DAILY", description="DAILY, MONTHLY, ALL")


# =============================================================================
# OAuth Endpoints
# =============================================================================
@router.post("/oauth/authorize")
async def get_authorization_url(data: LinkedInOAuthRequest):
    """
    Get LinkedIn OAuth authorization URL.

    Returns URL to redirect user for LinkedIn authorization.
    """
    client = get_linkedin_client()
    url = client.get_authorization_url(data.redirect_uri, data.state)

    return {
        "success": True,
        "data": {"authorization_url": url},
    }


@router.post("/oauth/callback")
async def handle_oauth_callback(
    data: LinkedInOAuthCallback,
    request: Request,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Handle OAuth callback and exchange code for tokens.

    Stores the access token for the user/tenant.
    """
    tenant_id = getattr(request.state, "tenant_id", None)

    try:
        client = get_linkedin_client()
        tokens = await client.exchange_code_for_token(data.code, data.redirect_uri)

        # In production, store tokens securely in database
        logger.info(f"LinkedIn OAuth successful for tenant {tenant_id}")

        return {
            "success": True,
            "data": {
                "access_token": tokens.get("access_token"),
                "expires_in": tokens.get("expires_in"),
                "refresh_token": tokens.get("refresh_token"),
                "refresh_token_expires_in": tokens.get("refresh_token_expires_in"),
            },
            "message": "LinkedIn account connected successfully",
        }

    except Exception as e:
        logger.error(f"LinkedIn OAuth error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth error: {str(e)}",
        )


@router.post("/oauth/refresh")
async def refresh_token(refresh_token: str):
    """Refresh an expired access token."""
    try:
        client = get_linkedin_client()
        tokens = await client.refresh_access_token(refresh_token)

        return {
            "success": True,
            "data": tokens,
        }

    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Token refresh failed: {str(e)}",
        )


# =============================================================================
# Ad Account Endpoints
# =============================================================================
@router.get("/accounts")
async def list_ad_accounts(request: Request):
    """List all LinkedIn ad accounts the user has access to."""
    try:
        client = get_linkedin_client()
        accounts = await client.get_ad_accounts()

        return {
            "success": True,
            "data": accounts,
        }

    except LinkedInAPIError as e:
        logger.error(f"LinkedIn API error: {e.message}")
        raise HTTPException(
            status_code=e.status_code or 500,
            detail=e.message,
        )


@router.get("/accounts/{account_id}")
async def get_ad_account(account_id: str):
    """Get details of a specific ad account."""
    try:
        client = get_linkedin_client()
        account = await client.get_ad_account(account_id)

        return {
            "success": True,
            "data": account,
        }

    except LinkedInAPIError as e:
        logger.error(f"LinkedIn API error: {e.message}")
        raise HTTPException(
            status_code=e.status_code or 500,
            detail=e.message,
        )


# =============================================================================
# Campaign Group Endpoints
# =============================================================================
@router.get("/accounts/{account_id}/campaign-groups")
async def list_campaign_groups(
    account_id: str,
    search: Optional[str] = None,
):
    """List campaign groups for an ad account."""
    try:
        client = get_linkedin_client()
        groups = await client.get_campaign_groups(account_id, search)

        return {
            "success": True,
            "data": groups,
        }

    except LinkedInAPIError as e:
        logger.error(f"LinkedIn API error: {e.message}")
        raise HTTPException(
            status_code=e.status_code or 500,
            detail=e.message,
        )


@router.post("/campaign-groups")
async def create_campaign_group(data: LinkedInCampaignGroupCreate):
    """Create a new campaign group."""
    try:
        client = get_linkedin_client()

        total_budget = None
        if data.total_budget_amount:
            total_budget = {
                "amount": data.total_budget_amount,
                "currencyCode": data.total_budget_currency,
            }

        group = await client.create_campaign_group(
            account_id=data.account_id,
            name=data.name,
            status=data.status,
            total_budget=total_budget,
        )

        return {
            "success": True,
            "data": group,
            "message": "Campaign group created successfully",
        }

    except LinkedInAPIError as e:
        logger.error(f"LinkedIn API error: {e.message}")
        raise HTTPException(
            status_code=e.status_code or 500,
            detail=e.message,
        )


# =============================================================================
# Campaign Endpoints
# =============================================================================
@router.get("/accounts/{account_id}/campaigns")
async def list_campaigns(
    account_id: str,
    campaign_group_id: Optional[str] = None,
    status: Optional[str] = Query(None, description="Comma-separated statuses"),
):
    """List campaigns for an ad account."""
    try:
        client = get_linkedin_client()

        status_list = status.split(",") if status else None
        campaigns = await client.get_campaigns(
            account_id=account_id,
            campaign_group_id=campaign_group_id,
            status=status_list,
        )

        return {
            "success": True,
            "data": campaigns,
        }

    except LinkedInAPIError as e:
        logger.error(f"LinkedIn API error: {e.message}")
        raise HTTPException(
            status_code=e.status_code or 500,
            detail=e.message,
        )


@router.get("/campaigns/{campaign_id}")
async def get_campaign(campaign_id: str):
    """Get details of a specific campaign."""
    try:
        client = get_linkedin_client()
        campaign = await client.get_campaign(campaign_id)

        return {
            "success": True,
            "data": campaign,
        }

    except LinkedInAPIError as e:
        logger.error(f"LinkedIn API error: {e.message}")
        raise HTTPException(
            status_code=e.status_code or 500,
            detail=e.message,
        )


@router.post("/campaigns")
async def create_campaign(data: LinkedInCampaignCreate):
    """Create a new campaign."""
    try:
        client = get_linkedin_client()

        daily_budget = {
            "amount": data.daily_budget_amount,
            "currencyCode": data.daily_budget_currency,
        }

        campaign = await client.create_campaign(
            account_id=data.account_id,
            campaign_group_id=data.campaign_group_id,
            name=data.name,
            objective_type=data.objective_type,
            daily_budget=daily_budget,
            targeting=data.targeting,
            status=data.status,
        )

        return {
            "success": True,
            "data": campaign,
            "message": "Campaign created successfully",
        }

    except LinkedInAPIError as e:
        logger.error(f"LinkedIn API error: {e.message}")
        raise HTTPException(
            status_code=e.status_code or 500,
            detail=e.message,
        )


@router.patch("/campaigns/{campaign_id}")
async def update_campaign(campaign_id: str, data: LinkedInCampaignUpdate):
    """Update a campaign."""
    try:
        client = get_linkedin_client()

        updates = data.model_dump(exclude_unset=True)

        # Handle budget updates
        if data.daily_budget_amount:
            updates["dailyBudget"] = {
                "amount": data.daily_budget_amount,
                "currencyCode": data.daily_budget_currency or "USD",
            }
            del updates["daily_budget_amount"]
            if "daily_budget_currency" in updates:
                del updates["daily_budget_currency"]

        campaign = await client.update_campaign(campaign_id, updates)

        return {
            "success": True,
            "data": campaign,
            "message": "Campaign updated successfully",
        }

    except LinkedInAPIError as e:
        logger.error(f"LinkedIn API error: {e.message}")
        raise HTTPException(
            status_code=e.status_code or 500,
            detail=e.message,
        )


@router.post("/campaigns/{campaign_id}/pause")
async def pause_campaign(campaign_id: str):
    """Pause a campaign."""
    try:
        client = get_linkedin_client()
        campaign = await client.update_campaign_status(campaign_id, "PAUSED")

        return {
            "success": True,
            "data": campaign,
            "message": "Campaign paused",
        }

    except LinkedInAPIError as e:
        logger.error(f"LinkedIn API error: {e.message}")
        raise HTTPException(
            status_code=e.status_code or 500,
            detail=e.message,
        )


@router.post("/campaigns/{campaign_id}/activate")
async def activate_campaign(campaign_id: str):
    """Activate a campaign."""
    try:
        client = get_linkedin_client()
        campaign = await client.update_campaign_status(campaign_id, "ACTIVE")

        return {
            "success": True,
            "data": campaign,
            "message": "Campaign activated",
        }

    except LinkedInAPIError as e:
        logger.error(f"LinkedIn API error: {e.message}")
        raise HTTPException(
            status_code=e.status_code or 500,
            detail=e.message,
        )


# =============================================================================
# Analytics Endpoints
# =============================================================================
@router.post("/analytics/campaigns")
async def get_campaign_analytics(data: LinkedInAnalyticsRequest):
    """Get analytics for campaigns."""
    try:
        client = get_linkedin_client()

        analytics = await client.get_campaign_analytics(
            campaign_ids=data.campaign_ids,
            start_date=data.start_date,
            end_date=data.end_date,
            time_granularity=data.time_granularity,
        )

        return {
            "success": True,
            "data": analytics,
        }

    except LinkedInAPIError as e:
        logger.error(f"LinkedIn API error: {e.message}")
        raise HTTPException(
            status_code=e.status_code or 500,
            detail=e.message,
        )


@router.get("/accounts/{account_id}/analytics")
async def get_account_analytics(
    account_id: str,
    start_date: date = Query(...),
    end_date: date = Query(...),
    time_granularity: str = Query(default="DAILY"),
):
    """Get account-level analytics."""
    try:
        client = get_linkedin_client()

        analytics = await client.get_account_analytics(
            account_id=account_id,
            start_date=start_date,
            end_date=end_date,
            time_granularity=time_granularity,
        )

        return {
            "success": True,
            "data": analytics,
        }

    except LinkedInAPIError as e:
        logger.error(f"LinkedIn API error: {e.message}")
        raise HTTPException(
            status_code=e.status_code or 500,
            detail=e.message,
        )


# =============================================================================
# Targeting Endpoints
# =============================================================================
@router.get("/targeting/facets")
async def get_targeting_facets():
    """Get available targeting facets."""
    try:
        client = get_linkedin_client()
        facets = await client.get_targeting_facets()

        return {
            "success": True,
            "data": facets,
        }

    except LinkedInAPIError as e:
        logger.error(f"LinkedIn API error: {e.message}")
        raise HTTPException(
            status_code=e.status_code or 500,
            detail=e.message,
        )


@router.get("/targeting/companies")
async def search_companies(
    query: str = Query(..., min_length=2),
    limit: int = Query(default=20, le=100),
):
    """Search for companies for targeting."""
    try:
        client = get_linkedin_client()
        companies = await client.search_companies(query, limit)

        return {
            "success": True,
            "data": companies,
        }

    except LinkedInAPIError as e:
        logger.error(f"LinkedIn API error: {e.message}")
        raise HTTPException(
            status_code=e.status_code or 500,
            detail=e.message,
        )


@router.post("/targeting/audience-count")
async def get_audience_count(targeting_criteria: Dict[str, Any]):
    """Get estimated audience size for targeting criteria."""
    try:
        client = get_linkedin_client()
        audience = await client.get_audience_counts(targeting_criteria)

        return {
            "success": True,
            "data": audience,
        }

    except LinkedInAPIError as e:
        logger.error(f"LinkedIn API error: {e.message}")
        raise HTTPException(
            status_code=e.status_code or 500,
            detail=e.message,
        )


# =============================================================================
# Conversion Tracking Endpoints
# =============================================================================
@router.get("/accounts/{account_id}/conversions")
async def list_conversions(account_id: str):
    """List conversion actions for an account."""
    try:
        client = get_linkedin_client()
        conversions = await client.get_conversions(account_id)

        return {
            "success": True,
            "data": conversions,
        }

    except LinkedInAPIError as e:
        logger.error(f"LinkedIn API error: {e.message}")
        raise HTTPException(
            status_code=e.status_code or 500,
            detail=e.message,
        )


@router.post("/accounts/{account_id}/conversions")
async def create_conversion(
    account_id: str,
    name: str,
    conversion_type: str,
    attribution_type: str = "LAST_TOUCH_BY_CAMPAIGN",
    post_click_window: int = 30,
    post_view_window: int = 7,
):
    """Create a conversion action."""
    try:
        client = get_linkedin_client()

        conversion = await client.create_conversion(
            account_id=account_id,
            name=name,
            conversion_type=conversion_type,
            attribution_type=attribution_type,
            post_click_window=post_click_window,
            post_view_window=post_view_window,
        )

        return {
            "success": True,
            "data": conversion,
            "message": "Conversion action created",
        }

    except LinkedInAPIError as e:
        logger.error(f"LinkedIn API error: {e.message}")
        raise HTTPException(
            status_code=e.status_code or 500,
            detail=e.message,
        )
