# =============================================================================
# Stratum AI - Authentication & Authorization Module
# =============================================================================
"""
Authentication and authorization components including:
- RBAC permissions system
- JWT token handling
- Role and permission dependencies
"""

from app.auth.permissions import (
    ROLE_PERMISSIONS,
    Permission,
    get_user_permissions,
    has_permission,
    require_permissions,
    require_role,
    require_super_admin,
)

__all__ = [
    "Permission",
    "ROLE_PERMISSIONS",
    "require_permissions",
    "require_role",
    "require_super_admin",
    "has_permission",
    "get_user_permissions",
]
