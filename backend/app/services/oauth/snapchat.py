# =============================================================================
# Stratum AI - Snapchat Ads OAuth Service
# =============================================================================
"""
OAuth implementation for Snapchat Marketing API.

Snapchat OAuth Flow:
1. Redirect user to Snapchat authorization page
2. User authorizes app and grants permissions
3. Snapchat redirects back with authorization code
4. Exchange code for access token (30 min) and refresh token (1 year)
5. Use refresh token to get new access tokens
6. Fetch ad accounts using Marketing API

Required Scopes:
- snapchat-marketing-api: Access to Marketing API

Docs: https://developers.snap.com/api/marketing-api/Authorization
"""

import base64
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

# Snapchat OAuth endpoints
SNAPCHAT_AUTH_URL = "https://accounts.snapchat.com/login/oauth2/authorize"
SNAPCHAT_TOKEN_URL = "https://accounts.snapchat.com/login/oauth2/access_token"

# Snapchat Marketing API
SNAPCHAT_API_URL = "https://adsapi.snapchat.com/v1"

# Default scopes for Snapchat Ads
SNAPCHAT_DEFAULT_SCOPES = [
    "snapchat-marketing-api",
]


class SnapchatOAuthService(OAuthService):
    """OAuth service for Snapchat Ads."""

    platform = "snapchat"

    def __init__(self) -> None:
        super().__init__()
        self.client_id = settings.snapchat_client_id
        self.client_secret = settings.snapchat_client_secret

    def get_authorization_url(
        self,
        state: OAuthState,
        scopes: Optional[list[str]] = None,
    ) -> str:
        """
        Generate Snapchat OAuth authorization URL.

        Args:
            state: OAuth state for CSRF protection
            scopes: Permissions to request

        Returns:
            Snapchat authorization page URL
        """
        if not self.client_id:
            raise ValueError("Snapchat Client ID not configured")

        requested_scopes = scopes or SNAPCHAT_DEFAULT_SCOPES
        redirect_uri = self.get_redirect_uri()

        params = {
            "client_id": self.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(requested_scopes),
            "state": state.state_token,
        }

        return self.build_url(SNAPCHAT_AUTH_URL, params)

    async def exchange_code_for_tokens(
        self,
        code: str,
        redirect_uri: str,
    ) -> OAuthTokens:
        """
        Exchange authorization code for access and refresh tokens.

        Snapchat returns:
        - access_token: Valid for 30 minutes
        - refresh_token: Valid for 1 year

        Args:
            code: Authorization code from callback
            redirect_uri: Same redirect_uri used in authorization

        Returns:
            OAuthTokens with access and refresh tokens
        """
        if not self.client_id or not self.client_secret:
            raise ValueError("Snapchat OAuth credentials not configured")

        # Snapchat requires Basic auth with client credentials
        credentials = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()

        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            }

            data = {
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect_uri,
            }

            async with session.post(SNAPCHAT_TOKEN_URL, headers=headers, data=data) as resp:
                if resp.status != 200:
                    error_data = await resp.json()
                    self.logger.error("Snapchat token exchange failed", error=error_data)
                    raise Exception(
                        f"Token exchange failed: {error_data.get('error_description', error_data.get('error', 'Unknown error'))}"
                    )

                token_data = await resp.json()

        # Snapchat access tokens expire in 30 minutes (1800 seconds)
        access_token = token_data.get("access_token")
        if not access_token:
            raise Exception("No access token in response")

        expires_in = token_data.get("expires_in", 1800)

        return OAuthTokens(
            access_token=access_token,
            refresh_token=token_data.get("refresh_token"),
            expires_in=expires_in,
            expires_at=self._calculate_expiry(expires_in),
            token_type=token_data.get("token_type", "Bearer"),
            scopes=token_data.get("scope", "").split(" ") if token_data.get("scope") else [],
            raw_response=token_data,
        )

    async def refresh_access_token(
        self,
        refresh_token: str,
    ) -> OAuthTokens:
        """
        Refresh Snapchat access token using refresh token.

        Args:
            refresh_token: Refresh token from initial authorization

        Returns:
            New OAuthTokens with refreshed tokens
        """
        if not self.client_id or not self.client_secret:
            raise ValueError("Snapchat OAuth credentials not configured")

        credentials = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()

        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Basic {credentials}",
                "Content-Type": "application/x-www-form-urlencoded",
            }

            data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
            }

            async with session.post(SNAPCHAT_TOKEN_URL, headers=headers, data=data) as resp:
                if resp.status != 200:
                    error_data = await resp.json()
                    self.logger.error("Snapchat token refresh failed", error=error_data)
                    raise Exception(
                        f"Token refresh failed: {error_data.get('error_description', error_data.get('error', 'Unknown error'))}"
                    )

                token_data = await resp.json()

        expires_in = token_data.get("expires_in", 1800)

        return OAuthTokens(
            access_token=token_data.get("access_token"),
            refresh_token=token_data.get("refresh_token", refresh_token),
            expires_in=expires_in,
            expires_at=self._calculate_expiry(expires_in),
            token_type=token_data.get("token_type", "Bearer"),
            scopes=token_data.get("scope", "").split(" ") if token_data.get("scope") else [],
            raw_response=token_data,
        )

    async def fetch_ad_accounts(
        self,
        access_token: str,
    ) -> list[AdAccountInfo]:
        """
        Fetch Snapchat ad accounts.

        Uses the /me/organizations and /organizations/{id}/adaccounts endpoints.

        Args:
            access_token: Valid access token

        Returns:
            List of AdAccountInfo
        """
        accounts = []

        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {access_token}",
            }

            # First, get user's organizations
            orgs_url = f"{SNAPCHAT_API_URL}/me/organizations"

            async with session.get(orgs_url, headers=headers) as resp:
                if resp.status != 200:
                    error_data = await resp.text()
                    self.logger.error("Failed to get organizations", error=error_data)

                    raise Exception(f"Failed to get organizations: {error_data}")

                org_data = await resp.json()

            organizations = org_data.get("organizations", [])

            # Get ad accounts for each organization
            for org in organizations:
                org_id = org.get("organization", {}).get("id")
                if not org_id:
                    continue

                accounts_url = f"{SNAPCHAT_API_URL}/organizations/{org_id}/adaccounts"

                try:
                    async with session.get(accounts_url, headers=headers) as resp:
                        if resp.status != 200:
                            continue

                        accounts_data = await resp.json()

                    for acc in accounts_data.get("adaccounts", []):
                        account_info = acc.get("adaccount", {})

                        status_map = {
                            "ACTIVE": "active",
                            "DISABLED": "disabled",
                            "DELETED": "deleted",
                        }

                        accounts.append(
                            AdAccountInfo(
                                account_id=account_info.get("id", ""),
                                name=account_info.get("name", "Unnamed Account"),
                                business_name=account_info.get("organization_id"),
                                currency=account_info.get("currency", "USD"),
                                timezone=account_info.get("timezone", "UTC"),
                                status=status_map.get(account_info.get("status"), "unknown"),
                                spend_cap=float(account_info.get("lifetime_spend_cap_micro", 0))
                                / 1000000
                                if account_info.get("lifetime_spend_cap_micro")
                                else None,
                                raw_data=account_info,
                            )
                        )

                except Exception as e:
                    self.logger.warning(f"Failed to get ad accounts for org {org_id}", error=str(e))

        return accounts

    async def revoke_access(
        self,
        access_token: str,
    ) -> bool:
        """
        Revoke Snapchat OAuth access.

        Note: Snapchat doesn't have a public token revocation endpoint.
        Tokens should be deleted from our storage.

        Args:
            access_token: Token to revoke

        Returns:
            True (delete tokens from storage)
        """
        self.logger.info(
            "Snapchat token revocation requested - tokens will be deleted from storage"
        )
        return True

    def _calculate_expiry(self, expires_in: Optional[int]) -> Optional[datetime]:
        """Calculate expiration datetime from expires_in seconds."""
        if expires_in is None:
            return None
        return datetime.now(UTC) + timedelta(seconds=expires_in)
