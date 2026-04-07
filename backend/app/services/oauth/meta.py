# =============================================================================
# Stratum AI - Meta (Facebook/Instagram) OAuth Service
# =============================================================================
"""
OAuth implementation for Meta Business Suite (Facebook/Instagram Ads).

Meta OAuth Flow:
1. Redirect user to Facebook login dialog
2. User authorizes app and grants permissions
3. Facebook redirects back with authorization code
4. Exchange code for short-lived access token
5. Exchange short-lived token for long-lived token (60 days)
6. Fetch ad accounts using Marketing API

Required Scopes:
- ads_management: Create, manage, and report on ads
- ads_read: Read ad data
- business_management: Manage Business Manager assets

Docs: https://developers.facebook.com/docs/marketing-api/overview/authorization
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

# Meta OAuth endpoints
META_AUTH_URL = "https://www.facebook.com/{version}/dialog/oauth"
META_TOKEN_URL = "https://graph.facebook.com/{version}/oauth/access_token"
META_DEBUG_TOKEN_URL = "https://graph.facebook.com/{version}/debug_token"
META_GRAPH_URL = "https://graph.facebook.com/{version}"

# Default scopes for ad management
META_DEFAULT_SCOPES = [
    "ads_management",
    "ads_read",
    "business_management",
    "pages_read_engagement",
]


class MetaOAuthService(OAuthService):
    """OAuth service for Meta (Facebook/Instagram) Ads."""

    platform = "meta"

    def __init__(self) -> None:
        super().__init__()
        self.app_id = settings.meta_app_id
        self.app_secret = settings.meta_app_secret
        self.api_version = settings.meta_api_version

    def _get_auth_url(self) -> str:
        """Get versioned auth URL."""
        return META_AUTH_URL.format(version=self.api_version)

    def _get_token_url(self) -> str:
        """Get versioned token URL."""
        return META_TOKEN_URL.format(version=self.api_version)

    def _get_graph_url(self, endpoint: str = "") -> str:
        """Get versioned Graph API URL."""
        base = META_GRAPH_URL.format(version=self.api_version)
        return f"{base}/{endpoint}" if endpoint else base

    def get_authorization_url(
        self,
        state: OAuthState,
        scopes: Optional[list[str]] = None,
    ) -> str:
        """
        Generate Meta OAuth authorization URL.

        Args:
            state: OAuth state for CSRF protection
            scopes: Permissions to request (defaults to ads_management, ads_read)

        Returns:
            Facebook login dialog URL
        """
        if not self.app_id:
            raise ValueError("Meta App ID not configured")

        requested_scopes = scopes or META_DEFAULT_SCOPES
        redirect_uri = self.get_redirect_uri()

        params = {
            "client_id": self.app_id,
            "redirect_uri": redirect_uri,
            "state": state.state_token,
            "scope": ",".join(requested_scopes),
            "response_type": "code",
            # Request re-authorization if permissions change
            "auth_type": "rerequest",
        }

        return self.build_url(self._get_auth_url(), params)

    async def exchange_code_for_tokens(
        self,
        code: str,
        redirect_uri: str,
    ) -> OAuthTokens:
        """
        Exchange authorization code for access tokens.

        Meta returns a short-lived token first, then we exchange it
        for a long-lived token (valid for 60 days).

        Args:
            code: Authorization code from callback
            redirect_uri: Same redirect_uri used in authorization

        Returns:
            OAuthTokens with long-lived access token
        """
        if not self.app_id or not self.app_secret:
            raise ValueError("Meta App credentials not configured")

        async with aiohttp.ClientSession() as session:
            # Step 1: Exchange code for short-lived token
            params = {
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "redirect_uri": redirect_uri,
                "code": code,
            }

            async with session.get(self._get_token_url(), params=params) as resp:
                if resp.status != 200:
                    error_data = await resp.json()
                    self.logger.error("Meta token exchange failed", error=error_data)
                    raise Exception(
                        f"Token exchange failed: {error_data.get('error', {}).get('message', 'Unknown error')}"
                    )

                token_data = await resp.json()

            short_lived_token = token_data.get("access_token")
            if not short_lived_token:
                raise Exception("No access token in response")

            # Step 2: Exchange short-lived for long-lived token
            long_lived_params = {
                "grant_type": "fb_exchange_token",
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "fb_exchange_token": short_lived_token,
            }

            async with session.get(self._get_token_url(), params=long_lived_params) as resp:
                if resp.status != 200:
                    error_data = await resp.json()
                    self.logger.error("Meta long-lived token exchange failed", error=error_data)
                    # Fall back to short-lived token
                    return OAuthTokens(
                        access_token=short_lived_token,
                        expires_in=token_data.get("expires_in"),
                        expires_at=self._calculate_expiry(token_data.get("expires_in")),
                        token_type=token_data.get("token_type", "Bearer"),
                        raw_response=token_data,
                    )

                long_lived_data = await resp.json()

            # Long-lived tokens expire in ~60 days
            expires_in = long_lived_data.get("expires_in", 5184000)  # Default 60 days

            long_lived_token = long_lived_data.get("access_token")
            if not long_lived_token:
                raise Exception("No access token in long-lived token response")

            return OAuthTokens(
                access_token=long_lived_token,
                expires_in=expires_in,
                expires_at=self._calculate_expiry(expires_in),
                token_type=long_lived_data.get("token_type", "Bearer"),
                raw_response=long_lived_data,
            )

    async def refresh_access_token(
        self,
        refresh_token: str,
    ) -> OAuthTokens:
        """
        Refresh Meta access token.

        Note: Meta long-lived tokens can only be refreshed when they have
        at least 24 hours of validity remaining. After 60 days, the user
        must re-authenticate.

        For Meta, the "refresh_token" is actually the access_token itself,
        as we use fb_exchange_token to get a new long-lived token.

        Args:
            refresh_token: Current access token to refresh

        Returns:
            New OAuthTokens
        """
        if not self.app_id or not self.app_secret:
            raise ValueError("Meta App credentials not configured")

        async with aiohttp.ClientSession() as session:
            params = {
                "grant_type": "fb_exchange_token",
                "client_id": self.app_id,
                "client_secret": self.app_secret,
                "fb_exchange_token": refresh_token,
            }

            async with session.get(self._get_token_url(), params=params) as resp:
                if resp.status != 200:
                    error_data = await resp.json()
                    self.logger.error("Meta token refresh failed", error=error_data)
                    raise Exception(
                        f"Token refresh failed: {error_data.get('error', {}).get('message', 'Unknown error')}"
                    )

                token_data = await resp.json()

            expires_in = token_data.get("expires_in", 5184000)

            return OAuthTokens(
                access_token=token_data.get("access_token"),
                expires_in=expires_in,
                expires_at=self._calculate_expiry(expires_in),
                token_type=token_data.get("token_type", "Bearer"),
                raw_response=token_data,
            )

    async def fetch_ad_accounts(
        self,
        access_token: str,
    ) -> list[AdAccountInfo]:
        """
        Fetch ad accounts accessible by the authenticated user.

        Uses the /me/adaccounts endpoint to get all ad accounts
        the user has access to.

        Args:
            access_token: Valid access token

        Returns:
            List of AdAccountInfo
        """
        accounts = []

        async with aiohttp.ClientSession() as session:
            url = self._get_graph_url("me/adaccounts")
            params = {
                "access_token": access_token,
                "fields": "id,name,account_id,business_name,currency,timezone_name,account_status,spend_cap,amount_spent,capabilities",
                "limit": 100,
            }

            while url:
                async with session.get(url, params=params) as resp:
                    if resp.status != 200:
                        error_data = await resp.json()
                        self.logger.error("Failed to fetch ad accounts", error=error_data)
                        raise Exception(
                            f"Failed to fetch ad accounts: {error_data.get('error', {}).get('message', 'Unknown error')}"
                        )

                    data = await resp.json()

                for account in data.get("data", []):
                    # Map account status
                    status_map = {
                        1: "active",
                        2: "disabled",
                        3: "unsettled",
                        7: "pending_risk_review",
                        8: "pending_settlement",
                        9: "in_grace_period",
                        100: "pending_closure",
                        101: "closed",
                        201: "any_active",
                        202: "any_closed",
                    }
                    account_status = status_map.get(account.get("account_status", 1), "unknown")

                    accounts.append(
                        AdAccountInfo(
                            account_id=account.get("id", ""),  # Format: act_123456789
                            name=account.get("name", "Unnamed Account"),
                            business_name=account.get("business_name"),
                            currency=account.get("currency", "USD"),
                            timezone=account.get("timezone_name", "UTC"),
                            status=account_status,
                            spend_cap=float(account.get("spend_cap", 0)) / 100
                            if account.get("spend_cap")
                            else None,
                            amount_spent=float(account.get("amount_spent", 0)) / 100
                            if account.get("amount_spent")
                            else None,
                            permissions=account.get("capabilities", []),
                            raw_data=account,
                        )
                    )

                # Handle pagination
                paging = data.get("paging", {})
                url = paging.get("next")
                params = {}  # Next URL includes params

        return accounts

    async def revoke_access(
        self,
        access_token: str,
    ) -> bool:
        """
        Revoke Meta OAuth access.

        Deletes the app's permissions for the user.

        Args:
            access_token: Token to revoke

        Returns:
            True if successful
        """
        async with aiohttp.ClientSession() as session:
            url = self._get_graph_url("me/permissions")
            params = {"access_token": access_token}

            async with session.delete(url, params=params) as resp:
                if resp.status != 200:
                    error_data = await resp.json()
                    self.logger.error("Failed to revoke access", error=error_data)
                    return False

                data = await resp.json()
                return data.get("success", False)

    def _calculate_expiry(self, expires_in: Optional[int]) -> Optional[datetime]:
        """Calculate expiration datetime from expires_in seconds."""
        if expires_in is None:
            return None
        return datetime.now(UTC) + timedelta(seconds=expires_in)
