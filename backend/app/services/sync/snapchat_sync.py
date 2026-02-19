# =============================================================================
# Stratum AI - Snapchat Campaign Sync Service
# =============================================================================
"""
Syncs campaigns and stats from Snapchat Marketing API v1.

Endpoints used:
- GET  /adaccounts/{id}/campaigns              — list campaigns
- GET  /campaigns/{id}/stats                   — campaign-level stats

Handles:
- Cursor-based pagination
- Bearer-token auth
- Micro-currency conversion (Snapchat uses microcurrency: 1 USD = 1_000_000)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any, Optional

import aiohttp

from app.base_models import CampaignStatus
from app.core.logging import get_logger
from app.services.sync.meta_sync import TokenExpiredError

logger = get_logger(__name__)

SNAPCHAT_API_URL = "https://adsapi.snapchat.com/v1"

# Snapchat campaign status → our CampaignStatus
_STATUS_MAP: dict[str, CampaignStatus] = {
    "ACTIVE": CampaignStatus.ACTIVE,
    "PAUSED": CampaignStatus.PAUSED,
    "EXHAUSTED": CampaignStatus.COMPLETED,
    "PENDING": CampaignStatus.DRAFT,
    "DELETED": CampaignStatus.ARCHIVED,
}


@dataclass
class SnapchatCampaignData:
    """Raw campaign data from Snapchat API."""

    external_id: str
    name: str
    status: CampaignStatus
    objective: Optional[str] = None
    daily_budget_cents: Optional[int] = None
    lifetime_budget_cents: Optional[int] = None
    start_time: Optional[date] = None
    stop_time: Optional[date] = None
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass
class SnapchatReportRow:
    """One day of reporting data for a campaign."""

    campaign_id: str
    date: date
    spend_cents: int = 0
    impressions: int = 0
    clicks: int = 0  # swipes
    conversions: int = 0
    revenue_cents: int = 0


class SnapchatCampaignSyncService:
    """Fetches campaigns and stats from Snapchat Marketing API."""

    # ------------------------------------------------------------------
    # Campaigns
    # ------------------------------------------------------------------

    async def fetch_campaigns(
        self,
        access_token: str,
        ad_account_id: str,
    ) -> list[SnapchatCampaignData]:
        """Fetch all campaigns for a Snapchat ad account."""
        campaigns: list[SnapchatCampaignData] = []
        cursor: Optional[str] = None

        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {access_token}"}

            while True:
                url = f"{SNAPCHAT_API_URL}/adaccounts/{ad_account_id}/campaigns"
                params: dict[str, Any] = {"limit": 100}
                if cursor:
                    params["cursor"] = cursor

                async with session.get(url, headers=headers, params=params) as resp:
                    if resp.status == 401:
                        raise TokenExpiredError("Snapchat access token expired")
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(
                            "snapchat_campaigns_fetch_error",
                            status=resp.status,
                            error=error_text[:500],
                            account=ad_account_id,
                        )
                        break
                    data = await resp.json()

                items = data.get("campaigns", [])
                for item in items:
                    raw = item.get("campaign", {})
                    campaigns.append(self._map_campaign(raw))

                # Pagination
                paging = data.get("paging", {})
                next_link = paging.get("next_link")
                if not next_link:
                    break
                # Extract cursor from next_link URL param
                import urllib.parse

                parsed = urllib.parse.urlparse(next_link)
                qs = urllib.parse.parse_qs(parsed.query)
                cursor = qs.get("cursor", [None])[0]
                if not cursor:
                    break
                await asyncio.sleep(0.1)  # throttle

        logger.info("snapchat_campaigns_fetched", account=ad_account_id, count=len(campaigns))
        return campaigns

    # ------------------------------------------------------------------
    # Stats / Reports
    # ------------------------------------------------------------------

    async def fetch_campaign_stats(
        self,
        access_token: str,
        campaign_ids: list[str],
        date_start: date,
        date_end: date,
    ) -> list[SnapchatReportRow]:
        """Fetch daily stats for a list of campaigns."""
        if not campaign_ids:
            return []

        rows: list[SnapchatReportRow] = []

        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {access_token}"}

            for campaign_id in campaign_ids:
                try:
                    url = f"{SNAPCHAT_API_URL}/campaigns/{campaign_id}/stats"
                    params: dict[str, Any] = {
                        "granularity": "DAY",
                        "start_time": f"{date_start.isoformat()}T00:00:00.000-00:00",
                        "end_time": f"{date_end.isoformat()}T00:00:00.000-00:00",
                        "fields": "impressions,swipes,spend,conversion_purchases,conversion_purchases_value",
                    }

                    async with session.get(url, headers=headers, params=params) as resp:
                        if resp.status == 401:
                            raise TokenExpiredError("Snapchat access token expired")
                        if resp.status != 200:
                            logger.warning(
                                "snapchat_stats_fetch_error",
                                campaign=campaign_id,
                                status=resp.status,
                            )
                            continue
                        data = await resp.json()

                    timeseries = (
                        data.get("timeseries_stats", [{}])[0]
                        .get("timeseries_stat", {})
                        .get("timeseries", [])
                    )

                    current_date = date_start
                    for point in timeseries:
                        stats = point.get("stats", {})
                        rows.append(
                            SnapchatReportRow(
                                campaign_id=campaign_id,
                                date=current_date,
                                spend_cents=self._micro_to_cents(stats.get("spend", 0)),
                                impressions=int(stats.get("impressions", 0)),
                                clicks=int(stats.get("swipes", 0)),
                                conversions=int(stats.get("conversion_purchases", 0)),
                                revenue_cents=self._micro_to_cents(
                                    stats.get("conversion_purchases_value", 0)
                                ),
                            )
                        )
                        current_date += timedelta(days=1)

                except TokenExpiredError:
                    raise
                except Exception as e:
                    logger.warning("snapchat_stats_error", campaign=campaign_id, error=str(e))

                await asyncio.sleep(0.1)

        return rows

    # ------------------------------------------------------------------
    # Mapping helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _map_campaign(raw: dict[str, Any]) -> SnapchatCampaignData:
        status_str = raw.get("status", "ACTIVE").upper()
        status = _STATUS_MAP.get(status_str, CampaignStatus.DRAFT)

        # Snapchat budgets in micro-currency (1 USD = 1,000,000)
        daily_budget_micro = raw.get("daily_budget_micro")
        lifetime_budget_micro = raw.get("lifetime_spend_cap_micro")

        # Parse dates
        start_time = None
        stop_time = None
        if raw.get("start_time"):
            try:
                start_time = date.fromisoformat(raw["start_time"][:10])
            except (ValueError, TypeError):
                pass
        if raw.get("end_time"):
            try:
                stop_time = date.fromisoformat(raw["end_time"][:10])
            except (ValueError, TypeError):
                pass

        return SnapchatCampaignData(
            external_id=str(raw.get("id", "")),
            name=raw.get("name", "Unnamed"),
            status=status,
            objective=raw.get("objective"),
            daily_budget_cents=(
                int(round(daily_budget_micro / 10000)) if daily_budget_micro else None
            ),
            lifetime_budget_cents=(
                int(round(lifetime_budget_micro / 10000)) if lifetime_budget_micro else None
            ),
            start_time=start_time,
            stop_time=stop_time,
            raw=raw,
        )

    @staticmethod
    def _micro_to_cents(micro_val: Any) -> int:
        """Convert Snapchat micro-currency to cents. 1 USD = 1_000_000 micro."""
        try:
            return int(round(float(micro_val) / 10000))
        except (ValueError, TypeError):
            return 0
