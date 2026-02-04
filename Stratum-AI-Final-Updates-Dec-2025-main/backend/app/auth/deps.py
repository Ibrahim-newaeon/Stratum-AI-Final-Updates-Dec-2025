# =============================================================================
# Stratum AI - Authentication Dependencies
# =============================================================================
"""
FastAPI dependencies for authentication and authorization.
Provides get_current_user and related dependencies for protected routes.
"""

import secrets
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.core.security import decode_token
from app.db.session import get_async_session
from app.models import User, UserRole

logger = get_logger(__name__)

# Security scheme for JWT Bearer tokens
security = HTTPBearer(auto_error=False)


class CurrentUser:
    """Container for current user information."""

    def __init__(
        self,
        user: User,
        email: str,
        full_name: Optional[str] = None,
    ):
        self.user = user
        self.id = user.id
        self.tenant_id = user.tenant_id
        self.email = email
        self.full_name = full_name
        self.role = user.role
        self.is_active = user.is_active
        self.is_verified = user.is_verified
        self.permissions = user.permissions or {}


async def get_current_user(
    request: Request,
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: AsyncSession = Depends(get_async_session),
) -> CurrentUser:
    """
    Get the current authenticated user from JWT token.

    Args:
        request: FastAPI request object
        credentials: Bearer token credentials
        db: Database session

    Returns:
        CurrentUser object with user details

    Raises:
        HTTPException: If authentication fails
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not credentials:
        raise credentials_exception

    token = credentials.credentials
    payload = decode_token(token)

    if not payload:
        raise credentials_exception

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise credentials_exception

    try:
        user_id = int(user_id)
    except ValueError:
        raise credentials_exception

    # Fetch user from database
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.is_deleted == False,
        )
    )
    user = result.scalar_one_or_none()

    if not user:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )

    # Decrypt PII for response
    from app.core.security import decrypt_pii

    email = payload.get("email") or decrypt_pii(user.email)
    full_name = decrypt_pii(user.full_name) if user.full_name else None

    # Store user info in request state for middleware/logging
    request.state.user_id = user.id
    request.state.tenant_id = user.tenant_id
    request.state.role = user.role.value
    request.state.permissions = list(user.permissions.keys()) if user.permissions else []

    return CurrentUser(user=user, email=email, full_name=full_name)


async def get_current_active_user(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    """
    Get current user that is active.
    Use this when you need to ensure the user is active.
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated",
        )
    return current_user


async def get_current_verified_user(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    """
    Get current user that is verified.
    Use this for endpoints that require email verification.
    """
    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email verification required",
        )
    return current_user


async def get_optional_user(
    request: Request,
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: AsyncSession = Depends(get_async_session),
) -> Optional[CurrentUser]:
    """
    Get current user if authenticated, None otherwise.
    Use this for endpoints that work both authenticated and unauthenticated.
    """
    if not credentials:
        return None

    try:
        return await get_current_user(request, credentials, db)
    except HTTPException:
        return None


def require_role(*roles: UserRole):
    """
    Dependency factory that requires the user to have one of the specified roles.

    Usage:
        @router.get("/admin", dependencies=[Depends(require_role(UserRole.ADMIN, UserRole.SUPERADMIN))])
        async def admin_endpoint(): ...
    """

    async def role_checker(
        current_user: Annotated[CurrentUser, Depends(get_current_user)],
    ) -> CurrentUser:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {current_user.role.value} not authorized for this action",
            )
        return current_user

    return role_checker


def require_admin():
    """Dependency that requires admin or superadmin role."""
    return require_role(UserRole.ADMIN, UserRole.SUPERADMIN)


def require_superadmin():
    """Dependency that requires superadmin role."""
    return require_role(UserRole.SUPERADMIN)


# =============================================================================
# Token Generation Utilities
# =============================================================================


def generate_verification_token() -> str:
    """Generate a secure token for email verification."""
    return secrets.token_urlsafe(32)


def generate_password_reset_token() -> str:
    """Generate a secure token for password reset."""
    return secrets.token_urlsafe(32)


# =============================================================================
# Type Aliases for Dependency Injection
# =============================================================================

# Common dependency types for cleaner endpoint signatures
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
ActiveUserDep = Annotated[CurrentUser, Depends(get_current_active_user)]
VerifiedUserDep = Annotated[CurrentUser, Depends(get_current_verified_user)]
OptionalUserDep = Annotated[Optional[CurrentUser], Depends(get_optional_user)]
