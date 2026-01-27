# =============================================================================
# Stratum AI - Integration Test Configuration
# =============================================================================
"""
Pytest configuration and fixtures for integration tests.

Provides:
- Database fixtures with async support
- Test tenant and user factories
- API client fixtures

NOTE: These tests require a running PostgreSQL database.
Set TEST_DATABASE_URL environment variable or use default test database.
"""

import os
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

# =============================================================================
# Database URL Configuration
# =============================================================================
# Auto-detect Docker environment and use appropriate database hostname.
# When running inside Docker, use 'db' (service name). When running locally, use 'localhost'.


def _is_running_in_docker() -> bool:
    """Detect if we're running inside a Docker container."""
    # Check for .dockerenv file (most reliable)
    if Path("/.dockerenv").exists():
        return True
    # Check for Docker-specific cgroup
    try:
        with Path("/proc/1/cgroup").open() as f:
            return "docker" in f.read()
    except (FileNotFoundError, PermissionError):
        pass
    # Check for explicit environment variable
    return os.environ.get("IN_DOCKER", "").lower() in ("true", "1", "yes")


def _get_db_host() -> str:
    """Get the appropriate database host based on environment."""
    # Allow explicit override via environment variable
    if os.environ.get("TEST_DB_HOST"):
        return os.environ["TEST_DB_HOST"]
    # Auto-detect Docker environment
    return "db" if _is_running_in_docker() else "localhost"


_db_host = _get_db_host()
_db_user = os.environ.get("POSTGRES_USER", "stratum")
_db_pass = os.environ.get("POSTGRES_PASSWORD", "stratum_secure_password_2024")
_db_name = os.environ.get("POSTGRES_DB", "stratum_ai")

# Set database URLs for tests
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL", f"postgresql+asyncpg://{_db_user}:{_db_pass}@{_db_host}:5432/{_db_name}"
)
os.environ["DATABASE_URL_SYNC"] = os.environ.get(
    "TEST_DATABASE_URL_SYNC", f"postgresql://{_db_user}:{_db_pass}@{_db_host}:5432/{_db_name}"
)


# =============================================================================
# Database Fixtures
# =============================================================================
# Note: Event loop is managed by pytest-asyncio with function scope
# (configured in pytest.ini via asyncio_default_fixture_loop_scope = function)


@pytest.fixture(scope="function")
def sync_engine():
    """Create a sync database engine for setup/teardown."""
    from app.core.config import settings

    engine = create_engine(
        settings.database_url_sync,
        echo=False,
        pool_pre_ping=True,
    )
    yield engine
    engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def async_engine():
    """Create an async database engine for tests (function-scoped to match event loop)."""
    from app.core.config import settings

    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a database session for each test.

    Uses savepoint for isolation - allows nested transactions from API calls.
    """
    async_session_factory = async_sessionmaker(
        bind=async_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with async_engine.connect() as connection:
        # Start a transaction that we'll rollback at the end
        transaction = await connection.begin()

        # Create session bound to this connection
        async with async_session_factory(bind=connection) as session:
            yield session

        # Rollback the transaction to reset state
        await transaction.rollback()


@pytest.fixture(scope="function")
def sync_db_session(sync_engine) -> Generator[Session, None, None]:
    """Create a sync database session for tests that require it."""
    SessionLocal = sessionmaker(bind=sync_engine, autoflush=False)
    session = SessionLocal()

    try:
        yield session
        session.rollback()
    finally:
        session.close()


# =============================================================================
# Application and Client Fixtures
# =============================================================================


@pytest_asyncio.fixture(scope="function")
async def app():
    """Get the FastAPI application instance."""
    from app.main import create_application

    application = create_application()
    yield application


@pytest_asyncio.fixture(scope="function")
async def client(app, db_session) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async HTTP client for API testing.

    Overrides the database session dependency.
    """
    from app.db.session import get_async_session

    # Override the database dependency
    async def get_test_session():
        yield db_session

    app.dependency_overrides[get_async_session] = get_test_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac

    # Clear dependency overrides
    app.dependency_overrides.clear()


@pytest_asyncio.fixture(scope="function")
async def authenticated_client(client, test_user, test_tenant) -> AsyncClient:
    """
    Create an authenticated client with JWT token.
    """
    from app.core.security import create_access_token

    token = create_access_token(
        subject=test_user["id"],
        additional_claims={
            "email": test_user["email"],
            "tenant_id": test_tenant["id"],
            "role": test_user["role"],
        },
    )

    client.headers["Authorization"] = f"Bearer {token}"
    client.headers["X-Tenant-ID"] = str(test_tenant["id"])

    return client


# =============================================================================
# Test Data Factories
# =============================================================================


@pytest_asyncio.fixture(scope="function")
async def test_tenant(db_session) -> dict:
    """Create a test tenant."""
    from app.base_models import Tenant

    tenant = Tenant(
        name="Test Tenant",
        slug="test-tenant",
        plan="professional",
        max_users=10,
        max_campaigns=100,
    )

    db_session.add(tenant)
    await db_session.flush()

    return {
        "id": tenant.id,
        "name": tenant.name,
        "slug": tenant.slug,
        "plan": tenant.plan,
    }


@pytest_asyncio.fixture(scope="function")
async def test_user(db_session, test_tenant) -> dict:
    """Create a test user."""
    from app.base_models import User, UserRole
    from app.core.security import get_password_hash

    user = User(
        tenant_id=test_tenant["id"],
        email="test@example.com",
        email_hash="test@example.com",  # Simplified for tests
        password_hash=get_password_hash("testpassword123"),
        full_name="Test User",
        role=UserRole.ADMIN,
        is_active=True,
        is_verified=True,
    )

    db_session.add(user)
    await db_session.flush()

    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "tenant_id": test_tenant["id"],
    }


@pytest_asyncio.fixture(scope="function")
async def test_campaign(db_session, test_tenant) -> dict:
    """Create a test campaign."""
    from app.models.campaign_builder import CampaignDraft

    draft_json = {
        "objective": "conversions",
        "daily_budget": 100.0,
        "currency": "USD",
    }

    campaign = CampaignDraft(
        tenant_id=test_tenant["id"],
        name="Test Campaign",
        status="draft",
        platform="meta",
        draft_json=draft_json,
    )

    db_session.add(campaign)
    await db_session.flush()

    return {
        "id": str(campaign.id),
        "name": campaign.name,
        "status": campaign.status,
        "platform": campaign.platform,
        "daily_budget": draft_json["daily_budget"],
    }


@pytest_asyncio.fixture(scope="function")
async def test_signal_health(db_session, test_tenant) -> dict:
    """Create a test signal health record."""
    from app.models.trust_layer import FactSignalHealthDaily, SignalHealthStatus

    record = FactSignalHealthDaily(
        tenant_id=test_tenant["id"],
        date=date.today(),
        platform="meta",
        emq_score=85.0,
        event_loss_pct=3.5,
        freshness_minutes=30,
        api_error_rate=0.5,
        status=SignalHealthStatus.OK,
    )

    db_session.add(record)
    await db_session.flush()

    return {
        "id": str(record.id),
        "tenant_id": test_tenant["id"],
        "platform": record.platform,
        "emq_score": record.emq_score,
        "status": record.status.value,
    }


@pytest_asyncio.fixture(scope="function")
async def test_action(db_session, test_tenant, test_user) -> dict:
    """Create a test action queue item."""
    import json

    from app.models.trust_layer import FactActionsQueue

    action = FactActionsQueue(
        tenant_id=test_tenant["id"],
        date=date.today(),
        action_type="budget_increase",
        entity_type="campaign",
        entity_id="campaign_123",
        entity_name="Test Campaign",
        platform="meta",
        action_json=json.dumps({"amount": 50, "percentage": 10}),
        status="queued",
        created_by_user_id=test_user["id"],
    )

    db_session.add(action)
    await db_session.flush()

    return {
        "id": str(action.id),
        "tenant_id": test_tenant["id"],
        "action_type": action.action_type,
        "status": action.status,
        "entity_name": action.entity_name,
    }


# =============================================================================
# Utility Fixtures
# =============================================================================


@pytest.fixture
def auth_headers(test_user, test_tenant):
    """Generate authentication headers for API requests."""
    from app.core.security import create_access_token

    token = create_access_token(
        subject=test_user["id"],
        additional_claims={
            "email": test_user["email"],
            "tenant_id": test_tenant["id"],
            "role": test_user["role"],
        },
    )

    return {
        "Authorization": f"Bearer {token}",
        "X-Tenant-ID": str(test_tenant["id"]),
    }


@pytest.fixture
def superadmin_headers():
    """Generate superadmin authentication headers."""
    from app.core.security import create_access_token

    token = create_access_token(
        subject=1,
        additional_claims={
            "email": "admin@stratum.ai",
            "role": "superadmin",
        },
    )

    return {
        "Authorization": f"Bearer {token}",
    }


# =============================================================================
# Database Setup/Teardown
# =============================================================================


@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    """
    Set up the test database before running tests.

    Creates all tables using a dedicated session-scoped engine.
    """
    # Import all models to register them with Base.metadata
    # This ensures all tables and enum types are created
    import app.base_models
    import app.models  # noqa: F401
    from app.core.config import settings
    from app.db.base_class import Base

    # Create a dedicated engine for setup (session-scoped)
    setup_engine = create_engine(
        settings.database_url_sync,
        echo=False,
        pool_pre_ping=True,
    )

    # Create all tables and enum types
    Base.metadata.create_all(bind=setup_engine)

    yield

    # Cleanup
    setup_engine.dispose()
    # Optionally drop tables after tests (comment out to preserve data for debugging)
    # Base.metadata.drop_all(bind=setup_engine)


# =============================================================================
# Sample Data Fixtures
# =============================================================================


@pytest.fixture
def sample_platform_metrics():
    """Sample platform metrics for EMQ calculation."""
    from app.analytics.logic.emq_calculation import PlatformMetrics

    return PlatformMetrics(
        platform="meta",
        pixel_events=10000,
        capi_events=8500,
        matched_events=8000,
        pages_with_pixel=95,
        total_pages=100,
        events_configured=8,
        events_expected=10,
        avg_conversion_latency_hours=2.5,
        platform_conversions=500,
        ga4_conversions=520,
        platform_revenue=50000.0,
        ga4_revenue=52000.0,
        last_event_at=datetime.now(UTC),
    )
