# =============================================================================
# Stratum AI - Tenancy Dependencies
# =============================================================================
"""
FastAPI dependencies for tenant isolation and scoped queries.

These dependencies ensure all data access is properly tenant-scoped
and provide audit logging for super admin bypass operations.
"""

from typing import Optional, TypeVar

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import Select

from app.db.session import get_async_session
from app.models import User
from app.tenancy.context import TenantContext, get_tenant_context

# Type variable for generic model queries
T = TypeVar("T")


# Re-export get_async_session as get_db for convenience
async def get_db():
    """
    Dependency for database session.
    Re-exports get_async_session for convenience.
    """
    async for session in get_async_session():
        yield session


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_async_session),
) -> User:
    """
    FastAPI dependency that extracts the current authenticated user.

    Raises 401 if not authenticated.
    """
    user_id = getattr(request.state, "user_id", None)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    return user


async def get_tenant(request: Request) -> TenantContext:
    """
    FastAPI dependency that extracts and validates tenant context.

    This is the primary dependency for tenant-scoped routes.
    Raises 401 if not authenticated or 403 if tenant access denied.

    Usage:
        @router.get("/campaigns")
        async def list_campaigns(
            tenant: TenantContext = Depends(get_tenant)
        ):
            campaigns = await service.get_campaigns(tenant.tenant_id)
            ...

    Args:
        request: FastAPI Request

    Returns:
        Validated TenantContext

    Raises:
        HTTPException: 401 if not authenticated, 403 if invalid tenant
    """
    context = get_tenant_context(request)

    if not context:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return context


async def get_tenant_id(request: Request) -> int:
    """
    FastAPI dependency that returns just the tenant_id.

    Use this when you only need the tenant_id for query filtering.

    Usage:
        @router.get("/alerts")
        async def list_alerts(
            tenant_id: int = Depends(get_tenant_id)
        ):
            ...
    """
    context = await get_tenant(request)
    return context.tenant_id


def require_tenant(tenant_id_param: str = "tenant_id"):
    """
    Factory for creating tenant validation dependencies.

    Validates that the URL parameter tenant_id matches the
    authenticated user's tenant (unless super admin bypass).

    Args:
        tenant_id_param: Name of the URL parameter containing tenant_id

    Usage:
        @router.get("/tenant/{tenant_id}/dashboard")
        async def get_dashboard(
            tenant_id: int,
            _: None = Depends(require_tenant("tenant_id"))
        ):
            ...
    """

    async def validator(request: Request) -> TenantContext:
        context = await get_tenant(request)

        # Get tenant_id from path parameters
        path_tenant_id = request.path_params.get(tenant_id_param)

        if path_tenant_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Missing {tenant_id_param} in path",
            )

        try:
            path_tenant_id = int(path_tenant_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid {tenant_id_param}: must be integer",
            )

        # Super admin with bypass can access any tenant
        if context.can_bypass_tenant:
            # Log the bypass for audit
            await _log_super_admin_bypass(
                request=request,
                context=context,
                target_tenant_id=path_tenant_id,
            )
            # Return context with target tenant for query purposes
            context.tenant_id = path_tenant_id
            return context

        # Regular users must match their tenant
        if context.tenant_id != path_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant",
            )

        return context

    return validator


async def with_super_admin_bypass(request: Request) -> tuple[TenantContext, bool]:
    """
    Dependency that returns context and whether bypass is active.

    Use this when logic differs for bypass vs normal access.

    Usage:
        @router.get("/tenants")
        async def list_tenants(
            ctx_bypass: tuple = Depends(with_super_admin_bypass)
        ):
            context, is_bypass = ctx_bypass
            if is_bypass:
                # Return all tenants
                ...
            else:
                # Return only user's tenant
                ...
    """
    context = await get_tenant(request)
    return (context, context.can_bypass_tenant)


def tenant_query(
    session: AsyncSession,
    model: type[T],
    tenant_id: int,
    *,
    include_deleted: bool = False,
) -> Select:
    """
    Create a tenant-scoped SQLAlchemy select query.

    This helper ensures all queries are properly filtered by tenant_id
    and optionally excludes soft-deleted records.

    Args:
        session: Async database session
        model: SQLAlchemy model class
        tenant_id: Tenant ID to filter by
        include_deleted: If True, include soft-deleted records

    Returns:
        SQLAlchemy Select query with tenant filter applied

    Usage:
        query = tenant_query(db, Campaign, tenant.tenant_id)
        result = await db.execute(query.where(Campaign.status == "active"))
        campaigns = result.scalars().all()
    """
    query = select(model)

    # Add tenant filter if model has tenant_id column
    if hasattr(model, "tenant_id"):
        query = query.where(model.tenant_id == tenant_id)

    # Exclude soft-deleted unless explicitly requested
    if not include_deleted and hasattr(model, "is_deleted"):
        query = query.where(model.is_deleted == False)

    return query


async def _log_super_admin_bypass(
    request: Request,
    context: TenantContext,
    target_tenant_id: int,
) -> None:
    """
    Log super admin bypass access for audit purposes.

    This is called automatically when a super admin uses
    X-Superadmin-Bypass header to access another tenant's data.
    """
    try:
        # Get database session
        async for db in get_async_session():
            from app.models import AuditLog

            # Create audit log entry
            audit_entry = AuditLog(
                tenant_id=target_tenant_id,
                user_id=context.user_id,
                action="superadmin_bypass",
                resource_type="tenant",
                resource_id=str(target_tenant_id),
                changes={
                    "source_tenant_id": context.tenant_id,
                    "target_tenant_id": target_tenant_id,
                    "endpoint": str(request.url.path),
                    "method": request.method,
                    "request_id": context.request_id,
                },
                ip_address=request.client.host if request.client else None,
                user_agent=request.headers.get("User-Agent"),
            )
            db.add(audit_entry)
            await db.commit()
            break
    except Exception:
        # Don't fail the request if audit logging fails
        # In production, this should be logged to an error tracking service
        pass


class TenantScopedService:
    """
    Base class for tenant-scoped services.

    Provides common patterns for tenant isolation in service classes.

    Usage:
        class CampaignService(TenantScopedService):
            async def get_campaigns(self) -> List[Campaign]:
                query = self.tenant_query(Campaign)
                result = await self.db.execute(query)
                return result.scalars().all()
    """

    def __init__(
        self,
        db: AsyncSession,
        tenant_id: int,
        user_id: Optional[int] = None,
        role: Optional[str] = None,
    ):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id
        self.role = role

    def tenant_query(
        self,
        model: type[T],
        include_deleted: bool = False,
    ) -> Select:
        """Create a tenant-scoped query."""
        return tenant_query(
            self.db,
            model,
            self.tenant_id,
            include_deleted=include_deleted,
        )

    @classmethod
    def from_context(
        cls,
        db: AsyncSession,
        context: TenantContext,
    ) -> "TenantScopedService":
        """Create service instance from TenantContext."""
        return cls(
            db=db,
            tenant_id=context.tenant_id,
            user_id=context.user_id,
            role=context.role,
        )
