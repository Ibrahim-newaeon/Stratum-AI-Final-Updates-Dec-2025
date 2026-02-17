# =============================================================================
# Stratum AI - Salesforce API Client
# =============================================================================
"""
Salesforce REST API client with OAuth 2.0 authentication.

Features:
- OAuth 2.0 Web Server Flow (authorization code)
- Token refresh with automatic retry
- Contact/Lead/Account CRUD operations
- Opportunity management
- Custom field operations
- Bulk API support for large data operations
"""

import hashlib
from datetime import UTC, datetime, timedelta
from typing import Any, Optional
from urllib.parse import urlencode

import aiohttp
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.models.crm import CRMConnection, CRMConnectionStatus, CRMProvider
from app.services.encryption import decrypt_token, encrypt_token

logger = get_logger(__name__)


# =============================================================================
# Constants
# =============================================================================

# Salesforce OAuth endpoints (Production)
SALESFORCE_AUTH_URL = "https://login.salesforce.com/services/oauth2/authorize"
SALESFORCE_TOKEN_URL = "https://login.salesforce.com/services/oauth2/token"
SALESFORCE_REVOKE_URL = "https://login.salesforce.com/services/oauth2/revoke"

# Sandbox endpoints
SANDBOX_AUTH_URL = "https://test.salesforce.com/services/oauth2/authorize"
SANDBOX_TOKEN_URL = "https://test.salesforce.com/services/oauth2/token"

# API version
API_VERSION = "v59.0"

# Default scopes
DEFAULT_SCOPES = [
    "api",
    "refresh_token",
    "offline_access",
]


def _escape_soql(value: str) -> str:
    """Escape a string value for safe use in SOQL queries.

    Prevents SOQL injection by escaping special characters.
    See: https://developer.salesforce.com/docs/atlas.en-us.soql_sosl.meta/soql_sosl/sforce_api_calls_soql_select_quotedstringescapes.htm
    """
    import re

    return re.sub(r"([\\'\"\n\r\t])", r"\\\1", value)


def hash_email(email: str) -> str:
    """Hash email for identity matching."""
    return hashlib.sha256(email.lower().strip().encode()).hexdigest()


def hash_phone(phone: str) -> str:
    """Hash phone for identity matching."""
    import re

    normalized = re.sub(r"\D", "", phone)
    return hashlib.sha256(normalized.encode()).hexdigest()


# =============================================================================
# Salesforce Client
# =============================================================================


class SalesforceClient:
    """
    Salesforce REST API client.

    Handles OAuth authentication and provides methods for
    interacting with Salesforce CRM data.
    """

    def __init__(
        self,
        db: AsyncSession,
        tenant_id: int,
        is_sandbox: bool = False,
    ):
        self.db = db
        self.tenant_id = tenant_id
        self.is_sandbox = is_sandbox
        self._session: Optional[aiohttp.ClientSession] = None
        self._connection: Optional[CRMConnection] = None
        self._instance_url: Optional[str] = None

    async def __aenter__(self):
        """Async context manager entry."""
        self._session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self._session:
            await self._session.close()
            self._session = None

    @property
    def auth_url(self) -> str:
        """Get appropriate auth URL based on sandbox setting."""
        return SANDBOX_AUTH_URL if self.is_sandbox else SALESFORCE_AUTH_URL

    @property
    def token_url(self) -> str:
        """Get appropriate token URL based on sandbox setting."""
        return SANDBOX_TOKEN_URL if self.is_sandbox else SALESFORCE_TOKEN_URL

    # =========================================================================
    # Connection Management
    # =========================================================================

    async def _get_connection(self) -> Optional[CRMConnection]:
        """Get existing Salesforce connection for tenant."""
        if self._connection:
            return self._connection

        result = await self.db.execute(
            select(CRMConnection).where(
                and_(
                    CRMConnection.tenant_id == self.tenant_id,
                    CRMConnection.provider == CRMProvider.SALESFORCE,
                )
            )
        )
        self._connection = result.scalar_one_or_none()
        return self._connection

    async def _get_access_token(self) -> Optional[str]:
        """Get valid access token, refreshing if necessary."""
        connection = await self._get_connection()
        if not connection or not connection.access_token_enc:
            return None

        # Check if token is expired (with 5 min buffer)
        if (
            connection.token_expires_at
            and datetime.now(UTC) >= connection.token_expires_at - timedelta(minutes=5)
        ):
            await self._refresh_token()
            connection = await self._get_connection()

        if not connection or not connection.access_token_enc:
            return None

        return decrypt_token(connection.access_token_enc)

    async def _make_request(
        self,
        method: str,
        endpoint: str,
        data: Optional[dict] = None,
        params: Optional[dict] = None,
        use_instance_url: bool = True,
    ) -> Optional[dict[str, Any]]:
        """Make authenticated request to Salesforce API."""
        access_token = await self._get_access_token()
        if not access_token:
            logger.error("salesforce_no_access_token", tenant_id=self.tenant_id)
            return None

        if not self._session:
            self._session = aiohttp.ClientSession()

        # Get instance URL from connection
        connection = await self._get_connection()
        if use_instance_url:
            if not self._instance_url and connection:
                # Instance URL stored in provider_account_id or raw_properties
                raw_props = connection.raw_properties or {}
                self._instance_url = raw_props.get("instance_url")

            if not self._instance_url:
                logger.error("salesforce_no_instance_url", tenant_id=self.tenant_id)
                return None

            url = f"{self._instance_url}/services/data/{API_VERSION}{endpoint}"
        else:
            url = endpoint

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        try:
            async with self._session.request(
                method,
                url,
                json=data,
                params=params,
                headers=headers,
            ) as response:
                if response.status == 401:
                    # Token expired, try refresh
                    await self._refresh_token()
                    return await self._make_request(method, endpoint, data, params)

                if response.status == 204:
                    return {"success": True}

                response_data = await response.json()

                if response.status >= 400:
                    logger.warning(
                        "salesforce_api_error",
                        status=response.status,
                        response=response_data,
                        endpoint=endpoint,
                    )
                    return {"success": False, "error": response_data}

                return response_data

        except aiohttp.ClientError as e:
            logger.error("salesforce_request_failed", error=str(e), endpoint=endpoint)
            return None

    # =========================================================================
    # OAuth Flow
    # =========================================================================

    def get_authorization_url(
        self,
        redirect_uri: str,
        state: str,
        scopes: Optional[list[str]] = None,
    ) -> str:
        """
        Generate OAuth authorization URL.

        Args:
            redirect_uri: OAuth callback URL
            state: State parameter for CSRF protection
            scopes: OAuth scopes to request

        Returns:
            Authorization URL to redirect user to
        """
        if scopes is None:
            scopes = DEFAULT_SCOPES

        params = {
            "response_type": "code",
            "client_id": settings.salesforce_client_id,
            "redirect_uri": redirect_uri,
            "state": state,
            "scope": " ".join(scopes),
        }

        return f"{self.auth_url}?{urlencode(params)}"

    async def exchange_code_for_tokens(
        self,
        code: str,
        redirect_uri: str,
    ) -> CRMConnection:
        """
        Exchange authorization code for access tokens.

        Args:
            code: Authorization code from OAuth callback
            redirect_uri: Same redirect_uri used in authorization

        Returns:
            CRMConnection with stored tokens
        """
        async with aiohttp.ClientSession() as session:
            data = {
                "grant_type": "authorization_code",
                "client_id": settings.salesforce_client_id,
                "client_secret": settings.salesforce_client_secret,
                "code": code,
                "redirect_uri": redirect_uri,
            }

            async with session.post(
                self.token_url,
                data=data,
            ) as response:
                if response.status != 200:
                    error_data = await response.json()
                    raise Exception(f"Token exchange failed: {error_data}")

                token_data = await response.json()

        # Extract token information
        access_token = token_data["access_token"]
        refresh_token = token_data.get("refresh_token")
        instance_url = token_data["instance_url"]
        issued_at = int(token_data.get("issued_at", 0)) / 1000  # Convert ms to seconds

        # Calculate expiration (Salesforce tokens typically last 2 hours)
        expires_at = datetime.fromtimestamp(issued_at, tz=UTC) + timedelta(hours=2)

        # Get user info for account details
        async with aiohttp.ClientSession() as session:
            headers = {"Authorization": f"Bearer {access_token}"}
            async with session.get(
                f"{instance_url}/services/oauth2/userinfo",
                headers=headers,
            ) as response:
                user_info = await response.json() if response.status == 200 else {}

        # Get or create connection
        connection = await self._get_connection()
        if not connection:
            connection = CRMConnection(
                tenant_id=self.tenant_id,
                provider=CRMProvider.SALESFORCE,
            )
            self.db.add(connection)

        # Update connection
        connection.access_token_enc = encrypt_token(access_token)
        if refresh_token:
            connection.refresh_token_enc = encrypt_token(refresh_token)
        connection.token_expires_at = expires_at
        connection.provider_account_id = user_info.get("organization_id", "")
        connection.provider_account_name = user_info.get(
            "organization_name", user_info.get("name", "")
        )
        connection.scopes = token_data.get("scope", "")
        connection.status = CRMConnectionStatus.CONNECTED
        connection.status_message = None
        connection.raw_properties = {
            "instance_url": instance_url,
            "user_id": user_info.get("user_id"),
            "username": user_info.get("preferred_username"),
            "is_sandbox": self.is_sandbox,
        }

        await self.db.commit()
        await self.db.refresh(connection)

        self._connection = connection
        self._instance_url = instance_url

        logger.info(
            "salesforce_connected",
            tenant_id=self.tenant_id,
            org_id=connection.provider_account_id,
        )

        return connection

    async def _refresh_token(self) -> bool:
        """Refresh expired access token."""
        connection = await self._get_connection()
        if not connection or not connection.refresh_token_enc:
            return False

        refresh_token = decrypt_token(connection.refresh_token_enc)

        async with aiohttp.ClientSession() as session:
            data = {
                "grant_type": "refresh_token",
                "client_id": settings.salesforce_client_id,
                "client_secret": settings.salesforce_client_secret,
                "refresh_token": refresh_token,
            }

            async with session.post(
                self.token_url,
                data=data,
            ) as response:
                if response.status != 200:
                    error_data = await response.json()
                    logger.error(
                        "salesforce_token_refresh_failed",
                        tenant_id=self.tenant_id,
                        error=error_data,
                    )
                    connection.status = CRMConnectionStatus.EXPIRED
                    connection.status_message = "Token refresh failed"
                    await self.db.commit()
                    return False

                token_data = await response.json()

        # Update connection with new token
        connection.access_token_enc = encrypt_token(token_data["access_token"])
        issued_at = int(token_data.get("issued_at", 0)) / 1000
        connection.token_expires_at = datetime.fromtimestamp(issued_at, tz=UTC) + timedelta(hours=2)

        # Update instance URL if provided
        if "instance_url" in token_data:
            raw_props = connection.raw_properties or {}
            raw_props["instance_url"] = token_data["instance_url"]
            connection.raw_properties = raw_props
            self._instance_url = token_data["instance_url"]

        await self.db.commit()
        self._connection = None  # Reset cache

        logger.info("salesforce_token_refreshed", tenant_id=self.tenant_id)
        return True

    async def disconnect(self) -> bool:
        """Disconnect Salesforce integration."""
        connection = await self._get_connection()
        if not connection:
            return False

        # Revoke token if possible
        if connection.access_token_enc:
            try:
                token = decrypt_token(connection.access_token_enc)
                async with aiohttp.ClientSession() as session:
                    await session.post(
                        SALESFORCE_REVOKE_URL,
                        data={"token": token},
                    )
            except Exception as e:
                logger.warning("salesforce_revoke_failed", error=str(e))

        # Delete connection
        await self.db.delete(connection)
        await self.db.commit()

        self._connection = None
        logger.info("salesforce_disconnected", tenant_id=self.tenant_id)
        return True

    async def get_connection_status(self) -> dict[str, Any]:
        """Get current connection status."""
        connection = await self._get_connection()

        if not connection:
            return {
                "connected": False,
                "status": "not_connected",
                "provider": "salesforce",
            }

        return {
            "connected": connection.status == CRMConnectionStatus.CONNECTED,
            "status": connection.status.value,
            "provider": "salesforce",
            "account_id": connection.provider_account_id,
            "account_name": connection.provider_account_name,
            "last_sync_at": connection.last_sync_at.isoformat()
            if connection.last_sync_at
            else None,
            "last_sync_status": connection.last_sync_status,
            "scopes": connection.scopes.split(" ") if connection.scopes else [],
            "is_sandbox": (connection.raw_properties or {}).get("is_sandbox", False),
        }

    # =========================================================================
    # Contact/Lead Operations
    # =========================================================================

    async def get_contacts(
        self,
        limit: int = 100,
        offset: int = 0,
        modified_since: Optional[datetime] = None,
    ) -> Optional[dict[str, Any]]:
        """Get contacts from Salesforce."""
        fields = [
            "Id",
            "FirstName",
            "LastName",
            "Name",
            "Email",
            "Phone",
            "AccountId",
            "OwnerId",
            "LeadSource",
            "CreatedDate",
            "LastModifiedDate",
        ]

        query = f"SELECT {', '.join(fields)} FROM Contact"

        if modified_since:
            modified_str = modified_since.strftime("%Y-%m-%dT%H:%M:%SZ")
            query += f" WHERE LastModifiedDate >= {modified_str}"

        query += f" ORDER BY LastModifiedDate DESC LIMIT {limit} OFFSET {offset}"

        return await self._make_request("GET", "/query", params={"q": query})

    async def get_leads(
        self,
        limit: int = 100,
        offset: int = 0,
        modified_since: Optional[datetime] = None,
    ) -> Optional[dict[str, Any]]:
        """Get leads from Salesforce."""
        fields = [
            "Id",
            "FirstName",
            "LastName",
            "Name",
            "Email",
            "Phone",
            "Company",
            "OwnerId",
            "LeadSource",
            "Status",
            "CreatedDate",
            "LastModifiedDate",
        ]

        query = f"SELECT {', '.join(fields)} FROM Lead"

        if modified_since:
            modified_str = modified_since.strftime("%Y-%m-%dT%H:%M:%SZ")
            query += f" WHERE LastModifiedDate >= {modified_str}"

        query += f" ORDER BY LastModifiedDate DESC LIMIT {limit} OFFSET {offset}"

        return await self._make_request("GET", "/query", params={"q": query})

    async def get_contact(self, contact_id: str) -> Optional[dict[str, Any]]:
        """Get a single contact by ID."""
        return await self._make_request("GET", f"/sobjects/Contact/{contact_id}")

    async def update_contact(
        self,
        contact_id: str,
        properties: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        """Update a contact."""
        return await self._make_request("PATCH", f"/sobjects/Contact/{contact_id}", data=properties)

    async def create_contact(self, properties: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Create a new contact."""
        return await self._make_request("POST", "/sobjects/Contact", data=properties)

    async def search_contacts(self, query: str) -> Optional[dict[str, Any]]:
        """Search contacts by email or name using SOSL."""
        sosl = f"FIND {{{query}}} IN EMAIL FIELDS RETURNING Contact(Id, Name, Email, Phone)"
        return await self._make_request("GET", "/search", params={"q": sosl})

    # =========================================================================
    # Opportunity/Deal Operations
    # =========================================================================

    async def get_opportunities(
        self,
        limit: int = 100,
        offset: int = 0,
        modified_since: Optional[datetime] = None,
    ) -> Optional[dict[str, Any]]:
        """Get opportunities from Salesforce."""
        fields = [
            "Id",
            "Name",
            "Amount",
            "StageName",
            "Probability",
            "CloseDate",
            "AccountId",
            "OwnerId",
            "IsClosed",
            "IsWon",
            "CreatedDate",
            "LastModifiedDate",
            "LeadSource",
        ]

        query = f"SELECT {', '.join(fields)} FROM Opportunity"

        if modified_since:
            modified_str = modified_since.strftime("%Y-%m-%dT%H:%M:%SZ")
            query += f" WHERE LastModifiedDate >= {modified_str}"

        query += f" ORDER BY LastModifiedDate DESC LIMIT {limit} OFFSET {offset}"

        return await self._make_request("GET", "/query", params={"q": query})

    async def get_opportunity(self, opportunity_id: str) -> Optional[dict[str, Any]]:
        """Get a single opportunity by ID."""
        return await self._make_request("GET", f"/sobjects/Opportunity/{opportunity_id}")

    async def update_opportunity(
        self,
        opportunity_id: str,
        properties: dict[str, Any],
    ) -> Optional[dict[str, Any]]:
        """Update an opportunity."""
        return await self._make_request(
            "PATCH", f"/sobjects/Opportunity/{opportunity_id}", data=properties
        )

    async def create_opportunity(self, properties: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Create a new opportunity."""
        return await self._make_request("POST", "/sobjects/Opportunity", data=properties)

    async def get_opportunity_contact_roles(
        self,
        opportunity_id: str,
    ) -> Optional[dict[str, Any]]:
        """Get contact roles for an opportunity."""
        safe_id = _escape_soql(opportunity_id)
        query = f"SELECT Id, ContactId, Role, IsPrimary FROM OpportunityContactRole WHERE OpportunityId = '{safe_id}'"
        return await self._make_request("GET", "/query", params={"q": query})

    # =========================================================================
    # Account Operations
    # =========================================================================

    async def get_accounts(
        self,
        limit: int = 100,
        offset: int = 0,
        modified_since: Optional[datetime] = None,
    ) -> Optional[dict[str, Any]]:
        """Get accounts from Salesforce."""
        fields = [
            "Id",
            "Name",
            "Website",
            "Industry",
            "Type",
            "OwnerId",
            "CreatedDate",
            "LastModifiedDate",
        ]

        query = f"SELECT {', '.join(fields)} FROM Account"

        if modified_since:
            modified_str = modified_since.strftime("%Y-%m-%dT%H:%M:%SZ")
            query += f" WHERE LastModifiedDate >= {modified_str}"

        query += f" ORDER BY LastModifiedDate DESC LIMIT {limit} OFFSET {offset}"

        return await self._make_request("GET", "/query", params={"q": query})

    async def get_account(self, account_id: str) -> Optional[dict[str, Any]]:
        """Get a single account by ID."""
        return await self._make_request("GET", f"/sobjects/Account/{account_id}")

    # =========================================================================
    # Custom Field Operations
    # =========================================================================

    async def describe_object(self, object_name: str) -> Optional[dict[str, Any]]:
        """Get metadata about an object including fields."""
        return await self._make_request("GET", f"/sobjects/{object_name}/describe")

    async def get_custom_fields(self, object_name: str) -> list[dict[str, Any]]:
        """Get list of custom fields for an object."""
        describe = await self.describe_object(object_name)
        if not describe:
            return []

        fields = describe.get("fields", [])
        return [f for f in fields if f.get("custom", False)]

    async def create_custom_field(
        self,
        object_name: str,
        field_name: str,
        field_type: str,
        label: str,
        description: str = "",
    ) -> Optional[dict[str, Any]]:
        """
        Create a custom field (requires Metadata API).

        Note: This is a simplified implementation. Full custom field creation
        requires the Metadata API which has different authentication.
        """
        # Custom field creation typically requires Metadata API
        # This is a placeholder - in production, use Salesforce Metadata API
        logger.warning(
            "salesforce_custom_field_creation_not_implemented",
            object_name=object_name,
            field_name=field_name,
        )
        return {"success": False, "error": "Custom field creation requires Metadata API"}

    # =========================================================================
    # Bulk Operations
    # =========================================================================

    async def create_bulk_job(
        self,
        object_name: str,
        operation: str,  # insert, update, upsert, delete
    ) -> Optional[dict[str, Any]]:
        """Create a bulk API job."""
        data = {
            "object": object_name,
            "operation": operation,
            "contentType": "JSON",
        }
        return await self._make_request("POST", "/jobs/ingest", data=data)

    async def upload_bulk_data(
        self,
        job_id: str,
        records: list[dict[str, Any]],
    ) -> Optional[dict[str, Any]]:
        """Upload data to a bulk job."""
        return await self._make_request(
            "PUT",
            f"/jobs/ingest/{job_id}/batches",
            data=records,
        )

    async def close_bulk_job(self, job_id: str) -> Optional[dict[str, Any]]:
        """Close a bulk job and start processing."""
        return await self._make_request(
            "PATCH",
            f"/jobs/ingest/{job_id}",
            data={"state": "UploadComplete"},
        )

    async def get_bulk_job_status(self, job_id: str) -> Optional[dict[str, Any]]:
        """Get status of a bulk job."""
        return await self._make_request("GET", f"/jobs/ingest/{job_id}")

    # =========================================================================
    # Query Operations
    # =========================================================================

    async def query(self, soql: str) -> Optional[dict[str, Any]]:
        """Execute a SOQL query."""
        return await self._make_request("GET", "/query", params={"q": soql})

    async def query_more(self, next_records_url: str) -> Optional[dict[str, Any]]:
        """Get next page of query results."""
        # next_records_url is a relative URL like /services/data/vXX.X/query/xxx-xxx
        return await self._make_request(
            "GET", next_records_url.replace(f"/services/data/{API_VERSION}", "")
        )

    # =========================================================================
    # Campaign Operations
    # =========================================================================

    async def get_campaigns(
        self,
        limit: int = 100,
        offset: int = 0,
    ) -> Optional[dict[str, Any]]:
        """Get campaigns from Salesforce."""
        fields = [
            "Id",
            "Name",
            "Type",
            "Status",
            "StartDate",
            "EndDate",
            "IsActive",
            "NumberOfLeads",
            "NumberOfContacts",
            "NumberOfOpportunities",
            "AmountAllOpportunities",
            "CreatedDate",
            "LastModifiedDate",
        ]

        query = f"SELECT {', '.join(fields)} FROM Campaign"
        query += f" ORDER BY LastModifiedDate DESC LIMIT {limit} OFFSET {offset}"

        return await self._make_request("GET", "/query", params={"q": query})

    async def get_campaign_members(
        self,
        campaign_id: str,
        limit: int = 100,
    ) -> Optional[dict[str, Any]]:
        """Get members of a campaign."""
        safe_id = _escape_soql(campaign_id)
        query = f"""
            SELECT Id, ContactId, LeadId, Status, FirstRespondedDate
            FROM CampaignMember
            WHERE CampaignId = '{safe_id}'
            LIMIT {limit}
        """
        return await self._make_request("GET", "/query", params={"q": query})
