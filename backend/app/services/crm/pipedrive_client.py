# =============================================================================
# Stratum AI - Pipedrive Client
# =============================================================================
"""
Pipedrive API client with OAuth support.
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


# Pipedrive API Configuration
PIPEDRIVE_AUTH_URL = "https://oauth.pipedrive.com/oauth/authorize"
PIPEDRIVE_TOKEN_URL = "https://oauth.pipedrive.com/oauth/token"
PIPEDRIVE_API_BASE = "https://api.pipedrive.com/v1"


class PipedriveClient:
    """
    Pipedrive API client with OAuth 2.0 support.

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
        self._api_domain: Optional[str] = None

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
        Generate Pipedrive OAuth authorization URL.

        Args:
            redirect_uri: OAuth callback URL
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL to redirect user to
        """
        if state is None:
            state = secrets.token_urlsafe(32)

        params = {
            "client_id": settings.pipedrive_client_id,
            "redirect_uri": redirect_uri,
            "state": state,
        }

        return f"{PIPEDRIVE_AUTH_URL}?{urlencode(params)}"

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
                PIPEDRIVE_TOKEN_URL,
                data={
                    "grant_type": "authorization_code",
                    "client_id": settings.pipedrive_client_id,
                    "client_secret": settings.pipedrive_client_secret,
                    "redirect_uri": redirect_uri,
                    "code": code,
                },
            )

            if response.status_code != 200:
                logger.error(
                    "pipedrive_token_exchange_failed",
                    status=response.status_code,
                    response=response.text,
                )
                raise ValueError(f"Pipedrive token exchange failed: {response.text}")

            data = response.json()

        # Get or create connection
        connection = await self._get_or_create_connection()

        # Encrypt and store tokens
        connection.access_token_enc = encrypt_pii(data["access_token"])
        connection.refresh_token_enc = encrypt_pii(data["refresh_token"])
        connection.token_expires_at = datetime.now(UTC) + timedelta(seconds=data["expires_in"])
        connection.status = CRMConnectionStatus.CONNECTED

        # Store API domain for this account
        self._api_domain = data.get("api_domain", "api.pipedrive.com")
        connection.provider_metadata = {"api_domain": self._api_domain}

        # Get company info
        company_info = await self._get_company_info(data["access_token"], self._api_domain)
        if company_info:
            connection.provider_account_id = str(company_info.get("id", ""))
            connection.provider_account_name = company_info.get("name", "Pipedrive")

        await self.db.commit()
        await self.db.refresh(connection)

        logger.info(
            "pipedrive_connected",
            tenant_id=self.tenant_id,
            company_id=connection.provider_account_id,
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
                PIPEDRIVE_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "client_id": settings.pipedrive_client_id,
                    "client_secret": settings.pipedrive_client_secret,
                    "refresh_token": refresh_token,
                },
            )

            if response.status_code != 200:
                logger.error(
                    "pipedrive_token_refresh_failed",
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

        logger.info("pipedrive_tokens_refreshed", tenant_id=self.tenant_id)
        return True

    async def disconnect(self) -> bool:
        """
        Disconnect Pipedrive integration.
        Revokes tokens and marks connection as revoked.
        """
        connection = await self._get_connection()
        if not connection:
            return False

        # Clear tokens and mark as revoked
        connection.access_token_enc = None
        connection.refresh_token_enc = None
        connection.token_expires_at = None
        connection.status = CRMConnectionStatus.REVOKED

        await self.db.commit()

        logger.info("pipedrive_disconnected", tenant_id=self.tenant_id)
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

    async def _get_api_domain(self) -> str:
        """Get API domain for this account."""
        if self._api_domain:
            return self._api_domain

        connection = await self._get_connection()
        if connection and connection.provider_metadata:
            self._api_domain = connection.provider_metadata.get("api_domain", "api.pipedrive.com")
        else:
            self._api_domain = "api.pipedrive.com"

        return self._api_domain

    async def api_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[dict] = None,
        json_data: Optional[dict] = None,
    ) -> Optional[dict[str, Any]]:
        """
        Make authenticated API request to Pipedrive.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path (e.g., "/persons")
            params: Optional query parameters
            json_data: Optional JSON body

        Returns:
            Response JSON or None on error
        """
        access_token = await self.get_access_token()
        if not access_token:
            logger.error("pipedrive_api_no_token", tenant_id=self.tenant_id)
            return None

        api_domain = await self._get_api_domain()
        url = f"https://{api_domain}/v1{endpoint}"
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
                    "pipedrive_api_error",
                    status=response.status_code,
                    endpoint=endpoint,
                    response=response.text[:500],
                )
                return None

            return response.json() if response.text else {}

        except Exception as e:
            logger.error("pipedrive_api_exception", error=str(e), endpoint=endpoint)
            return None

        finally:
            if should_close:
                await client.aclose()

    # =========================================================================
    # Person (Contact) Operations
    # =========================================================================

    async def get_persons(
        self,
        limit: int = 100,
        start: int = 0,
        updated_since: Optional[datetime] = None,
    ) -> Optional[dict[str, Any]]:
        """
        Get persons (contacts) from Pipedrive.

        Args:
            limit: Number of persons per page (max 500)
            start: Pagination offset
            updated_since: Filter by update time

        Returns:
            Pipedrive persons response with pagination
        """
        params = {
            "limit": min(limit, 500),
            "start": start,
        }

        if updated_since:
            params["filter_id"] = None  # Would need filter API
            params["since_timestamp"] = updated_since.isoformat()

        return await self.api_request("GET", "/persons", params=params)

    async def get_person(self, person_id: int) -> Optional[dict[str, Any]]:
        """Get a single person by ID."""
        return await self.api_request("GET", f"/persons/{person_id}")

    async def search_persons(
        self,
        term: str,
        fields: Optional[list[str]] = None,
        limit: int = 100,
    ) -> Optional[dict[str, Any]]:
        """
        Search persons.

        Args:
            term: Search term
            fields: Fields to search in (email, phone, name)
            limit: Max results
        """
        params = {
            "term": term,
            "limit": min(limit, 500),
            "item_types": "person",
        }

        if fields:
            params["fields"] = ",".join(fields)

        return await self.api_request("GET", "/itemSearch", params=params)

    async def update_person(self, person_id: int, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Update person properties (for writeback)."""
        return await self.api_request("PUT", f"/persons/{person_id}", json_data=data)

    async def create_person(self, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Create a new person."""
        return await self.api_request("POST", "/persons", json_data=data)

    # =========================================================================
    # Deal Operations
    # =========================================================================

    async def get_deals(
        self,
        limit: int = 100,
        start: int = 0,
        status: str = "all_not_deleted",
        updated_since: Optional[datetime] = None,
    ) -> Optional[dict[str, Any]]:
        """
        Get deals from Pipedrive.

        Args:
            limit: Number of deals per page (max 500)
            start: Pagination offset
            status: Deal status filter
            updated_since: Filter by update time
        """
        params = {
            "limit": min(limit, 500),
            "start": start,
            "status": status,
        }

        if updated_since:
            params["since_timestamp"] = updated_since.isoformat()

        return await self.api_request("GET", "/deals", params=params)

    async def get_deal(self, deal_id: int) -> Optional[dict[str, Any]]:
        """Get a single deal by ID."""
        return await self.api_request("GET", f"/deals/{deal_id}")

    async def update_deal(self, deal_id: int, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Update deal properties (for writeback)."""
        return await self.api_request("PUT", f"/deals/{deal_id}", json_data=data)

    async def get_deal_persons(self, deal_id: int) -> Optional[dict[str, Any]]:
        """Get persons associated with a deal."""
        return await self.api_request("GET", f"/deals/{deal_id}/persons")

    # =========================================================================
    # Organization Operations
    # =========================================================================

    async def get_organizations(
        self,
        limit: int = 100,
        start: int = 0,
    ) -> Optional[dict[str, Any]]:
        """Get organizations (companies)."""
        params = {
            "limit": min(limit, 500),
            "start": start,
        }
        return await self.api_request("GET", "/organizations", params=params)

    async def get_organization(self, org_id: int) -> Optional[dict[str, Any]]:
        """Get a single organization by ID."""
        return await self.api_request("GET", f"/organizations/{org_id}")

    # =========================================================================
    # Pipeline & Stage Operations
    # =========================================================================

    async def get_pipelines(self) -> Optional[dict[str, Any]]:
        """Get all pipelines."""
        return await self.api_request("GET", "/pipelines")

    async def get_stages(self, pipeline_id: Optional[int] = None) -> Optional[dict[str, Any]]:
        """Get pipeline stages."""
        params = {}
        if pipeline_id:
            params["pipeline_id"] = pipeline_id
        return await self.api_request("GET", "/stages", params=params)

    # =========================================================================
    # Activity Operations
    # =========================================================================

    async def get_activities(
        self,
        limit: int = 100,
        start: int = 0,
        done: Optional[bool] = None,
    ) -> Optional[dict[str, Any]]:
        """Get activities."""
        params = {
            "limit": min(limit, 500),
            "start": start,
        }
        if done is not None:
            params["done"] = 1 if done else 0

        return await self.api_request("GET", "/activities", params=params)

    async def create_activity(self, data: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Create a new activity."""
        return await self.api_request("POST", "/activities", json_data=data)

    # =========================================================================
    # Notes Operations
    # =========================================================================

    async def add_note(
        self,
        content: str,
        person_id: Optional[int] = None,
        deal_id: Optional[int] = None,
        org_id: Optional[int] = None,
    ) -> Optional[dict[str, Any]]:
        """Add a note to a person, deal, or organization."""
        data = {"content": content}
        if person_id:
            data["person_id"] = person_id
        if deal_id:
            data["deal_id"] = deal_id
        if org_id:
            data["org_id"] = org_id

        return await self.api_request("POST", "/notes", json_data=data)

    # =========================================================================
    # Custom Fields
    # =========================================================================

    async def get_person_fields(self) -> Optional[dict[str, Any]]:
        """Get all person custom fields."""
        return await self.api_request("GET", "/personFields")

    async def get_deal_fields(self) -> Optional[dict[str, Any]]:
        """Get all deal custom fields."""
        return await self.api_request("GET", "/dealFields")

    async def create_person_field(
        self,
        name: str,
        field_type: str = "varchar",
        options: Optional[list[dict]] = None,
    ) -> Optional[dict[str, Any]]:
        """
        Create a custom person field.

        Args:
            name: Field name
            field_type: varchar, text, double, monetary, date, set, enum, etc.
            options: For set/enum types, list of options
        """
        data = {
            "name": name,
            "field_type": field_type,
        }
        if options:
            data["options"] = options

        return await self.api_request("POST", "/personFields", json_data=data)

    async def create_deal_field(
        self,
        name: str,
        field_type: str = "varchar",
        options: Optional[list[dict]] = None,
    ) -> Optional[dict[str, Any]]:
        """Create a custom deal field."""
        data = {
            "name": name,
            "field_type": field_type,
        }
        if options:
            data["options"] = options

        return await self.api_request("POST", "/dealFields", json_data=data)

    # =========================================================================
    # Users
    # =========================================================================

    async def get_users(self) -> Optional[dict[str, Any]]:
        """Get all users in the account."""
        return await self.api_request("GET", "/users")

    async def get_current_user(self) -> Optional[dict[str, Any]]:
        """Get current authenticated user."""
        return await self.api_request("GET", "/users/me")

    # =========================================================================
    # Webhooks
    # =========================================================================

    async def get_webhooks(self) -> Optional[dict[str, Any]]:
        """Get all webhooks."""
        return await self.api_request("GET", "/webhooks")

    async def create_webhook(
        self,
        subscription_url: str,
        event_action: str,
        event_object: str,
    ) -> Optional[dict[str, Any]]:
        """
        Create a webhook subscription.

        Args:
            subscription_url: URL to receive webhook events
            event_action: added, updated, deleted, merged, etc.
            event_object: deal, person, organization, activity, etc.
        """
        return await self.api_request(
            "POST",
            "/webhooks",
            json_data={
                "subscription_url": subscription_url,
                "event_action": event_action,
                "event_object": event_object,
            },
        )

    async def delete_webhook(self, webhook_id: int) -> Optional[dict[str, Any]]:
        """Delete a webhook subscription."""
        return await self.api_request("DELETE", f"/webhooks/{webhook_id}")

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _get_connection(self) -> Optional[CRMConnection]:
        """Get existing Pipedrive connection for tenant."""
        if self._connection:
            return self._connection

        result = await self.db.execute(
            select(CRMConnection).where(
                CRMConnection.tenant_id == self.tenant_id,
                CRMConnection.provider == CRMProvider.PIPEDRIVE,
            )
        )
        self._connection = result.scalar_one_or_none()
        return self._connection

    async def _get_or_create_connection(self) -> CRMConnection:
        """Get or create Pipedrive connection for tenant."""
        connection = await self._get_connection()
        if connection:
            return connection

        connection = CRMConnection(
            tenant_id=self.tenant_id,
            provider=CRMProvider.PIPEDRIVE,
            status=CRMConnectionStatus.PENDING,
            webhook_secret=secrets.token_urlsafe(32),
        )
        self.db.add(connection)
        await self.db.flush()
        self._connection = connection
        return connection

    async def _get_company_info(self, access_token: str, api_domain: str) -> Optional[dict]:
        """Get Pipedrive company info."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://{api_domain}/v1/users/me",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("success") and data.get("data"):
                    user = data["data"]
                    return {
                        "id": user.get("company_id"),
                        "name": user.get("company_name"),
                    }
        return None

    async def get_connection_status(self) -> dict[str, Any]:
        """Get current connection status."""
        connection = await self._get_connection()
        if not connection:
            return {
                "connected": False,
                "status": "not_configured",
                "provider": "pipedrive",
            }

        return {
            "connected": connection.status == CRMConnectionStatus.CONNECTED,
            "status": connection.status.value,
            "provider": "pipedrive",
            "account_id": connection.provider_account_id,
            "account_name": connection.provider_account_name,
            "last_sync_at": connection.last_sync_at.isoformat()
            if connection.last_sync_at
            else None,
            "last_sync_status": connection.last_sync_status,
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
