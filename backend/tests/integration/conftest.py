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

import asyncio
import os
from datetime import datetime, date, timezone
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker, Session


# Set database URLs for tests
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://stratum:password@localhost:5432/stratum_ai_test"
)
os.environ["DATABASE_URL_SYNC"] = os.environ.get(
    "TEST_DATABASE_URL_SYNC",
    "postgresql://stratum:password@localhost:5432/stratum_ai_test"
)


# =============================================================================
# Async Event Loop Configuration
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the entire test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Database Fixtures
# =============================================================================

@pytest.fixture(scope="session")
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
    """
    Create an async database engine per test.

    Function-scoped to avoid "Future attached to a different loop" errors
    that occur when a session-scoped engine creates connections on one
    event loop but tests run on another (pytest-asyncio creates a new
    loop per function with asyncio_mode=auto).
    """
    from app.core.config import settings

    engine = create_async_engine(
        settings.database_url,
        echo=False,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=0,
    )
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db_session(async_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Create a database session for each test with savepoint-based rollback.

    Strategy:
    1. Open a real connection + begin an outer transaction.
    2. Start a savepoint (begin_nested) inside that transaction.
    3. Hand the session to both test fixtures and endpoint code.
    4. After each endpoint commit(), the savepoint listener restarts it.
    5. On teardown, roll back the outer transaction → all changes vanish.
    """
    connection = await async_engine.connect()
    transaction = await connection.begin()

    session = AsyncSession(bind=connection, expire_on_commit=False, autoflush=False)

    # Use nested transactions (savepoints) so endpoint commit() doesn't
    # close our outer transaction.
    nested = await connection.begin_nested()

    # After every commit from endpoint code, restart the savepoint
    @event.listens_for(session.sync_session, "after_transaction_end")
    def restart_savepoint(session_inner, trans):
        if trans.nested and not trans._parent.nested:
            session_inner.begin_nested()

    yield session

    # Tear down: rollback everything
    await session.close()
    await transaction.rollback()
    await connection.close()


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
    """
    Build a stripped-down FastAPI app for integration tests.

    The full ``create_application()`` adds middleware (rate-limiter, audit,
    prometheus) that creates async Redis / DB connections at middleware init
    time.  Those connections bind to the *import-time* event loop, which
    differs from the per-test loop created by pytest-asyncio, causing
    "Future attached to a different loop" RuntimeErrors.

    To avoid this, we construct a **lightweight test app** that keeps the
    router & tenant middleware but drops the problematic I/O middleware.
    """
    from fastapi import FastAPI
    from fastapi.responses import ORJSONResponse

    from app.api.v1 import api_router
    from app.core.config import settings
    from app.middleware.tenant import TenantMiddleware

    application = FastAPI(
        title="Stratum AI (test)",
        default_response_class=ORJSONResponse,
    )

    # Only the tenant middleware – enough for auth / row-level security
    application.add_middleware(TenantMiddleware)

    # Include the full API router (same routes as production)
    application.include_router(api_router, prefix=settings.api_v1_prefix)

    # Minimal health endpoint (some tests may hit /health)
    @application.get("/health")
    async def health():
        return {"status": "healthy"}

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
        }
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

    campaign = CampaignDraft(
        tenant_id=test_tenant["id"],
        name="Test Campaign",
        status="draft",
        platform="meta",
        draft_json={
            "objective": "conversions",
            "daily_budget": 100.0,
            "currency": "USD",
        },
    )

    db_session.add(campaign)
    await db_session.flush()

    return {
        "id": str(campaign.id),
        "name": campaign.name,
        "status": campaign.status,
        "platform": campaign.platform,
        "daily_budget": campaign.draft_json.get("daily_budget"),
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
    from app.models.trust_layer import FactActionsQueue
    import json

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
        }
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
        }
    )

    return {
        "Authorization": f"Bearer {token}",
    }


# =============================================================================
# Database Setup/Teardown
# =============================================================================

@pytest.fixture(scope="session", autouse=True)
def setup_test_database(sync_engine):
    """
    Set up the test database before running tests.

    Creates all tables and runs migrations if needed.
    """
    from app.db.base_class import Base
    # Import ALL models so they register with Base.metadata
    import app.base_models  # noqa: F401
    import app.models.cdp  # noqa: F401
    import app.models.cms  # noqa: F401
    import app.models.campaign_builder  # noqa: F401
    import app.models.trust_layer  # noqa: F401
    import app.models.autopilot  # noqa: F401
    import app.models.attribution  # noqa: F401
    import app.models.audience_sync  # noqa: F401
    # import app.models.audit_services  # noqa: F401 — excluded: 'metadata' column name conflicts with SQLAlchemy
    import app.models.capi_delivery  # noqa: F401
    import app.models.client  # noqa: F401
    import app.models.crm  # noqa: F401
    import app.models.embed_widgets  # noqa: F401
    import app.models.newsletter  # noqa: F401
    import app.models.onboarding  # noqa: F401
    import app.models.pacing  # noqa: F401
    import app.models.profit  # noqa: F401
    import app.models.reporting  # noqa: F401
    import app.models.settings  # noqa: F401

    # Drop and recreate all tables for a clean state
    Base.metadata.drop_all(bind=sync_engine)
    Base.metadata.create_all(bind=sync_engine)

    yield

    # Optionally drop tables after tests (comment out to preserve data for debugging)
    # Base.metadata.drop_all(bind=sync_engine)


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
        last_event_at=datetime.now(timezone.utc),
    )
