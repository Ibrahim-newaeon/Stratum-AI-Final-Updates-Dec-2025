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
# Redis isolation
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _fake_security_redis(monkeypatch):
    """Keep auth (token-blacklist / login-attempt checks) off a real Redis.

    `app.core.security` caches a module-global Redis pool and lock that bind to
    whichever event loop first created them. Because each async unit test runs
    on a fresh loop, reusing that pool raises ``RuntimeError: Event loop is
    closed`` — which `is_token_blacklisted` does not catch, 500-ing every
    authenticated request. Unit tests must not depend on a live Redis, so swap
    the pool for an in-memory async fake (no token is ever blacklisted) and
    clear the cached globals before each test.
    """
    import app.core.security as security

    fake = AsyncMock()
    fake.exists = AsyncMock(return_value=0)  # nothing blacklisted
    fake.setex = AsyncMock()
    fake.get = AsyncMock(return_value=None)
    fake.set = AsyncMock()
    fake.incr = AsyncMock(return_value=1)
    fake.expire = AsyncMock()
    fake.delete = AsyncMock()
    fake.ttl = AsyncMock(return_value=-2)
    fake.aclose = AsyncMock()

    async def _fake_pool():
        return fake

    monkeypatch.setattr(security, "get_redis_pool", _fake_pool)
    security._redis_pool = None
    security._redis_pool_lock = None
    yield


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
    from types import SimpleNamespace

    from fastapi import HTTPException, Request

    from app.auth.deps import CurrentUser, get_current_user
    from app.base_models import UserRole
    from app.core.security import decode_token
    from app.db.session import get_async_session, get_db

    async def override_session():
        yield mock_db

    async def override_current_user(request: Request) -> CurrentUser:
        """Synthesize the current user from the JWT (no DB / Redis).

        `get_current_user` is a router-level dependency on many endpoints and
        normally loads the user from the database; with the mocked session that
        lookup returns None → 401. Rebuild a CurrentUser from the verified token
        so identity/tenant flow through, while still 401-ing missing or invalid
        tokens. Tenant-mismatch (403) is enforced downstream via the tenant
        context set by TenantMiddleware.
        """
        unauthorized = HTTPException(
            status_code=401, detail="Could not validate credentials"
        )
        auth = request.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            raise unauthorized
        payload = decode_token(auth.split(" ", 1)[1])
        if not payload or payload.get("type") != "access":
            raise unauthorized
        try:
            role = UserRole(payload.get("role", "viewer"))
        except ValueError:
            role = UserRole.VIEWER
        try:
            user_id = int(payload.get("sub"))
        except (TypeError, ValueError):
            raise unauthorized
        fake_user = SimpleNamespace(
            id=user_id,
            tenant_id=payload.get("tenant_id"),
            role=role,
            is_active=True,
            is_verified=True,
            permissions={},
        )
        return CurrentUser(
            user=fake_user, email=payload.get("email", ""), full_name=None
        )

    test_app.dependency_overrides[get_async_session] = override_session
    test_app.dependency_overrides[get_db] = override_session
    test_app.dependency_overrides[get_current_user] = override_current_user

    async with AsyncClient(
        transport=ASGITransport(app=test_app),
        base_url="http://testserver",
    ) as ac:
        yield ac

    test_app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# JWT / Auth Helpers
# ---------------------------------------------------------------------------


def _make_token(
    subject: int = 1,
    tenant_id: int = 1,
    role: str = "admin",
    email: str = "test@example.com",
    cms_role: str = "admin",
    **extra_claims,
) -> str:
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
    token = _make_token(
        subject=99, role="superadmin", email="admin@stratum.ai", tenant_id=0
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def tenant2_headers() -> dict:
    """Auth headers for a user on a DIFFERENT tenant (tenant_id=2)."""
    token = _make_token(subject=10, tenant_id=2, role="admin")
    return {"Authorization": f"Bearer {token}"}


def make_auth_headers(
    subject: int = 1, tenant_id: int = 1, role: str = "admin", **kw
) -> dict:
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
