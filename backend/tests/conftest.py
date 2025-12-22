"""
Stratum AI - Test Configuration
Shared fixtures and configuration for pytest.
"""

import asyncio
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_async_session
from app.main import create_app
from app.models import Tenant, User, UserRole
from app.core.security import get_password_hash, create_access_token

# Test database URL - use SQLite for fast tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def async_engine():
    """Create async engine for tests."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def async_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create async session for tests."""
    async_session_maker = async_sessionmaker(
        async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session_maker() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def app(async_session: AsyncSession) -> FastAPI:
    """Create FastAPI app with test database."""
    application = create_app()

    async def override_get_session():
        yield async_session

    application.dependency_overrides[get_async_session] = override_get_session

    yield application

    application.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Create async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture(scope="function")
async def test_tenant(async_session: AsyncSession) -> Tenant:
    """Create a test tenant."""
    tenant = Tenant(
        name="Test Company",
        slug="test-company",
        plan="professional",
        max_users=10,
        max_campaigns=100,
    )
    async_session.add(tenant)
    await async_session.commit()
    await async_session.refresh(tenant)
    return tenant


@pytest_asyncio.fixture(scope="function")
async def test_user(async_session: AsyncSession, test_tenant: Tenant) -> User:
    """Create a test user."""
    from app.core.security import encrypt_pii, hash_pii_for_lookup

    email = "testuser@example.com"
    user = User(
        tenant_id=test_tenant.id,
        email=encrypt_pii(email),
        email_hash=hash_pii_for_lookup(email),
        password_hash=get_password_hash("TestPassword123"),
        full_name=encrypt_pii("Test User"),
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest_asyncio.fixture(scope="function")
async def test_superadmin(async_session: AsyncSession, test_tenant: Tenant) -> User:
    """Create a test superadmin user."""
    from app.core.security import encrypt_pii, hash_pii_for_lookup

    email = "superadmin@stratum.ai"
    user = User(
        tenant_id=test_tenant.id,
        email=encrypt_pii(email),
        email_hash=hash_pii_for_lookup(email),
        password_hash=get_password_hash("SuperAdmin123"),
        full_name=encrypt_pii("Super Admin"),
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )
    async_session.add(user)
    await async_session.commit()
    await async_session.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user: User, test_tenant: Tenant) -> dict:
    """Generate authentication headers for test user."""
    token = create_access_token(
        subject=test_user.id,
        additional_claims={
            "tenant_id": test_tenant.id,
            "role": test_user.role.value,
        },
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def superadmin_headers(test_superadmin: User, test_tenant: Tenant) -> dict:
    """Generate authentication headers for superadmin."""
    token = create_access_token(
        subject=test_superadmin.id,
        additional_claims={
            "tenant_id": test_tenant.id,
            "role": test_superadmin.role.value,
        },
    )
    return {"Authorization": f"Bearer {token}"}
