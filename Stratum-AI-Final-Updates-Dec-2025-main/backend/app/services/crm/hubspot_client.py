# =============================================================================
# Stratum AI - HubSpot Client
# =============================================================================
"""
HubSpot API client with OAuth support.
Handles authentication, token refresh, and API calls.
"""

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import decrypt_pii, encrypt_pii
from app.models.crm import (
    CRMConnection,
    CRMConnectionStatus,
    CRMProvider,
)

logger = get_logger(__name__)


# HubSpot API Configuration
HUBSPOT_AUTH_URL = "https://app.hubspot.com/oauth/authorize"
HUBSPOT_TOKEN_URL = "https://api.hubapi.com/oauth/v1/token"
HUBSPOT_API_BASE = "https://api.hubapi.com"

# Required scopes for Stratum AI integration
HUBSPOT_SCOPES = [
    "crm.objects.contacts.read",
    "crm.objects.contacts.write",
    "crm.objects.deals.read",
    "crm.objects.deals.write",
    "crm.objects.owners.read",
    "crm.schemas.contacts.read",
    "crm.schemas.deals.read",
]


class HubSpotClient:
    """
    HubSpot API client with OAuth 2.0 support.

    Features:
    - OAuth authorization flow
    - Automatic token refresh
    - Encrypted token storage
    - Rate limiting awareness
    """

    def __init__(self, db: AsyncSession, tenant_id: int):
        self.db = db
        self.tenant_id = tenant_id
        self._connection: Optional[CRMConnection] = None
        self._http_client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._http_client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._http_client:
            await self._http_client.aclose()

    # =========================================================================
    # OAuth Flow
    # =========================================================================

    def get_authorization_url(self, redirect_uri: str, state: Optional[str] = None) -> str:
        """
        Generate HubSpot OAuth authorization URL.

        Args:
            redirect_uri: OAuth callback URL
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL to redirect user to
        """
        if state is None:
            state = secrets.token_urlsafe(32)

        params = {
            "client_id": settings.hubspot_client_id,
            "redirect_uri": redirect_uri,
            "scope": " ".join(HUBSPOT_SCOPES),
            "state": state,
        }

        return f"{HUBSPOT_AUTH_URL}?{urlencode(params)}"

    async def exchange_code_for_tokens(
        self,
        code: str,
        redirect_uri: str,
    ) -> CRMConnection:
        """
        Exchange authorization code for access/refresh tokens.

        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Same redirect URI used in authorization

        Returns:
            Created/updated CRMConnection with encrypted tokens
        """
        async with httpx.AsyncClient() as client:
            response = await client.post(
                HUBSPOT_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "client_id": settings.hubspot_client_id,
                    "client_secret": settings.hubspot_client_secret,
                    "redirect_uri": redirect_uri,
                    "code": code,
                },
            )

            if response.status_code != 200:
                logger.error(
                    "hubspot_token_exchange_failed",
                    status=response.status_code,
                    response=response.text,
                )
                raise ValueError(f"HubSpot token exchange failed: {response.text}")

            data = response.json()

        # Get or create connection
        connection = await self._get_or_create_connection()

        # Encrypt and store tokens
        connection.access_token_enc = encrypt_pii(data["access_token"])
        connection.refresh_token_enc = encrypt_pii(data["refresh_token"])
        connection.token_expires_at = datetime.now(UTC) + timedelta(seconds=data["expires_in"])
        connection.scopes = " ".join(HUBSPOT_SCOPES)
        connection.status = CRMConnectionStatus.CONNECTED

        # Get portal info
        portal_info = await self._get_portal_info(data["access_token"])
        if portal_info:
            connection.provider_account_id = str(portal_info.get("portalId", ""))
            connection.provider_account_name = portal_info.get("accountType", "HubSpot")

        await self.db.commit()
        await self.db.refresh(connection)

        logger.info(
            "hubspot_connected",
            tenant_id=self.tenant_id,
            portal_id=connection.provider_account_id,
        )

        return connection

    async def refresh_tokens(self) -> bool:
        """
        Refresh access token using refresh token.

        Returns:
            True if refresh successful, False otherwise
        """
        connection = await self._get_connection()
        if not connection or not connection.refresh_token_enc:
            return False

        refresh_token = decrypt_pii(connection.refresh_token_enc)

        async with httpx.AsyncClient() as client:
            response = await client.post(
                HUBSPOT_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "client_id": settings.hubspot_client_id,
                    "client_secret": settings.hubspot_client_secret,
                    "refresh_token": refresh_token,
                },
            )

            if response.status_code != 200:
                logger.error(
                    "hubspot_token_refresh_failed",
                    status=response.status_code,
                    tenant_id=self.tenant_id,
                )
                connection.status = CRMConnectionStatus.EXPIRED
                await self.db.commit()
                return False

            data = response.json()

        # Update tokens
        connection.access_token_enc = encrypt_pii(data["access_token"])
        connection.refresh_token_enc = encrypt_pii(data["refresh_token"])
        connection.token_expires_at = datetime.now(UTC) + timedelta(seconds=data["expires_in"])
        connection.status = CRMConnectionStatus.CONNECTED

        await self.db.commit()

        logger.info("hubspot_tokens_refreshed", tenant_id=self.tenant_id)
        return True

    async def disconnect(self) -> bool:
        """
        Disconnect HubSpot integration.
        Revokes tokens and marks connection as revoked.
        """
        connection = await self._get_connection()
        if not connection:
            return False

        # Revoke token (best effort)
        if connection.access_token_enc:
            try:
                access_token = decrypt_pii(connection.access_token_enc)
                async with httpx.AsyncClient() as client:
                    await client.delete(
                        f"{HUBSPOT_API_BASE}/oauth/v1/refresh-tokens/{decrypt_pii(connection.refresh_token_enc)}"
                    )
            except Exception as e:
                logger.warning("hubspot_token_revoke_failed", error=str(e))

        # Clear tokens and mark as revoked
        connection.access_token_enc = None
        connection.refresh_token_enc = None
        connection.token_expires_at = None
        connection.status = CRMConnectionStatus.REVOKED

        await self.db.commit()

        logger.info("hubspot_disconnected", tenant_id=self.tenant_id)
        return True

    # =========================================================================
    # API Methods
    # =========================================================================

    async def get_access_token(self) -> Optional[str]:
        """
        Get valid access token, refreshing if needed.

        Returns:
            Access token string or None if unavailable
        """
        connection = await self._get_connection()
        if not connection or connection.status != CRMConnectionStatus.CONNECTED:
            return None

        # Check if token needs refresh (5 min buffer)
        if connection.token_expires_at:
            buffer = timedelta(minutes=5)
            if datetime.now(UTC) >= connection.token_expires_at - buffer:
                if not await self.refresh_tokens():
                    return None
                await self.db.refresh(connection)

        return decrypt_pii(connection.access_token_enc) if connection.access_token_enc else None

    async def api_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None,
    ) -> Optional[dict[str, Any]]:
        """
        Make authenticated API request to HubSpot.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: API endpoint path (e.g., "/crm/v3/objects/contacts")
            params: Optional query parameters
            json_data: Optional JSON body

        Returns:
            Response JSON or None on error
        """
        access_token = await self.get_access_token()
        if not access_token:
            logger.error("hubspot_api_no_token", tenant_id=self.tenant_id)
            return None

        url = f"{HUBSPOT_API_BASE}{endpoint}"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        client = self._http_client or httpx.AsyncClient(timeout=30.0)
        should_close = self._http_client is None

        try:
            response = await client.request(
                method=method,
                url=url,
                params=params,
                json=json_data,
                headers=headers,
            )

            if response.status_code == 401:
                # Token expired, try refresh
                if await self.refresh_tokens():
                    return await self.api_request(method, endpoint, params, json_data)
                return None

            if response.status_code >= 400:
                logger.error(
                    "hubspot_api_error",
                    status=response.status_code,
                    endpoint=endpoint,
                    response=response.text[:500],
                )
                return None

            return response.json() if response.text else {}

        except Exception as e:
            logger.error("hubspot_api_exception", error=str(e), endpoint=endpoint)
            return None

        finally:
            if should_close:
                await client.aclose()

    # =========================================================================
    # Contact Operations
    # =========================================================================

    async def get_contacts(
        self,
        limit: int = 100,
        after: Optional[str] = None,
        properties: Optional[list[str]] = None,
        updated_after: Optional[datetime] = None,
    ) -> Optional[dict[str, Any]]:
        """
        Get contacts from HubSpot.

        Args:
            limit: Number of contacts per page (max 100)
            after: Pagination cursor
            properties: List of properties to include
            updated_after: Filter by last modified date

        Returns:
            HubSpot contacts response with paging
        """
        if properties is None:
            properties = [
                "email",
                "phone",
                "firstname",
                "lastname",
                "lifecyclestage",
                "hs_lead_status",
                "utm_source",
                "utm_medium",
                "utm_campaign",
                "utm_content",
                "utm_term",
                "hs_analytics_source",
                "hs_analytics_first_url",
                "gclid",
                "hs_google_click_id",
            ]

        params = {
            "limit": min(limit, 100),
            "properties": ",".join(properties),
        }

        if after:
            params["after"] = after

        # Use search API for filtering by updated date
        if updated_after:
            return await self.search_contacts(
                filters=[
                    {
                        "propertyName": "lastmodifieddate",
                        "operator": "GTE",
                        "value": int(updated_after.timestamp() * 1000),
                    }
                ],
                properties=properties,
                limit=limit,
                after=after,
            )

        return await self.api_request("GET", "/crm/v3/objects/contacts", params=params)

    async def search_contacts(
        self,
        filters: list[dict],
        properties: Optional[list[str]] = None,
        limit: int = 100,
        after: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """
        Search contacts with filters.
        """
        if properties is None:
            properties = ["email", "phone", "firstname", "lastname", "lifecyclestage"]

        body = {
            "filterGroups": [{"filters": filters}],
            "properties": properties,
            "limit": min(limit, 100),
        }

        if after:
            body["after"] = after

        return await self.api_request("POST", "/crm/v3/objects/contacts/search", json_data=body)

    async def get_contact(
        self, contact_id: str, properties: Optional[list[str]] = None
    ) -> Optional[dict[str, Any]]:
        """Get a single contact by ID."""
        params = {}
        if properties:
            params["properties"] = ",".join(properties)

        return await self.api_request(
            "GET", f"/crm/v3/objects/contacts/{contact_id}", params=params
        )

    async def update_contact(
        self, contact_id: str, properties: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        """Update contact properties (for writeback)."""
        return await self.api_request(
            "PATCH",
            f"/crm/v3/objects/contacts/{contact_id}",
            json_data={"properties": properties},
        )

    # =========================================================================
    # Deal Operations
    # =========================================================================

    async def get_deals(
        self,
        limit: int = 100,
        after: Optional[str] = None,
        properties: Optional[list[str]] = None,
        updated_after: Optional[datetime] = None,
    ) -> Optional[dict[str, Any]]:
        """
        Get deals from HubSpot.
        """
        if properties is None:
            properties = [
                "dealname",
                "amount",
                "dealstage",
                "pipeline",
                "closedate",
                "hs_is_closed_won",
                "hs_is_closed",
                "hubspot_owner_id",
                "hs_analytics_source",
            ]

        params = {
            "limit": min(limit, 100),
            "properties": ",".join(properties),
        }

        if after:
            params["after"] = after

        if updated_after:
            return await self.search_deals(
                filters=[
                    {
                        "propertyName": "hs_lastmodifieddate",
                        "operator": "GTE",
                        "value": int(updated_after.timestamp() * 1000),
                    }
                ],
                properties=properties,
                limit=limit,
                after=after,
            )

        return await self.api_request("GET", "/crm/v3/objects/deals", params=params)

    async def search_deals(
        self,
        filters: list[dict],
        properties: Optional[list[str]] = None,
        limit: int = 100,
        after: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Search deals with filters."""
        if properties is None:
            properties = ["dealname", "amount", "dealstage", "closedate"]

        body = {
            "filterGroups": [{"filters": filters}],
            "properties": properties,
            "limit": min(limit, 100),
        }

        if after:
            body["after"] = after

        return await self.api_request("POST", "/crm/v3/objects/deals/search", json_data=body)

    async def get_deal(
        self, deal_id: str, properties: Optional[list[str]] = None
    ) -> Optional[dict[str, Any]]:
        """Get a single deal by ID."""
        params = {}
        if properties:
            params["properties"] = ",".join(properties)

        return await self.api_request("GET", f"/crm/v3/objects/deals/{deal_id}", params=params)

    async def get_deal_associations(
        self, deal_id: str, to_object_type: str = "contacts"
    ) -> Optional[dict[str, Any]]:
        """Get deal associations (e.g., linked contacts)."""
        return await self.api_request(
            "GET",
            f"/crm/v3/objects/deals/{deal_id}/associations/{to_object_type}",
        )

    async def update_deal(
        self, deal_id: str, properties: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        """Update deal properties (for writeback)."""
        return await self.api_request(
            "PATCH",
            f"/crm/v3/objects/deals/{deal_id}",
            json_data={"properties": properties},
        )

    # =========================================================================
    # Batch Operations (for Writeback)
    # =========================================================================

    async def batch_update_contacts(
        self,
        updates: list[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        """
        Batch update multiple contacts.

        Args:
            updates: List of {"id": contact_id, "properties": {...}}

        Returns:
            Batch response with results and errors
        """
        if not updates:
            return {"status": "success", "results": [], "errors": []}

        # HubSpot batch limit is 100
        results = []
        errors = []

        for i in range(0, len(updates), 100):
            batch = updates[i : i + 100]
            response = await self.api_request(
                "POST",
                "/crm/v3/objects/contacts/batch/update",
                json_data={"inputs": batch},
            )

            if response:
                results.extend(response.get("results", []))
                errors.extend(response.get("errors", []))
            else:
                errors.append({"message": f"Batch {i // 100 + 1} failed"})

        return {"results": results, "errors": errors}

    async def batch_update_deals(
        self,
        updates: list[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        """
        Batch update multiple deals.

        Args:
            updates: List of {"id": deal_id, "properties": {...}}

        Returns:
            Batch response with results and errors
        """
        if not updates:
            return {"status": "success", "results": [], "errors": []}

        results = []
        errors = []

        for i in range(0, len(updates), 100):
            batch = updates[i : i + 100]
            response = await self.api_request(
                "POST",
                "/crm/v3/objects/deals/batch/update",
                json_data={"inputs": batch},
            )

            if response:
                results.extend(response.get("results", []))
                errors.extend(response.get("errors", []))
            else:
                errors.append({"message": f"Batch {i // 100 + 1} failed"})

        return {"results": results, "errors": errors}

    # =========================================================================
    # Custom Properties (for Writeback)
    # =========================================================================

    async def get_contact_properties(self) -> Optional[dict[str, Any]]:
        """Get all contact properties (schema)."""
        return await self.api_request("GET", "/crm/v3/properties/contacts")

    async def get_deal_properties(self) -> Optional[dict[str, Any]]:
        """Get all deal properties (schema)."""
        return await self.api_request("GET", "/crm/v3/properties/deals")

    async def create_contact_property(
        self,
        name: str,
        label: str,
        property_type: str = "string",
        field_type: str = "text",
        group_name: str = "stratumroas",
        description: str = "",
    ) -> Optional[dict[str, Any]]:
        """
        Create a custom contact property.

        Args:
            name: Internal property name (e.g., "stratum_ad_platform")
            label: Display label
            property_type: string, number, date, datetime, enumeration
            field_type: text, textarea, number, date, etc.
            group_name: Property group
            description: Property description
        """
        return await self.api_request(
            "POST",
            "/crm/v3/properties/contacts",
            json_data={
                "name": name,
                "label": label,
                "type": property_type,
                "fieldType": field_type,
                "groupName": group_name,
                "description": description,
            },
        )

    async def create_deal_property(
        self,
        name: str,
        label: str,
        property_type: str = "string",
        field_type: str = "text",
        group_name: str = "stratumroas",
        description: str = "",
    ) -> Optional[dict[str, Any]]:
        """Create a custom deal property."""
        return await self.api_request(
            "POST",
            "/crm/v3/properties/deals",
            json_data={
                "name": name,
                "label": label,
                "type": property_type,
                "fieldType": field_type,
                "groupName": group_name,
                "description": description,
            },
        )

    async def create_property_group(
        self,
        object_type: str,
        name: str,
        label: str,
    ) -> Optional[dict[str, Any]]:
        """
        Create a property group.

        Args:
            object_type: "contacts" or "deals"
            name: Internal group name
            label: Display label
        """
        return await self.api_request(
            "POST",
            f"/crm/v3/properties/{object_type}/groups",
            json_data={
                "name": name,
                "label": label,
            },
        )

    async def property_exists(
        self,
        object_type: str,
        property_name: str,
    ) -> bool:
        """Check if a property exists."""
        response = await self.api_request(
            "GET",
            f"/crm/v3/properties/{object_type}/{property_name}",
        )
        return response is not None

    # =========================================================================
    # Owners
    # =========================================================================

    async def get_owners(self) -> Optional[dict[str, Any]]:
        """Get all owners (sales reps) in the account."""
        return await self.api_request("GET", "/crm/v3/owners")

    # =========================================================================
    # Pipelines
    # =========================================================================

    async def get_deal_pipelines(self) -> Optional[dict[str, Any]]:
        """Get deal pipelines and stages."""
        return await self.api_request("GET", "/crm/v3/pipelines/deals")

    # =========================================================================
    # Webhooks
    # =========================================================================

    async def create_webhook_subscription(
        self,
        event_type: str,
        webhook_url: str,
    ) -> Optional[dict[str, Any]]:
        """
        Create webhook subscription for real-time updates.

        Args:
            event_type: e.g., "contact.creation", "deal.propertyChange"
            webhook_url: URL to receive webhook events
        """
        # Note: HubSpot webhooks are configured at the app level, not via API
        # This would require using HubSpot's webhook settings
        logger.info(
            "hubspot_webhook_subscription",
            event_type=event_type,
            webhook_url=webhook_url,
        )
        return {"status": "configured_in_hubspot_app"}

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _get_connection(self) -> Optional[CRMConnection]:
        """Get existing HubSpot connection for tenant."""
        if self._connection:
            return self._connection

        result = await self.db.execute(
            select(CRMConnection).where(
                CRMConnection.tenant_id == self.tenant_id,
                CRMConnection.provider == CRMProvider.HUBSPOT,
            )
        )
        self._connection = result.scalar_one_or_none()
        return self._connection

    async def _get_or_create_connection(self) -> CRMConnection:
        """Get or create HubSpot connection for tenant."""
        connection = await self._get_connection()
        if connection:
            return connection

        connection = CRMConnection(
            tenant_id=self.tenant_id,
            provider=CRMProvider.HUBSPOT,
            status=CRMConnectionStatus.PENDING,
            webhook_secret=secrets.token_urlsafe(32),
        )
        self.db.add(connection)
        await self.db.flush()
        self._connection = connection
        return connection

    async def _get_portal_info(self, access_token: str) -> Optional[dict]:
        """Get HubSpot portal/account info."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{HUBSPOT_API_BASE}/account-info/v3/details",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if response.status_code == 200:
                return response.json()
        return None

    async def get_connection_status(self) -> dict[str, Any]:
        """Get current connection status."""
        connection = await self._get_connection()
        if not connection:
            return {
                "connected": False,
                "status": "not_configured",
                "provider": "hubspot",
            }

        return {
            "connected": connection.status == CRMConnectionStatus.CONNECTED,
            "status": connection.status.value,
            "provider": "hubspot",
            "account_id": connection.provider_account_id,
            "account_name": connection.provider_account_name,
            "last_sync_at": connection.last_sync_at.isoformat()
            if connection.last_sync_at
            else None,
            "last_sync_status": connection.last_sync_status,
            "scopes": connection.scopes.split() if connection.scopes else [],
        }


# =============================================================================
# Helper Functions
# =============================================================================


def hash_email(email: str) -> str:
    """Hash email for privacy-safe identity matching."""
    normalized = email.lower().strip()
    return hashlib.sha256(normalized.encode()).hexdigest()


def hash_phone(phone: str) -> str:
    """Hash phone number for privacy-safe identity matching."""
    # Remove all non-digit characters
    normalized = "".join(c for c in phone if c.isdigit())
    return hashlib.sha256(normalized.encode()).hexdigest()
