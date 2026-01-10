# =============================================================================
# Stratum AI - Multi-Tenancy Module
# =============================================================================
"""
Multi-tenancy support including:
- TenantContext: Request-scoped tenant information
- Tenant isolation dependencies
- Cross-tenant bypass for super admin (with audit)
"""

from app.tenancy.context import TenantContext, get_tenant_context
from app.tenancy.deps import (
    get_tenant,
    get_tenant_id,
    require_tenant,
    tenant_query,
    with_super_admin_bypass,
)

__all__ = [
    "TenantContext",
    "get_tenant_context",
    "get_tenant",
    "get_tenant_id",
    "require_tenant",
    "tenant_query",
    "with_super_admin_bypass",
]
