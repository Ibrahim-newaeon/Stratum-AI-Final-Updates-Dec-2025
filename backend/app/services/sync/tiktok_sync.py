# =============================================================================
# Stratum AI - TikTok Campaign Sync Service
# =============================================================================
"""
Syncs campaigns and reports from TikTok Marketing API v1.3.

Endpoints used:
- GET  /campaign/get/                  — list campaigns
- POST /report/integrated/get/         — daily performance reports

Handles:
- Page-based pagination
- Per-second throttling (10 req/s)
- Access-Token header auth
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Optional

import aiohttp

from app.base_models import CampaignStatus
from app.core.logging import get_logger
from app.services.sync.meta_sync import TokenExpiredError

logger = get_logger(__name__)

TIKTOK_API_URL = "https://business-api.tiktok.com/open_api/v1.3"

# TikTok campaign status → our CampaignStatus
_STATUS_MAP: dict[str, CampaignStatus] = {
    "CAMPAIGN_STATUS_ENABLE": CampaignStatus.ACTIVE,
    "CAMPAIGN_STATUS_DISABLE": CampaignStatus.PAUSED,
    "CAMPAIGN_STATUS_DELETE": CampaignStatus.ARCHIVED,
    "CAMPAIGN_STATUS_ALL": CampaignStatus.ACTIVE,
    "CAMPAIGN_STATUS_NOT_DELETE": CampaignStatus.ACTIVE,
    "CAMPAIGN_STATUS_BUDGET_EXCEED": CampaignStatus.PAUSED,
}


@dataclass
class TikTokCampaignData:
    """Raw campaign data from TikTok API."""

    external_id: str
    name: str
    status: CampaignStatus
    objective: Optional[str] = None
    daily_budget_cents: Optional[int] = None
    lifetime_budget_cents: Optional[int] = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class TikTokReportRow:
    """One day of reporting data for a campaign."""

    campaign_id: str
    date: date
    spend_cents: int = 0
    impressions: int = 0
    clicks: int = 0
    conversions: int = 0
    revenue_cents: int = 0


class TikTokCampaignSyncService:
    """Fetches campaigns and reports from TikTok Marketing API."""

    # ------------------------------------------------------------------
    # Campaigns
    # ------------------------------------------------------------------

    async def fetch_campaigns(
        self,
        access_token: str,
        advertiser_id: str,
    ) -> list[TikTokCampaignData]:
        """Fetch all campaigns for an advertiser account."""
        campaigns: list[TikTokCampaignData] = []
        page = 1
        page_size = 100

        async with aiohttp.ClientSession() as session:
            headers = {"Access-Token": access_token}

            while True:
                params: dict[str, Any] = {
                    "advertiser_id": advertiser_id,
                    "page": page,
                    "page_size": page_size,
                }
                url = f"{TIKTOK_API_URL}/campaign/get/"

                async with session.get(url, headers=headers, params=params) as resp:
                    if resp.status == 401:
                        raise TokenExpiredError("TikTok access token expired")
                    data = await resp.json()

                if data.get("code") != 0:
                    msg = data.get("message", "Unknown error")
                    logger.error("tiktok_campaigns_fetch_error", message=msg, adv=advertiser_id)
                    break

                items = data.get("data", {}).get("list", [])
                for raw in items:
                    campaigns.append(self._map_campaign(raw))

                total_pages = data.get("data", {}).get("page_info", {}).get("total_page", 1)
                if page >= total_pages:
                    break
                page += 1
                await asyncio.sleep(0.1)  # throttle: ~10 req/s

        logger.info("tiktok_campaigns_fetched", advertiser=advertiser_id, count=len(campaigns))
        return campaigns

    # ------------------------------------------------------------------
    # Reports
    # ------------------------------------------------------------------

    async def fetch_campaign_reports(
        self,
        access_token: str,
        advertiser_id: str,
        campaign_ids: list[str],
        date_start: date,
        date_end: date,
    ) -> list[TikTokReportRow]:
        """Fetch daily reports for a list of campaigns."""
        if not campaign_ids:
            return []

        rows: list[TikTokReportRow] = []
        page = 1
        page_size = 100

        async with aiohttp.ClientSession() as session:
            headers = {"Access-Token": access_token, "Content-Type": "application/json"}

            while True:
                body: dict[str, Any] = {
                    "advertiser_id": advertiser_id,
                    "report_type": "BASIC",
                    "data_level": "AUCTION_CAMPAIGN",
                    "dimensions": ["campaign_id", "stat_time_day"],
                    "metrics": [
                        "spend",
                        "impressions",
                        "clicks",
                        "conversion",
                        "total_purchase_value",
                    ],
                    "start_date": date_start.isoformat(),
                    "end_date": date_end.isoformat(),
                    "filtering": [
                        {
                            "field_name": "campaign_ids",
                            "filter_type": "IN",
                            "filter_value": [str(cid) for cid in campaign_ids],
                        }
                    ],
                    "page": page,
                    "page_size": page_size,
                }
                url = f"{TIKTOK_API_URL}/report/integrated/get/"

                async with session.post(url, headers=headers, json=body) as resp:
                    if resp.status == 401:
                        raise TokenExpiredError("TikTok access token expired")
                    data = await resp.json()

                if data.get("code") != 0:
                    msg = data.get("message", "Unknown error")
                    logger.error("tiktok_reports_fetch_error", message=msg)
                    break

                items = data.get("data", {}).get("list", [])
                for raw in items:
                    rows.append(self._map_report(raw))

                total_pages = data.get("data", {}).get("page_info", {}).get("total_page", 1)
                if page >= total_pages:
                    break
                page += 1
                await asyncio.sleep(0.1)

        return rows

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _map_campaign(raw: dict[str, Any]) -> TikTokCampaignData:
        status_str = raw.get("campaign_status", raw.get("status", ""))
        status = _STATUS_MAP.get(status_str.upper(), CampaignStatus.DRAFT)

        # TikTok budgets are in dollars (float)
        daily_budget = raw.get("budget")
        lifetime_budget = raw.get("lifetime_budget")

        return TikTokCampaignData(
            external_id=str(raw.get("campaign_id", "")),
            name=raw.get("campaign_name", "Unnamed"),
            status=status,
            objective=raw.get("objective_type") or raw.get("objective"),
            daily_budget_cents=int(round(float(daily_budget) * 100)) if daily_budget else None,
            lifetime_budget_cents=int(round(float(lifetime_budget) * 100)) if lifetime_budget else None,
            raw=raw,
        )

    @staticmethod
    def _map_report(raw: dict[str, Any]) -> TikTokReportRow:
        dimensions = raw.get("dimensions", {})
        metrics = raw.get("metrics", {})

        # TikTok spend is dollars string e.g. "12.34"
        spend_dollars = float(metrics.get("spend", "0"))
        revenue_dollars = float(metrics.get("total_purchase_value", "0"))

        # stat_time_day is "YYYY-MM-DD HH:MM:SS" or "YYYY-MM-DD"
        date_str = dimensions.get("stat_time_day", "2024-01-01")
        row_date = date.fromisoformat(date_str[:10])

        return TikTokReportRow(
            campaign_id=str(dimensions.get("campaign_id", "")),
            date=row_date,
            spend_cents=int(round(spend_dollars * 100)),
            impressions=int(float(metrics.get("impressions", "0"))),
            clicks=int(float(metrics.get("clicks", "0"))),
            conversions=int(float(metrics.get("conversion", "0"))),
            revenue_cents=int(round(revenue_dollars * 100)),
        )
