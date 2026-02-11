# =============================================================================
# Stratum AI - RBAC Permissions System (v2 — Client-Scoped)
# =============================================================================
"""
Role-Based Access Control with client-scope enforcement.

Roles (UserRole enum values — DO NOT RENAME):
- SUPERADMIN  → super_admin   — Full platform access, cross-tenant
- ADMIN       → admin         — Full tenant access, user management
- MANAGER     → account_mgr   — Assigned-client scope, campaign management
- ANALYST     → media_buyer   — Assigned-client scope, campaign execution
- VIEWER      → client_viewer — Single-client portal scope

Permission levels: NONE=0, VIEW=1, EDIT=2, FULL=3
Scope labels: global, tenant, assigned, own_client
"""

from collections.abc import Callable
from enum import Enum, IntEnum
from functools import wraps
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_async_session
from app.models import UserRole


# =============================================================================
# Permission Level Enum
# =============================================================================
class PermLevel(IntEnum):
    """Granular permission levels for RBAC matrix."""

    NONE = 0
    VIEW = 1
    EDIT = 2
    FULL = 3


# =============================================================================
# Legacy Permission Enum (kept for backwards compatibility)
# =============================================================================
class Permission(str, Enum):
    """Granular permissions for RBAC (legacy — kept for existing endpoint compat)."""

    TENANT_READ = "tenant:read"
    TENANT_WRITE = "tenant:write"
    TENANT_DELETE = "tenant:delete"
    TENANT_SETTINGS = "tenant:settings"
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    USER_ROLE_ASSIGN = "user:role_assign"
    CAMPAIGN_READ = "campaign:read"
    CAMPAIGN_WRITE = "campaign:write"
    CAMPAIGN_DELETE = "campaign:delete"
    CAMPAIGN_BUDGET = "campaign:budget"
    CAMPAIGN_RULES = "campaign:rules"
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_EXPORT = "analytics:export"
    ANALYTICS_ADVANCED = "analytics:advanced"
    BILLING_READ = "billing:read"
    BILLING_WRITE = "billing:write"
    BILLING_MANAGE = "billing:manage"
    SYSTEM_READ = "system:read"
    SYSTEM_WRITE = "system:write"
    SYSTEM_ADMIN = "system:admin"
    CONNECTOR_READ = "connector:read"
    CONNECTOR_WRITE = "connector:write"
    CONNECTOR_DELETE = "connector:delete"
    AUDIT_READ = "audit:read"
    AUDIT_EXPORT = "audit:export"
    ALERT_READ = "alert:read"
    ALERT_ACKNOWLEDGE = "alert:acknowledge"
    ALERT_RESOLVE = "alert:resolve"
    ALERT_CREATE = "alert:create"
    ASSET_READ = "asset:read"
    ASSET_WRITE = "asset:write"
    ASSET_DELETE = "asset:delete"
    RULE_READ = "rule:read"
    RULE_WRITE = "rule:write"
    RULE_DELETE = "rule:delete"
    RULE_EXECUTE = "rule:execute"
    # New client-related permissions
    CLIENT_READ = "client:read"
    CLIENT_WRITE = "client:write"
    CLIENT_DELETE = "client:delete"
    CLIENT_PORTAL = "client:portal"


# =============================================================================
# Role Hierarchy
# =============================================================================
ROLE_HIERARCHY: dict[UserRole, int] = {
    UserRole.SUPERADMIN: 100,
    UserRole.ADMIN: 80,
    UserRole.MANAGER: 50,
    UserRole.ANALYST: 30,
    UserRole.VIEWER: 10,
}


# =============================================================================
# RBAC Matrix — Resource → Role → Permission Level
# =============================================================================
# fmt: off
RBAC_MATRIX: dict[str, dict[UserRole, PermLevel]] = {
    # TENANT & SYSTEM
    "tenants.settings":       {UserRole.SUPERADMIN: PermLevel.FULL, UserRole.ADMIN: PermLevel.FULL, UserRole.MANAGER: PermLevel.NONE, UserRole.ANALYST: PermLevel.NONE, UserRole.VIEWER: PermLevel.NONE},
    "tenants.audit_logs":     {UserRole.SUPERADMIN: PermLevel.FULL, UserRole.ADMIN: PermLevel.VIEW, UserRole.MANAGER: PermLevel.NONE, UserRole.ANALYST: PermLevel.NONE, UserRole.VIEWER: PermLevel.NONE},
    "tenants.billing":        {UserRole.SUPERADMIN: PermLevel.FULL, UserRole.ADMIN: PermLevel.VIEW, UserRole.MANAGER: PermLevel.NONE, UserRole.ANALYST: PermLevel.NONE, UserRole.VIEWER: PermLevel.NONE},
    "tenants.feature_flags":  {UserRole.SUPERADMIN: PermLevel.FULL, UserRole.ADMIN: PermLevel.NONE, UserRole.MANAGER: PermLevel.NONE, UserRole.ANALYST: PermLevel.NONE, UserRole.VIEWER: PermLevel.NONE},

    # USER MANAGEMENT
    "users.manage":           {UserRole.SUPERADMIN: PermLevel.FULL, UserRole.ADMIN: PermLevel.EDIT, UserRole.MANAGER: PermLevel.NONE, UserRole.ANALYST: PermLevel.NONE, UserRole.VIEWER: PermLevel.NONE},
    "users.roles":            {UserRole.SUPERADMIN: PermLevel.FULL, UserRole.ADMIN: PermLevel.EDIT, UserRole.MANAGER: PermLevel.NONE, UserRole.ANALYST: PermLevel.NONE, UserRole.VIEWER: PermLevel.NONE},
    "users.list":             {UserRole.SUPERADMIN: PermLevel.FULL, UserRole.ADMIN: PermLevel.FULL, UserRole.MANAGER: PermLevel.VIEW, UserRole.ANALYST: PermLevel.VIEW, UserRole.VIEWER: PermLevel.NONE},
    "users.profile":          {UserRole.SUPERADMIN: PermLevel.FULL, UserRole.ADMIN: PermLevel.FULL, UserRole.MANAGER: PermLevel.FULL, UserRole.ANALYST: PermLevel.FULL, UserRole.VIEWER: PermLevel.FULL},

    # CLIENT MANAGEMENT
    "clients":                {UserRole.SUPERADMIN: PermLevel.FULL, UserRole.ADMIN: PermLevel.FULL, UserRole.MANAGER: PermLevel.EDIT, UserRole.ANALYST: PermLevel.VIEW, UserRole.VIEWER: PermLevel.VIEW},
    "clients.kpi_targets":    {UserRole.SUPERADMIN: PermLevel.FULL, UserRole.ADMIN: PermLevel.FULL, UserRole.MANAGER: PermLevel.EDIT, UserRole.ANALYST: PermLevel.NONE, UserRole.VIEWER: PermLevel.NONE},
    "clients.portal_users":   {UserRole.SUPERADMIN: PermLevel.FULL, UserRole.ADMIN: PermLevel.FULL, UserRole.MANAGER: PermLevel.EDIT, UserRole.ANALYST: PermLevel.NONE, UserRole.VIEWER: PermLevel.NONE},

    # CAMPAIGNS
    "campaigns":              {UserRole.SUPERADMIN: PermLevel.FULL, UserRole.ADMIN: PermLevel.FULL, UserRole.MANAGER: PermLevel.EDIT, UserRole.ANALYST: PermLevel.EDIT, UserRole.VIEWER: PermLevel.VIEW},
    "campaigns.metrics":      {UserRole.SUPERADMIN: PermLevel.FULL, UserRole.ADMIN: PermLevel.FULL, UserRole.MANAGER: PermLevel.FULL, UserRole.ANALYST: PermLevel.FULL, UserRole.VIEWER: PermLevel.VIEW},
    "campaigns.delete":       {UserRole.SUPERADMIN: PermLevel.FULL, UserRole.ADMIN: PermLevel.FULL, UserRole.MANAGER: PermLevel.FULL, UserRole.ANALYST: PermLevel.NONE, UserRole.VIEWER: PermLevel.NONE},

    # DEMOGRAPHICS & ANALYTICS
    "demographics":           {UserRole.SUPERADMIN: PermLevel.FULL, UserRole.ADMIN: PermLevel.FULL, UserRole.MANAGER: PermLevel.FULL, UserRole.ANALYST: PermLevel.FULL, UserRole.VIEWER: PermLevel.VIEW},
    "analytics":              {UserRole.SUPERADMIN: PermLevel.FULL, UserRole.ADMIN: PermLevel.FULL, UserRole.MANAGER: PermLevel.FULL, UserRole.ANALYST: PermLevel.FULL, UserRole.VIEWER: PermLevel.VIEW},
    "analytics.export":       {UserRole.SUPERADMIN: PermLevel.FULL, UserRole.ADMIN: PermLevel.FULL, UserRole.MANAGER: PermLevel.FULL, UserRole.ANALYST: PermLevel.EDIT, UserRole.VIEWER: PermLevel.EDIT},

    # ML / AI
    "ml.predictions":         {UserRole.SUPERADMIN: PermLevel.FULL, UserRole.ADMIN: PermLevel.FULL, UserRole.MANAGER: PermLevel.FULL, UserRole.ANALYST: PermLevel.VIEW, UserRole.VIEWER: PermLevel.NONE},
    "ml.models":              {UserRole.SUPERADMIN: PermLevel.FULL, UserRole.ADMIN: PermLevel.EDIT, UserRole.MANAGER: PermLevel.NONE, UserRole.ANALYST: PermLevel.NONE, UserRole.VIEWER: PermLevel.NONE},
    "ml.anomalies":           {UserRole.SUPERADMIN: PermLevel.FULL, UserRole.ADMIN: PermLevel.FULL, UserRole.MANAGER: PermLevel.FULL, UserRole.ANALYST: PermLevel.FULL, UserRole.VIEWER: PermLevel.NONE},

    # AUTOMATION RULES
    "rules":                  {UserRole.SUPERADMIN: PermLevel.FULL, UserRole.ADMIN: PermLevel.FULL, UserRole.MANAGER: PermLevel.EDIT, UserRole.ANALYST: PermLevel.VIEW, UserRole.VIEWER: PermLevel.NONE},
    "rules.history":          {UserRole.SUPERADMIN: PermLevel.FULL, UserRole.ADMIN: PermLevel.FULL, UserRole.MANAGER: PermLevel.FULL, UserRole.ANALYST: PermLevel.VIEW, UserRole.VIEWER: PermLevel.NONE},

    # REPORTS
    "reports":                {UserRole.SUPERADMIN: PermLevel.FULL, UserRole.ADMIN: PermLevel.FULL, UserRole.MANAGER: PermLevel.FULL, UserRole.ANALYST: PermLevel.EDIT, UserRole.VIEWER: PermLevel.VIEW},
    "reports.download":       {UserRole.SUPERADMIN: PermLevel.FULL, UserRole.ADMIN: PermLevel.FULL, UserRole.MANAGER: PermLevel.FULL, UserRole.ANALYST: PermLevel.FULL, UserRole.VIEWER: PermLevel.FULL},
    "reports.schedule":       {UserRole.SUPERADMIN: PermLevel.FULL, UserRole.ADMIN: PermLevel.FULL, UserRole.MANAGER: PermLevel.EDIT, UserRole.ANALYST: PermLevel.NONE, UserRole.VIEWER: PermLevel.NONE},

    # NOTIFICATIONS
    "notifications":          {UserRole.SUPERADMIN: PermLevel.FULL, UserRole.ADMIN: PermLevel.FULL, UserRole.MANAGER: PermLevel.FULL, UserRole.ANALYST: PermLevel.FULL, UserRole.VIEWER: PermLevel.VIEW},
    "notifications.whatsapp": {UserRole.SUPERADMIN: PermLevel.FULL, UserRole.ADMIN: PermLevel.FULL, UserRole.MANAGER: PermLevel.FULL, UserRole.ANALYST: PermLevel.FULL, UserRole.VIEWER: PermLevel.NONE},

    # CREATIVES
    "creatives":              {UserRole.SUPERADMIN: PermLevel.FULL, UserRole.ADMIN: PermLevel.FULL, UserRole.MANAGER: PermLevel.EDIT, UserRole.ANALYST: PermLevel.EDIT, UserRole.VIEWER: PermLevel.VIEW},
    "creatives.performance":  {UserRole.SUPERADMIN: PermLevel.FULL, UserRole.ADMIN: PermLevel.FULL, UserRole.MANAGER: PermLevel.FULL, UserRole.ANALYST: PermLevel.FULL, UserRole.VIEWER: PermLevel.VIEW},

    # SETTINGS
    "settings.integrations":  {UserRole.SUPERADMIN: PermLevel.FULL, UserRole.ADMIN: PermLevel.FULL, UserRole.MANAGER: PermLevel.NONE, UserRole.ANALYST: PermLevel.NONE, UserRole.VIEWER: PermLevel.NONE},
    "settings.whatsapp":      {UserRole.SUPERADMIN: PermLevel.FULL, UserRole.ADMIN: PermLevel.EDIT, UserRole.MANAGER: PermLevel.NONE, UserRole.ANALYST: PermLevel.NONE, UserRole.VIEWER: PermLevel.NONE},
}
# fmt: on


# =============================================================================
# Legacy Role → Permission Mapping (backwards compatible)
# =============================================================================
ROLE_PERMISSIONS: dict[str, set[Permission]] = {
    "superadmin": set(Permission),
    "admin": {
        Permission.TENANT_READ, Permission.TENANT_WRITE, Permission.TENANT_SETTINGS,
        Permission.USER_READ, Permission.USER_WRITE, Permission.USER_DELETE, Permission.USER_ROLE_ASSIGN,
        Permission.CAMPAIGN_READ, Permission.CAMPAIGN_WRITE, Permission.CAMPAIGN_DELETE,
        Permission.CAMPAIGN_BUDGET, Permission.CAMPAIGN_RULES,
        Permission.ANALYTICS_READ, Permission.ANALYTICS_EXPORT, Permission.ANALYTICS_ADVANCED,
        Permission.BILLING_READ, Permission.BILLING_WRITE,
        Permission.CONNECTOR_READ, Permission.CONNECTOR_WRITE, Permission.CONNECTOR_DELETE,
        Permission.AUDIT_READ,
        Permission.ALERT_READ, Permission.ALERT_ACKNOWLEDGE, Permission.ALERT_RESOLVE, Permission.ALERT_CREATE,
        Permission.ASSET_READ, Permission.ASSET_WRITE, Permission.ASSET_DELETE,
        Permission.RULE_READ, Permission.RULE_WRITE, Permission.RULE_DELETE, Permission.RULE_EXECUTE,
        Permission.CLIENT_READ, Permission.CLIENT_WRITE, Permission.CLIENT_DELETE, Permission.CLIENT_PORTAL,
    },
    "manager": {
        Permission.TENANT_READ, Permission.USER_READ, Permission.USER_WRITE,
        Permission.CAMPAIGN_READ, Permission.CAMPAIGN_WRITE, Permission.CAMPAIGN_BUDGET, Permission.CAMPAIGN_RULES,
        Permission.ANALYTICS_READ, Permission.ANALYTICS_EXPORT,
        Permission.BILLING_READ,
        Permission.CONNECTOR_READ, Permission.CONNECTOR_WRITE,
        Permission.ALERT_READ, Permission.ALERT_ACKNOWLEDGE, Permission.ALERT_RESOLVE,
        Permission.ASSET_READ, Permission.ASSET_WRITE,
        Permission.RULE_READ, Permission.RULE_WRITE, Permission.RULE_EXECUTE,
        Permission.CLIENT_READ, Permission.CLIENT_WRITE, Permission.CLIENT_PORTAL,
    },
    # ANALYST enum value — semantic role: media_buyer
    "analyst": {
        Permission.TENANT_READ,
        Permission.CAMPAIGN_READ, Permission.CAMPAIGN_WRITE, Permission.CAMPAIGN_BUDGET, Permission.CAMPAIGN_RULES,
        Permission.ANALYTICS_READ, Permission.ANALYTICS_EXPORT, Permission.ANALYTICS_ADVANCED,
        Permission.CONNECTOR_READ,
        Permission.ALERT_READ, Permission.ALERT_ACKNOWLEDGE,
        Permission.ASSET_READ, Permission.ASSET_WRITE,
        Permission.RULE_READ, Permission.RULE_WRITE, Permission.RULE_EXECUTE,
        Permission.CLIENT_READ,
    },
    # Keep legacy keys for backwards compat
    "media_buyer": {
        Permission.TENANT_READ,
        Permission.CAMPAIGN_READ, Permission.CAMPAIGN_WRITE, Permission.CAMPAIGN_BUDGET, Permission.CAMPAIGN_RULES,
        Permission.ANALYTICS_READ, Permission.ANALYTICS_EXPORT,
        Permission.CONNECTOR_READ,
        Permission.ALERT_READ, Permission.ALERT_ACKNOWLEDGE,
        Permission.ASSET_READ, Permission.ASSET_WRITE,
        Permission.RULE_READ, Permission.RULE_WRITE, Permission.RULE_EXECUTE,
        Permission.CLIENT_READ,
    },
    "account_manager": {
        Permission.TENANT_READ, Permission.USER_READ,
        Permission.CAMPAIGN_READ,
        Permission.ANALYTICS_READ, Permission.ANALYTICS_EXPORT,
        Permission.BILLING_READ,
        Permission.CONNECTOR_READ,
        Permission.ALERT_READ, Permission.ALERT_ACKNOWLEDGE,
        Permission.ASSET_READ,
        Permission.RULE_READ,
        Permission.CLIENT_READ, Permission.CLIENT_WRITE,
    },
    "viewer": {
        Permission.TENANT_READ,
        Permission.CAMPAIGN_READ,
        Permission.ANALYTICS_READ,
        Permission.ALERT_READ,
        Permission.ASSET_READ,
        Permission.CLIENT_READ,
    },
}


# =============================================================================
# Sidebar Visibility per Role
# =============================================================================
SIDEBAR_VISIBILITY: dict[UserRole, list[str]] = {
    UserRole.SUPERADMIN: [
        "dashboard", "clients", "campaigns", "demographics", "analytics",
        "reports", "creatives", "rules", "ml", "notifications",
        "settings", "users", "tenants", "audit", "billing", "profile",
    ],
    UserRole.ADMIN: [
        "dashboard", "clients", "campaigns", "demographics", "analytics",
        "reports", "creatives", "rules", "ml", "notifications",
        "settings", "users", "audit", "billing", "profile",
    ],
    UserRole.MANAGER: [
        "dashboard", "clients", "campaigns", "demographics", "analytics",
        "reports", "creatives", "rules", "notifications", "profile",
    ],
    UserRole.ANALYST: [
        "dashboard", "clients", "campaigns", "demographics", "analytics",
        "reports", "creatives", "rules", "notifications", "profile",
    ],
    UserRole.VIEWER: [
        "dashboard", "campaigns", "demographics", "analytics",
        "reports", "creatives", "notifications", "profile",
    ],
}


# =============================================================================
# Scope Functions
# =============================================================================
def get_resource_scope(role: UserRole) -> str:
    """Return the data-access scope label for a role."""
    if role == UserRole.SUPERADMIN:
        return "global"
    if role == UserRole.ADMIN:
        return "tenant"
    if role in (UserRole.MANAGER, UserRole.ANALYST):
        return "assigned"
    return "own_client"


def get_permission_level(role: UserRole, resource: str) -> PermLevel:
    """Look up the permission level a role has on a resource."""
    resource_perms = RBAC_MATRIX.get(resource)
    if not resource_perms:
        return PermLevel.NONE
    return resource_perms.get(role, PermLevel.NONE)


def can_manage_role(actor_role: UserRole, target_role: UserRole) -> bool:
    """Check if actor can assign/manage target_role. Prevents privilege escalation."""
    if actor_role == UserRole.SUPERADMIN:
        return True
    if actor_role == UserRole.ADMIN:
        return target_role in (UserRole.MANAGER, UserRole.ANALYST, UserRole.VIEWER)
    return False


# =============================================================================
# Client Scope Enforcement (async — requires DB)
# =============================================================================
async def get_accessible_client_ids(
    user_id: int,
    user_role: UserRole,
    tenant_id: int,
    db: AsyncSession,
    client_id: Optional[int] = None,
) -> Optional[list[int]]:
    """
    Determine which client IDs a user may access.

    Returns:
        None  — user can see ALL clients in tenant (SUPERADMIN, ADMIN)
        list  — specific client IDs (MANAGER, ANALYST via assignments; VIEWER via user.client_id)
    """
    if user_role in (UserRole.SUPERADMIN, UserRole.ADMIN):
        return None  # unrestricted within tenant

    if user_role == UserRole.VIEWER:
        if client_id:
            return [client_id]
        # Fetch from User.client_id
        from app.models import User
        result = await db.execute(
            select(User.client_id).where(User.id == user_id)
        )
        user_client_id = result.scalar_one_or_none()
        return [user_client_id] if user_client_id else []

    # MANAGER or ANALYST — fetch from client_assignments
    from app.models.client import ClientAssignment
    result = await db.execute(
        select(ClientAssignment.client_id).where(
            ClientAssignment.user_id == user_id
        )
    )
    return list(result.scalars().all())  # type: ignore[arg-type]


async def enforce_client_access(
    user_id: int,
    user_role: UserRole,
    client_id: int,
    tenant_id: int,
    db: AsyncSession,
    user_client_id: Optional[int] = None,
) -> None:
    """Raise 403 if user cannot access the specified client."""
    accessible = await get_accessible_client_ids(
        user_id, user_role, tenant_id, db, client_id=user_client_id
    )
    if accessible is None:
        return  # unrestricted
    if client_id not in accessible:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this client",
        )


async def enforce_campaign_access(
    user_id: int,
    user_role: UserRole,
    campaign_id: int,
    tenant_id: int,
    db: AsyncSession,
    user_client_id: Optional[int] = None,
) -> None:
    """Resolve campaign -> client_id, then check access."""
    from app.models import Campaign
    result = await db.execute(
        select(Campaign.client_id).where(
            Campaign.id == campaign_id,
            Campaign.tenant_id == tenant_id,
        )
    )
    campaign_client_id = result.scalar_one_or_none()
    if campaign_client_id is None:
        return  # campaign has no client (legacy), allow access
    await enforce_client_access(
        user_id, user_role, campaign_client_id, tenant_id, db,
        user_client_id=user_client_id,
    )


# =============================================================================
# Legacy Permission Helpers (backwards compatible)
# =============================================================================
def get_user_permissions(role: str) -> set[Permission]:
    """Get all permissions for a given role."""
    return ROLE_PERMISSIONS.get(role.lower(), set())


def has_permission(role: str, permission: Permission) -> bool:
    """Check if a role has a specific permission."""
    return permission in get_user_permissions(role)


def has_any_permission(role: str, permissions: list[Permission]) -> bool:
    """Check if a role has any of the specified permissions."""
    user_permissions = get_user_permissions(role)
    return any(p in user_permissions for p in permissions)


def has_all_permissions(role: str, permissions: list[Permission]) -> bool:
    """Check if a role has all of the specified permissions."""
    user_permissions = get_user_permissions(role)
    return all(p in user_permissions for p in permissions)


# =============================================================================
# FastAPI Dependency Factories
# =============================================================================
def require_permissions(
    permissions: list[Permission],
    require_all: bool = True,
) -> Callable:
    """FastAPI dependency that requires specific legacy Permission enums."""

    async def permission_checker(request: Request) -> None:
        role = getattr(request.state, "role", None)
        user_id = getattr(request.state, "user_id", None)
        if not role or not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if require_all:
            authorized = has_all_permissions(role, permissions)
        else:
            authorized = has_any_permission(role, permissions)
        if not authorized:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {[p.value for p in permissions]}",
            )

    return permission_checker


def require_permission(resource: str, min_level: PermLevel = PermLevel.VIEW) -> Callable:
    """
    FastAPI dependency factory using the new RBAC matrix.

    Usage:
        @router.get("/campaigns", dependencies=[Depends(require_permission("campaigns"))])
        @router.post("/campaigns", dependencies=[Depends(require_permission("campaigns", PermLevel.EDIT))])
    """

    async def checker(request: Request) -> None:
        role_str = getattr(request.state, "role", None)
        user_id = getattr(request.state, "user_id", None)
        if not role_str or not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        try:
            role = UserRole(role_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Unknown role: {role_str}",
            )
        level = get_permission_level(role, resource)
        if level < min_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions on '{resource}'. Requires level {min_level.name}, you have {level.name}.",
            )

    return checker


def require_role(roles: list[str]) -> Callable:
    """FastAPI dependency that requires one of the specified roles."""

    async def role_checker(request: Request) -> None:
        role = getattr(request.state, "role", None)
        user_id = getattr(request.state, "user_id", None)
        if not role or not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if role.lower() not in [r.lower() for r in roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role not authorized. Required: {roles}",
            )

    return role_checker


async def require_super_admin(request: Request) -> None:
    """FastAPI dependency that requires super admin role."""
    role = getattr(request.state, "role", None)
    user_id = getattr(request.state, "user_id", None)
    if not role or not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if role.lower() != "superadmin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required",
        )


def require_client_access(client_id_param: str = "client_id") -> Callable:
    """
    FastAPI dependency factory: extracts client_id from path params, checks access.

    Usage:
        @router.get("/clients/{client_id}", dependencies=[Depends(require_client_access())])
    """

    async def checker(
        request: Request,
        db: AsyncSession = Depends(get_async_session),
    ) -> None:
        role_str = getattr(request.state, "role", None)
        user_id = getattr(request.state, "user_id", None)
        tenant_id = getattr(request.state, "tenant_id", None)
        if not role_str or not user_id or not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        client_id = request.path_params.get(client_id_param)
        if client_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing path parameter: {client_id_param}",
            )
        try:
            client_id = int(client_id)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid client_id",
            )
        try:
            role = UserRole(role_str)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Unknown role: {role_str}",
            )
        await enforce_client_access(user_id, role, client_id, tenant_id, db)

    return checker


# =============================================================================
# Permission Decorator for Service Functions (legacy)
# =============================================================================
def check_permission(permission: Permission) -> Callable:
    """Decorator for service functions that need permission checking."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            role = kwargs.get("role")
            if not role:
                raise ValueError("Role argument required for permission-checked functions")
            if not has_permission(role, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {permission.value}",
                )
            return await func(*args, **kwargs)
        return wrapper
    return decorator
