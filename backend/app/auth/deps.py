# =============================================================================
# Stratum AI - Authentication Dependencies
# =============================================================================
"""
FastAPI dependencies for authentication and authorization.
Provides get_current_user and related dependencies for protected routes.
"""

import secrets
from typing import Annotated, Any, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func, select
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

    # Decrypt PII for response (gracefully handle key mismatch)
    from app.core.security import decrypt_pii

    try:
        email = payload.get("email") or decrypt_pii(user.email)
    except Exception:
        # Fallback: use raw stored value or email from JWT
        email = payload.get("email") or user.email or f"user-{user.id}@unknown"

    try:
        full_name = decrypt_pii(user.full_name) if user.full_name else None
    except Exception:
        full_name = None

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


def require_role(*roles: UserRole) -> Any:
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
# CMS Auth Dependencies
# =============================================================================


async def get_cms_user(
    request: Request,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
) -> CurrentUser:
    """
    Dependency that verifies the user has a CMS role assigned.

    Stores the cms_role in request.state for downstream use.

    Raises:
        HTTPException(403): If the user has no CMS role assigned.
    """
    cms_role = current_user.user.cms_role
    if not cms_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CMS access denied: no CMS role assigned",
        )
    request.state.cms_role = cms_role
    return current_user


def require_cms_permission(*permissions: str) -> Any:
    """
    Dependency factory that requires the user to have specific CMS permissions.

    Usage:
        @router.get("/posts", dependencies=[Depends(require_cms_permission("view_all_posts"))])
        async def list_posts(): ...

    Args:
        permissions: One or more permission strings to check (all must pass).

    Returns:
        A dependency function that validates CMS permissions.
    """
    from app.models.cms import CMSRole, CMS_PERMISSIONS, has_permission

    async def cms_permission_checker(
        request: Request,
        current_user: Annotated[CurrentUser, Depends(get_cms_user)],
    ) -> CurrentUser:
        cms_role_str = current_user.user.cms_role
        try:
            cms_role = CMSRole(cms_role_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Invalid CMS role: {cms_role_str}",
            )

        for perm in permissions:
            if not has_permission(cms_role, perm):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"CMS permission denied: '{perm}' not granted to role '{cms_role_str}'",
                )
        return current_user

    return cms_permission_checker


async def check_cms_permission(request: Request, permission: str) -> bool:
    """
    Simple async helper to check a CMS permission from request state.

    Returns True if the permission is granted, False otherwise.
    Useful for conditional logic inside endpoint handlers.

    Args:
        request: The FastAPI request (must have cms_role set in state via get_cms_user).
        permission: The permission string to check.

    Returns:
        bool: True if permission granted, False otherwise.
    """
    from app.models.cms import CMSRole, has_permission

    cms_role_str = getattr(request.state, "cms_role", None)
    if not cms_role_str:
        return False
    try:
        cms_role = CMSRole(cms_role_str)
    except ValueError:
        return False
    return has_permission(cms_role, permission)


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
# Client Scope Dependencies
# =============================================================================


async def get_accessible_client_ids(
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    db: AsyncSession = Depends(get_async_session),
) -> Optional[list[int]]:
    """
    Inject accessible client IDs based on user role.

    Returns:
        None  — user can see ALL clients (SUPERADMIN, ADMIN)
        list  — filtered client IDs (MANAGER/ANALYST via assignments, VIEWER via user.client_id)
    """
    from app.auth.permissions import get_accessible_client_ids as _get_ids

    user = current_user.user
    return await _get_ids(
        user_id=user.id,
        user_role=user.role,
        tenant_id=user.tenant_id,
        db=db,
        client_id=getattr(user, "client_id", None),
    )


async def check_tier_limit(
    resource: str,
    tenant_id: int,
    db: AsyncSession,
) -> None:
    """
    Raise 403 if tenant has exceeded tier limit for this resource.

    Args:
        resource: One of "users", "clients", "campaigns"
        tenant_id: The tenant to check
        db: Database session
    """
    from app.models import Campaign, Tenant, User

    result = await db.execute(
        select(Tenant).where(Tenant.id == tenant_id)
    )
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tenant not found",
        )

    if resource == "users":
        count_result = await db.execute(
            select(func.count()).select_from(
                select(User.id).where(
                    User.tenant_id == tenant_id,
                    User.is_deleted == False,
                ).subquery()
            )
        )
        current_count = count_result.scalar() or 0
        if current_count >= tenant.max_users:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tier limit reached: max {tenant.max_users} users",
            )

    elif resource == "campaigns":
        count_result = await db.execute(
            select(func.count()).select_from(
                select(Campaign.id).where(
                    Campaign.tenant_id == tenant_id,
                    Campaign.is_deleted == False,
                ).subquery()
            )
        )
        current_count = count_result.scalar() or 0
        if current_count >= tenant.max_campaigns:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tier limit reached: max {tenant.max_campaigns} campaigns",
            )

    elif resource == "clients":
        # Client limit from tenant settings (default 50)
        from app.models.client import Client

        max_clients = tenant.settings.get("max_clients", 50) if tenant.settings else 50
        count_result = await db.execute(
            select(func.count()).select_from(
                select(Client.id).where(
                    Client.tenant_id == tenant_id,
                    Client.is_deleted == False,
                ).subquery()
            )
        )
        current_count = count_result.scalar() or 0
        if current_count >= max_clients:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Tier limit reached: max {max_clients} clients",
            )


# =============================================================================
# Type Aliases for Dependency Injection
# =============================================================================

# Common dependency types for cleaner endpoint signatures
CurrentUserDep = Annotated[CurrentUser, Depends(get_current_user)]
ActiveUserDep = Annotated[CurrentUser, Depends(get_current_active_user)]
VerifiedUserDep = Annotated[CurrentUser, Depends(get_current_verified_user)]
OptionalUserDep = Annotated[Optional[CurrentUser], Depends(get_optional_user)]
AccessibleClientIdsDep = Annotated[Optional[list[int]], Depends(get_accessible_client_ids)]
