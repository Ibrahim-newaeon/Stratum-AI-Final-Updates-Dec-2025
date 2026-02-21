# =============================================================================
# Stratum AI - Google Ads OAuth Service
# =============================================================================
"""
OAuth implementation for Google Ads API.

Google OAuth Flow:
1. Redirect user to Google OAuth consent screen
2. User authorizes app and grants permissions
3. Google redirects back with authorization code
4. Exchange code for access and refresh tokens
5. Use refresh token to get new access tokens (valid 1 hour)
6. Fetch customer accounts using Google Ads API

Required Scopes:
- https://www.googleapis.com/auth/adwords: Full access to Google Ads

Docs: https://developers.google.com/google-ads/api/docs/oauth/overview
"""

from datetime import UTC, datetime, timedelta
from typing import Optional

import aiohttp

from app.core.config import settings
from app.core.logging import get_logger
from app.services.oauth.base import (
    AdAccountInfo,
    OAuthService,
    OAuthState,
    OAuthTokens,
)

logger = get_logger(__name__)

# Google OAuth endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"

# Google Ads API
GOOGLE_ADS_API_URL = "https://googleads.googleapis.com/v15"

# Default scopes for Google Ads
GOOGLE_DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/adwords",
]


class GoogleOAuthService(OAuthService):
    """OAuth service for Google Ads."""

    platform = "google"

    def __init__(self) -> None:
        super().__init__()
        self.client_id = settings.google_ads_client_id
        self.client_secret = settings.google_ads_client_secret
        self.developer_token = settings.google_ads_developer_token

    def get_authorization_url(
        self,
        state: OAuthState,
        scopes: Optional[list[str]] = None,
    ) -> str:
        """
        Generate Google OAuth authorization URL.

        Args:
            state: OAuth state for CSRF protection
            scopes: Permissions to request

        Returns:
            Google OAuth consent screen URL
        """
        if not self.client_id:
            raise ValueError("Google Client ID not configured")

        requested_scopes = scopes or GOOGLE_DEFAULT_SCOPES
        redirect_uri = self.get_redirect_uri()

        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(requested_scopes),
            "state": state.state_token,
            "access_type": "offline",  # Request refresh token
            "prompt": "consent",  # Always show consent to get refresh token
            "include_granted_scopes": "true",
        }

        return self.build_url(GOOGLE_AUTH_URL, params)

    async def exchange_code_for_tokens(
        self,
        code: str,
        redirect_uri: str,
    ) -> OAuthTokens:
        """
        Exchange authorization code for access and refresh tokens.

        Google returns both access_token (1 hour) and refresh_token.
        The refresh_token is only returned on first authorization
        unless prompt=consent is used.

        Args:
            code: Authorization code from callback
            redirect_uri: Same redirect_uri used in authorization

        Returns:
            OAuthTokens with access and refresh tokens
        """
        if not self.client_id or not self.client_secret:
            raise ValueError("Google OAuth credentials not configured")

        async with aiohttp.ClientSession() as session:
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": redirect_uri,
            }

            async with session.post(GOOGLE_TOKEN_URL, data=data) as resp:
                if resp.status != 200:
                    error_data = await resp.json()
                    self.logger.error("Google token exchange failed", error=error_data)
                    raise Exception(
                        f"Token exchange failed: {error_data.get('error_description', error_data.get('error', 'Unknown error'))}"
                    )

                token_data = await resp.json()

        access_token = token_data.get("access_token")
        if not access_token:
            raise Exception("No access token in response")

        expires_in = token_data.get("expires_in", 3600)

        return OAuthTokens(
            access_token=access_token,
            refresh_token=token_data.get("refresh_token"),
            expires_in=expires_in,
            expires_at=self._calculate_expiry(expires_in),
            token_type=token_data.get("token_type", "Bearer"),
            scopes=token_data.get("scope", "").split(" "),
            raw_response=token_data,
        )

    async def refresh_access_token(
        self,
        refresh_token: str,
    ) -> OAuthTokens:
        """
        Refresh Google access token using refresh token.

        Args:
            refresh_token: Refresh token from initial authorization

        Returns:
            New OAuthTokens (note: refresh_token usually not returned)
        """
        if not self.client_id or not self.client_secret:
            raise ValueError("Google OAuth credentials not configured")

        async with aiohttp.ClientSession() as session:
            data = {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }

            async with session.post(GOOGLE_TOKEN_URL, data=data) as resp:
                if resp.status != 200:
                    error_data = await resp.json()
                    self.logger.error("Google token refresh failed", error=error_data)
                    raise Exception(
                        f"Token refresh failed: {error_data.get('error_description', error_data.get('error', 'Unknown error'))}"
                    )

                token_data = await resp.json()

        expires_in = token_data.get("expires_in", 3600)

        return OAuthTokens(
            access_token=token_data.get("access_token"),
            refresh_token=refresh_token,  # Keep original refresh token
            expires_in=expires_in,
            expires_at=self._calculate_expiry(expires_in),
            token_type=token_data.get("token_type", "Bearer"),
            scopes=token_data.get("scope", "").split(" "),
            raw_response=token_data,
        )

    async def fetch_ad_accounts(
        self,
        access_token: str,
    ) -> list[AdAccountInfo]:
        """
        Fetch Google Ads customer accounts.

        Uses the listAccessibleCustomers endpoint to get all accounts
        the user has access to.

        Args:
            access_token: Valid access token

        Returns:
            List of AdAccountInfo
        """
        if not self.developer_token:
            self.logger.warning("Developer token not configured, returning mock data")
            return self._get_mock_accounts()

        accounts = []

        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {access_token}",
                "developer-token": self.developer_token,
            }

            # Get list of accessible customer IDs
            list_url = f"{GOOGLE_ADS_API_URL}/customers:listAccessibleCustomers"

            async with session.get(list_url, headers=headers) as resp:
                if resp.status != 200:
                    error_data = await resp.text()
                    self.logger.error("Failed to list customers", error=error_data)
                    # Return mock data in development
                    if settings.is_development:
                        return self._get_mock_accounts()
                    raise Exception(f"Failed to list customers: {error_data}")

                data = await resp.json()

            customer_ids = data.get("resourceNames", [])

            # Fetch details for each customer
            for resource_name in customer_ids:
                # Extract customer ID from resource name (customers/123456789)
                customer_id = resource_name.split("/")[-1]

                try:
                    # Use Google Ads Query Language to get customer details
                    query_url = (
                        f"{GOOGLE_ADS_API_URL}/customers/{customer_id}/googleAds:searchStream"
                    )
                    query = """
                        SELECT
                            customer.id,
                            customer.descriptive_name,
                            customer.currency_code,
                            customer.time_zone,
                            customer.status,
                            customer.manager
                        FROM customer
                        LIMIT 1
                    """

                    async with session.post(
                        query_url, headers=headers, json={"query": query}
                    ) as resp:
                        if resp.status != 200:
                            continue

                        stream_data = await resp.json()

                    for result in stream_data:
                        for row in result.get("results", []):
                            customer = row.get("customer", {})

                            # Skip manager accounts unless they have campaigns
                            is_manager = customer.get("manager", False)

                            status_map = {
                                "ENABLED": "active",
                                "CANCELED": "cancelled",
                                "SUSPENDED": "suspended",
                                "CLOSED": "closed",
                            }

                            accounts.append(
                                AdAccountInfo(
                                    account_id=str(customer.get("id", customer_id)),
                                    name=customer.get("descriptiveName", f"Account {customer_id}"),
                                    business_name="Manager Account" if is_manager else None,
                                    currency=customer.get("currencyCode", "USD"),
                                    timezone=customer.get("timeZone", "UTC"),
                                    status=status_map.get(customer.get("status"), "unknown"),
                                    permissions=["STANDARD"] if not is_manager else ["MANAGER"],
                                    raw_data=customer,
                                )
                            )

                except Exception as e:
                    self.logger.warning(f"Failed to fetch customer {customer_id}", error=str(e))
                    # Add basic info from resource name
                    accounts.append(
                        AdAccountInfo(
                            account_id=customer_id,
                            name=f"Account {customer_id}",
                            status="unknown",
                        )
                    )

        return accounts

    async def revoke_access(
        self,
        access_token: str,
    ) -> bool:
        """
        Revoke Google OAuth access.

        Args:
            access_token: Token to revoke

        Returns:
            True if successful
        """
        async with aiohttp.ClientSession() as session:
            params = {"token": access_token}

            async with session.post(GOOGLE_REVOKE_URL, params=params) as resp:
                return resp.status == 200

    def _calculate_expiry(self, expires_in: Optional[int]) -> Optional[datetime]:
        """Calculate expiration datetime from expires_in seconds."""
        if expires_in is None:
            return None
        return datetime.now(UTC) + timedelta(seconds=expires_in)

    def _get_mock_accounts(self) -> list[AdAccountInfo]:
        """Return mock accounts for development/testing."""
        return [
            AdAccountInfo(
                account_id="1234567890",
                name="Demo Google Ads Account",
                business_name="Demo Company",
                currency="USD",
                timezone="America/New_York",
                status="active",
                permissions=["STANDARD"],
            ),
            AdAccountInfo(
                account_id="0987654321",
                name="Test Campaign Account",
                business_name="Test Business",
                currency="USD",
                timezone="America/Los_Angeles",
                status="active",
                permissions=["STANDARD"],
            ),
        ]
