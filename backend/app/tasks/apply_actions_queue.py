# =============================================================================
# Stratum AI - Apply Actions Queue Task
# =============================================================================
"""
Celery task for processing and applying approved autopilot actions.
Handles safe execution of budget changes, pauses, and other campaign modifications.

When ``settings.use_mock_ad_data`` is True (default), executors return
simulated responses.  When False, executors make real API calls to
Meta Marketing API, Google Ads REST API, and TikTok Business API using
tokens stored in the application settings.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import logging
import json

from celery import shared_task
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.trust_layer import FactActionsQueue, FactSignalHealthDaily, SignalHealthStatus
from app.autopilot.service import ActionStatus, ActionType, SAFE_ACTIONS
from app.features.flags import get_autopilot_caps, AutopilotLevel
from app.core.websocket import publish_action_status_update
from app.core.config import settings


logger = logging.getLogger(__name__)


# =============================================================================
# Platform Executors
# =============================================================================

class PlatformExecutor:
    """Base class for platform-specific action execution."""

    async def execute_action(
        self,
        action_type: str,
        entity_type: str,
        entity_id: str,
        action_details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute an action on the platform.

        Delegates to ``_live_execute`` when ``settings.use_mock_ad_data``
        is False, otherwise falls back to ``_mock_execute``.

        Returns:
            Dict with keys: success, before_value, after_value, platform_response, error
        """
        if settings.use_mock_ad_data:
            return self._mock_execute(action_type, entity_type, entity_id, action_details)

        return await self._live_execute(action_type, entity_type, entity_id, action_details)

    def _mock_execute(
        self,
        action_type: str,
        entity_type: str,
        entity_id: str,
        action_details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Mock execution - must be overridden by subclasses."""
        raise NotImplementedError

    async def _live_execute(
        self,
        action_type: str,
        entity_type: str,
        entity_id: str,
        action_details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Live execution against the real platform API - must be overridden by subclasses."""
        raise NotImplementedError


class MetaExecutor(PlatformExecutor):
    """Executor for Meta (Facebook/Instagram) platform actions."""

    def _mock_execute(
        self,
        action_type: str,
        entity_type: str,
        entity_id: str,
        action_details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Simulate successful execution for Meta platform."""
        logger.info(f"[META] Mock executing {action_type} on {entity_type} {entity_id}")

        before_value: Dict[str, Any] = {"status": "ACTIVE", "daily_budget": 10000}
        after_value = before_value.copy()

        if action_type == ActionType.BUDGET_INCREASE.value:
            amount = action_details.get("amount", 0)
            after_value["daily_budget"] = before_value["daily_budget"] + amount

        elif action_type == ActionType.BUDGET_DECREASE.value:
            amount = action_details.get("amount", 0)
            after_value["daily_budget"] = max(0, before_value["daily_budget"] - amount)

        elif action_type in [ActionType.PAUSE_CAMPAIGN.value, ActionType.PAUSE_ADSET.value, ActionType.PAUSE_CREATIVE.value]:
            after_value["status"] = "PAUSED"

        elif action_type in [ActionType.ENABLE_CAMPAIGN.value, ActionType.ENABLE_ADSET.value, ActionType.ENABLE_CREATIVE.value]:
            after_value["status"] = "ACTIVE"

        return {
            "success": True,
            "before_value": before_value,
            "after_value": after_value,
            "platform_response": {"request_id": "meta_mock_123", "status": "success"},
            "error": None,
        }

    async def _live_execute(
        self,
        action_type: str,
        entity_type: str,
        entity_id: str,
        action_details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute action on Meta Marketing API.

        Uses ``httpx`` to call the Graph API.  Budget values are sent in
        cents (the Meta API unit) and status changes use PAUSED/ACTIVE.

        Args:
            action_type: One of the ActionType enum values.
            entity_type: campaign, adset, or creative.
            entity_id: The Meta object ID.
            action_details: Dict with amount/percentage keys for budget ops.

        Returns:
            Standardised result dict.
        """
        import httpx
        from app.core.config import settings

        logger.info(f"[META] Live executing {action_type} on {entity_type} {entity_id}")

        base_url = f"https://graph.facebook.com/{settings.meta_api_version}"
        access_token = settings.meta_access_token

        if not access_token:
            return {
                "success": False,
                "before_value": None,
                "after_value": None,
                "platform_response": None,
                "error": "Meta access token is not configured",
            }

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Step 1: GET current state to capture before_value
                get_resp = await client.get(
                    f"{base_url}/{entity_id}",
                    params={
                        "fields": "status,daily_budget",
                        "access_token": access_token,
                    },
                )
                if get_resp.status_code != 200:
                    error_body = get_resp.text
                    logger.error(f"[META] GET entity failed: {error_body}")
                    return {
                        "success": False,
                        "before_value": None,
                        "after_value": None,
                        "platform_response": {"status_code": get_resp.status_code, "body": error_body},
                        "error": f"Failed to fetch entity state: HTTP {get_resp.status_code}",
                    }

                before_value = get_resp.json()

                # Step 2: Determine the update payload
                update_payload: Dict[str, Any] = {}

                if action_type in [ActionType.BUDGET_INCREASE.value, ActionType.BUDGET_DECREASE.value]:
                    amount = action_details.get("amount", 0)
                    current_budget = int(before_value.get("daily_budget", 0))

                    if action_type == ActionType.BUDGET_INCREASE.value:
                        new_budget = current_budget + int(amount * 100)  # amount in dollars -> cents
                    else:
                        new_budget = max(0, current_budget - int(amount * 100))

                    update_payload["daily_budget"] = new_budget

                elif action_type in [
                    ActionType.PAUSE_CAMPAIGN.value,
                    ActionType.PAUSE_ADSET.value,
                    ActionType.PAUSE_CREATIVE.value,
                ]:
                    update_payload["status"] = "PAUSED"

                elif action_type in [
                    ActionType.ENABLE_CAMPAIGN.value,
                    ActionType.ENABLE_ADSET.value,
                    ActionType.ENABLE_CREATIVE.value,
                ]:
                    update_payload["status"] = "ACTIVE"

                if not update_payload:
                    return {
                        "success": False,
                        "before_value": before_value,
                        "after_value": None,
                        "platform_response": None,
                        "error": f"Unsupported action type for Meta: {action_type}",
                    }

                # Step 3: POST update
                update_payload["access_token"] = access_token
                post_resp = await client.post(
                    f"{base_url}/{entity_id}",
                    data=update_payload,
                )

                if post_resp.status_code != 200:
                    error_body = post_resp.text
                    logger.error(f"[META] POST update failed: {error_body}")
                    return {
                        "success": False,
                        "before_value": before_value,
                        "after_value": None,
                        "platform_response": {"status_code": post_resp.status_code, "body": error_body},
                        "error": f"Failed to update entity: HTTP {post_resp.status_code}",
                    }

                platform_response = post_resp.json()

                # Step 4: GET updated state for after_value
                after_resp = await client.get(
                    f"{base_url}/{entity_id}",
                    params={
                        "fields": "status,daily_budget",
                        "access_token": access_token,
                    },
                )
                after_value = after_resp.json() if after_resp.status_code == 200 else update_payload

                return {
                    "success": True,
                    "before_value": before_value,
                    "after_value": after_value,
                    "platform_response": platform_response,
                    "error": None,
                }

        except Exception as exc:
            logger.error(f"[META] Live execution error: {exc}", exc_info=True)
            return {
                "success": False,
                "before_value": None,
                "after_value": None,
                "platform_response": None,
                "error": str(exc),
            }


class GoogleExecutor(PlatformExecutor):
    """Executor for Google Ads platform actions."""

    def _mock_execute(
        self,
        action_type: str,
        entity_type: str,
        entity_id: str,
        action_details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Simulate successful execution for Google Ads platform."""
        logger.info(f"[GOOGLE] Mock executing {action_type} on {entity_type} {entity_id}")

        before_value: Dict[str, Any] = {"status": "ENABLED", "budget_micros": 10000000}
        after_value = before_value.copy()

        if action_type == ActionType.BUDGET_INCREASE.value:
            amount = action_details.get("amount", 0)
            after_value["budget_micros"] = before_value["budget_micros"] + (amount * 1000000)

        elif action_type == ActionType.BUDGET_DECREASE.value:
            amount = action_details.get("amount", 0)
            after_value["budget_micros"] = max(0, before_value["budget_micros"] - (amount * 1000000))

        elif action_type in [ActionType.PAUSE_CAMPAIGN.value, ActionType.PAUSE_ADSET.value]:
            after_value["status"] = "PAUSED"

        elif action_type in [ActionType.ENABLE_CAMPAIGN.value, ActionType.ENABLE_ADSET.value]:
            after_value["status"] = "ENABLED"

        return {
            "success": True,
            "before_value": before_value,
            "after_value": after_value,
            "platform_response": {"operation_name": "operations/mock_123", "status": "DONE"},
            "error": None,
        }

    async def _get_access_token(self) -> Optional[str]:
        """Obtain an access token by refreshing via Google OAuth.

        Uses the ``google_ads_refresh_token``, ``google_ads_client_id``,
        and ``google_ads_client_secret`` from settings.

        Returns:
            Access token string or None if refresh fails.
        """
        import httpx
        from app.core.config import settings

        if not settings.google_ads_refresh_token:
            return None

        if not settings.google_ads_client_id or not settings.google_ads_client_secret:
            logger.error("[GOOGLE] Client ID/Secret not configured for token refresh")
            return None

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": settings.google_ads_client_id,
                        "client_secret": settings.google_ads_client_secret,
                        "refresh_token": settings.google_ads_refresh_token,
                        "grant_type": "refresh_token",
                    },
                )
                if resp.status_code == 200:
                    return resp.json().get("access_token")
                else:
                    logger.error(f"[GOOGLE] Token refresh failed: {resp.text}")
                    return None
        except Exception as exc:
            logger.error(f"[GOOGLE] Token refresh error: {exc}", exc_info=True)
            return None

    async def _live_execute(
        self,
        action_type: str,
        entity_type: str,
        entity_id: str,
        action_details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute action on Google Ads REST API.

        Uses v18 of the Google Ads REST API.  Budget mutations target
        campaignBudgets resources (amount_micros) and status mutations
        target campaigns resources.

        ``entity_id`` is expected to encode the required identifiers:
        - For budget changes: ``{customer_id}/campaignBudgets/{budget_id}``
          or action_details should contain ``customer_id`` and ``budget_id``.
        - For status changes: ``{customer_id}/campaigns/{campaign_id}``
          or action_details should contain ``customer_id``.

        Args:
            action_type: One of the ActionType enum values.
            entity_type: campaign, adset, etc.
            entity_id: Platform entity ID or composite key.
            action_details: Dict with amount, customer_id, budget_id keys.

        Returns:
            Standardised result dict.
        """
        import httpx
        from app.core.config import settings

        logger.info(f"[GOOGLE] Live executing {action_type} on {entity_type} {entity_id}")

        base_url = "https://googleads.googleapis.com/v18"
        developer_token = settings.google_ads_developer_token

        if not developer_token:
            return {
                "success": False,
                "before_value": None,
                "after_value": None,
                "platform_response": None,
                "error": "Google Ads developer token is not configured",
            }

        access_token = await self._get_access_token()
        if not access_token:
            return {
                "success": False,
                "before_value": None,
                "after_value": None,
                "platform_response": None,
                "error": "Failed to obtain Google Ads access token",
            }

        customer_id = action_details.get("customer_id") or settings.google_ads_customer_id
        if not customer_id:
            return {
                "success": False,
                "before_value": None,
                "after_value": None,
                "platform_response": None,
                "error": "Google Ads customer ID is not configured",
            }

        # Strip hyphens from customer ID (Google API expects plain digits)
        customer_id = str(customer_id).replace("-", "")

        headers = {
            "Authorization": f"Bearer {access_token}",
            "developer-token": developer_token,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
                # Budget operations
                if action_type in [ActionType.BUDGET_INCREASE.value, ActionType.BUDGET_DECREASE.value]:
                    budget_id = action_details.get("budget_id", entity_id)
                    resource_name = f"customers/{customer_id}/campaignBudgets/{budget_id}"

                    # GET current budget (via searchStream GAQL)
                    search_url = f"{base_url}/customers/{customer_id}/googleAds:searchStream"
                    query = (
                        f"SELECT campaign_budget.amount_micros "
                        f"FROM campaign_budget "
                        f"WHERE campaign_budget.resource_name = '{resource_name}' "
                        f"LIMIT 1"
                    )
                    search_resp = await client.post(search_url, json={"query": query})
                    current_micros = 0
                    before_value: Dict[str, Any] = {"budget_micros": 0}

                    if search_resp.status_code == 200:
                        stream_data = search_resp.json()
                        for batch in stream_data:
                            for row in batch.get("results", []):
                                current_micros = int(
                                    row.get("campaignBudget", {}).get("amountMicros", 0)
                                )
                        before_value = {"budget_micros": current_micros}

                    amount = action_details.get("amount", 0)
                    if action_type == ActionType.BUDGET_INCREASE.value:
                        new_micros = current_micros + int(amount * 1_000_000)
                    else:
                        new_micros = max(0, current_micros - int(amount * 1_000_000))

                    # PATCH budget
                    patch_url = f"{base_url}/{resource_name}"
                    patch_resp = await client.patch(
                        patch_url,
                        json={"amount_micros": str(new_micros)},
                        params={"updateMask": "amount_micros"},
                    )

                    if patch_resp.status_code not in (200, 204):
                        error_body = patch_resp.text
                        logger.error(f"[GOOGLE] Budget PATCH failed: {error_body}")
                        return {
                            "success": False,
                            "before_value": before_value,
                            "after_value": None,
                            "platform_response": {"status_code": patch_resp.status_code, "body": error_body},
                            "error": f"Budget update failed: HTTP {patch_resp.status_code}",
                        }

                    after_value: Dict[str, Any] = {"budget_micros": new_micros}
                    return {
                        "success": True,
                        "before_value": before_value,
                        "after_value": after_value,
                        "platform_response": patch_resp.json() if patch_resp.text else {"status": "OK"},
                        "error": None,
                    }

                # Status operations (pause/enable)
                elif action_type in [
                    ActionType.PAUSE_CAMPAIGN.value,
                    ActionType.PAUSE_ADSET.value,
                    ActionType.ENABLE_CAMPAIGN.value,
                    ActionType.ENABLE_ADSET.value,
                ]:
                    campaign_id = action_details.get("campaign_id", entity_id)
                    resource_name = f"customers/{customer_id}/campaigns/{campaign_id}"

                    # Determine target status
                    if action_type in [ActionType.PAUSE_CAMPAIGN.value, ActionType.PAUSE_ADSET.value]:
                        new_status = "PAUSED"
                    else:
                        new_status = "ENABLED"

                    before_value = {"status": "ENABLED" if new_status == "PAUSED" else "PAUSED"}

                    patch_url = f"{base_url}/{resource_name}"
                    patch_resp = await client.patch(
                        patch_url,
                        json={"status": new_status},
                        params={"updateMask": "status"},
                    )

                    if patch_resp.status_code not in (200, 204):
                        error_body = patch_resp.text
                        logger.error(f"[GOOGLE] Status PATCH failed: {error_body}")
                        return {
                            "success": False,
                            "before_value": before_value,
                            "after_value": None,
                            "platform_response": {"status_code": patch_resp.status_code, "body": error_body},
                            "error": f"Status update failed: HTTP {patch_resp.status_code}",
                        }

                    after_value = {"status": new_status}
                    return {
                        "success": True,
                        "before_value": before_value,
                        "after_value": after_value,
                        "platform_response": patch_resp.json() if patch_resp.text else {"status": "OK"},
                        "error": None,
                    }

                else:
                    return {
                        "success": False,
                        "before_value": None,
                        "after_value": None,
                        "platform_response": None,
                        "error": f"Unsupported action type for Google: {action_type}",
                    }

        except Exception as exc:
            logger.error(f"[GOOGLE] Live execution error: {exc}", exc_info=True)
            return {
                "success": False,
                "before_value": None,
                "after_value": None,
                "platform_response": None,
                "error": str(exc),
            }


class TikTokExecutor(PlatformExecutor):
    """Executor for TikTok Ads platform actions."""

    def _mock_execute(
        self,
        action_type: str,
        entity_type: str,
        entity_id: str,
        action_details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Simulate successful execution for TikTok platform."""
        logger.info(f"[TIKTOK] Mock executing {action_type} on {entity_type} {entity_id}")

        before_value: Dict[str, Any] = {"operation_status": "ENABLE", "budget": 100.00}
        after_value = before_value.copy()

        if action_type == ActionType.BUDGET_INCREASE.value:
            amount = action_details.get("amount", 0)
            after_value["budget"] = before_value["budget"] + amount

        elif action_type == ActionType.BUDGET_DECREASE.value:
            amount = action_details.get("amount", 0)
            after_value["budget"] = max(0, before_value["budget"] - amount)

        elif action_type in [ActionType.PAUSE_CAMPAIGN.value, ActionType.PAUSE_ADSET.value]:
            after_value["operation_status"] = "DISABLE"

        return {
            "success": True,
            "before_value": before_value,
            "after_value": after_value,
            "platform_response": {"code": 0, "message": "success"},
            "error": None,
        }

    async def _live_execute(
        self,
        action_type: str,
        entity_type: str,
        entity_id: str,
        action_details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute action on TikTok Ads API.

        Uses v1.3 of the TikTok Business API.  Budget and status changes
        are performed via the ``campaign/update/`` endpoint.

        ``action_details`` should include ``advertiser_id`` (falls back to
        ``settings.tiktok_advertiser_id``).  ``entity_id`` is the
        campaign/adgroup ID.

        Args:
            action_type: One of the ActionType enum values.
            entity_type: campaign, adset, etc.
            entity_id: The TikTok campaign or ad group ID.
            action_details: Dict with amount, advertiser_id keys.

        Returns:
            Standardised result dict.
        """
        import httpx
        from app.core.config import settings

        logger.info(f"[TIKTOK] Live executing {action_type} on {entity_type} {entity_id}")

        base_url = "https://business-api.tiktok.com/open_api/v1.3"
        access_token = settings.tiktok_access_token
        advertiser_id = action_details.get("advertiser_id") or settings.tiktok_advertiser_id

        if not access_token:
            return {
                "success": False,
                "before_value": None,
                "after_value": None,
                "platform_response": None,
                "error": "TikTok access token is not configured",
            }

        if not advertiser_id:
            return {
                "success": False,
                "before_value": None,
                "after_value": None,
                "platform_response": None,
                "error": "TikTok advertiser ID is not configured",
            }

        headers = {
            "Access-Token": access_token,
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=30.0, headers=headers) as client:
                # Step 1: GET current campaign info for before_value
                info_url = f"{base_url}/campaign/get/"
                info_params = {
                    "advertiser_id": advertiser_id,
                    "filtering": json.dumps({"campaign_ids": [entity_id]}),
                }
                info_resp = await client.get(info_url, params=info_params)

                before_value: Dict[str, Any] = {"operation_status": "ENABLE", "budget": 0}
                if info_resp.status_code == 200:
                    info_data = info_resp.json()
                    if info_data.get("code") == 0:
                        campaigns = info_data.get("data", {}).get("list", [])
                        if campaigns:
                            camp = campaigns[0]
                            before_value = {
                                "operation_status": camp.get("operation_status", "ENABLE"),
                                "budget": camp.get("budget", 0),
                            }

                # Step 2: Build update payload
                update_url = f"{base_url}/campaign/update/"
                update_payload: Dict[str, Any] = {
                    "advertiser_id": advertiser_id,
                    "campaign_id": entity_id,
                }

                if action_type in [ActionType.BUDGET_INCREASE.value, ActionType.BUDGET_DECREASE.value]:
                    amount = action_details.get("amount", 0)
                    current_budget = float(before_value.get("budget", 0))

                    if action_type == ActionType.BUDGET_INCREASE.value:
                        new_budget = current_budget + amount
                    else:
                        new_budget = max(0, current_budget - amount)

                    update_payload["budget"] = new_budget

                elif action_type in [ActionType.PAUSE_CAMPAIGN.value, ActionType.PAUSE_ADSET.value]:
                    update_payload["operation_status"] = "DISABLE"

                elif action_type in [ActionType.ENABLE_CAMPAIGN.value, ActionType.ENABLE_ADSET.value]:
                    update_payload["operation_status"] = "ENABLE"

                else:
                    return {
                        "success": False,
                        "before_value": before_value,
                        "after_value": None,
                        "platform_response": None,
                        "error": f"Unsupported action type for TikTok: {action_type}",
                    }

                # Step 3: POST update
                post_resp = await client.post(update_url, json=update_payload)
                resp_data = post_resp.json()

                if resp_data.get("code") != 0:
                    error_msg = resp_data.get("message", "Unknown TikTok API error")
                    logger.error(f"[TIKTOK] Update failed: {error_msg}")
                    return {
                        "success": False,
                        "before_value": before_value,
                        "after_value": None,
                        "platform_response": resp_data,
                        "error": error_msg,
                    }

                # Build after_value from what we sent
                after_value = before_value.copy()
                if "budget" in update_payload:
                    after_value["budget"] = update_payload["budget"]
                if "operation_status" in update_payload:
                    after_value["operation_status"] = update_payload["operation_status"]

                return {
                    "success": True,
                    "before_value": before_value,
                    "after_value": after_value,
                    "platform_response": resp_data,
                    "error": None,
                }

        except Exception as exc:
            logger.error(f"[TIKTOK] Live execution error: {exc}", exc_info=True)
            return {
                "success": False,
                "before_value": None,
                "after_value": None,
                "platform_response": None,
                "error": str(exc),
            }


class SnapchatExecutor(PlatformExecutor):
    """Executor for Snapchat Ads platform actions.

    Uses the Snapchat Marketing API v1 to modify campaigns and ad squads.
    Budget values are in micro-currency (1 USD = 1_000_000 micro).
    """

    def _mock_execute(
        self,
        action_type: str,
        entity_type: str,
        entity_id: str,
        action_details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Simulate successful execution for Snapchat platform."""
        logger.info(f"[SNAP] Mock executing {action_type} on {entity_type} {entity_id}")

        before_value: Dict[str, Any] = {"status": "ACTIVE", "daily_budget_micro": 10000000}
        after_value = before_value.copy()

        if action_type == ActionType.BUDGET_INCREASE.value:
            amount = action_details.get("amount", 0)
            after_value["daily_budget_micro"] = before_value["daily_budget_micro"] + int(amount * 1_000_000)

        elif action_type == ActionType.BUDGET_DECREASE.value:
            amount = action_details.get("amount", 0)
            after_value["daily_budget_micro"] = max(0, before_value["daily_budget_micro"] - int(amount * 1_000_000))

        elif action_type in [ActionType.PAUSE_CAMPAIGN.value, ActionType.PAUSE_ADSET.value]:
            after_value["status"] = "PAUSED"

        elif action_type in [ActionType.ENABLE_CAMPAIGN.value, ActionType.ENABLE_ADSET.value]:
            after_value["status"] = "ACTIVE"

        return {
            "success": True,
            "before_value": before_value,
            "after_value": after_value,
            "platform_response": {"request_id": "snap_mock_123", "request_status": "SUCCESS"},
            "error": None,
        }

    async def _live_execute(
        self,
        action_type: str,
        entity_type: str,
        entity_id: str,
        action_details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute action on Snapchat Marketing API.

        Uses the Snapchat Ads API v1 endpoints:
        - GET /campaigns/{id} or /adsquads/{id} for before_value
        - PUT /campaigns/{id} or /adsquads/{id} for updates

        Args:
            action_type: One of the ActionType enum values.
            entity_type: campaign or adsquad.
            entity_id: The Snapchat entity ID.
            action_details: Dict with amount/percentage keys for budget ops.

        Returns:
            Standardised result dict.
        """
        import httpx
        from app.core.config import settings

        logger.info(f"[SNAP] Live executing {action_type} on {entity_type} {entity_id}")

        base_url = "https://adsapi.snapchat.com/v1"
        access_token = settings.snapchat_access_token

        if not access_token:
            return {
                "success": False,
                "before_value": None,
                "after_value": None,
                "platform_response": None,
                "error": "Snapchat access token is not configured",
            }

        # Map entity types to Snapchat API resource paths
        resource_map = {
            "campaign": "campaigns",
            "adset": "adsquads",
            "ad_squad": "adsquads",
            "adsquad": "adsquads",
        }
        resource = resource_map.get(entity_type, "campaigns")

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                headers = {"Authorization": f"Bearer {access_token}"}

                # Step 1: GET current state
                get_resp = await client.get(
                    f"{base_url}/{resource}/{entity_id}",
                    headers=headers,
                )
                if get_resp.status_code != 200:
                    error_body = get_resp.text
                    logger.error(f"[SNAP] GET entity failed: {error_body}")
                    return {
                        "success": False,
                        "before_value": None,
                        "after_value": None,
                        "platform_response": {"status_code": get_resp.status_code, "body": error_body},
                        "error": f"Failed to fetch entity state: HTTP {get_resp.status_code}",
                    }

                resp_json = get_resp.json()
                # Snapchat wraps responses: {"campaigns": [{"campaign": {...}}]}
                items = resp_json.get(resource, [])
                entity_data = items[0].get(resource[:-1], {}) if items else {}
                before_value = {
                    "status": entity_data.get("status"),
                    "daily_budget_micro": entity_data.get("daily_budget_micro", 0),
                }

                # Step 2: Build update payload
                update_payload = dict(entity_data)

                if action_type in [ActionType.BUDGET_INCREASE.value, ActionType.BUDGET_DECREASE.value]:
                    amount = action_details.get("amount", 0)
                    current_budget = int(entity_data.get("daily_budget_micro", 0))

                    if action_type == ActionType.BUDGET_INCREASE.value:
                        new_budget = current_budget + int(amount * 1_000_000)
                    else:
                        new_budget = max(0, current_budget - int(amount * 1_000_000))

                    update_payload["daily_budget_micro"] = new_budget

                elif action_type in [
                    ActionType.PAUSE_CAMPAIGN.value,
                    ActionType.PAUSE_ADSET.value,
                ]:
                    update_payload["status"] = "PAUSED"

                elif action_type in [
                    ActionType.ENABLE_CAMPAIGN.value,
                    ActionType.ENABLE_ADSET.value,
                ]:
                    update_payload["status"] = "ACTIVE"

                # Step 3: PUT update
                put_body = {resource: [{resource[:-1]: update_payload}]}
                put_resp = await client.put(
                    f"{base_url}/{resource}/{entity_id}",
                    headers=headers,
                    json=put_body,
                )

                resp_data = put_resp.json() if put_resp.status_code == 200 else {"body": put_resp.text}

                if put_resp.status_code != 200:
                    error_msg = resp_data.get("body", str(put_resp.status_code))
                    logger.error(f"[SNAP] PUT update failed: {error_msg}")
                    return {
                        "success": False,
                        "before_value": before_value,
                        "after_value": None,
                        "platform_response": resp_data,
                        "error": f"Failed to update entity: HTTP {put_resp.status_code}",
                    }

                # Build after_value from update payload
                after_value = before_value.copy()
                if "daily_budget_micro" in update_payload:
                    after_value["daily_budget_micro"] = update_payload["daily_budget_micro"]
                if "status" in update_payload:
                    after_value["status"] = update_payload["status"]

                return {
                    "success": True,
                    "before_value": before_value,
                    "after_value": after_value,
                    "platform_response": resp_data,
                    "error": None,
                }

        except Exception as exc:
            logger.error(f"[SNAP] Live execution error: {exc}", exc_info=True)
            return {
                "success": False,
                "before_value": None,
                "after_value": None,
                "platform_response": None,
                "error": str(exc),
            }


# Platform executor registry
PLATFORM_EXECUTORS: Dict[str, PlatformExecutor] = {
    "meta": MetaExecutor(),
    "google": GoogleExecutor(),
    "tiktok": TikTokExecutor(),
    "snapchat": SnapchatExecutor(),
}


# =============================================================================
# Helper Functions
# =============================================================================

async def check_signal_health(db: AsyncSession, tenant_id: int) -> bool:
    """
    Check if signal health allows action execution.
    Returns True if OK/Risk, False if Degraded/Critical.
    """
    result = await db.execute(
        select(FactSignalHealthDaily).where(
            and_(
                FactSignalHealthDaily.tenant_id == tenant_id,
                FactSignalHealthDaily.date == datetime.now(timezone.utc).date(),
            )
        )
    )
    records = result.scalars().all()

    if not records:
        # No data means we proceed cautiously
        return True

    # Check if any platform has degraded/critical status
    for record in records:
        if record.status in [SignalHealthStatus.DEGRADED, SignalHealthStatus.CRITICAL]:
            return False

    return True


async def get_tenant_autopilot_level(db: AsyncSession, tenant_id: int) -> int:
    """Get the autopilot level for a tenant."""
    from app.features.service import get_tenant_features

    features = await get_tenant_features(db, tenant_id)
    return features.get("autopilot_level", 0)


def validate_action_caps(action_type: str, action_details: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate that an action doesn't exceed caps.

    Returns:
        Tuple of (is_valid, error_message)
    """
    caps = get_autopilot_caps()

    if action_type in [ActionType.BUDGET_INCREASE.value, ActionType.BUDGET_DECREASE.value]:
        amount = action_details.get("amount", 0)
        percentage = action_details.get("percentage", 0)

        if abs(amount) > caps["max_daily_budget_change"]:
            return False, f"Budget change ${amount} exceeds max ${caps['max_daily_budget_change']}"

        if abs(percentage) > caps["max_budget_pct_change"]:
            return False, f"Budget change {percentage}% exceeds max {caps['max_budget_pct_change']}%"

    return True, None


# =============================================================================
# Main Task
# =============================================================================

@shared_task(
    name="tasks.apply_actions_queue",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def apply_actions_queue(self, tenant_id: Optional[int] = None):
    """
    Process and apply approved actions from the queue.

    This task:
    1. Fetches approved actions that haven't been applied yet
    2. Validates signal health before execution
    3. Applies actions to platforms
    4. Records results and audit logs

    Args:
        tenant_id: Optional tenant ID to process (None = all tenants)
    """
    import asyncio

    async def run_apply():
        async with async_session_factory() as db:
            try:
                logger.info(f"Starting action queue processing for tenant_id={tenant_id}")

                # Build query for approved actions
                query = select(FactActionsQueue).where(
                    FactActionsQueue.status == ActionStatus.APPROVED.value
                )

                if tenant_id:
                    query = query.where(FactActionsQueue.tenant_id == tenant_id)

                # Order by creation time
                query = query.order_by(FactActionsQueue.created_at)

                result = await db.execute(query)
                actions = result.scalars().all()

                if not actions:
                    logger.info("No approved actions to process")
                    return {"status": "success", "processed": 0, "failed": 0}

                processed = 0
                failed = 0

                for action in actions:
                    try:
                        # Check signal health for this tenant
                        health_ok = await check_signal_health(db, action.tenant_id)
                        if not health_ok:
                            logger.warning(f"Skipping action {action.id}: Signal health degraded")
                            action.error = "Signal health degraded - action deferred"
                            continue

                        # Parse action details
                        action_details = json.loads(action.action_json) if action.action_json else {}

                        # Validate against caps
                        is_valid, cap_error = validate_action_caps(action.action_type, action_details)
                        if not is_valid:
                            logger.warning(f"Action {action.id} exceeds caps: {cap_error}")
                            action.status = ActionStatus.FAILED.value
                            action.error = cap_error
                            failed += 1
                            continue

                        # Get platform executor
                        executor = PLATFORM_EXECUTORS.get(action.platform)
                        if not executor:
                            logger.error(f"No executor for platform: {action.platform}")
                            action.status = ActionStatus.FAILED.value
                            action.error = f"Unsupported platform: {action.platform}"
                            failed += 1
                            continue

                        # Execute the action
                        exec_result = await executor.execute_action(
                            action_type=action.action_type,
                            entity_type=action.entity_type,
                            entity_id=action.entity_id,
                            action_details=action_details,
                        )

                        if exec_result["success"]:
                            action.status = ActionStatus.APPLIED.value
                            action.applied_at = datetime.now(timezone.utc)
                            action.after_value = json.dumps(exec_result["after_value"])
                            action.platform_response = json.dumps(exec_result["platform_response"])
                            processed += 1

                            logger.info(f"Successfully applied action {action.id}")

                            # Log to audit (in production, write to audit_log table)
                            await log_action_audit(
                                db=db,
                                action=action,
                                result=exec_result,
                            )

                            # Publish WebSocket notification
                            await publish_action_status_update(
                                tenant_id=action.tenant_id,
                                action_id=str(action.id),
                                status="applied",
                                before_value=exec_result.get("before_value"),
                                after_value=exec_result.get("after_value"),
                            )
                        else:
                            action.status = ActionStatus.FAILED.value
                            action.error = exec_result.get("error", "Unknown error")
                            action.platform_response = json.dumps(exec_result.get("platform_response"))
                            failed += 1

                            logger.error(f"Failed to apply action {action.id}: {exec_result.get('error')}")

                            # Publish WebSocket notification for failure
                            await publish_action_status_update(
                                tenant_id=action.tenant_id,
                                action_id=str(action.id),
                                status="failed",
                            )

                    except Exception as e:
                        logger.error(f"Error processing action {action.id}: {str(e)}")
                        action.status = ActionStatus.FAILED.value
                        action.error = str(e)
                        failed += 1

                await db.commit()

                logger.info(f"Action queue processing complete: {processed} applied, {failed} failed")

                return {
                    "status": "success",
                    "processed": processed,
                    "failed": failed,
                }

            except Exception as e:
                logger.error(f"Action queue processing failed: {str(e)}")
                await db.rollback()
                raise self.retry(exc=e)

    return asyncio.run(run_apply())


async def log_action_audit(db: AsyncSession, action: FactActionsQueue, result: Dict[str, Any]):
    """
    Log action execution to audit trail.

    In production, this would write to a dedicated audit_log table.
    """
    audit_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tenant_id": action.tenant_id,
        "action_id": str(action.id),
        "action_type": action.action_type,
        "entity_type": action.entity_type,
        "entity_id": action.entity_id,
        "entity_name": action.entity_name,
        "platform": action.platform,
        "before_value": result.get("before_value"),
        "after_value": result.get("after_value"),
        "approved_by": action.approved_by_user_id,
        "applied_at": action.applied_at.isoformat() if action.applied_at else None,
        "platform_response": result.get("platform_response"),
    }

    logger.info(f"AUDIT: {json.dumps(audit_entry)}")


# =============================================================================
# Scheduled Task
# =============================================================================

@shared_task(name="tasks.schedule_apply_actions_queue")
def schedule_apply_actions_queue():
    """
    Scheduled task to process action queue.
    Should run every 5 minutes to pick up newly approved actions.
    """
    return apply_actions_queue.delay()


# =============================================================================
# Single Action Execution
# =============================================================================

@shared_task(
    name="tasks.apply_single_action",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def apply_single_action(self, action_id: str, user_id: Optional[int] = None):
    """
    Apply a single action immediately.

    Used for immediate execution when approval is granted.

    Args:
        action_id: UUID of the action to apply
        user_id: ID of user triggering the execution
    """
    import asyncio
    from uuid import UUID

    async def run_single():
        async with async_session_factory() as db:
            try:
                uuid_id = UUID(action_id)

                result = await db.execute(
                    select(FactActionsQueue).where(FactActionsQueue.id == uuid_id)
                )
                action = result.scalar_one_or_none()

                if not action:
                    return {"status": "error", "error": "Action not found"}

                if action.status != ActionStatus.APPROVED.value:
                    return {"status": "error", "error": f"Action status is {action.status}, expected approved"}

                # Check signal health
                health_ok = await check_signal_health(db, action.tenant_id)
                if not health_ok:
                    return {"status": "error", "error": "Signal health degraded"}

                # Parse and validate
                action_details = json.loads(action.action_json) if action.action_json else {}
                is_valid, cap_error = validate_action_caps(action.action_type, action_details)

                if not is_valid:
                    action.status = ActionStatus.FAILED.value
                    action.error = cap_error
                    await db.commit()
                    return {"status": "error", "error": cap_error}

                # Execute
                executor = PLATFORM_EXECUTORS.get(action.platform)
                if not executor:
                    action.status = ActionStatus.FAILED.value
                    action.error = f"Unsupported platform: {action.platform}"
                    await db.commit()
                    return {"status": "error", "error": action.error}

                exec_result = await executor.execute_action(
                    action_type=action.action_type,
                    entity_type=action.entity_type,
                    entity_id=action.entity_id,
                    action_details=action_details,
                )

                if exec_result["success"]:
                    action.status = ActionStatus.APPLIED.value
                    action.applied_at = datetime.now(timezone.utc)
                    action.applied_by_user_id = user_id
                    action.after_value = json.dumps(exec_result["after_value"])
                    action.platform_response = json.dumps(exec_result["platform_response"])

                    await log_action_audit(db, action, exec_result)
                    await db.commit()

                    # Publish WebSocket notification
                    await publish_action_status_update(
                        tenant_id=action.tenant_id,
                        action_id=action_id,
                        status="applied",
                        before_value=exec_result.get("before_value"),
                        after_value=exec_result.get("after_value"),
                    )

                    return {"status": "success", "action_id": action_id}
                else:
                    action.status = ActionStatus.FAILED.value
                    action.error = exec_result.get("error", "Unknown error")
                    action.platform_response = json.dumps(exec_result.get("platform_response"))
                    await db.commit()

                    # Publish WebSocket notification for failure
                    await publish_action_status_update(
                        tenant_id=action.tenant_id,
                        action_id=action_id,
                        status="failed",
                    )

                    return {"status": "error", "error": action.error}

            except Exception as e:
                logger.error(f"Single action execution failed: {str(e)}")
                await db.rollback()
                raise self.retry(exc=e)

    return asyncio.run(run_single())
