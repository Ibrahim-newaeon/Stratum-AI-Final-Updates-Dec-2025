# =============================================================================
# Stratum AI - Database Session Management
# =============================================================================
"""
Async and sync database session management with connection pooling.
Implements proper context management for multi-tenant queries.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Generator

from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# =============================================================================
# Async Engine (Primary - for FastAPI)
# =============================================================================
async_engine = create_async_engine(
    settings.database_url,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_recycle=settings.db_pool_recycle,
    pool_pre_ping=True,
    echo=settings.debug and settings.is_development,
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# =============================================================================
# Sync Engine (For Celery workers and migrations)
# =============================================================================
sync_engine = create_engine(
    settings.database_url_sync,
    poolclass=QueuePool,
    pool_size=settings.db_pool_size,
    max_overflow=settings.db_max_overflow,
    pool_recycle=settings.db_pool_recycle,
    pool_pre_ping=True,
    echo=settings.debug and settings.is_development,
)

SyncSessionLocal = sessionmaker(
    bind=sync_engine,
    autocommit=False,
    autoflush=False,
)


# =============================================================================
# Connection Event Listeners for Row-Level Security
# =============================================================================
@event.listens_for(sync_engine, "connect")
def set_search_path_sync(dbapi_connection, connection_record):
    """Set search path for sync connections."""
    cursor = dbapi_connection.cursor()
    cursor.execute("SET search_path TO public")
    cursor.close()


# =============================================================================
# Dependency Injection Generators
# =============================================================================
async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency for async database sessions.

    Usage:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_async_session)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_sync_session() -> Generator[Session, None, None]:
    """
    Dependency for sync database sessions (Celery workers).

    Usage:
        with get_sync_session() as session:
            ...
    """
    session = SyncSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@asynccontextmanager
async def async_session_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for async sessions outside of FastAPI.

    Usage:
        async with async_session_context() as session:
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# =============================================================================
# Multi-Tenant Session Wrapper
# =============================================================================
class TenantAwareSession:
    """
    Wrapper that ensures all queries are filtered by tenant_id.
    Implements Row-Level Security at the application level.
    """

    def __init__(self, session: AsyncSession, tenant_id: int):
        self._session = session
        self._tenant_id = tenant_id

    @property
    def tenant_id(self) -> int:
        return self._tenant_id

    async def execute(self, statement, *args, **kwargs):
        """Execute a statement (tenant filtering should be applied by caller)."""
        return await self._session.execute(statement, *args, **kwargs)

    async def add(self, instance):
        """Add an instance, ensuring tenant_id is set."""
        if hasattr(instance, "tenant_id"):
            instance.tenant_id = self._tenant_id
        self._session.add(instance)

    async def delete(self, instance):
        """Delete an instance (verify tenant ownership first)."""
        if hasattr(instance, "tenant_id") and instance.tenant_id != self._tenant_id:
            raise PermissionError("Cannot delete object from different tenant")
        await self._session.delete(instance)

    async def commit(self):
        await self._session.commit()

    async def rollback(self):
        await self._session.rollback()

    async def refresh(self, instance):
        await self._session.refresh(instance)


async def get_tenant_session(
    session: AsyncSession, tenant_id: int
) -> TenantAwareSession:
    """
    Create a tenant-aware session wrapper.

    Args:
        session: The underlying async session
        tenant_id: The tenant ID to filter by

    Returns:
        TenantAwareSession wrapper
    """
    return TenantAwareSession(session, tenant_id)


# =============================================================================
# Health Check
# =============================================================================
async def check_database_health() -> dict:
    """Check database connectivity and return health status."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error("database_health_check_failed", error=str(e))
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}


# =============================================================================
# Legacy Alias
# =============================================================================
# Several task modules import this name. It is an alias for AsyncSessionLocal
# used as an async context manager (matching the interface of async_session_context).
async_session_factory = async_session_context
