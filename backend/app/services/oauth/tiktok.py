# =============================================================================
# Stratum AI - TikTok Ads OAuth Service
# =============================================================================
"""
OAuth implementation for TikTok Marketing API.

TikTok OAuth Flow:
1. Redirect user to TikTok authorization page
2. User authorizes app and grants permissions
3. TikTok redirects back with authorization code
4. Exchange code for access token (valid 24 hours) and refresh token
5. Use refresh token to get new tokens (refresh token valid 365 days)
6. Fetch advertiser accounts using Marketing API

Required Scopes:
- advertiser.read: Read advertiser info
- advertiser.write: Manage advertiser settings
- campaign.read: Read campaign data
- campaign.write: Create/update campaigns
- report.read: Access reports

Docs: https://business-api.tiktok.com/portal/docs?id=1738373164380162
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

# TikTok OAuth endpoints
TIKTOK_AUTH_URL = "https://business-api.tiktok.com/portal/auth"
TIKTOK_TOKEN_URL = "https://business-api.tiktok.com/open_api/v1.3/oauth2/access_token/"
TIKTOK_REFRESH_URL = "https://business-api.tiktok.com/open_api/v1.3/oauth2/refresh_token/"

# TikTok Marketing API
TIKTOK_API_URL = "https://business-api.tiktok.com/open_api/v1.3"

# Default scopes for TikTok Ads
TIKTOK_DEFAULT_SCOPES = [
    "advertiser.read",
    "advertiser.write",
    "campaign.read",
    "campaign.write",
    "report.read",
]


class TikTokOAuthService(OAuthService):
    """OAuth service for TikTok Ads."""

    platform = "tiktok"

    def __init__(self) -> None:
        super().__init__()
        self.app_id = settings.tiktok_app_id
        self.app_secret = settings.tiktok_secret

    def get_authorization_url(
        self,
        state: OAuthState,
        scopes: Optional[list[str]] = None,
    ) -> str:
        """
        Generate TikTok OAuth authorization URL.

        Args:
            state: OAuth state for CSRF protection
            scopes: Permissions to request

        Returns:
            TikTok authorization page URL
        """
        if not self.app_id:
            raise ValueError("TikTok App ID not configured")

        redirect_uri = self.get_redirect_uri()

        params = {
            "app_id": self.app_id,
            "redirect_uri": redirect_uri,
            "state": state.state_token,
        }

        return self.build_url(TIKTOK_AUTH_URL, params)

    async def exchange_code_for_tokens(
        self,
        code: str,
        redirect_uri: str,
    ) -> OAuthTokens:
        """
        Exchange authorization code for access and refresh tokens.

        TikTok returns:
        - access_token: Valid for 24 hours
        - refresh_token: Valid for 365 days

        Args:
            code: Authorization code from callback
            redirect_uri: Same redirect_uri used in authorization

        Returns:
            OAuthTokens with access and refresh tokens
        """
        if not self.app_id or not self.app_secret:
            raise ValueError("TikTok OAuth credentials not configured")

        async with aiohttp.ClientSession() as session:
            data = {
                "app_id": self.app_id,
                "secret": self.app_secret,
                "auth_code": code,
            }

            async with session.post(TIKTOK_TOKEN_URL, json=data) as resp:
                response_data = await resp.json()

                if response_data.get("code") != 0:
                    error_msg = response_data.get("message", "Unknown error")
                    self.logger.error("TikTok token exchange failed", error=response_data)
                    raise Exception(f"Token exchange failed: {error_msg}")

                token_data = response_data.get("data", {})

        # TikTok access tokens expire in 24 hours (86400 seconds)
        access_token = token_data.get("access_token")
        if not access_token:
            raise Exception("No access token in response")

        expires_in = token_data.get("expires_in", 86400)

        return OAuthTokens(
            access_token=access_token,
            refresh_token=token_data.get("refresh_token"),
            expires_in=expires_in,
            expires_at=self._calculate_expiry(expires_in),
            token_type="Bearer",
            scopes=token_data.get("scope", []),
            raw_response=token_data,
        )

    async def refresh_access_token(
        self,
        refresh_token: str,
    ) -> OAuthTokens:
        """
        Refresh TikTok access token using refresh token.

        TikTok refresh tokens are valid for 365 days.

        Args:
            refresh_token: Refresh token from initial authorization

        Returns:
            New OAuthTokens with refreshed tokens
        """
        if not self.app_id or not self.app_secret:
            raise ValueError("TikTok OAuth credentials not configured")

        async with aiohttp.ClientSession() as session:
            data = {
                "app_id": self.app_id,
                "secret": self.app_secret,
                "refresh_token": refresh_token,
            }

            async with session.post(TIKTOK_REFRESH_URL, json=data) as resp:
                response_data = await resp.json()

                if response_data.get("code") != 0:
                    error_msg = response_data.get("message", "Unknown error")
                    self.logger.error("TikTok token refresh failed", error=response_data)
                    raise Exception(f"Token refresh failed: {error_msg}")

                token_data = response_data.get("data", {})

        expires_in = token_data.get("expires_in", 86400)

        return OAuthTokens(
            access_token=token_data.get("access_token"),
            refresh_token=token_data.get("refresh_token", refresh_token),
            expires_in=expires_in,
            expires_at=self._calculate_expiry(expires_in),
            token_type="Bearer",
            scopes=token_data.get("scope", []),
            raw_response=token_data,
        )

    async def fetch_ad_accounts(
        self,
        access_token: str,
    ) -> list[AdAccountInfo]:
        """
        Fetch TikTok advertiser accounts.

        Uses the advertiser/info endpoint to get account details.

        Args:
            access_token: Valid access token

        Returns:
            List of AdAccountInfo
        """
        accounts = []

        async with aiohttp.ClientSession() as session:
            headers = {
                "Access-Token": access_token,
            }

            # First, get the list of authorized advertiser IDs from token info
            # This is typically included in the token response
            # For now, we'll use the advertiser info endpoint

            url = f"{TIKTOK_API_URL}/oauth2/advertiser/get/"
            post_data = {
                "app_id": self.app_id,
                "secret": self.app_secret,
            }

            async with session.post(url, headers=headers, json=post_data) as resp:
                response_data = await resp.json()

                if response_data.get("code") != 0:
                    error_msg = response_data.get("message", "Unknown error")
                    self.logger.error("Failed to get advertisers", error=response_data)

                    raise Exception(f"Failed to get advertisers: {error_msg}")

                advertisers = response_data.get("data", {}).get("list", [])

            # Fetch details for each advertiser
            for adv in advertisers:
                adv_id = adv.get("advertiser_id")
                if not adv_id:
                    continue

                # Get advertiser info
                info_url = f"{TIKTOK_API_URL}/advertiser/info/"
                info_params = {
                    "advertiser_ids": f'["{adv_id}"]',
                    "fields": '["name", "currency", "timezone", "status", "company"]',
                }

                try:
                    async with session.get(info_url, headers=headers, params=info_params) as resp:
                        info_data = await resp.json()

                        if info_data.get("code") == 0:
                            for info in info_data.get("data", {}).get("list", []):
                                status_map = {
                                    "STATUS_ENABLE": "active",
                                    "STATUS_DISABLE": "disabled",
                                    "STATUS_PENDING_CONFIRM": "pending",
                                    "STATUS_PENDING_VERIFIED": "pending_verification",
                                    "STATUS_CONFIRM_FAIL": "rejected",
                                }

                                accounts.append(
                                    AdAccountInfo(
                                        account_id=str(info.get("advertiser_id", adv_id)),
                                        name=info.get("name", f"Advertiser {adv_id}"),
                                        business_name=info.get("company"),
                                        currency=info.get("currency", "USD"),
                                        timezone=info.get("timezone", "UTC"),
                                        status=status_map.get(info.get("status"), "unknown"),
                                        raw_data=info,
                                    )
                                )
                        else:
                            # Add basic info if details fetch fails
                            accounts.append(
                                AdAccountInfo(
                                    account_id=str(adv_id),
                                    name=adv.get("advertiser_name", f"Advertiser {adv_id}"),
                                    status="active",
                                )
                            )

                except Exception as e:
                    self.logger.warning(f"Failed to get advertiser info for {adv_id}", error=str(e))
                    accounts.append(
                        AdAccountInfo(
                            account_id=str(adv_id),
                            name=adv.get("advertiser_name", f"Advertiser {adv_id}"),
                            status="unknown",
                        )
                    )

        return accounts

    async def revoke_access(
        self,
        access_token: str,
    ) -> bool:
        """
        Revoke TikTok OAuth access.

        Note: TikTok doesn't have a direct revoke endpoint.
        Tokens will expire naturally.

        Args:
            access_token: Token to revoke

        Returns:
            True (always succeeds as we just let token expire)
        """
        # TikTok doesn't have a token revocation endpoint
        # Best practice is to delete stored tokens on our side
        self.logger.info("TikTok token revocation requested - tokens will expire naturally")
        return True

    def _calculate_expiry(self, expires_in: Optional[int]) -> Optional[datetime]:
        """Calculate expiration datetime from expires_in seconds."""
        if expires_in is None:
            return None
        return datetime.now(UTC) + timedelta(seconds=expires_in)

    def _get_mock_accounts(self) -> list[AdAccountInfo]:
        """Return mock accounts for development/testing."""
        return [
            AdAccountInfo(
                account_id="7000000000000000001",
                name="Demo TikTok Ads Account",
                business_name="Demo Company",
                currency="USD",
                timezone="America/New_York",
                status="active",
            ),
            AdAccountInfo(
                account_id="7000000000000000002",
                name="Test TikTok Business",
                business_name="Test Business",
                currency="USD",
                timezone="America/Los_Angeles",
                status="active",
            ),
        ]
