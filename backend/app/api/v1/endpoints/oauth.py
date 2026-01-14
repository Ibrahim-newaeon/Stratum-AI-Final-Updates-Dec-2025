# =============================================================================
# Stratum AI - OAuth API Endpoints
# =============================================================================
"""
OAuth endpoints for ad platform integrations.

Handles the complete OAuth flow for Meta, Google, TikTok, and Snapchat:
- Initiate OAuth authorization
- Handle OAuth callbacks
- List available ad accounts
- Connect selected accounts
- Refresh and revoke tokens

All endpoints are tenant-scoped and require authentication.
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import get_async_session
from app.models.campaign_builder import (
    AdPlatform,
    ConnectionStatus,
    TenantAdAccount,
    TenantPlatformConnection,
)
from app.auth.deps import CurrentUserDep, VerifiedUserDep
from app.schemas import APIResponse
from app.services.oauth import (
    get_oauth_service,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/oauth", tags=["oauth"])


# =============================================================================
# Pydantic Schemas
# =============================================================================

class OAuthStartRequest(BaseModel):
    """Request to start OAuth flow."""

    scopes: Optional[List[str]] = Field(
        None,
        description="Optional list of scopes to request (uses defaults if not provided)"
    )
    frontend_callback_url: Optional[str] = Field(
        None,
        description="Frontend URL to redirect to after OAuth completes"
    )


class OAuthStartResponse(BaseModel):
    """Response with OAuth authorization URL."""

    authorization_url: str
    state: str
    platform: str


class OAuthCallbackParams(BaseModel):
    """OAuth callback query parameters."""

    code: Optional[str] = None
    state: Optional[str] = None
    error: Optional[str] = None
    error_description: Optional[str] = None


class ConnectionStatusResponse(BaseModel):
    """Platform connection status."""

    platform: str
    status: str
    connected_at: Optional[datetime] = None
    token_expires_at: Optional[datetime] = None
    last_refreshed_at: Optional[datetime] = None
    scopes: List[str] = []
    last_error: Optional[str] = None
    ad_accounts_count: int = 0


class AdAccountResponse(BaseModel):
    """Ad account information."""

    id: Optional[UUID] = None  # Internal ID (None if not connected)
    platform_account_id: str
    name: str
    business_name: Optional[str] = None
    currency: str = "USD"
    timezone: str = "UTC"
    status: str = "active"
    is_connected: bool = False
    is_enabled: bool = False
    spend_cap: Optional[float] = None


class ConnectAccountsRequest(BaseModel):
    """Request to connect ad accounts."""

    account_ids: List[str] = Field(
        ...,
        min_length=1,
        description="List of platform account IDs to connect"
    )


class ConnectAccountsResponse(BaseModel):
    """Response after connecting accounts."""

    connected_count: int
    accounts: List[AdAccountResponse]


class RefreshTokenResponse(BaseModel):
    """Response after token refresh."""

    success: bool
    expires_at: Optional[datetime] = None
    message: str


# =============================================================================
# OAuth Initiation Endpoints
# =============================================================================

@router.post("/{platform}/authorize", response_model=APIResponse[OAuthStartResponse])
async def start_oauth(
    platform: AdPlatform,
    request_data: OAuthStartRequest,
    current_user: VerifiedUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Start OAuth flow for a platform.

    Returns an authorization URL to redirect the user to the platform's
    OAuth consent screen.

    Args:
        platform: Ad platform (meta, google, tiktok, snapchat)
        request_data: Optional scopes and frontend callback URL
        current_user: Authenticated and verified user

    Returns:
        Authorization URL and state token
    """
    try:
        oauth_service = get_oauth_service(platform.value)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    # Create OAuth state for CSRF protection
    try:
        state = await oauth_service.create_state(
            tenant_id=current_user.tenant_id,
            user_id=current_user.id,
            redirect_uri=request_data.frontend_callback_url or settings.frontend_url,
        )
    except Exception as e:
        logger.error("Failed to create OAuth state", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize OAuth flow"
        )

    # Generate authorization URL
    try:
        auth_url = oauth_service.get_authorization_url(
            state=state,
            scopes=request_data.scopes,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

    logger.info(
        "oauth_started",
        platform=platform.value,
        user_id=current_user.id,
        tenant_id=current_user.tenant_id,
    )

    return APIResponse(
        success=True,
        data=OAuthStartResponse(
            authorization_url=auth_url,
            state=state.state_token,
            platform=platform.value,
        ),
        message=f"Redirect user to authorization URL for {platform.value}",
    )


# =============================================================================
# OAuth Callback Endpoints
# =============================================================================

@router.get("/{platform}/callback")
async def oauth_callback(
    platform: AdPlatform,
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
    error_description: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_session),
):
    """
    Handle OAuth callback from platform.

    This endpoint is called by the platform after user authorization.
    It exchanges the authorization code for tokens and stores them.

    On success, redirects to frontend with success status.
    On failure, redirects to frontend with error details.
    """
    frontend_url = settings.frontend_url

    # Handle error from platform
    if error:
        logger.warning(
            "oauth_error_from_platform",
            platform=platform.value,
            error=error,
            description=error_description,
        )
        return RedirectResponse(
            f"{frontend_url}/connect?platform={platform.value}&error={error}&message={error_description or 'Authorization denied'}"
        )

    if not code or not state:
        logger.warning("oauth_missing_params", platform=platform.value)
        return RedirectResponse(
            f"{frontend_url}/connect?platform={platform.value}&error=invalid_request&message=Missing code or state"
        )

    try:
        oauth_service = get_oauth_service(platform.value)
    except ValueError:
        return RedirectResponse(
            f"{frontend_url}/connect?platform={platform.value}&error=invalid_platform"
        )

    # Validate state token
    oauth_state = await oauth_service.validate_state(state)
    if not oauth_state:
        logger.warning("oauth_invalid_state", platform=platform.value)
        return RedirectResponse(
            f"{frontend_url}/connect?platform={platform.value}&error=invalid_state&message=Session expired, please try again"
        )

    # Exchange code for tokens
    try:
        redirect_uri = oauth_service.get_redirect_uri()
        tokens = await oauth_service.exchange_code_for_tokens(code, redirect_uri)
    except Exception as e:
        logger.error(
            "oauth_token_exchange_failed",
            platform=platform.value,
            error=str(e),
        )
        return RedirectResponse(
            f"{frontend_url}/connect?platform={platform.value}&error=token_exchange_failed&message=Failed to complete authorization"
        )

    # Store or update connection
    try:
        result = await db.execute(
            select(TenantPlatformConnection).where(
                and_(
                    TenantPlatformConnection.tenant_id == oauth_state.tenant_id,
                    TenantPlatformConnection.platform == platform,
                )
            )
        )
        connection = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)

        if connection:
            # Update existing connection
            connection.status = ConnectionStatus.CONNECTED
            connection.access_token_encrypted = oauth_service.encrypt_token(tokens.access_token)
            if tokens.refresh_token:
                connection.refresh_token_encrypted = oauth_service.encrypt_token(tokens.refresh_token)
            connection.token_expires_at = tokens.expires_at
            connection.scopes = tokens.scopes
            connection.connected_at = now
            connection.last_refreshed_at = now
            connection.last_error = None
            connection.error_count = 0
            connection.granted_by_user_id = oauth_state.user_id
        else:
            # Create new connection
            connection = TenantPlatformConnection(
                tenant_id=oauth_state.tenant_id,
                platform=platform,
                status=ConnectionStatus.CONNECTED,
                access_token_encrypted=oauth_service.encrypt_token(tokens.access_token),
                refresh_token_encrypted=oauth_service.encrypt_token(tokens.refresh_token) if tokens.refresh_token else None,
                token_expires_at=tokens.expires_at,
                scopes=tokens.scopes,
                connected_at=now,
                last_refreshed_at=now,
                granted_by_user_id=oauth_state.user_id,
            )
            db.add(connection)

        await db.commit()

        logger.info(
            "oauth_completed",
            platform=platform.value,
            tenant_id=oauth_state.tenant_id,
            user_id=oauth_state.user_id,
        )

    except Exception as e:
        logger.error(
            "oauth_storage_failed",
            platform=platform.value,
            error=str(e),
        )
        return RedirectResponse(
            f"{frontend_url}/connect?platform={platform.value}&error=storage_failed&message=Failed to save connection"
        )

    # Redirect to frontend with success
    redirect_url = oauth_state.redirect_uri or frontend_url
    return RedirectResponse(
        f"{redirect_url}/connect?platform={platform.value}&status=success"
    )


# =============================================================================
# Connection Status Endpoints
# =============================================================================

@router.get("/{platform}/status", response_model=APIResponse[ConnectionStatusResponse])
async def get_connection_status(
    platform: AdPlatform,
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get connection status for a platform.

    Returns the current connection status, token expiry, and ad accounts count.
    """
    result = await db.execute(
        select(TenantPlatformConnection).where(
            and_(
                TenantPlatformConnection.tenant_id == current_user.tenant_id,
                TenantPlatformConnection.platform == platform,
            )
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        return APIResponse(
            success=True,
            data=ConnectionStatusResponse(
                platform=platform.value,
                status=ConnectionStatus.DISCONNECTED.value,
            ),
        )

    # Count connected ad accounts
    accounts_result = await db.execute(
        select(TenantAdAccount).where(
            and_(
                TenantAdAccount.connection_id == connection.id,
                TenantAdAccount.is_enabled == True,
            )
        )
    )
    accounts_count = len(accounts_result.scalars().all())

    return APIResponse(
        success=True,
        data=ConnectionStatusResponse(
            platform=connection.platform.value,
            status=connection.status.value,
            connected_at=connection.connected_at,
            token_expires_at=connection.token_expires_at,
            last_refreshed_at=connection.last_refreshed_at,
            scopes=connection.scopes or [],
            last_error=connection.last_error,
            ad_accounts_count=accounts_count,
        ),
    )


@router.get("/status", response_model=APIResponse[List[ConnectionStatusResponse]])
async def get_all_connection_statuses(
    current_user: CurrentUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Get connection status for all platforms.
    """
    result = await db.execute(
        select(TenantPlatformConnection).where(
            TenantPlatformConnection.tenant_id == current_user.tenant_id,
        )
    )
    connections = result.scalars().all()

    statuses = []
    for connection in connections:
        # Count enabled accounts
        accounts_result = await db.execute(
            select(TenantAdAccount).where(
                and_(
                    TenantAdAccount.connection_id == connection.id,
                    TenantAdAccount.is_enabled == True,
                )
            )
        )
        accounts_count = len(accounts_result.scalars().all())

        statuses.append(ConnectionStatusResponse(
            platform=connection.platform.value,
            status=connection.status.value,
            connected_at=connection.connected_at,
            token_expires_at=connection.token_expires_at,
            last_refreshed_at=connection.last_refreshed_at,
            scopes=connection.scopes or [],
            last_error=connection.last_error,
            ad_accounts_count=accounts_count,
        ))

    # Add disconnected status for platforms without connections
    connected_platforms = {s.platform for s in statuses}
    for platform in AdPlatform:
        if platform.value not in connected_platforms:
            statuses.append(ConnectionStatusResponse(
                platform=platform.value,
                status=ConnectionStatus.DISCONNECTED.value,
            ))

    return APIResponse(
        success=True,
        data=statuses,
    )


# =============================================================================
# Ad Account Endpoints
# =============================================================================

@router.get("/{platform}/accounts", response_model=APIResponse[List[AdAccountResponse]])
async def list_ad_accounts(
    platform: AdPlatform,
    current_user: VerifiedUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    List available ad accounts from platform.

    Fetches ad accounts from the platform API and merges with
    locally stored connection status.
    """
    # Get connection
    result = await db.execute(
        select(TenantPlatformConnection).where(
            and_(
                TenantPlatformConnection.tenant_id == current_user.tenant_id,
                TenantPlatformConnection.platform == platform,
            )
        )
    )
    connection = result.scalar_one_or_none()

    if not connection or connection.status != ConnectionStatus.CONNECTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Platform {platform.value} is not connected"
        )

    # Decrypt access token
    try:
        oauth_service = get_oauth_service(platform.value)
        access_token = oauth_service.decrypt_token(connection.access_token_encrypted)
    except Exception as e:
        logger.error("Failed to decrypt token", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve access token"
        )

    # Check if token needs refresh
    if connection.token_expires_at and connection.token_expires_at <= datetime.now(timezone.utc):
        if connection.refresh_token_encrypted:
            try:
                refresh_token = oauth_service.decrypt_token(connection.refresh_token_encrypted)
                new_tokens = await oauth_service.refresh_access_token(refresh_token)

                # Update stored tokens
                connection.access_token_encrypted = oauth_service.encrypt_token(new_tokens.access_token)
                if new_tokens.refresh_token:
                    connection.refresh_token_encrypted = oauth_service.encrypt_token(new_tokens.refresh_token)
                connection.token_expires_at = new_tokens.expires_at
                connection.last_refreshed_at = datetime.now(timezone.utc)
                await db.commit()

                access_token = new_tokens.access_token
            except Exception as e:
                logger.error("Token refresh failed", error=str(e))
                connection.status = ConnectionStatus.EXPIRED
                connection.last_error = str(e)
                await db.commit()
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token expired. Please reconnect."
                )
        else:
            connection.status = ConnectionStatus.EXPIRED
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired. Please reconnect."
            )

    # Fetch accounts from platform
    try:
        platform_accounts = await oauth_service.fetch_ad_accounts(access_token)
    except Exception as e:
        logger.error("Failed to fetch ad accounts", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch accounts from {platform.value}"
        )

    # Get locally stored accounts
    local_result = await db.execute(
        select(TenantAdAccount).where(
            TenantAdAccount.connection_id == connection.id
        )
    )
    local_accounts = {a.platform_account_id: a for a in local_result.scalars().all()}

    # Merge platform accounts with local status
    accounts = []
    for acc in platform_accounts:
        local_acc = local_accounts.get(acc.account_id)
        accounts.append(AdAccountResponse(
            id=local_acc.id if local_acc else None,
            platform_account_id=acc.account_id,
            name=acc.name,
            business_name=acc.business_name,
            currency=acc.currency,
            timezone=acc.timezone,
            status=acc.status,
            is_connected=local_acc is not None,
            is_enabled=local_acc.is_enabled if local_acc else False,
            spend_cap=acc.spend_cap,
        ))

    return APIResponse(
        success=True,
        data=accounts,
    )


@router.post("/{platform}/accounts/connect", response_model=APIResponse[ConnectAccountsResponse])
async def connect_ad_accounts(
    platform: AdPlatform,
    request_data: ConnectAccountsRequest,
    current_user: VerifiedUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Connect selected ad accounts for use in Stratum.

    Creates local records for the selected accounts and enables them.
    """
    # Get connection
    result = await db.execute(
        select(TenantPlatformConnection).where(
            and_(
                TenantPlatformConnection.tenant_id == current_user.tenant_id,
                TenantPlatformConnection.platform == platform,
            )
        )
    )
    connection = result.scalar_one_or_none()

    if not connection or connection.status != ConnectionStatus.CONNECTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Platform {platform.value} is not connected"
        )

    # Fetch accounts from platform to validate
    try:
        oauth_service = get_oauth_service(platform.value)
        access_token = oauth_service.decrypt_token(connection.access_token_encrypted)
        platform_accounts = await oauth_service.fetch_ad_accounts(access_token)
    except Exception as e:
        logger.error("Failed to fetch ad accounts for validation", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to validate accounts"
        )

    platform_accounts_map = {a.account_id: a for a in platform_accounts}

    # Validate requested accounts exist
    for account_id in request_data.account_ids:
        if account_id not in platform_accounts_map:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Account {account_id} not found or not accessible"
            )

    # Connect accounts
    connected_accounts = []
    for account_id in request_data.account_ids:
        platform_acc = platform_accounts_map[account_id]

        # Check if already exists
        result = await db.execute(
            select(TenantAdAccount).where(
                and_(
                    TenantAdAccount.tenant_id == current_user.tenant_id,
                    TenantAdAccount.platform == platform,
                    TenantAdAccount.platform_account_id == account_id,
                )
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update and enable
            existing.name = platform_acc.name
            existing.business_name = platform_acc.business_name
            existing.currency = platform_acc.currency
            existing.timezone = platform_acc.timezone
            existing.account_status = platform_acc.status
            existing.is_enabled = True
            existing.last_synced_at = datetime.now(timezone.utc)
            account = existing
        else:
            # Create new
            account = TenantAdAccount(
                tenant_id=current_user.tenant_id,
                connection_id=connection.id,
                platform=platform,
                platform_account_id=account_id,
                name=platform_acc.name,
                business_name=platform_acc.business_name,
                currency=platform_acc.currency,
                timezone=platform_acc.timezone,
                account_status=platform_acc.status,
                is_enabled=True,
                last_synced_at=datetime.now(timezone.utc),
            )
            db.add(account)

        await db.flush()

        connected_accounts.append(AdAccountResponse(
            id=account.id,
            platform_account_id=account.platform_account_id,
            name=account.name,
            business_name=account.business_name,
            currency=account.currency,
            timezone=account.timezone,
            status=account.account_status or "active",
            is_connected=True,
            is_enabled=True,
        ))

    await db.commit()

    logger.info(
        "ad_accounts_connected",
        platform=platform.value,
        tenant_id=current_user.tenant_id,
        count=len(connected_accounts),
    )

    return APIResponse(
        success=True,
        data=ConnectAccountsResponse(
            connected_count=len(connected_accounts),
            accounts=connected_accounts,
        ),
        message=f"Connected {len(connected_accounts)} ad account(s)",
    )


# =============================================================================
# Token Management Endpoints
# =============================================================================

@router.post("/{platform}/refresh", response_model=APIResponse[RefreshTokenResponse])
async def refresh_token(
    platform: AdPlatform,
    current_user: VerifiedUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Refresh OAuth token for a platform.
    """
    result = await db.execute(
        select(TenantPlatformConnection).where(
            and_(
                TenantPlatformConnection.tenant_id == current_user.tenant_id,
                TenantPlatformConnection.platform == platform,
            )
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Platform {platform.value} is not connected"
        )

    if not connection.refresh_token_encrypted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No refresh token available. Please reconnect."
        )

    try:
        oauth_service = get_oauth_service(platform.value)
        refresh_token = oauth_service.decrypt_token(connection.refresh_token_encrypted)
        new_tokens = await oauth_service.refresh_access_token(refresh_token)

        # Update stored tokens
        connection.access_token_encrypted = oauth_service.encrypt_token(new_tokens.access_token)
        if new_tokens.refresh_token:
            connection.refresh_token_encrypted = oauth_service.encrypt_token(new_tokens.refresh_token)
        connection.token_expires_at = new_tokens.expires_at
        connection.last_refreshed_at = datetime.now(timezone.utc)
        connection.status = ConnectionStatus.CONNECTED
        connection.last_error = None
        connection.error_count = 0

        await db.commit()

        logger.info(
            "token_refreshed",
            platform=platform.value,
            tenant_id=current_user.tenant_id,
        )

        return APIResponse(
            success=True,
            data=RefreshTokenResponse(
                success=True,
                expires_at=new_tokens.expires_at,
                message="Token refreshed successfully",
            ),
        )

    except Exception as e:
        logger.error("Token refresh failed", error=str(e))
        connection.status = ConnectionStatus.ERROR
        connection.last_error = str(e)
        connection.error_count = (connection.error_count or 0) + 1
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Token refresh failed: {str(e)}"
        )


@router.delete("/{platform}/disconnect", response_model=APIResponse[dict])
async def disconnect_platform(
    platform: AdPlatform,
    current_user: VerifiedUserDep,
    db: AsyncSession = Depends(get_async_session),
):
    """
    Disconnect a platform (revoke OAuth).

    This will:
    - Revoke access with the platform (if supported)
    - Delete stored tokens
    - Mark connection as disconnected
    - Disable all connected ad accounts
    """
    result = await db.execute(
        select(TenantPlatformConnection).where(
            and_(
                TenantPlatformConnection.tenant_id == current_user.tenant_id,
                TenantPlatformConnection.platform == platform,
            )
        )
    )
    connection = result.scalar_one_or_none()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Platform {platform.value} is not connected"
        )

    # Try to revoke access with platform
    if connection.access_token_encrypted:
        try:
            oauth_service = get_oauth_service(platform.value)
            access_token = oauth_service.decrypt_token(connection.access_token_encrypted)
            await oauth_service.revoke_access(access_token)
        except Exception as e:
            logger.warning("Failed to revoke access with platform", error=str(e))
            # Continue with local disconnect anyway

    # Disable all ad accounts
    await db.execute(
        select(TenantAdAccount).where(
            TenantAdAccount.connection_id == connection.id
        )
    )
    # Update all related ad accounts
    accounts_result = await db.execute(
        select(TenantAdAccount).where(
            TenantAdAccount.connection_id == connection.id
        )
    )
    for account in accounts_result.scalars().all():
        account.is_enabled = False

    # Mark connection as disconnected and clear tokens
    connection.status = ConnectionStatus.DISCONNECTED
    connection.access_token_encrypted = None
    connection.refresh_token_encrypted = None
    connection.token_expires_at = None

    await db.commit()

    logger.info(
        "platform_disconnected",
        platform=platform.value,
        tenant_id=current_user.tenant_id,
    )

    return APIResponse(
        success=True,
        data={"message": f"Disconnected from {platform.value}"},
    )
