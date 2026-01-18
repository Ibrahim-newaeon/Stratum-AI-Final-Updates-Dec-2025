# =============================================================================
# Stratum AI - Zoho CRM Client
# =============================================================================
"""
Zoho CRM API client with OAuth support.
Handles authentication, token refresh, and API calls.

Zoho CRM API v3 Reference:
- Auth: https://www.zoho.com/crm/developer/docs/api/v3/oauth-overview.html
- Contacts: https://www.zoho.com/crm/developer/docs/api/v3/get-records.html
- Deals: https://www.zoho.com/crm/developer/docs/api/v3/get-records.html
"""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.core.security import encrypt_pii, decrypt_pii
from app.models.crm import (
    CRMConnection,
    CRMConnectionStatus,
    CRMProvider,
)

logger = get_logger(__name__)


# Zoho API Configuration
# Note: Zoho has region-specific domains (US, EU, IN, AU, JP, CN)
ZOHO_AUTH_URL = "https://accounts.zoho.com/oauth/v2/auth"
ZOHO_TOKEN_URL = "https://accounts.zoho.com/oauth/v2/token"
ZOHO_API_BASE = "https://www.zohoapis.com/crm/v3"
ZOHO_REVOKE_URL = "https://accounts.zoho.com/oauth/v2/token/revoke"

# Required scopes for Stratum AI integration
ZOHO_SCOPES = [
    "ZohoCRM.modules.contacts.READ",
    "ZohoCRM.modules.contacts.WRITE",
    "ZohoCRM.modules.deals.READ",
    "ZohoCRM.modules.deals.WRITE",
    "ZohoCRM.modules.accounts.READ",
    "ZohoCRM.modules.leads.READ",
    "ZohoCRM.users.READ",
    "ZohoCRM.org.READ",
    "ZohoCRM.settings.READ",
]

# Zoho field mapping to internal schema
ZOHO_CONTACT_FIELD_MAP = {
    "Email": "email",
    "First_Name": "first_name",
    "Last_Name": "last_name",
    "Phone": "phone",
    "Mobile": "mobile",
    "Account_Name": "company",
    "Lead_Source": "lead_source",
    "Owner": "owner",
    "Created_Time": "created_at",
    "Modified_Time": "updated_at",
}

ZOHO_DEAL_FIELD_MAP = {
    "Deal_Name": "deal_name",
    "Amount": "amount",
    "Stage": "stage",
    "Closing_Date": "close_date",
    "Pipeline": "pipeline",
    "Account_Name": "account",
    "Contact_Name": "contact",
    "Owner": "owner",
    "Created_Time": "created_at",
    "Modified_Time": "updated_at",
}


class ZohoClient:
    """
    Zoho CRM API client with OAuth 2.0 support.

    Features:
    - OAuth authorization flow with offline_access
    - Automatic token refresh
    - Encrypted token storage
    - Rate limiting awareness
    - Multi-region support
    """

    def __init__(self, db: AsyncSession, tenant_id: int, region: str = "com"):
        """
        Initialize Zoho client.

        Args:
            db: Database session
            tenant_id: Tenant ID
            region: Zoho region domain (com, eu, in, com.au, jp, com.cn)
        """
        self.db = db
        self.tenant_id = tenant_id
        self.region = region
        self._connection: Optional[CRMConnection] = None
        self._http_client: Optional[httpx.AsyncClient] = None

        # Set region-specific URLs
        self._set_region_urls(region)

    def _set_region_urls(self, region: str) -> None:
        """Set API URLs based on region."""
        self.auth_url = f"https://accounts.zoho.{region}/oauth/v2/auth"
        self.token_url = f"https://accounts.zoho.{region}/oauth/v2/token"
        self.api_base = f"https://www.zohoapis.{region}/crm/v3"
        self.revoke_url = f"https://accounts.zoho.{region}/oauth/v2/token/revoke"

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
        Generate Zoho OAuth authorization URL.

        Args:
            redirect_uri: OAuth callback URL
            state: Optional state parameter for CSRF protection

        Returns:
            Authorization URL to redirect user to
        """
        if state is None:
            state = secrets.token_urlsafe(32)

        params = {
            "client_id": settings.zoho_client_id,
            "redirect_uri": redirect_uri,
            "scope": ",".join(ZOHO_SCOPES),
            "state": state,
            "response_type": "code",
            "access_type": "offline",  # Required for refresh token
            "prompt": "consent",  # Force consent to get refresh token
        }

        return f"{self.auth_url}?{urlencode(params)}"

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
                self.token_url,
                data={
                    "grant_type": "authorization_code",
                    "client_id": settings.zoho_client_id,
                    "client_secret": settings.zoho_client_secret,
                    "redirect_uri": redirect_uri,
                    "code": code,
                },
            )

            if response.status_code != 200:
                logger.error(
                    "zoho_token_exchange_failed",
                    status=response.status_code,
                    response=response.text,
                )
                raise ValueError(f"Zoho token exchange failed: {response.text}")

            data = response.json()

            # Check for errors in response
            if "error" in data:
                raise ValueError(f"Zoho OAuth error: {data.get('error')}")

        # Get or create connection
        connection = await self._get_or_create_connection()

        # Encrypt and store tokens
        connection.access_token_enc = encrypt_pii(data["access_token"])
        if "refresh_token" in data:
            connection.refresh_token_enc = encrypt_pii(data["refresh_token"])

        # Zoho tokens expire in 1 hour by default
        expires_in = data.get("expires_in", 3600)
        connection.token_expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=expires_in
        )
        connection.scopes = ",".join(ZOHO_SCOPES)
        connection.status = CRMConnectionStatus.CONNECTED

        # Get organization info
        org_info = await self._get_org_info(data["access_token"])
        if org_info:
            connection.provider_account_id = str(org_info.get("id", ""))
            connection.provider_account_name = org_info.get("company_name", "Zoho CRM")

        await self.db.commit()
        await self.db.refresh(connection)

        logger.info(
            "zoho_connected",
            tenant_id=self.tenant_id,
            org_id=connection.provider_account_id,
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
                self.token_url,
                data={
                    "grant_type": "refresh_token",
                    "client_id": settings.zoho_client_id,
                    "client_secret": settings.zoho_client_secret,
                    "refresh_token": refresh_token,
                },
            )

            if response.status_code != 200:
                logger.error(
                    "zoho_token_refresh_failed",
                    status=response.status_code,
                    tenant_id=self.tenant_id,
                )
                connection.status = CRMConnectionStatus.EXPIRED
                await self.db.commit()
                return False

            data = response.json()

            if "error" in data:
                logger.error(
                    "zoho_token_refresh_error",
                    error=data.get("error"),
                    tenant_id=self.tenant_id,
                )
                connection.status = CRMConnectionStatus.EXPIRED
                await self.db.commit()
                return False

        # Update access token (Zoho doesn't return new refresh token on refresh)
        connection.access_token_enc = encrypt_pii(data["access_token"])
        expires_in = data.get("expires_in", 3600)
        connection.token_expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=expires_in
        )
        connection.status = CRMConnectionStatus.CONNECTED

        await self.db.commit()

        logger.info("zoho_tokens_refreshed", tenant_id=self.tenant_id)
        return True

    async def disconnect(self) -> bool:
        """
        Disconnect Zoho integration.
        Revokes tokens and marks connection as revoked.
        """
        connection = await self._get_connection()
        if not connection:
            return False

        # Revoke token (best effort)
        if connection.refresh_token_enc:
            try:
                refresh_token = decrypt_pii(connection.refresh_token_enc)
                async with httpx.AsyncClient() as client:
                    await client.post(
                        self.revoke_url,
                        data={"token": refresh_token},
                    )
            except Exception as e:
                logger.warning("zoho_token_revoke_failed", error=str(e))

        # Clear tokens and mark as revoked
        connection.access_token_enc = None
        connection.refresh_token_enc = None
        connection.token_expires_at = None
        connection.status = CRMConnectionStatus.REVOKED

        await self.db.commit()

        logger.info("zoho_disconnected", tenant_id=self.tenant_id)
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
            if datetime.now(timezone.utc) >= connection.token_expires_at - buffer:
                if not await self.refresh_tokens():
                    return None
                await self.db.refresh(connection)

        return decrypt_pii(connection.access_token_enc) if connection.access_token_enc else None

    async def api_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Make authenticated API request to Zoho CRM.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint path (e.g., "/Contacts")
            params: Optional query parameters
            json_data: Optional JSON body

        Returns:
            Response JSON or None on error
        """
        access_token = await self.get_access_token()
        if not access_token:
            logger.error("zoho_api_no_token", tenant_id=self.tenant_id)
            return None

        url = f"{self.api_base}{endpoint}"
        headers = {
            "Authorization": f"Zoho-oauthtoken {access_token}",
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
                    "zoho_api_error",
                    status=response.status_code,
                    endpoint=endpoint,
                    response=response.text[:500],
                )
                return None

            return response.json() if response.text else {}

        except Exception as e:
            logger.error("zoho_api_exception", error=str(e), endpoint=endpoint)
            return None

        finally:
            if should_close:
                await client.aclose()

    # =========================================================================
    # Contact Operations
    # =========================================================================

    async def get_contacts(
        self,
        page: int = 1,
        per_page: int = 200,
        fields: Optional[List[str]] = None,
        modified_since: Optional[datetime] = None,
        sort_by: str = "Modified_Time",
        sort_order: str = "desc",
    ) -> Optional[Dict[str, Any]]:
        """
        Get contacts from Zoho CRM.

        Args:
            page: Page number (1-based)
            per_page: Records per page (max 200)
            fields: List of fields to include
            modified_since: Filter by last modified date
            sort_by: Field to sort by
            sort_order: asc or desc

        Returns:
            Zoho contacts response with data and info
        """
        if fields is None:
            fields = [
                "Email", "Phone", "Mobile", "First_Name", "Last_Name",
                "Account_Name", "Lead_Source", "Owner",
                "Created_Time", "Modified_Time",
                # UTM and tracking fields (if custom fields exist)
                "utm_source", "utm_medium", "utm_campaign",
                "gclid", "fbclid",
            ]

        params = {
            "page": page,
            "per_page": min(per_page, 200),
            "fields": ",".join(fields),
            "sort_by": sort_by,
            "sort_order": sort_order,
        }

        # Use COQL for filtering by modified date
        if modified_since:
            return await self.search_contacts(
                criteria=f"Modified_Time:greater_than:{modified_since.strftime('%Y-%m-%dT%H:%M:%S+00:00')}",
                fields=fields,
                page=page,
                per_page=per_page,
            )

        return await self.api_request("GET", "/Contacts", params=params)

    async def search_contacts(
        self,
        criteria: str,
        fields: Optional[List[str]] = None,
        page: int = 1,
        per_page: int = 200,
    ) -> Optional[Dict[str, Any]]:
        """
        Search contacts using COQL (Zoho CRM Object Query Language).

        Args:
            criteria: COQL criteria string
            fields: Fields to return
            page: Page number
            per_page: Records per page

        Returns:
            Search results
        """
        if fields is None:
            fields = ["Email", "Phone", "First_Name", "Last_Name", "Account_Name"]

        body = {
            "select_query": f"select {','.join(fields)} from Contacts where {criteria} limit {per_page} offset {(page - 1) * per_page}"
        }

        return await self.api_request("POST", "/coql", json_data=body)

    async def get_contact(
        self,
        contact_id: str,
        fields: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get a single contact by ID."""
        params = {}
        if fields:
            params["fields"] = ",".join(fields)

        return await self.api_request("GET", f"/Contacts/{contact_id}", params=params)

    async def update_contact(
        self,
        contact_id: str,
        data: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Update contact fields (for writeback)."""
        body = {
            "data": [{"id": contact_id, **data}]
        }
        return await self.api_request("PUT", "/Contacts", json_data=body)

    async def search_contacts_by_email(
        self,
        email: str,
    ) -> Optional[Dict[str, Any]]:
        """Search for a contact by email."""
        return await self.api_request(
            "GET",
            "/Contacts/search",
            params={"email": email},
        )

    # =========================================================================
    # Deal Operations
    # =========================================================================

    async def get_deals(
        self,
        page: int = 1,
        per_page: int = 200,
        fields: Optional[List[str]] = None,
        modified_since: Optional[datetime] = None,
        sort_by: str = "Modified_Time",
        sort_order: str = "desc",
    ) -> Optional[Dict[str, Any]]:
        """
        Get deals from Zoho CRM.

        Args:
            page: Page number (1-based)
            per_page: Records per page (max 200)
            fields: List of fields to include
            modified_since: Filter by last modified date
            sort_by: Field to sort by
            sort_order: asc or desc

        Returns:
            Zoho deals response
        """
        if fields is None:
            fields = [
                "Deal_Name", "Amount", "Stage", "Pipeline",
                "Closing_Date", "Account_Name", "Contact_Name",
                "Owner", "Created_Time", "Modified_Time",
            ]

        params = {
            "page": page,
            "per_page": min(per_page, 200),
            "fields": ",".join(fields),
            "sort_by": sort_by,
            "sort_order": sort_order,
        }

        if modified_since:
            return await self.search_deals(
                criteria=f"Modified_Time:greater_than:{modified_since.strftime('%Y-%m-%dT%H:%M:%S+00:00')}",
                fields=fields,
                page=page,
                per_page=per_page,
            )

        return await self.api_request("GET", "/Deals", params=params)

    async def search_deals(
        self,
        criteria: str,
        fields: Optional[List[str]] = None,
        page: int = 1,
        per_page: int = 200,
    ) -> Optional[Dict[str, Any]]:
        """Search deals using COQL."""
        if fields is None:
            fields = ["Deal_Name", "Amount", "Stage", "Closing_Date"]

        body = {
            "select_query": f"select {','.join(fields)} from Deals where {criteria} limit {per_page} offset {(page - 1) * per_page}"
        }

        return await self.api_request("POST", "/coql", json_data=body)

    async def get_deal(
        self,
        deal_id: str,
        fields: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get a single deal by ID."""
        params = {}
        if fields:
            params["fields"] = ",".join(fields)

        return await self.api_request("GET", f"/Deals/{deal_id}", params=params)

    async def update_deal(
        self,
        deal_id: str,
        data: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Update deal fields (for writeback)."""
        body = {
            "data": [{"id": deal_id, **data}]
        }
        return await self.api_request("PUT", "/Deals", json_data=body)

    async def get_deal_contacts(
        self,
        deal_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Get contacts associated with a deal."""
        return await self.api_request(
            "GET",
            f"/Deals/{deal_id}/Contacts",
        )

    # =========================================================================
    # Account Operations
    # =========================================================================

    async def get_accounts(
        self,
        page: int = 1,
        per_page: int = 200,
        fields: Optional[List[str]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get accounts (companies) from Zoho CRM."""
        if fields is None:
            fields = [
                "Account_Name", "Website", "Phone", "Industry",
                "Annual_Revenue", "Owner", "Created_Time", "Modified_Time",
            ]

        params = {
            "page": page,
            "per_page": min(per_page, 200),
            "fields": ",".join(fields),
        }

        return await self.api_request("GET", "/Accounts", params=params)

    # =========================================================================
    # Lead Operations
    # =========================================================================

    async def get_leads(
        self,
        page: int = 1,
        per_page: int = 200,
        fields: Optional[List[str]] = None,
        modified_since: Optional[datetime] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get leads from Zoho CRM."""
        if fields is None:
            fields = [
                "Email", "Phone", "First_Name", "Last_Name",
                "Company", "Lead_Source", "Lead_Status",
                "Owner", "Created_Time", "Modified_Time",
            ]

        params = {
            "page": page,
            "per_page": min(per_page, 200),
            "fields": ",".join(fields),
        }

        if modified_since:
            params["modified_since"] = modified_since.strftime("%Y-%m-%dT%H:%M:%S+00:00")

        return await self.api_request("GET", "/Leads", params=params)

    # =========================================================================
    # Batch Operations (for Writeback)
    # =========================================================================

    async def batch_update_contacts(
        self,
        updates: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        Batch update multiple contacts.

        Args:
            updates: List of contact updates with "id" and fields

        Returns:
            Batch response with results
        """
        if not updates:
            return {"data": [], "status": "success"}

        # Zoho batch limit is 100
        results = []
        errors = []

        for i in range(0, len(updates), 100):
            batch = updates[i:i + 100]
            response = await self.api_request(
                "PUT",
                "/Contacts",
                json_data={"data": batch},
            )

            if response and "data" in response:
                results.extend(response.get("data", []))
            else:
                errors.append({"message": f"Batch {i // 100 + 1} failed"})

        return {"data": results, "errors": errors}

    async def batch_update_deals(
        self,
        updates: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        Batch update multiple deals.

        Args:
            updates: List of deal updates with "id" and fields

        Returns:
            Batch response with results
        """
        if not updates:
            return {"data": [], "status": "success"}

        results = []
        errors = []

        for i in range(0, len(updates), 100):
            batch = updates[i:i + 100]
            response = await self.api_request(
                "PUT",
                "/Deals",
                json_data={"data": batch},
            )

            if response and "data" in response:
                results.extend(response.get("data", []))
            else:
                errors.append({"message": f"Batch {i // 100 + 1} failed"})

        return {"data": results, "errors": errors}

    # =========================================================================
    # Custom Fields (for Writeback)
    # =========================================================================

    async def get_module_fields(
        self,
        module: str = "Contacts",
    ) -> Optional[Dict[str, Any]]:
        """Get all fields for a module (schema)."""
        return await self.api_request("GET", f"/settings/fields", params={"module": module})

    async def create_custom_field(
        self,
        module: str,
        field_label: str,
        field_type: str = "text",
        length: int = 255,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a custom field.

        Note: Zoho custom field creation via API requires Enterprise edition.
        For other editions, fields must be created manually in Zoho CRM settings.
        """
        body = {
            "fields": [{
                "field_label": field_label,
                "data_type": field_type,
                "length": length,
            }]
        }
        return await self.api_request(
            "POST",
            f"/settings/fields",
            params={"module": module},
            json_data=body,
        )

    # =========================================================================
    # Users and Organization
    # =========================================================================

    async def get_users(self) -> Optional[Dict[str, Any]]:
        """Get all users (sales reps) in the organization."""
        return await self.api_request("GET", "/users")

    async def get_organization(self) -> Optional[Dict[str, Any]]:
        """Get organization details."""
        return await self.api_request("GET", "/org")

    async def get_pipelines(self) -> Optional[Dict[str, Any]]:
        """Get deal pipelines and stages."""
        return await self.api_request(
            "GET",
            "/settings/pipeline",
            params={"module": "Deals"},
        )

    # =========================================================================
    # Helper Methods
    # =========================================================================

    async def _get_connection(self) -> Optional[CRMConnection]:
        """Get existing Zoho connection for tenant."""
        if self._connection:
            return self._connection

        result = await self.db.execute(
            select(CRMConnection).where(
                CRMConnection.tenant_id == self.tenant_id,
                CRMConnection.provider == CRMProvider.ZOHO,
            )
        )
        self._connection = result.scalar_one_or_none()
        return self._connection

    async def _get_or_create_connection(self) -> CRMConnection:
        """Get or create Zoho connection for tenant."""
        connection = await self._get_connection()
        if connection:
            return connection

        connection = CRMConnection(
            tenant_id=self.tenant_id,
            provider=CRMProvider.ZOHO,
            status=CRMConnectionStatus.PENDING,
            webhook_secret=secrets.token_urlsafe(32),
        )
        self.db.add(connection)
        await self.db.flush()
        self._connection = connection
        return connection

    async def _get_org_info(self, access_token: str) -> Optional[Dict]:
        """Get Zoho organization info."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.api_base}/org",
                headers={"Authorization": f"Zoho-oauthtoken {access_token}"},
            )
            if response.status_code == 200:
                data = response.json()
                if "org" in data and len(data["org"]) > 0:
                    return data["org"][0]
        return None

    async def get_connection_status(self) -> Dict[str, Any]:
        """Get current connection status."""
        connection = await self._get_connection()
        if not connection:
            return {
                "connected": False,
                "status": "not_configured",
                "provider": "zoho",
            }

        return {
            "connected": connection.status == CRMConnectionStatus.CONNECTED,
            "status": connection.status.value,
            "provider": "zoho",
            "account_id": connection.provider_account_id,
            "account_name": connection.provider_account_name,
            "last_sync_at": connection.last_sync_at.isoformat() if connection.last_sync_at else None,
            "last_sync_status": connection.last_sync_status,
            "scopes": connection.scopes.split(",") if connection.scopes else [],
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


def normalize_zoho_contact(zoho_contact: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize Zoho contact data to internal schema.

    Args:
        zoho_contact: Raw contact from Zoho API

    Returns:
        Normalized contact dict
    """
    normalized = {
        "zoho_id": zoho_contact.get("id"),
    }

    for zoho_field, internal_field in ZOHO_CONTACT_FIELD_MAP.items():
        if zoho_field in zoho_contact:
            value = zoho_contact[zoho_field]
            # Handle nested objects (like Owner, Account_Name)
            if isinstance(value, dict):
                value = value.get("name") or value.get("id")
            normalized[internal_field] = value

    return normalized


def normalize_zoho_deal(zoho_deal: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize Zoho deal data to internal schema.

    Args:
        zoho_deal: Raw deal from Zoho API

    Returns:
        Normalized deal dict
    """
    normalized = {
        "zoho_id": zoho_deal.get("id"),
    }

    for zoho_field, internal_field in ZOHO_DEAL_FIELD_MAP.items():
        if zoho_field in zoho_deal:
            value = zoho_deal[zoho_field]
            # Handle nested objects
            if isinstance(value, dict):
                value = value.get("name") or value.get("id")
            normalized[internal_field] = value

    return normalized
