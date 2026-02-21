# =============================================================================
# Stratum AI - RBAC Permissions System
# =============================================================================
"""
Role-Based Access Control (RBAC) implementation.

Roles:
- super_admin: Full platform access, cross-tenant operations
- tenant_admin: Full tenant access, user management
- media_buyer: Campaign management, budget control
- analyst: Read-only analytics, reports
- account_manager: Client relationship, limited campaign access

Permissions are granular and can be checked individually or in combination.
"""

from enum import Enum
from functools import wraps
from typing import Callable, List, Optional, Set, TYPE_CHECKING

from fastapi import HTTPException, Request, status

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class PermLevel(int, Enum):
    """Permission level for resource-scoped access control (integer-comparable)."""

    NONE = 0
    VIEW = 1
    EDIT = 2
    FULL = 3


# Minimum roles for each PermLevel
_PERM_LEVEL_ROLES: dict[PermLevel, set[str]] = {
    PermLevel.VIEW: {"superadmin", "admin", "manager", "analyst", "account_manager", "viewer"},
    PermLevel.EDIT: {"superadmin", "admin", "manager"},
    PermLevel.FULL: {"superadmin", "admin"},
}


class Permission(str, Enum):
    """
    Granular permissions for RBAC.
    Naming convention: RESOURCE_ACTION
    """

    # Tenant permissions
    TENANT_READ = "tenant:read"
    TENANT_WRITE = "tenant:write"
    TENANT_DELETE = "tenant:delete"
    TENANT_SETTINGS = "tenant:settings"

    # User management
    USER_READ = "user:read"
    USER_WRITE = "user:write"
    USER_DELETE = "user:delete"
    USER_ROLE_ASSIGN = "user:role_assign"

    # Campaign permissions
    CAMPAIGN_READ = "campaign:read"
    CAMPAIGN_WRITE = "campaign:write"
    CAMPAIGN_DELETE = "campaign:delete"
    CAMPAIGN_BUDGET = "campaign:budget"
    CAMPAIGN_RULES = "campaign:rules"

    # Analytics permissions
    ANALYTICS_READ = "analytics:read"
    ANALYTICS_EXPORT = "analytics:export"
    ANALYTICS_ADVANCED = "analytics:advanced"

    # Billing permissions
    BILLING_READ = "billing:read"
    BILLING_WRITE = "billing:write"
    BILLING_MANAGE = "billing:manage"

    # System permissions (super admin only)
    SYSTEM_READ = "system:read"
    SYSTEM_WRITE = "system:write"
    SYSTEM_ADMIN = "system:admin"

    # Connector/Integration permissions
    CONNECTOR_READ = "connector:read"
    CONNECTOR_WRITE = "connector:write"
    CONNECTOR_DELETE = "connector:delete"

    # Audit permissions
    AUDIT_READ = "audit:read"
    AUDIT_EXPORT = "audit:export"

    # Alert permissions
    ALERT_READ = "alert:read"
    ALERT_ACKNOWLEDGE = "alert:acknowledge"
    ALERT_RESOLVE = "alert:resolve"
    ALERT_CREATE = "alert:create"

    # Asset/Creative permissions
    ASSET_READ = "asset:read"
    ASSET_WRITE = "asset:write"
    ASSET_DELETE = "asset:delete"

    # Rule permissions
    RULE_READ = "rule:read"
    RULE_WRITE = "rule:write"
    RULE_DELETE = "rule:delete"
    RULE_EXECUTE = "rule:execute"

    # Client permissions
    CLIENT_READ = "client:read"
    CLIENT_WRITE = "client:write"
    CLIENT_DELETE = "client:delete"
    CLIENT_PORTAL = "client:portal"


# =============================================================================
# Role to Permission Mapping
# =============================================================================

ROLE_PERMISSIONS: dict[str, Set[Permission]] = {
    # Super Admin: Full platform access
    "superadmin": {
        # All tenant permissions
        Permission.TENANT_READ,
        Permission.TENANT_WRITE,
        Permission.TENANT_DELETE,
        Permission.TENANT_SETTINGS,
        # All user permissions
        Permission.USER_READ,
        Permission.USER_WRITE,
        Permission.USER_DELETE,
        Permission.USER_ROLE_ASSIGN,
        # All campaign permissions
        Permission.CAMPAIGN_READ,
        Permission.CAMPAIGN_WRITE,
        Permission.CAMPAIGN_DELETE,
        Permission.CAMPAIGN_BUDGET,
        Permission.CAMPAIGN_RULES,
        # All analytics permissions
        Permission.ANALYTICS_READ,
        Permission.ANALYTICS_EXPORT,
        Permission.ANALYTICS_ADVANCED,
        # All billing permissions
        Permission.BILLING_READ,
        Permission.BILLING_WRITE,
        Permission.BILLING_MANAGE,
        # System permissions
        Permission.SYSTEM_READ,
        Permission.SYSTEM_WRITE,
        Permission.SYSTEM_ADMIN,
        # All connector permissions
        Permission.CONNECTOR_READ,
        Permission.CONNECTOR_WRITE,
        Permission.CONNECTOR_DELETE,
        # All audit permissions
        Permission.AUDIT_READ,
        Permission.AUDIT_EXPORT,
        # All alert permissions
        Permission.ALERT_READ,
        Permission.ALERT_ACKNOWLEDGE,
        Permission.ALERT_RESOLVE,
        Permission.ALERT_CREATE,
        # All asset permissions
        Permission.ASSET_READ,
        Permission.ASSET_WRITE,
        Permission.ASSET_DELETE,
        # All rule permissions
        Permission.RULE_READ,
        Permission.RULE_WRITE,
        Permission.RULE_DELETE,
        Permission.RULE_EXECUTE,
        # All client permissions
        Permission.CLIENT_READ,
        Permission.CLIENT_WRITE,
        Permission.CLIENT_DELETE,
        Permission.CLIENT_PORTAL,
    },

    # Tenant Admin: Full tenant access
    "admin": {
        Permission.TENANT_READ,
        Permission.TENANT_WRITE,
        Permission.TENANT_SETTINGS,
        Permission.USER_READ,
        Permission.USER_WRITE,
        Permission.USER_DELETE,
        Permission.USER_ROLE_ASSIGN,
        Permission.CAMPAIGN_READ,
        Permission.CAMPAIGN_WRITE,
        Permission.CAMPAIGN_DELETE,
        Permission.CAMPAIGN_BUDGET,
        Permission.CAMPAIGN_RULES,
        Permission.ANALYTICS_READ,
        Permission.ANALYTICS_EXPORT,
        Permission.ANALYTICS_ADVANCED,
        Permission.BILLING_READ,
        Permission.BILLING_WRITE,
        Permission.CONNECTOR_READ,
        Permission.CONNECTOR_WRITE,
        Permission.CONNECTOR_DELETE,
        Permission.AUDIT_READ,
        Permission.ALERT_READ,
        Permission.ALERT_ACKNOWLEDGE,
        Permission.ALERT_RESOLVE,
        Permission.ALERT_CREATE,
        Permission.ASSET_READ,
        Permission.ASSET_WRITE,
        Permission.ASSET_DELETE,
        Permission.RULE_READ,
        Permission.RULE_WRITE,
        Permission.RULE_DELETE,
        Permission.RULE_EXECUTE,
        # All client permissions
        Permission.CLIENT_READ,
        Permission.CLIENT_WRITE,
        Permission.CLIENT_DELETE,
        Permission.CLIENT_PORTAL,
    },

    # Manager: Campaign and team management
    "manager": {
        Permission.TENANT_READ,
        Permission.USER_READ,
        Permission.USER_WRITE,
        Permission.CAMPAIGN_READ,
        Permission.CAMPAIGN_WRITE,
        Permission.CAMPAIGN_BUDGET,
        Permission.CAMPAIGN_RULES,
        Permission.ANALYTICS_READ,
        Permission.ANALYTICS_EXPORT,
        Permission.BILLING_READ,
        Permission.CONNECTOR_READ,
        Permission.CONNECTOR_WRITE,
        Permission.ALERT_READ,
        Permission.ALERT_ACKNOWLEDGE,
        Permission.ALERT_RESOLVE,
        Permission.ASSET_READ,
        Permission.ASSET_WRITE,
        Permission.RULE_READ,
        Permission.RULE_WRITE,
        Permission.RULE_EXECUTE,
        Permission.CLIENT_READ,
        Permission.CLIENT_WRITE,
        Permission.CLIENT_PORTAL,
    },

    # Media Buyer: Campaign execution focus
    "media_buyer": {
        Permission.TENANT_READ,
        Permission.CAMPAIGN_READ,
        Permission.CAMPAIGN_WRITE,
        Permission.CAMPAIGN_BUDGET,
        Permission.CAMPAIGN_RULES,
        Permission.ANALYTICS_READ,
        Permission.ANALYTICS_EXPORT,
        Permission.CONNECTOR_READ,
        Permission.ALERT_READ,
        Permission.ALERT_ACKNOWLEDGE,
        Permission.ASSET_READ,
        Permission.ASSET_WRITE,
        Permission.RULE_READ,
        Permission.RULE_WRITE,
        Permission.RULE_EXECUTE,
    },

    # Analyst: Read-only analytics focus
    "analyst": {
        Permission.TENANT_READ,
        Permission.CAMPAIGN_READ,
        Permission.ANALYTICS_READ,
        Permission.ANALYTICS_EXPORT,
        Permission.ANALYTICS_ADVANCED,
        Permission.CONNECTOR_READ,
        Permission.ALERT_READ,
        Permission.ASSET_READ,
        Permission.RULE_READ,
        Permission.CLIENT_READ,
    },

    # Account Manager: Client relationship focus
    "account_manager": {
        Permission.TENANT_READ,
        Permission.USER_READ,
        Permission.CAMPAIGN_READ,
        Permission.ANALYTICS_READ,
        Permission.ANALYTICS_EXPORT,
        Permission.BILLING_READ,
        Permission.CONNECTOR_READ,
        Permission.ALERT_READ,
        Permission.ALERT_ACKNOWLEDGE,
        Permission.ASSET_READ,
        Permission.RULE_READ,
    },

    # Viewer: Minimal read access
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
# RBAC Matrix: resource → role → PermLevel
# =============================================================================

# Import UserRole lazily to avoid circular imports
from app.base_models import UserRole

RBAC_MATRIX: dict[str, dict[UserRole, PermLevel]] = {
    "campaigns": {
        UserRole.SUPERADMIN: PermLevel.FULL,
        UserRole.ADMIN: PermLevel.FULL,
        UserRole.MANAGER: PermLevel.EDIT,
        UserRole.ANALYST: PermLevel.EDIT,
        UserRole.VIEWER: PermLevel.VIEW,
    },
    "campaigns.delete": {
        UserRole.SUPERADMIN: PermLevel.FULL,
        UserRole.ADMIN: PermLevel.FULL,
        UserRole.MANAGER: PermLevel.NONE,
        UserRole.ANALYST: PermLevel.NONE,
        UserRole.VIEWER: PermLevel.NONE,
    },
    "clients": {
        UserRole.SUPERADMIN: PermLevel.FULL,
        UserRole.ADMIN: PermLevel.FULL,
        UserRole.MANAGER: PermLevel.EDIT,
        UserRole.ANALYST: PermLevel.VIEW,
        UserRole.VIEWER: PermLevel.VIEW,
    },
    "clients.portal_users": {
        UserRole.SUPERADMIN: PermLevel.FULL,
        UserRole.ADMIN: PermLevel.FULL,
        UserRole.MANAGER: PermLevel.EDIT,
        UserRole.ANALYST: PermLevel.NONE,
        UserRole.VIEWER: PermLevel.NONE,
    },
    "analytics": {
        UserRole.SUPERADMIN: PermLevel.FULL,
        UserRole.ADMIN: PermLevel.FULL,
        UserRole.MANAGER: PermLevel.EDIT,
        UserRole.ANALYST: PermLevel.EDIT,
        UserRole.VIEWER: PermLevel.VIEW,
    },
    "reports": {
        UserRole.SUPERADMIN: PermLevel.FULL,
        UserRole.ADMIN: PermLevel.FULL,
        UserRole.MANAGER: PermLevel.FULL,
        UserRole.ANALYST: PermLevel.EDIT,
        UserRole.VIEWER: PermLevel.VIEW,
    },
    "reports.download": {
        UserRole.SUPERADMIN: PermLevel.FULL,
        UserRole.ADMIN: PermLevel.FULL,
        UserRole.MANAGER: PermLevel.FULL,
        UserRole.ANALYST: PermLevel.FULL,
        UserRole.VIEWER: PermLevel.FULL,
    },
    "tenants.settings": {
        UserRole.SUPERADMIN: PermLevel.FULL,
        UserRole.ADMIN: PermLevel.FULL,
        UserRole.MANAGER: PermLevel.NONE,
        UserRole.ANALYST: PermLevel.NONE,
        UserRole.VIEWER: PermLevel.NONE,
    },
    "users.manage": {
        UserRole.SUPERADMIN: PermLevel.FULL,
        UserRole.ADMIN: PermLevel.FULL,
        UserRole.MANAGER: PermLevel.NONE,
        UserRole.ANALYST: PermLevel.NONE,
        UserRole.VIEWER: PermLevel.NONE,
    },
    "connectors": {
        UserRole.SUPERADMIN: PermLevel.FULL,
        UserRole.ADMIN: PermLevel.FULL,
        UserRole.MANAGER: PermLevel.EDIT,
        UserRole.ANALYST: PermLevel.VIEW,
        UserRole.VIEWER: PermLevel.NONE,
    },
    "billing": {
        UserRole.SUPERADMIN: PermLevel.FULL,
        UserRole.ADMIN: PermLevel.FULL,
        UserRole.MANAGER: PermLevel.VIEW,
        UserRole.ANALYST: PermLevel.NONE,
        UserRole.VIEWER: PermLevel.NONE,
    },
    "audit": {
        UserRole.SUPERADMIN: PermLevel.FULL,
        UserRole.ADMIN: PermLevel.VIEW,
        UserRole.MANAGER: PermLevel.NONE,
        UserRole.ANALYST: PermLevel.NONE,
        UserRole.VIEWER: PermLevel.NONE,
    },
}


def get_permission_level(role: UserRole, resource: str) -> PermLevel:
    """
    Look up the PermLevel for a role on a specific resource.

    Falls back to PermLevel.NONE if the resource or role is not in the matrix.
    """
    resource_map = RBAC_MATRIX.get(resource)
    if resource_map is None:
        return PermLevel.NONE
    return resource_map.get(role, PermLevel.NONE)


# =============================================================================
# Role Hierarchy (numeric for comparisons)
# =============================================================================

ROLE_HIERARCHY: dict[UserRole, int] = {
    UserRole.SUPERADMIN: 100,
    UserRole.ADMIN: 80,
    UserRole.MANAGER: 60,
    UserRole.ANALYST: 40,
    UserRole.VIEWER: 10,
}


def can_manage_role(actor_role: UserRole, target_role: UserRole) -> bool:
    """
    Check whether *actor_role* can assign / manage *target_role*.

    Only SUPERADMIN and ADMIN may manage roles, and they may only
    assign roles **strictly below** their own hierarchy level
    (prevents privilege escalation).
    """
    if actor_role not in {UserRole.SUPERADMIN, UserRole.ADMIN}:
        return False
    if actor_role == UserRole.SUPERADMIN:
        return True  # superadmin can assign anything
    return ROLE_HIERARCHY[target_role] < ROLE_HIERARCHY[actor_role]


# =============================================================================
# Resource Scope per Role
# =============================================================================

_ROLE_SCOPE: dict[UserRole, str] = {
    UserRole.SUPERADMIN: "global",
    UserRole.ADMIN: "tenant",
    UserRole.MANAGER: "assigned",
    UserRole.ANALYST: "assigned",
    UserRole.VIEWER: "own_client",
}


def get_resource_scope(role: UserRole) -> str:
    """Return the scope label for a given role."""
    return _ROLE_SCOPE.get(role, "none")


# =============================================================================
# Sidebar Visibility per Role
# =============================================================================

SIDEBAR_VISIBILITY: dict[UserRole, set[str]] = {
    UserRole.SUPERADMIN: {
        "dashboard", "campaigns", "analytics", "clients", "users",
        "settings", "connectors", "billing", "audit", "tenants",
        "reports", "alerts", "profile",
    },
    UserRole.ADMIN: {
        "dashboard", "campaigns", "analytics", "clients", "users",
        "settings", "connectors", "billing", "audit", "reports",
        "alerts", "profile",
    },
    UserRole.MANAGER: {
        "dashboard", "campaigns", "analytics", "clients",
        "connectors", "reports", "alerts", "profile",
    },
    UserRole.ANALYST: {
        "dashboard", "campaigns", "analytics", "reports",
        "alerts", "profile",
    },
    UserRole.VIEWER: {
        "dashboard", "campaigns", "analytics", "profile",
    },
}


# =============================================================================
# Permission Helper Functions
# =============================================================================

def get_user_permissions(role: str) -> Set[Permission]:
    """
    Get all permissions for a given role.

    Args:
        role: User role string (e.g., "admin", "analyst")

    Returns:
        Set of Permission enums the role has access to
    """
    return ROLE_PERMISSIONS.get(role.lower(), set())


def has_permission(role: str, permission: Permission) -> bool:
    """
    Check if a role has a specific permission.

    Args:
        role: User role string
        permission: Permission to check

    Returns:
        True if role has the permission
    """
    user_permissions = get_user_permissions(role)
    return permission in user_permissions


def has_any_permission(role: str, permissions: List[Permission]) -> bool:
    """
    Check if a role has any of the specified permissions.

    Args:
        role: User role string
        permissions: List of permissions to check

    Returns:
        True if role has at least one of the permissions
    """
    user_permissions = get_user_permissions(role)
    return any(p in user_permissions for p in permissions)


def has_all_permissions(role: str, permissions: List[Permission]) -> bool:
    """
    Check if a role has all of the specified permissions.

    Args:
        role: User role string
        permissions: List of permissions to check

    Returns:
        True if role has all of the permissions
    """
    user_permissions = get_user_permissions(role)
    return all(p in user_permissions for p in permissions)


# =============================================================================
# FastAPI Dependency Decorators
# =============================================================================

def require_permissions(
    permissions: List[Permission],
    require_all: bool = True,
) -> Callable:
    """
    FastAPI dependency that requires specific permissions.

    Args:
        permissions: List of required permissions
        require_all: If True, all permissions are required. If False, any one is sufficient.

    Returns:
        Dependency function that raises HTTPException if unauthorized

    Usage:
        @router.get("/campaigns")
        async def list_campaigns(
            request: Request,
            _: None = Depends(require_permissions([Permission.CAMPAIGN_READ]))
        ):
            ...
    """
    async def permission_checker(request: Request) -> None:
        # Get user role from request state (set by middleware)
        role = getattr(request.state, "role", None)
        user_id = getattr(request.state, "user_id", None)

        if not role or not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check permissions based on require_all flag
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


def require_role(roles: List[str]) -> Callable:
    """
    FastAPI dependency that requires one of the specified roles.

    Args:
        roles: List of allowed role strings

    Returns:
        Dependency function that raises HTTPException if unauthorized

    Usage:
        @router.post("/users")
        async def create_user(
            request: Request,
            _: None = Depends(require_role(["admin", "superadmin"]))
        ):
            ...
    """
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
    """
    FastAPI dependency that requires super admin role.

    This is a convenience dependency for routes that should only
    be accessible to super admins (platform-level operations).

    Usage:
        @router.get("/system/health")
        async def system_health(
            request: Request,
            _: None = Depends(require_super_admin)
        ):
            ...
    """
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


# =============================================================================
# Permission Decorator for Service Functions
# =============================================================================

def check_permission(permission: Permission):
    """
    Decorator for service functions that need permission checking.

    The decorated function must have 'role' as a keyword argument.

    Usage:
        @check_permission(Permission.CAMPAIGN_WRITE)
        async def create_campaign(data: dict, role: str, tenant_id: int):
            ...
    """
    def decorator(func: Callable):
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


# =============================================================================
# Resource-Level Permission (PermLevel) Dependency
# =============================================================================

def require_permission(resource: str, level: PermLevel) -> Callable:
    """
    FastAPI dependency that checks the user's role against a PermLevel.

    Args:
        resource: Resource name (e.g., "clients", "clients.portal_users")
        level: Required PermLevel (VIEW, EDIT, FULL)

    Usage:
        @router.post("/clients", dependencies=[Depends(require_permission("clients", PermLevel.FULL))])
    """
    async def _checker(request: Request) -> None:
        role = getattr(request.state, "role", None)
        user_id = getattr(request.state, "user_id", None)

        if not role or not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )

        allowed_roles = _PERM_LEVEL_ROLES.get(level, set())
        if role.lower() not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions for {resource} ({level.value})",
            )

    return _checker


# =============================================================================
# Client-Scope Access Helpers
# =============================================================================

async def enforce_client_access(
    *,
    user_id: int,
    user_role: str,
    client_id: int,
    tenant_id: int,
    db: "AsyncSession",
    user_client_id: Optional[int] = None,
) -> None:
    """
    Raise 403 unless the user is allowed to access the given client.

    Admins and superadmins have unrestricted access.
    Other roles must be explicitly assigned to the client, or have a
    matching ``client_id`` on their user record.
    """
    role = user_role if isinstance(user_role, str) else user_role.value
    if role.lower() in {"superadmin", "admin"}:
        return

    # If the user's own profile is scoped to this client, allow
    if user_client_id is not None and user_client_id == client_id:
        return

    # Look up accessible client IDs (uses the same logic as get_accessible_client_ids)
    accessible = await get_accessible_client_ids(
        user_id=user_id,
        user_role=user_role,
        tenant_id=tenant_id,
        db=db,
        client_id=user_client_id,
    )

    if accessible is None:
        return  # unrestricted

    if client_id in accessible:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You do not have access to this client",
    )


async def get_accessible_client_ids(
    *,
    user_id: int,
    user_role: str,
    tenant_id: int,
    db: "AsyncSession",
    client_id: Optional[int] = None,
) -> Optional[List[int]]:
    """
    Return the list of client IDs the user may see, or *None* if
    the user has unrestricted access (admin/superadmin).

    Returns:
        ``None``  – unrestricted (don't filter)
        ``list``  – restrict query to these IDs only
    """
    from sqlalchemy import select

    role = user_role if isinstance(user_role, str) else user_role.value
    if role.lower() in {"superadmin", "admin"}:
        return None  # unrestricted

    # Viewer: scoped to their own client_id
    if role.lower() == "viewer":
        if client_id is not None:
            return [client_id]
        # Look up the viewer's client_id from User table
        from app.base_models import User as UserModel
        result = await db.execute(
            select(UserModel.client_id).where(UserModel.id == user_id)
        )
        user_client_id = result.scalar_one_or_none()
        return [user_client_id] if user_client_id else []

    # Manager / Analyst: scoped to assigned clients
    from app.models.client import ClientAssignment

    result = await db.execute(
        select(ClientAssignment.client_id).where(
            ClientAssignment.user_id == user_id,
        )
    )
    return list(result.scalars().all())
