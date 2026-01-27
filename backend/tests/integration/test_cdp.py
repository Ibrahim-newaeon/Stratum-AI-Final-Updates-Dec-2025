# =============================================================================
# Stratum AI - CDP Integration Tests
# =============================================================================
"""
Integration tests for CDP (Customer Data Platform) module.

Tests:
- Event ingestion flow (single and batch)
- Profile lookup by ID and identifier
- Profile tenant isolation
- Source creation and listing
- Duplicate event handling (idempotency)
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

pytestmark = pytest.mark.integration


# =============================================================================
# CDP-Specific Fixtures with Auth Mocking
# =============================================================================


class MockCurrentUser:
    """Mock user for CDP tests."""

    def __init__(self, user_id: int = 1, tenant_id: int = 1):
        self.id = user_id
        self.tenant_id = tenant_id
        self.email = "test@example.com"
        self.role = "admin"
        self.is_active = True
        self.is_verified = True


@pytest_asyncio.fixture(scope="function")
async def cdp_client(app, db_session, test_tenant) -> AsyncClient:
    """
    Create an async HTTP client for CDP API testing with mocked auth.
    """
    from app.auth.deps import get_current_user
    from app.db.session import get_async_session

    # Override the database dependency
    async def get_test_session():
        yield db_session

    # Mock auth to return a user with the test tenant
    async def mock_get_current_user():
        return MockCurrentUser(user_id=1, tenant_id=test_tenant["id"])

    app.dependency_overrides[get_async_session] = get_test_session
    app.dependency_overrides[get_current_user] = mock_get_current_user

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac

    # Clear dependency overrides
    app.dependency_overrides.clear()


# =============================================================================
# CDP Test Fixtures
# =============================================================================


@pytest.fixture
def sample_event_data():
    """Sample event data for testing."""
    return {
        "events": [
            {
                "event_name": "PageView",
                "event_time": datetime.now(UTC).isoformat(),
                "identifiers": [{"type": "anonymous_id", "value": "anon_test_123"}],
                "properties": {"page_url": "/products/sofa", "page_title": "Milano Sofa"},
            }
        ]
    }


@pytest.fixture
def sample_purchase_event_data():
    """Sample purchase event with PII identifier."""
    return {
        "events": [
            {
                "event_name": "Purchase",
                "event_time": datetime.now(UTC).isoformat(),
                "idempotency_key": f"order_{uuid4().hex[:8]}_{int(datetime.now().timestamp())}",
                "identifiers": [
                    {"type": "email", "value": "customer@example.com"},
                    {"type": "anonymous_id", "value": "anon_purchase_456"},
                ],
                "properties": {"order_id": "ORD-12345", "total": 2499.00, "currency": "AED"},
                "context": {
                    "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
                    "ip": "185.23.45.67",
                    "campaign": {"source": "google", "medium": "cpc"},
                },
                "consent": {"analytics": True, "ads": True},
            }
        ]
    }


@pytest.fixture
def sample_batch_events():
    """Sample batch of events for testing."""
    base_time = datetime.now(UTC)
    events = []
    for i in range(10):
        events.append(
            {
                "event_name": "PageView",
                "event_time": (base_time + timedelta(seconds=i)).isoformat(),
                "identifiers": [{"type": "anonymous_id", "value": f"anon_batch_{i}"}],
                "properties": {"page_url": f"/page/{i}"},
            }
        )
    return {"events": events}


# =============================================================================
# Event Ingestion Tests
# =============================================================================


class TestEventIngestion:
    """Tests for event ingestion endpoint."""

    @pytest.mark.asyncio
    async def test_ingest_single_event(
        self,
        cdp_client: AsyncClient,
        sample_event_data: dict,
    ):
        """Test ingesting a single event."""
        response = await cdp_client.post("/api/v1/cdp/events", json=sample_event_data)

        assert response.status_code == 201
        data = response.json()

        assert data["accepted"] == 1
        assert data["rejected"] == 0
        assert data["duplicates"] == 0
        assert len(data["results"]) == 1
        assert data["results"][0]["status"] == "accepted"
        assert data["results"][0]["event_id"] is not None
        assert data["results"][0]["profile_id"] is not None

    @pytest.mark.asyncio
    async def test_ingest_event_with_pii(
        self,
        cdp_client: AsyncClient,
        sample_purchase_event_data: dict,
    ):
        """Test ingesting event with email identifier (PII)."""
        response = await cdp_client.post("/api/v1/cdp/events", json=sample_purchase_event_data)

        assert response.status_code == 201
        data = response.json()

        assert data["accepted"] == 1
        assert data["results"][0]["status"] == "accepted"

    @pytest.mark.asyncio
    async def test_ingest_batch_events(
        self,
        cdp_client: AsyncClient,
        sample_batch_events: dict,
    ):
        """Test ingesting batch of events."""
        response = await cdp_client.post("/api/v1/cdp/events", json=sample_batch_events)

        assert response.status_code == 201
        data = response.json()

        assert data["accepted"] == 10
        assert data["rejected"] == 0

    @pytest.mark.asyncio
    async def test_ingest_duplicate_event_rejected(
        self,
        cdp_client: AsyncClient,
    ):
        """Test that duplicate events (same idempotency_key) are rejected."""
        idempotency_key = f"test_duplicate_{uuid4().hex}"

        event_data = {
            "events": [
                {
                    "event_name": "PageView",
                    "event_time": datetime.now(UTC).isoformat(),
                    "idempotency_key": idempotency_key,
                    "identifiers": [{"type": "anonymous_id", "value": "anon_dup_test"}],
                }
            ]
        }

        # First request should succeed
        response1 = await cdp_client.post("/api/v1/cdp/events", json=event_data)
        assert response1.status_code == 201
        assert response1.json()["accepted"] == 1

        # Second request with same idempotency_key should be duplicate
        response2 = await cdp_client.post("/api/v1/cdp/events", json=event_data)
        assert response2.status_code == 201
        data2 = response2.json()
        assert data2["duplicates"] == 1
        assert data2["accepted"] == 0

    @pytest.mark.asyncio
    async def test_ingest_event_invalid_identifier_type(
        self,
        cdp_client: AsyncClient,
    ):
        """Test that invalid identifier type is rejected."""
        event_data = {
            "events": [
                {
                    "event_name": "PageView",
                    "event_time": datetime.now(UTC).isoformat(),
                    "identifiers": [{"type": "invalid_type", "value": "test123"}],
                }
            ]
        }

        response = await cdp_client.post("/api/v1/cdp/events", json=event_data)

        # Should return 422 validation error
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_ingest_event_no_identifiers(
        self,
        cdp_client: AsyncClient,
    ):
        """Test that event without identifiers is rejected."""
        event_data = {
            "events": [
                {
                    "event_name": "PageView",
                    "event_time": datetime.now(UTC).isoformat(),
                    "identifiers": [],
                }
            ]
        }

        response = await cdp_client.post("/api/v1/cdp/events", json=event_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_ingest_event_creates_profile(
        self,
        cdp_client: AsyncClient,
    ):
        """Test that ingesting event creates a new profile."""
        unique_id = uuid4().hex[:8]
        event_data = {
            "events": [
                {
                    "event_name": "SignUp",
                    "event_time": datetime.now(UTC).isoformat(),
                    "identifiers": [{"type": "email", "value": f"newuser_{unique_id}@example.com"}],
                }
            ]
        }

        response = await cdp_client.post("/api/v1/cdp/events", json=event_data)

        assert response.status_code == 201
        data = response.json()
        profile_id = data["results"][0]["profile_id"]

        # Verify profile exists
        profile_response = await cdp_client.get(f"/api/v1/cdp/profiles/{profile_id}")
        assert profile_response.status_code == 200


# =============================================================================
# Profile Lookup Tests
# =============================================================================


class TestProfileLookup:
    """Tests for profile lookup endpoints."""

    @pytest.mark.asyncio
    async def test_lookup_profile_by_id(
        self,
        cdp_client: AsyncClient,
    ):
        """Test looking up profile by UUID."""
        # First, create a profile by ingesting an event
        event_data = {
            "events": [
                {
                    "event_name": "PageView",
                    "event_time": datetime.now(UTC).isoformat(),
                    "identifiers": [
                        {"type": "anonymous_id", "value": f"anon_lookup_{uuid4().hex[:8]}"}
                    ],
                }
            ]
        }

        ingest_response = await cdp_client.post("/api/v1/cdp/events", json=event_data)
        assert ingest_response.status_code == 201
        profile_id = ingest_response.json()["results"][0]["profile_id"]

        # Look up by ID
        response = await cdp_client.get(f"/api/v1/cdp/profiles/{profile_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == profile_id

    @pytest.mark.asyncio
    async def test_lookup_profile_by_email(
        self,
        cdp_client: AsyncClient,
    ):
        """Test looking up profile by email identifier."""
        email = f"lookup_test_{uuid4().hex[:8]}@example.com"

        # Create profile with email
        event_data = {
            "events": [
                {
                    "event_name": "SignUp",
                    "event_time": datetime.now(UTC).isoformat(),
                    "identifiers": [{"type": "email", "value": email}],
                }
            ]
        }

        await cdp_client.post("/api/v1/cdp/events", json=event_data)

        # Look up by email
        response = await cdp_client.get(
            "/api/v1/cdp/profiles", params={"identifier_type": "email", "identifier_value": email}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data["identifiers"]) >= 1

    @pytest.mark.asyncio
    async def test_lookup_profile_not_found(
        self,
        cdp_client: AsyncClient,
    ):
        """Test looking up non-existent profile."""
        fake_id = str(uuid4())

        response = await cdp_client.get(f"/api/v1/cdp/profiles/{fake_id}")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_lookup_profile_by_unknown_identifier(
        self,
        cdp_client: AsyncClient,
    ):
        """Test looking up profile with unknown identifier value."""
        response = await cdp_client.get(
            "/api/v1/cdp/profiles",
            params={"identifier_type": "email", "identifier_value": "nonexistent@nowhere.com"},
        )

        assert response.status_code == 404


# =============================================================================
# Profile Tenant Isolation Tests
# =============================================================================


class TestProfileTenantIsolation:
    """Tests for profile tenant isolation."""

    @pytest.mark.asyncio
    async def test_cannot_access_other_tenant_profile(
        self,
        cdp_client: AsyncClient,
        test_tenant: dict,
        db_session,
    ):
        """Test that a user cannot access another tenant's profile."""
        # Create another tenant and profile
        from app.base_models import Tenant
        from app.models.cdp import CDPProfile

        other_tenant = Tenant(
            name="Other CDP Tenant",
            slug="other-cdp-tenant",
            plan="professional",
        )
        db_session.add(other_tenant)
        await db_session.flush()

        # Create a profile for the other tenant
        other_profile = CDPProfile(
            tenant_id=other_tenant.id,
            lifecycle_stage="anonymous",
        )
        db_session.add(other_profile)
        await db_session.flush()

        # Try to access the other tenant's profile
        response = await cdp_client.get(f"/api/v1/cdp/profiles/{other_profile.id}")

        # Should be not found (tenant scoping hides it)
        assert response.status_code == 404


# =============================================================================
# Source Management Tests
# =============================================================================


class TestSourceManagement:
    """Tests for data source management endpoints."""

    @pytest.mark.asyncio
    async def test_create_source(
        self,
        cdp_client: AsyncClient,
    ):
        """Test creating a new data source."""
        source_data = {
            "name": "Website Pixel",
            "source_type": "website",
            "config": {"domain": "example.com"},
        }

        response = await cdp_client.post("/api/v1/cdp/sources", json=source_data)

        assert response.status_code == 201
        data = response.json()

        assert data["name"] == "Website Pixel"
        assert data["source_type"] == "website"
        assert "source_key" in data
        assert data["source_key"].startswith("cdp_")
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_list_sources(
        self,
        cdp_client: AsyncClient,
    ):
        """Test listing data sources."""
        # Create a source first
        await cdp_client.post(
            "/api/v1/cdp/sources", json={"name": "Test Source", "source_type": "server"}
        )

        response = await cdp_client.get("/api/v1/cdp/sources")

        assert response.status_code == 200
        data = response.json()

        assert "sources" in data
        assert "total" in data
        assert data["total"] >= 1

    @pytest.mark.asyncio
    async def test_create_source_invalid_type(
        self,
        cdp_client: AsyncClient,
    ):
        """Test creating source with invalid type."""
        source_data = {"name": "Invalid Source", "source_type": "invalid_type"}

        response = await cdp_client.post("/api/v1/cdp/sources", json=source_data)

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_source_key_is_unique(
        self,
        cdp_client: AsyncClient,
    ):
        """Test that each source gets a unique key."""
        source1 = await cdp_client.post(
            "/api/v1/cdp/sources", json={"name": "Source 1", "source_type": "website"}
        )
        source2 = await cdp_client.post(
            "/api/v1/cdp/sources", json={"name": "Source 2", "source_type": "website"}
        )

        assert source1.status_code == 201
        assert source2.status_code == 201

        key1 = source1.json()["source_key"]
        key2 = source2.json()["source_key"]

        assert key1 != key2


# =============================================================================
# CDP Health Check Tests
# =============================================================================


class TestCDPHealth:
    """Tests for CDP health check endpoint."""

    @pytest.mark.asyncio
    async def test_health_check(
        self,
        client: AsyncClient,
    ):
        """Test CDP health check endpoint."""
        response = await client.get("/api/v1/cdp/health")

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["module"] == "cdp"
        assert "version" in data


# =============================================================================
# EMQ Score Integration Tests
# =============================================================================


class TestEMQScoreIntegration:
    """Tests for EMQ score calculation in event ingestion."""

    @pytest.mark.asyncio
    async def test_event_with_email_gets_high_emq(
        self,
        cdp_client: AsyncClient,
        db_session,
    ):
        """Test that event with email identifier gets high EMQ score."""
        from sqlalchemy import select

        from app.models.cdp import CDPEvent

        event_data = {
            "events": [
                {
                    "event_name": "Purchase",
                    "event_time": datetime.now(UTC).isoformat(),
                    "identifiers": [
                        {"type": "email", "value": f"emq_test_{uuid4().hex[:8]}@example.com"}
                    ],
                    "properties": {"order_id": "ORD-EMQ-TEST"},
                    "context": {
                        "user_agent": "Mozilla/5.0",
                        "ip": "1.2.3.4",
                        "campaign": {"source": "google"},
                    },
                }
            ]
        }

        response = await cdp_client.post("/api/v1/cdp/events", json=event_data)

        assert response.status_code == 201
        event_id = response.json()["results"][0]["event_id"]

        # Query the event to check EMQ score
        result = await db_session.execute(select(CDPEvent).where(CDPEvent.id == event_id))
        event = result.scalar_one_or_none()

        # With email + properties + context, EMQ should be high (>= 80)
        if event:
            assert float(event.emq_score) >= 80

    @pytest.mark.asyncio
    async def test_event_with_anonymous_only_gets_lower_emq(
        self,
        cdp_client: AsyncClient,
        db_session,
    ):
        """Test that event with only anonymous identifier gets lower EMQ score."""
        from sqlalchemy import select

        from app.models.cdp import CDPEvent

        event_data = {
            "events": [
                {
                    "event_name": "PageView",
                    "event_time": datetime.now(UTC).isoformat(),
                    "identifiers": [
                        {"type": "anonymous_id", "value": f"anon_emq_{uuid4().hex[:8]}"}
                    ],
                }
            ]
        }

        response = await cdp_client.post("/api/v1/cdp/events", json=event_data)

        assert response.status_code == 201
        event_id = response.json()["results"][0]["event_id"]

        # Query the event to check EMQ score
        result = await db_session.execute(select(CDPEvent).where(CDPEvent.id == event_id))
        event = result.scalar_one_or_none()

        # With only anonymous_id and no properties/context, EMQ should be lower
        if event:
            assert float(event.emq_score) < 60


# =============================================================================
# Profile Lifecycle Tests
# =============================================================================


class TestProfileLifecycle:
    """Tests for profile lifecycle stage management."""

    @pytest.mark.asyncio
    async def test_profile_starts_anonymous(
        self,
        cdp_client: AsyncClient,
    ):
        """Test that profile created from anonymous event starts as anonymous."""
        event_data = {
            "events": [
                {
                    "event_name": "PageView",
                    "event_time": datetime.now(UTC).isoformat(),
                    "identifiers": [
                        {"type": "anonymous_id", "value": f"anon_lifecycle_{uuid4().hex[:8]}"}
                    ],
                }
            ]
        }

        response = await cdp_client.post("/api/v1/cdp/events", json=event_data)

        profile_id = response.json()["results"][0]["profile_id"]

        profile_response = await cdp_client.get(f"/api/v1/cdp/profiles/{profile_id}")

        assert profile_response.status_code == 200
        assert profile_response.json()["lifecycle_stage"] == "anonymous"

    @pytest.mark.asyncio
    async def test_profile_becomes_known_with_email(
        self,
        cdp_client: AsyncClient,
    ):
        """Test that profile transitions to known when email is provided."""
        unique_id = uuid4().hex[:8]

        # First, create anonymous profile
        anon_event = {
            "events": [
                {
                    "event_name": "PageView",
                    "event_time": datetime.now(UTC).isoformat(),
                    "identifiers": [
                        {"type": "anonymous_id", "value": f"anon_to_known_{unique_id}"}
                    ],
                }
            ]
        }

        response1 = await cdp_client.post("/api/v1/cdp/events", json=anon_event)
        profile_id = response1.json()["results"][0]["profile_id"]

        # Now send event with email AND the same anonymous_id
        email_event = {
            "events": [
                {
                    "event_name": "SignUp",
                    "event_time": datetime.now(UTC).isoformat(),
                    "identifiers": [
                        {"type": "email", "value": f"known_{unique_id}@example.com"},
                        {"type": "anonymous_id", "value": f"anon_to_known_{unique_id}"},
                    ],
                }
            ]
        }

        await cdp_client.post("/api/v1/cdp/events", json=email_event)

        # Check profile lifecycle
        profile_response = await cdp_client.get(f"/api/v1/cdp/profiles/{profile_id}")

        assert profile_response.status_code == 200
        assert profile_response.json()["lifecycle_stage"] == "known"
