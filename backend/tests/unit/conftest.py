# =============================================================================
# Stratum AI - Deep Unit Test Fixtures
# =============================================================================
"""
Fixtures for deep endpoint testing without a real database.

Provides:
- Lightweight FastAPI test app with TenantMiddleware
- httpx.AsyncClient for full request/response cycle testing
- Mock DB session with configurable returns
- JWT token generation for various roles
- Service mocking utilities
"""

import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


# ---------------------------------------------------------------------------
# Test Application
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def test_app():
    """
    Build a lightweight FastAPI app for deep endpoint testing.

    Includes TenantMiddleware (for real JWT decode / tenant extraction)
    but skips heavy I/O middleware (rate limiter, audit, prometheus).
    """
    from fastapi import FastAPI
    from app.api.v1 import api_router
    from app.core.config import settings
    from app.middleware.tenant import TenantMiddleware

    application = FastAPI(title="Stratum AI (deep-test)")
    application.add_middleware(TenantMiddleware)
    application.include_router(api_router, prefix=settings.api_v1_prefix)

    @application.get("/health")
    async def health():
        return {"status": "healthy"}

    return application


# ---------------------------------------------------------------------------
# Mock Database Session
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def mock_db():
    """
    Mock AsyncSession.

    Default behaviour: commit/rollback/close/flush are silent no-ops.
    Tests can configure `mock_db.execute.return_value` or
    `mock_db.execute.side_effect` for per-query returns.
    """
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()

    # Default execute returns empty result
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    result.scalars.return_value.first.return_value = None
    result.scalar.return_value = None
    result.scalar_one_or_none.return_value = None
    result.fetchall.return_value = []
    result.fetchone.return_value = None
    session.execute = AsyncMock(return_value=result)

    return session


# ---------------------------------------------------------------------------
# httpx Client
# ---------------------------------------------------------------------------

@pytest_asyncio.fixture
async def api_client(test_app, mock_db) -> AsyncGenerator[AsyncClient, None]:
    """
    httpx.AsyncClient wired to the test app with mocked DB.

    Goes through the full ASGI stack: middleware → route → handler → response.
    """
    from app.db.session import get_async_session, get_db

    async def override_session():
        yield mock_db

    test_app.dependency_overrides[get_async_session] = override_session
    test_app.dependency_overrides[get_db] = override_session

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://testserver",
    ) as ac:
        yield ac

    test_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# JWT / Auth Helpers
# ---------------------------------------------------------------------------

def _make_token(subject: int = 1, tenant_id: int = 1, role: str = "admin",
                email: str = "test@example.com", cms_role: str = "admin",
                **extra_claims) -> str:
    """Create a real JWT token using the app's security module."""
    from app.core.security import create_access_token

    claims = {
        "email": email,
        "tenant_id": tenant_id,
        "role": role,
        "cms_role": cms_role,
        **extra_claims,
    }
    return create_access_token(subject=subject, additional_claims=claims)


@pytest.fixture
def admin_headers() -> dict:
    """Auth headers for a tenant admin (tenant_id=1, user_id=1)."""
    token = _make_token(subject=1, tenant_id=1, role="admin")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def viewer_headers() -> dict:
    """Auth headers for a tenant viewer (tenant_id=1, user_id=2)."""
    token = _make_token(subject=2, tenant_id=1, role="viewer")
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def superadmin_headers() -> dict:
    """Auth headers for a superadmin (no tenant binding)."""
    token = _make_token(subject=99, role="superadmin", email="admin@stratum.ai",
                        tenant_id=0)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def tenant2_headers() -> dict:
    """Auth headers for a user on a DIFFERENT tenant (tenant_id=2)."""
    token = _make_token(subject=10, tenant_id=2, role="admin")
    return {"Authorization": f"Bearer {token}"}


def make_auth_headers(subject: int = 1, tenant_id: int = 1, role: str = "admin",
                      **kw) -> dict:
    """Helper to build auth headers with custom claims (usable in test body)."""
    token = _make_token(subject=subject, tenant_id=tenant_id, role=role, **kw)
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Mock Result Helpers
# ---------------------------------------------------------------------------

def make_scalar_result(value):
    """Create a mock DB execute result that returns `value` from .scalar()."""
    result = MagicMock()
    result.scalar.return_value = value
    result.scalar_one_or_none.return_value = value
    return result


def make_scalars_result(items: list):
    """Create a mock DB execute result whose .scalars().all() returns `items`."""
    result = MagicMock()
    result.scalars.return_value.all.return_value = items
    result.scalars.return_value.first.return_value = items[0] if items else None
    return result


def make_row_result(rows: list):
    """Create a mock DB execute result whose .fetchall() returns `rows`."""
    result = MagicMock()
    result.fetchall.return_value = rows
    result.fetchone.return_value = rows[0] if rows else None
    return result
