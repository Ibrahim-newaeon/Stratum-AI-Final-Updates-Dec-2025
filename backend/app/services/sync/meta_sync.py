# =============================================================================
# Stratum AI - Meta Campaign Sync Service
# =============================================================================
"""
Syncs campaigns and daily insights from Meta Marketing API v19.0.

Endpoints used:
- GET /{ad_account_id}/campaigns — list campaigns
- GET /{campaign_id}/insights — daily performance metrics

Handles:
- Cursor-based pagination
- Rate-limit back-off (Retry-After / X-Business-Use-Case-Usage)
- 401 token expiry detection
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Optional

import aiohttp

from app.base_models import CampaignStatus
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

META_GRAPH_URL = "https://graph.facebook.com/{version}"

# Meta effective_status → our CampaignStatus
_STATUS_MAP: dict[str, CampaignStatus] = {
    "ACTIVE": CampaignStatus.ACTIVE,
    "PAUSED": CampaignStatus.PAUSED,
    "DELETED": CampaignStatus.ARCHIVED,
    "ARCHIVED": CampaignStatus.ARCHIVED,
    "IN_PROCESS": CampaignStatus.DRAFT,
    "WITH_ISSUES": CampaignStatus.ACTIVE,
    "CAMPAIGN_PAUSED": CampaignStatus.PAUSED,
    "ADSET_PAUSED": CampaignStatus.PAUSED,
    "DISAPPROVED": CampaignStatus.PAUSED,
    "PENDING_REVIEW": CampaignStatus.DRAFT,
    "PREAPPROVED": CampaignStatus.DRAFT,
}


@dataclass
class MetaCampaignData:
    """Raw campaign data from Meta API."""

    external_id: str
    name: str
    status: CampaignStatus
    objective: Optional[str] = None
    daily_budget_cents: Optional[int] = None
    lifetime_budget_cents: Optional[int] = None
    start_time: Optional[datetime] = None
    stop_time: Optional[datetime] = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class MetaInsightRow:
    """One day of insights for a campaign."""

    date: date
    spend_cents: int = 0
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    revenue_cents: int = 0
    video_views: int = 0


class MetaCampaignSyncService:
    """Fetches campaigns and insights from Meta Marketing API."""

    def __init__(self) -> None:
        self.api_version = settings.meta_api_version

    def _graph_url(self, path: str) -> str:
        base = META_GRAPH_URL.format(version=self.api_version)
        return f"{base}/{path}"

    # ------------------------------------------------------------------
    # Campaigns
    # ------------------------------------------------------------------

    async def fetch_campaigns(
        self,
        access_token: str,
        ad_account_id: str,
    ) -> list[MetaCampaignData]:
        """Fetch all campaigns for an ad account."""
        campaigns: list[MetaCampaignData] = []
        url: Optional[str] = self._graph_url(f"{ad_account_id}/campaigns")
        params: dict[str, Any] = {
            "access_token": access_token,
            "fields": "id,name,status,effective_status,objective,daily_budget,lifetime_budget,start_time,stop_time",
            "limit": 200,
        }

        async with aiohttp.ClientSession() as session:
            while url:
                async with session.get(url, params=params) as resp:
                    await self._handle_rate_limit(resp)
                    if resp.status == 401:
                        raise TokenExpiredError("Meta access token expired")
                    if resp.status != 200:
                        body = await resp.text()
                        logger.error("meta_campaigns_fetch_error", status=resp.status, body=body[:500])
                        break
                    data = await resp.json()

                for raw in data.get("data", []):
                    campaigns.append(self._map_campaign(raw))

                paging = data.get("paging", {})
                url = paging.get("next")
                params = {}  # next URL includes all params

        logger.info("meta_campaigns_fetched", account=ad_account_id, count=len(campaigns))
        return campaigns

    # ------------------------------------------------------------------
    # Insights
    # ------------------------------------------------------------------

    async def fetch_campaign_insights(
        self,
        access_token: str,
        campaign_id: str,
        date_start: date,
        date_end: date,
    ) -> list[MetaInsightRow]:
        """Fetch daily insights for a single campaign."""
        rows: list[MetaInsightRow] = []
        url: Optional[str] = self._graph_url(f"{campaign_id}/insights")
        params: dict[str, Any] = {
            "access_token": access_token,
            "fields": "spend,impressions,clicks,actions,action_values,video_views",
            "time_range": f'{{"since":"{date_start.isoformat()}","until":"{date_end.isoformat()}"}}',
            "time_increment": 1,
            "limit": 500,
        }

        async with aiohttp.ClientSession() as session:
            while url:
                async with session.get(url, params=params) as resp:
                    await self._handle_rate_limit(resp)
                    if resp.status == 401:
                        raise TokenExpiredError("Meta access token expired")
                    if resp.status != 200:
                        body = await resp.text()
                        logger.warning(
                            "meta_insights_fetch_error",
                            campaign=campaign_id,
                            status=resp.status,
                            body=body[:500],
                        )
                        break
                    data = await resp.json()

                for raw in data.get("data", []):
                    rows.append(self._map_insight(raw))

                paging = data.get("paging", {})
                url = paging.get("next")
                params = {}

        return rows

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    def _map_campaign(self, raw: dict[str, Any]) -> MetaCampaignData:
        effective = raw.get("effective_status", raw.get("status", "ACTIVE"))
        status = _STATUS_MAP.get(effective.upper(), CampaignStatus.DRAFT)

        daily = raw.get("daily_budget")
        lifetime = raw.get("lifetime_budget")

        return MetaCampaignData(
            external_id=str(raw["id"]),
            name=raw.get("name", "Unnamed"),
            status=status,
            objective=raw.get("objective"),
            daily_budget_cents=int(float(daily)) if daily else None,
            lifetime_budget_cents=int(float(lifetime)) if lifetime else None,
            start_time=_parse_iso(raw.get("start_time")),
            stop_time=_parse_iso(raw.get("stop_time")),
            raw=raw,
        )

    @staticmethod
    def _map_insight(raw: dict[str, Any]) -> MetaInsightRow:
        # Spend comes as dollar string e.g. "12.34"
        spend_dollars = float(raw.get("spend", "0"))
        spend_cents = int(round(spend_dollars * 100))

        conversions = 0
        revenue_cents = 0

        # Parse actions for purchase conversions
        for action in raw.get("actions", []):
            if action.get("action_type") in (
                "offsite_conversion.fb_pixel_purchase",
                "purchase",
                "omni_purchase",
            ):
                conversions += int(float(action.get("value", "0")))

        # Parse action_values for revenue
        for av in raw.get("action_values", []):
            if av.get("action_type") in (
                "offsite_conversion.fb_pixel_purchase",
                "purchase",
                "omni_purchase",
            ):
                revenue_cents += int(round(float(av.get("value", "0")) * 100))

        row_date = date.fromisoformat(raw.get("date_start", raw.get("date_stop", "2024-01-01")))

        return MetaInsightRow(
            date=row_date,
            spend_cents=spend_cents,
            impressions=int(raw.get("impressions", "0")),
            clicks=int(raw.get("clicks", "0")),
            conversions=conversions,
            revenue_cents=revenue_cents,
            video_views=int(raw.get("video_views", "0") or "0"),
        )

    # ------------------------------------------------------------------
    # Rate-limit helper
    # ------------------------------------------------------------------

    @staticmethod
    async def _handle_rate_limit(resp: aiohttp.ClientResponse) -> None:
        """Sleep if Meta returns rate-limit headers."""
        if resp.status == 429:
            retry_after = int(resp.headers.get("Retry-After", "60"))
            logger.warning("meta_rate_limited", retry_after=retry_after)
            await asyncio.sleep(min(retry_after, 300))


class TokenExpiredError(Exception):
    """Raised when the platform returns 401 / token expired."""


# ------------------------------------------------------------------
# Utility
# ------------------------------------------------------------------

def _parse_iso(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
