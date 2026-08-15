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
from uuid import UUID, uuid4

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
async def cdp_client(app, db_session, test_tenant, test_user) -> AsyncClient:
    """
    Create an async HTTP client for CDP API testing with mocked auth.

    Adds a JWT token so TenantMiddleware can extract tenant context
    before the request reaches endpoint-level auth dependencies.

    The mock user carries ``test_user``'s real id rather than a hardcoded 1.
    GDPR profile erasure writes an ``audit_logs`` row whose ``user_id`` is FK'd
    to ``users``, so a synthetic id fails the constraint — and a fixture that
    cannot represent the acting user is a fixture that cannot exercise any
    endpoint recording who acted.
    """
    from app.auth.deps import get_current_user
    from app.core.security import create_access_token
    from app.db.session import get_async_session

    # Override the database dependency
    async def get_test_session():
        yield db_session

    # Mock auth to return a user with the test tenant
    async def mock_get_current_user():
        return MockCurrentUser(user_id=test_user["id"], tenant_id=test_tenant["id"])

    app.dependency_overrides[get_async_session] = get_test_session
    app.dependency_overrides[get_current_user] = mock_get_current_user

    # Create a JWT so TenantMiddleware can extract tenant_id
    token = create_access_token(
        subject=test_user["id"],
        additional_claims={
            "email": "test@example.com",
            "tenant_id": test_tenant["id"],
            "role": "admin",
        },
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
        headers={
            "Authorization": f"Bearer {token}",
            "X-Tenant-ID": str(test_tenant["id"]),
        },
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
                "properties": {
                    "page_url": "/products/sofa",
                    "page_title": "Milano Sofa",
                },
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
                "idempotency_key": f"order_{uuid4().hex[:8]}_{int(datetime.now(UTC).timestamp())}",
                "identifiers": [
                    {"type": "email", "value": "customer@example.com"},
                    {"type": "anonymous_id", "value": "anon_purchase_456"},
                ],
                "properties": {
                    "order_id": "ORD-12345",
                    "total": 2499.00,
                    "currency": "AED",
                },
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
        response = await cdp_client.post(
            "/api/v1/cdp/events", json=sample_purchase_event_data
        )

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
                    "identifiers": [
                        {"type": "email", "value": f"newuser_{unique_id}@example.com"}
                    ],
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


class TestGDPRProfileErasure:
    """SEC-002: a profile erasure must remove ALL of the profile's PII."""

    async def test_erasure_deletes_events_even_when_flag_false(
        self, cdp_client: AsyncClient
    ):
        # Ingest an event with PII → creates a profile + a PII-bearing event.
        unique_id = uuid4().hex[:8]
        resp = await cdp_client.post(
            "/api/v1/cdp/events",
            json={
                "events": [
                    {
                        "event_name": "Purchase",
                        "event_time": datetime.now(UTC).isoformat(),
                        "identifiers": [
                            {"type": "email", "value": f"erase_{unique_id}@example.com"}
                        ],
                        "properties": {"value": 99.0},
                    }
                ]
            },
        )
        assert resp.status_code == 201
        profile_id = resp.json()["results"][0]["profile_id"]

        # Erase with delete_events=false — events must STILL be removed.
        deleted = await cdp_client.delete(
            f"/api/v1/cdp/profiles/{profile_id}?delete_events=false"
        )
        assert deleted.status_code == 200
        assert deleted.json()["events_deleted"] >= 1  # erased despite the flag

        # Profile is gone.
        gone = await cdp_client.get(f"/api/v1/cdp/profiles/{profile_id}")
        assert gone.status_code == 404

    async def test_erasure_deletes_profile_merge_records(
        self, cdp_client: AsyncClient, db_session
    ):
        from sqlalchemy import func, select

        from app.models.cdp import CDPProfileMerge

        unique_id = uuid4().hex[:8]
        resp = await cdp_client.post(
            "/api/v1/cdp/events",
            json={
                "events": [
                    {
                        "event_name": "SignUp",
                        "event_time": datetime.now(UTC).isoformat(),
                        "identifiers": [
                            {"type": "email", "value": f"merge_{unique_id}@example.com"}
                        ],
                    }
                ]
            },
        )
        profile_id = UUID(resp.json()["results"][0]["profile_id"])

        # A merge record referencing this profile as the surviving party.
        db_session.add(
            CDPProfileMerge(
                tenant_id=(await _tenant_of(db_session, profile_id)),
                surviving_profile_id=profile_id,
                merged_profile_id=uuid4(),
                merge_reason="test",
            )
        )
        await db_session.commit()

        await cdp_client.delete(f"/api/v1/cdp/profiles/{profile_id}")

        remaining = await db_session.execute(
            select(func.count(CDPProfileMerge.id)).where(
                CDPProfileMerge.surviving_profile_id == profile_id
            )
        )
        assert (remaining.scalar() or 0) == 0


async def _tenant_of(db_session, profile_id):
    from sqlalchemy import select

    from app.models.cdp import CDPProfile

    row = await db_session.execute(
        select(CDPProfile.tenant_id).where(CDPProfile.id == profile_id)
    )
    return row.scalar_one()


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
                        {
                            "type": "anonymous_id",
                            "value": f"anon_lookup_{uuid4().hex[:8]}",
                        }
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
            "/api/v1/cdp/profiles",
            params={"identifier_type": "email", "identifier_value": email},
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
            params={
                "identifier_type": "email",
                "identifier_value": "nonexistent@nowhere.com",
            },
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
        cdp_client: AsyncClient,
    ):
        """Test CDP health check endpoint."""
        response = await cdp_client.get("/api/v1/cdp/health")

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
                        {
                            "type": "email",
                            "value": f"emq_test_{uuid4().hex[:8]}@example.com",
                        }
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
        result = await db_session.execute(
            select(CDPEvent).where(CDPEvent.id == event_id)
        )
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
        result = await db_session.execute(
            select(CDPEvent).where(CDPEvent.id == event_id)
        )
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
                        {
                            "type": "anonymous_id",
                            "value": f"anon_lifecycle_{uuid4().hex[:8]}",
                        }
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


# =============================================================================
# Shared Helpers for Extended Coverage (issue #342 batch 2)
# =============================================================================

_MISSING_ID = "00000000-0000-0000-0000-000000000000"


def _mk_event(
    event_name: str = "PageView",
    identifiers: list | None = None,
    properties: dict | None = None,
    event_time: datetime | None = None,
    **extra,
) -> dict:
    """Build a single valid event payload."""
    body = {
        "event_name": event_name,
        "event_time": (event_time or datetime.now(UTC)).isoformat(),
        "identifiers": identifiers
        or [{"type": "anonymous_id", "value": f"anon_{uuid4().hex[:12]}"}],
    }
    if properties is not None:
        body["properties"] = properties
    body.update(extra)
    return body


async def _ingest(client: AsyncClient, *events: dict) -> dict:
    """Ingest events and return the batch response JSON."""
    resp = await client.post("/api/v1/cdp/events", json={"events": list(events)})
    assert resp.status_code == 201, resp.text
    return resp.json()


async def _make_profile(client: AsyncClient, *events: dict) -> str:
    """Ingest events (defaults to one PageView) and return the profile id."""
    if not events:
        events = (_mk_event(),)
    data = await _ingest(client, *events)
    return data["results"][0]["profile_id"]


async def _make_customer_profile(client: AsyncClient) -> str:
    """Create a profile with an email identifier and two purchase events."""
    email = f"buyer_{uuid4().hex[:10]}@example.com"
    idents = [{"type": "email", "value": email}]
    data = await _ingest(
        client,
        _mk_event("PageView", identifiers=idents),
        _mk_event("Purchase", identifiers=idents, properties={"total": 120.0}),
        _mk_event("Purchase", identifiers=idents, properties={"total": 80.0}),
    )
    return data["results"][0]["profile_id"]


async def _make_static_segment_with_member(client: AsyncClient) -> tuple[str, str]:
    """Create a static segment containing one freshly-ingested profile.

    Returns (segment_id, profile_id).
    """
    seg_resp = await client.post(
        "/api/v1/cdp/segments",
        json={
            "name": f"Static filter seg {uuid4().hex[:6]}",
            "segment_type": "static",
            "rules": {"logic": "and", "conditions": []},
        },
    )
    assert seg_resp.status_code in (200, 201)
    segment_id = seg_resp.json()["id"]

    profile_id = await _make_profile(client)
    add_resp = await client.post(
        f"/api/v1/cdp/segments/{segment_id}/profiles/{profile_id}"
    )
    assert add_resp.status_code == 201
    return segment_id, profile_id


# =============================================================================
# Unauthenticated Access
# =============================================================================


class TestCDPUnauthenticated:
    """One auth-required check per major CDP route group."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "path",
        [
            "/api/v1/cdp/sources",
            "/api/v1/cdp/events/statistics",
            "/api/v1/cdp/traits",
            "/api/v1/cdp/funnels",
            "/api/v1/cdp/rfm/summary",
            "/api/v1/cdp/merge-history",
            "/api/v1/cdp/identity-links",
            "/api/v1/cdp/anomalies/summary",
        ],
    )
    async def test_get_requires_auth(self, client: AsyncClient, path: str):
        resp = await client.get(path)
        assert resp.status_code in {401, 403}

    @pytest.mark.asyncio
    async def test_ingest_requires_auth(self, client: AsyncClient):
        resp = await client.post("/api/v1/cdp/events", json={"events": [_mk_event()]})
        assert resp.status_code in {401, 403}


# =============================================================================
# Source-Key Authenticated Ingestion
# =============================================================================


class TestSourceKeyIngestion:
    """Tests for source_key validation on event ingestion."""

    @pytest.mark.asyncio
    async def test_ingest_with_valid_source_key(
        self, authenticated_client: AsyncClient
    ):
        created = await authenticated_client.post(
            "/api/v1/cdp/sources",
            json={"name": "Keyed Source", "source_type": "server"},
        )
        assert created.status_code == 201
        source_key = created.json()["source_key"]

        resp = await authenticated_client.post(
            "/api/v1/cdp/events",
            params={"source_key": source_key},
            json={"events": [_mk_event()]},
        )
        assert resp.status_code == 201
        assert resp.json()["accepted"] == 1

        # Source event counters must be updated
        listed = await authenticated_client.get("/api/v1/cdp/sources")
        source = next(
            s for s in listed.json()["sources"] if s["source_key"] == source_key
        )
        assert source["event_count"] == 1
        assert source["last_event_at"] is not None

    @pytest.mark.asyncio
    async def test_ingest_with_invalid_source_key(
        self, authenticated_client: AsyncClient
    ):
        resp = await authenticated_client.post(
            "/api/v1/cdp/events",
            params={"source_key": "cdp_definitely_not_a_key"},
            json={"events": [_mk_event()]},
        )
        assert resp.status_code == 401


# =============================================================================
# Consent Handling During Ingestion
# =============================================================================


class TestConsentIngestion:
    """Tests for consent upsert branches in event ingestion."""

    @pytest.mark.asyncio
    async def test_consent_grant_then_revoke(self, authenticated_client: AsyncClient):
        email = f"consent_{uuid4().hex[:10]}@example.com"
        idents = [{"type": "email", "value": email}]

        granted = await _ingest(
            authenticated_client,
            _mk_event("SignUp", identifiers=idents, consent={"analytics": True}),
        )
        assert granted["accepted"] == 1

        # Second event revokes consent -> exercises existing-consent update path
        revoked = await _ingest(
            authenticated_client,
            _mk_event("OptOut", identifiers=idents, consent={"analytics": False}),
        )
        assert revoked["accepted"] == 1

        # Re-grant covers the granted_at/revoked_at reset branch
        regranted = await _ingest(
            authenticated_client,
            _mk_event("OptIn", identifiers=idents, consent={"analytics": True}),
        )
        assert regranted["accepted"] == 1


# =============================================================================
# Profile Caching
# =============================================================================


class TestProfileCaching:
    """Second lookups should be served from the in-memory profile cache."""

    @pytest.mark.asyncio
    async def test_get_profile_cache_hit(self, authenticated_client: AsyncClient):
        profile_id = await _make_profile(authenticated_client)

        first = await authenticated_client.get(f"/api/v1/cdp/profiles/{profile_id}")
        second = await authenticated_client.get(f"/api/v1/cdp/profiles/{profile_id}")

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["id"] == second.json()["id"]

    @pytest.mark.asyncio
    async def test_lookup_profile_cache_hit(self, authenticated_client: AsyncClient):
        email = f"cached_{uuid4().hex[:10]}@example.com"
        await _make_profile(
            authenticated_client,
            _mk_event("SignUp", identifiers=[{"type": "email", "value": email}]),
        )

        params = {"identifier_type": "email", "identifier_value": email}
        first = await authenticated_client.get("/api/v1/cdp/profiles", params=params)
        second = await authenticated_client.get("/api/v1/cdp/profiles", params=params)

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["id"] == second.json()["id"]


# =============================================================================
# Data Export Endpoints
# =============================================================================


class TestExportProfiles:
    """Tests for GET /export/profiles."""

    @pytest.mark.asyncio
    async def test_export_profiles_json(self, authenticated_client: AsyncClient):
        await _make_profile(authenticated_client)

        resp = await authenticated_client.get("/api/v1/cdp/export/profiles")

        assert resp.status_code == 200
        body = resp.json()
        assert body["format"] == "json"
        assert body["count"] >= 1
        assert isinstance(body["data"], list)
        assert "lifecycle_stage" in body["data"][0]

    @pytest.mark.asyncio
    async def test_export_profiles_csv(self, authenticated_client: AsyncClient):
        await _make_profile(authenticated_client)

        resp = await authenticated_client.get(
            "/api/v1/cdp/export/profiles", params={"format": "csv"}
        )

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")
        assert "identifier_count" in resp.text.splitlines()[0]


class TestExportEvents:
    """Tests for GET /export/events."""

    @pytest.mark.asyncio
    async def test_export_events_json_with_filters(
        self, authenticated_client: AsyncClient
    ):
        await _make_profile(authenticated_client, _mk_event("ExportedEvent"))

        resp = await authenticated_client.get(
            "/api/v1/cdp/export/events",
            params={
                "event_name": "ExportedEvent",
                "start_date": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
                "end_date": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["format"] == "json"
        assert body["count"] >= 1
        assert body["filters"]["event_name"] == "ExportedEvent"
        assert all(e["event_name"] == "ExportedEvent" for e in body["data"])

    @pytest.mark.asyncio
    async def test_export_events_csv(self, authenticated_client: AsyncClient):
        await _make_profile(authenticated_client)

        resp = await authenticated_client.get(
            "/api/v1/cdp/export/events", params={"format": "csv"}
        )

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")
        assert "event_name" in resp.text.splitlines()[0]


# =============================================================================
# Event Statistics and Trends
# =============================================================================


class TestEventStatistics:
    """Tests for GET /events/statistics."""

    @pytest.mark.asyncio
    async def test_statistics_empty(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/cdp/events/statistics")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total_events"] == 0
        assert body["unique_profiles"] == 0
        assert body["avg_emq_score"] is None
        assert body["events_by_name"] == []

    @pytest.mark.asyncio
    async def test_statistics_with_events(self, authenticated_client: AsyncClient):
        await _make_customer_profile(authenticated_client)

        resp = await authenticated_client.get(
            "/api/v1/cdp/events/statistics", params={"period_days": 7}
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["period_days"] == 7
        assert body["total_events"] >= 3
        assert body["unique_profiles"] >= 1
        assert body["avg_emq_score"] is not None
        names = {e["event_name"] for e in body["events_by_name"]}
        assert "Purchase" in names
        assert len(body["daily_volume"]) >= 1
        assert len(body["emq_distribution"]) >= 1


class TestEventTrends:
    """Tests for GET /events/trends."""

    @pytest.mark.asyncio
    async def test_trends_empty(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/cdp/events/trends")

        assert resp.status_code == 200
        body = resp.json()
        assert body["overall_trend"] == "stable"
        assert body["overall_change_pct"] == 0.0
        assert body["event_trends"] == []

    @pytest.mark.asyncio
    async def test_trends_with_events(self, authenticated_client: AsyncClient):
        await _make_profile(authenticated_client, _mk_event("TrendEvent"))

        resp = await authenticated_client.get(
            "/api/v1/cdp/events/trends", params={"period_days": 7}
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["overall_trend"] == "up"
        assert body["current_period"]["total_events"] >= 1
        trend_names = {t["event_name"] for t in body["event_trends"]}
        assert "TrendEvent" in trend_names


class TestProfileStatistics:
    """Tests for GET /profiles/statistics."""

    @pytest.mark.asyncio
    async def test_profile_statistics_empty(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/cdp/profiles/statistics")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total_profiles"] == 0
        assert body["email_coverage_pct"] == 0
        assert body["revenue"]["total"] == 0

    @pytest.mark.asyncio
    async def test_profile_statistics_with_profiles(
        self, authenticated_client: AsyncClient
    ):
        await _make_customer_profile(authenticated_client)
        await _make_profile(authenticated_client)

        resp = await authenticated_client.get("/api/v1/cdp/profiles/statistics")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total_profiles"] >= 2
        assert body["profiles_with_email"] >= 1
        assert body["email_coverage_pct"] > 0
        assert body["new_profiles_7d"] >= 2
        assert "lifecycle_distribution" in body


# =============================================================================
# Profile Search
# =============================================================================


class TestProfileSearch:
    """Tests for POST /profiles/search."""

    @pytest.mark.asyncio
    async def test_search_empty(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post("/api/v1/cdp/profiles/search")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["profiles"] == []

    @pytest.mark.asyncio
    async def test_search_with_inclusive_filters(
        self, authenticated_client: AsyncClient
    ):
        await _make_customer_profile(authenticated_client)

        resp = await authenticated_client.post(
            "/api/v1/cdp/profiles/search",
            params={
                "lifecycle_stages": ["known", "customer"],
                "has_email": "true",
                "min_events": 1,
                "max_events": 1000,
                "min_revenue": 0,
                "max_revenue": 100000,
                "identifier_types": ["email"],
                "sort_by": "total_events",
                "sort_order": "asc",
                "include_identifiers": "true",
                "first_seen_after": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
                "last_seen_before": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        assert body["sort_by"] == "total_events"
        assert "identifiers" in body["profiles"][0]

    @pytest.mark.asyncio
    async def test_search_with_exclusive_filters(
        self, authenticated_client: AsyncClient
    ):
        await _make_profile(authenticated_client)

        resp = await authenticated_client.post(
            "/api/v1/cdp/profiles/search",
            params={
                "query": "no_such_external_id",
                "has_email": "false",
                "has_phone": "false",
                "is_customer": "false",
                "rfm_segments": ["champions"],
                "first_seen_before": (
                    datetime.now(UTC) + timedelta(days=1)
                ).isoformat(),
                "last_seen_after": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
            },
        )

        assert resp.status_code == 200
        # RFM filter excludes freshly-ingested profiles with no traits
        assert resp.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_search_segment_ids_filter(self, authenticated_client: AsyncClient):
        """Regression for #525: this filter 500ed on a non-existent column."""
        segment_id, profile_id = await _make_static_segment_with_member(
            authenticated_client
        )
        # A second profile outside the segment must be filtered out.
        await _make_profile(authenticated_client)

        resp = await authenticated_client.post(
            "/api/v1/cdp/profiles/search", params={"segment_ids": [segment_id]}
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 1
        assert body["profiles"][0]["id"] == profile_id

    @pytest.mark.asyncio
    async def test_search_exclude_segment_ids_filter(
        self, authenticated_client: AsyncClient
    ):
        """Regression for #525 (exclusion direction)."""
        segment_id, member_profile_id = await _make_static_segment_with_member(
            authenticated_client
        )
        outsider_profile_id = await _make_profile(authenticated_client)

        resp = await authenticated_client.post(
            "/api/v1/cdp/profiles/search",
            params={"exclude_segment_ids": [segment_id]},
        )

        assert resp.status_code == 200
        body = resp.json()
        returned_ids = {p["id"] for p in body["profiles"]}
        assert member_profile_id not in returned_ids
        assert outsider_profile_id in returned_ids


# =============================================================================
# Audience Export
# =============================================================================


class TestAudienceExport:
    """Tests for POST /audiences/export."""

    @pytest.mark.asyncio
    async def test_audience_export_json(self, authenticated_client: AsyncClient):
        await _make_customer_profile(authenticated_client)

        resp = await authenticated_client.post(
            "/api/v1/cdp/audiences/export",
            params={
                "lifecycle_stage": "known",
                "min_events": 0,
                "max_events": 1000,
                "min_revenue": 0,
                "max_revenue": 100000,
                "first_seen_after": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
                "first_seen_before": (
                    datetime.now(UTC) + timedelta(days=1)
                ).isoformat(),
                "last_seen_after": (datetime.now(UTC) - timedelta(days=1)).isoformat(),
                "last_seen_before": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
                "has_identifier_type": "email",
                "include_identifiers": "true",
                "include_rfm": "true",
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["format"] == "json"
        assert body["count"] >= 1
        assert body["filters_applied"]["lifecycle_stage"] == "known"
        assert "identifiers" in body["data"][0]

    @pytest.mark.asyncio
    async def test_audience_export_csv(self, authenticated_client: AsyncClient):
        await _make_customer_profile(authenticated_client)

        resp = await authenticated_client.post(
            "/api/v1/cdp/audiences/export",
            params={
                "format": "csv",
                "include_rfm": "true",
                "include_identifiers": "true",
            },
        )

        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/csv")
        header = resp.text.splitlines()[0]
        assert "rfm_segment" in header
        assert "identifier_types" in header

    @pytest.mark.asyncio
    async def test_audience_export_segment_id_filter(
        self, authenticated_client: AsyncClient
    ):
        """Regression for #525: this filter 500ed on a non-existent column."""
        segment_id, _profile_id = await _make_static_segment_with_member(
            authenticated_client
        )
        await _make_profile(authenticated_client)  # outside the segment

        resp = await authenticated_client.post(
            "/api/v1/cdp/audiences/export", params={"segment_id": segment_id}
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 1
        assert body["filters_applied"]["segment_id"] == segment_id

    @pytest.mark.asyncio
    async def test_audience_export_rfm_segment_filter(
        self, authenticated_client: AsyncClient
    ):
        resp = await authenticated_client.post(
            "/api/v1/cdp/audiences/export", params={"rfm_segment": "champions"}
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["count"] == 0
        assert body["filters_applied"]["rfm_segment"] == "champions"


# =============================================================================
# Anomaly Detection
# =============================================================================


class TestAnomalyDetection:
    """Tests for /anomalies/events and /anomalies/summary."""

    @pytest.mark.asyncio
    async def test_anomalies_empty(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/cdp/anomalies/events")

        assert resp.status_code == 200
        body = resp.json()
        assert body["anomaly_count"] == 0
        assert body["has_critical"] is False
        assert body["total_sources_analyzed"] == 0

    @pytest.mark.asyncio
    async def test_anomalies_detects_spike(
        self, authenticated_client: AsyncClient, db_session, test_tenant
    ):
        from app.models.cdp import CDPEvent

        # Seed a stable baseline (4 days) followed by a big spike today.
        now = datetime.now(UTC)
        daily_counts = {4: 4, 3: 5, 2: 6, 1: 5, 0: 30}
        for days_ago, count in daily_counts.items():
            when = now - timedelta(days=days_ago)
            for _ in range(count):
                db_session.add(
                    CDPEvent(
                        tenant_id=test_tenant["id"],
                        event_name="SeededEvent",
                        event_time=when,
                        received_at=when,
                    )
                )
        await db_session.flush()

        resp = await authenticated_client.get(
            "/api/v1/cdp/anomalies/events",
            params={"window_days": 14, "zscore_threshold": 2.5},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["anomaly_count"] >= 1
        top = body["anomalies"][0]
        assert top["direction"] == "high"
        assert top["severity"] in {"medium", "high", "critical"}

    @pytest.mark.asyncio
    async def test_anomaly_summary_empty(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/cdp/anomalies/summary")

        assert resp.status_code == 200
        body = resp.json()
        assert body["health_status"] == "unknown"
        assert body["events_7d"] == 0
        assert body["volume_trend"] == "stable"

    @pytest.mark.asyncio
    async def test_anomaly_summary_with_events(self, authenticated_client: AsyncClient):
        await _make_customer_profile(authenticated_client)

        resp = await authenticated_client.get("/api/v1/cdp/anomalies/summary")

        assert resp.status_code == 200
        body = resp.json()
        assert body["events_7d"] >= 1
        assert body["events_today"] >= 1
        assert body["health_status"] in {"healthy", "fair", "degraded", "critical"}
        assert body["volume_trend"] == "increasing"


# =============================================================================
# Identity Graph / Canonical Identity / Merge
# =============================================================================


class TestIdentityGraph:
    """Tests for identity graph, canonical identity, and merge history."""

    @pytest.mark.asyncio
    async def test_identity_graph_for_profile(self, authenticated_client: AsyncClient):
        anon = f"anon_graph_{uuid4().hex[:10]}"
        email = f"graph_{uuid4().hex[:10]}@example.com"
        profile_id = await _make_profile(
            authenticated_client,
            _mk_event(
                "SignUp",
                identifiers=[
                    {"type": "anonymous_id", "value": anon},
                    {"type": "email", "value": email},
                ],
            ),
        )

        resp = await authenticated_client.get(
            f"/api/v1/cdp/profiles/{profile_id}/identity-graph"
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["profile_id"] == profile_id
        assert body["total_identifiers"] >= 2

    @pytest.mark.asyncio
    async def test_identity_graph_profile_not_found(
        self, authenticated_client: AsyncClient
    ):
        resp = await authenticated_client.get(
            f"/api/v1/cdp/profiles/{_MISSING_ID}/identity-graph"
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_canonical_identity_not_found(
        self, authenticated_client: AsyncClient
    ):
        profile_id = await _make_profile(authenticated_client)
        resp = await authenticated_client.get(
            f"/api/v1/cdp/profiles/{profile_id}/canonical-identity"
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_canonical_identity_found(
        self, authenticated_client: AsyncClient, db_session, test_tenant
    ):
        from app.models.cdp import CDPCanonicalIdentity

        profile_id = await _make_profile(authenticated_client)

        db_session.add(
            CDPCanonicalIdentity(
                tenant_id=test_tenant["id"],
                profile_id=profile_id,
                canonical_type="email",
                canonical_value_hash="a" * 64,
                priority_score=100,
            )
        )
        await db_session.flush()

        resp = await authenticated_client.get(
            f"/api/v1/cdp/profiles/{profile_id}/canonical-identity"
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["profile_id"] == profile_id
        assert body["canonical_type"] == "email"
        assert body["priority_score"] == 100

    @pytest.mark.asyncio
    async def test_profile_merge_history_empty(self, authenticated_client: AsyncClient):
        profile_id = await _make_profile(authenticated_client)
        resp = await authenticated_client.get(
            f"/api/v1/cdp/profiles/{profile_id}/merge-history"
        )
        assert resp.status_code == 200
        assert resp.json()["total"] == 0


class TestProfileMerge:
    """Tests for POST /profiles/merge and GET /merge-history."""

    @pytest.mark.asyncio
    async def test_merge_profiles_roundtrip(self, authenticated_client: AsyncClient):
        source_id = await _make_profile(authenticated_client)
        target_id = await _make_profile(authenticated_client)

        resp = await authenticated_client.post(
            "/api/v1/cdp/profiles/merge",
            json={"source_profile_id": source_id, "target_profile_id": target_id},
        )

        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["surviving_profile_id"] == target_id
        assert body["merged_profile_id"] == source_id
        assert body["is_rolled_back"] is False

        # Merge appears in the tenant-wide history
        history = await authenticated_client.get("/api/v1/cdp/merge-history")
        assert history.status_code == 200
        assert history.json()["total"] >= 1

        # And in the surviving profile's history
        prof_history = await authenticated_client.get(
            f"/api/v1/cdp/profiles/{target_id}/merge-history"
        )
        assert prof_history.status_code == 200
        assert prof_history.json()["total"] >= 1

    @pytest.mark.asyncio
    async def test_merge_profile_with_itself(self, authenticated_client: AsyncClient):
        profile_id = await _make_profile(authenticated_client)
        resp = await authenticated_client.post(
            "/api/v1/cdp/profiles/merge",
            json={"source_profile_id": profile_id, "target_profile_id": profile_id},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_merge_source_not_found(self, authenticated_client: AsyncClient):
        target_id = await _make_profile(authenticated_client)
        resp = await authenticated_client.post(
            "/api/v1/cdp/profiles/merge",
            json={"source_profile_id": _MISSING_ID, "target_profile_id": target_id},
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_merge_target_not_found(self, authenticated_client: AsyncClient):
        source_id = await _make_profile(authenticated_client)
        resp = await authenticated_client.post(
            "/api/v1/cdp/profiles/merge",
            json={"source_profile_id": source_id, "target_profile_id": _MISSING_ID},
        )
        assert resp.status_code == 404


class TestIdentityLinks:
    """Tests for GET /identity-links."""

    @pytest.mark.asyncio
    async def test_identity_links_empty(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/cdp/identity-links")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 0
        assert body["links"] == []

    @pytest.mark.asyncio
    async def test_identity_links_with_type_filter(
        self, authenticated_client: AsyncClient
    ):
        resp = await authenticated_client.get(
            "/api/v1/cdp/identity-links", params={"link_type": "deterministic"}
        )

        assert resp.status_code == 200
        assert resp.json()["total"] == 0


# =============================================================================
# Profile Deletion (GDPR)
# =============================================================================


class TestProfileDeletion:
    """Tests for DELETE /profiles/{profile_id}."""

    @pytest.mark.asyncio
    async def test_delete_profile_with_events(self, authenticated_client: AsyncClient):
        profile_id = await _make_customer_profile(authenticated_client)

        resp = await authenticated_client.delete(
            f"/api/v1/cdp/profiles/{profile_id}",
            params={"reason": "gdpr_request"},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["deleted"] is True
        assert body["events_deleted"] >= 3
        assert body["identifiers_deleted"] >= 1

        gone = await authenticated_client.get(f"/api/v1/cdp/profiles/{profile_id}")
        assert gone.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_profile_always_erases_events(
        self, authenticated_client: AsyncClient
    ):
        # SEC-002: delete_events=false no longer keeps events — a GDPR erasure
        # always removes the profile's PII-bearing events, and the profile.
        profile_id = await _make_profile(authenticated_client)

        resp = await authenticated_client.delete(
            f"/api/v1/cdp/profiles/{profile_id}", params={"delete_events": "false"}
        )

        assert resp.status_code == 200
        gone = await authenticated_client.get(f"/api/v1/cdp/profiles/{profile_id}")
        assert gone.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_profile_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.delete(f"/api/v1/cdp/profiles/{_MISSING_ID}")
        assert resp.status_code == 404


# =============================================================================
# Computed Traits
# =============================================================================


def _trait_payload(name: str | None = None, **extra) -> dict:
    body = {
        "name": name or f"trait_{uuid4().hex[:10]}",
        "display_name": "Total Purchases",
        "trait_type": "count",
        "source_config": {"event_name": "Purchase"},
    }
    body.update(extra)
    return body


class TestComputedTraits:
    """Tests for /traits CRUD and compute endpoints."""

    @pytest.mark.asyncio
    async def test_create_trait(self, authenticated_client: AsyncClient):
        payload = _trait_payload()
        resp = await authenticated_client.post("/api/v1/cdp/traits", json=payload)

        assert resp.status_code == 201
        body = resp.json()
        assert body["name"] == payload["name"]
        assert body["trait_type"] == "count"
        assert body["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_duplicate_trait_conflict(
        self, authenticated_client: AsyncClient
    ):
        payload = _trait_payload()
        first = await authenticated_client.post("/api/v1/cdp/traits", json=payload)
        assert first.status_code == 201

        second = await authenticated_client.post("/api/v1/cdp/traits", json=payload)
        assert second.status_code == 409

    @pytest.mark.asyncio
    async def test_create_trait_invalid_type(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            "/api/v1/cdp/traits", json=_trait_payload(trait_type="not_a_type")
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_list_traits(self, authenticated_client: AsyncClient):
        created = await authenticated_client.post(
            "/api/v1/cdp/traits", json=_trait_payload()
        )
        assert created.status_code == 201

        resp = await authenticated_client.get("/api/v1/cdp/traits")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        assert len(body["traits"]) >= 1

    @pytest.mark.asyncio
    async def test_get_trait_roundtrip(self, authenticated_client: AsyncClient):
        created = await authenticated_client.post(
            "/api/v1/cdp/traits", json=_trait_payload()
        )
        trait_id = created.json()["id"]

        resp = await authenticated_client.get(f"/api/v1/cdp/traits/{trait_id}")

        assert resp.status_code == 200
        assert resp.json()["id"] == trait_id

    @pytest.mark.asyncio
    async def test_get_trait_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"/api/v1/cdp/traits/{_MISSING_ID}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_trait_roundtrip(self, authenticated_client: AsyncClient):
        created = await authenticated_client.post(
            "/api/v1/cdp/traits", json=_trait_payload()
        )
        trait_id = created.json()["id"]

        deleted = await authenticated_client.delete(f"/api/v1/cdp/traits/{trait_id}")
        assert deleted.status_code == 204

        gone = await authenticated_client.get(f"/api/v1/cdp/traits/{trait_id}")
        assert gone.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_trait_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.delete(f"/api/v1/cdp/traits/{_MISSING_ID}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_compute_all_traits(self, authenticated_client: AsyncClient):
        created = await authenticated_client.post(
            "/api/v1/cdp/traits", json=_trait_payload()
        )
        assert created.status_code == 201
        await _make_customer_profile(authenticated_client)

        resp = await authenticated_client.post("/api/v1/cdp/traits/compute")

        assert resp.status_code == 200
        body = resp.json()
        assert body["profiles_processed"] >= 1
        assert body["errors"] == 0

    @pytest.mark.asyncio
    async def test_compute_traits_for_profile(self, authenticated_client: AsyncClient):
        created = await authenticated_client.post(
            "/api/v1/cdp/traits", json=_trait_payload()
        )
        trait_name = created.json()["name"]
        profile_id = await _make_customer_profile(authenticated_client)

        resp = await authenticated_client.post(
            f"/api/v1/cdp/profiles/{profile_id}/compute-traits"
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["profile_id"] == profile_id
        assert body["computed_traits"][trait_name] == 2

    @pytest.mark.asyncio
    async def test_compute_traits_profile_not_found(
        self, authenticated_client: AsyncClient
    ):
        resp = await authenticated_client.post(
            f"/api/v1/cdp/profiles/{_MISSING_ID}/compute-traits"
        )
        assert resp.status_code == 404


# =============================================================================
# RFM Analysis
# =============================================================================


class TestRFMAnalysis:
    """Tests for RFM endpoints."""

    @pytest.mark.asyncio
    async def test_profile_rfm_with_purchases(self, authenticated_client: AsyncClient):
        profile_id = await _make_customer_profile(authenticated_client)

        resp = await authenticated_client.get(f"/api/v1/cdp/profiles/{profile_id}/rfm")

        assert resp.status_code == 200
        body = resp.json()
        assert body["frequency"] == 2
        assert body["monetary"] == 200.0
        assert body["recency_score"] == 5
        assert 1 <= body["rfm_score"] <= 5
        assert body["rfm_segment"]

    @pytest.mark.asyncio
    async def test_profile_rfm_no_purchases(self, authenticated_client: AsyncClient):
        profile_id = await _make_profile(authenticated_client)

        resp = await authenticated_client.get(
            f"/api/v1/cdp/profiles/{profile_id}/rfm",
            params={"analysis_window_days": 90},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["frequency"] == 0
        assert body["monetary"] == 0.0

    @pytest.mark.asyncio
    async def test_profile_rfm_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"/api/v1/cdp/profiles/{_MISSING_ID}/rfm")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_rfm_batch_compute(self, authenticated_client: AsyncClient):
        await _make_customer_profile(authenticated_client)

        resp = await authenticated_client.post(
            "/api/v1/cdp/rfm/compute", json={"analysis_window_days": 90}
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["profiles_processed"] >= 1
        assert body["analysis_window_days"] == 90
        assert isinstance(body["segment_distribution"], dict)

    @pytest.mark.asyncio
    async def test_rfm_summary_after_compute(self, authenticated_client: AsyncClient):
        await _make_customer_profile(authenticated_client)
        computed = await authenticated_client.post("/api/v1/cdp/rfm/compute", json={})
        assert computed.status_code == 200

        resp = await authenticated_client.get("/api/v1/cdp/rfm/summary")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total_profiles"] >= 1
        assert body["profiles_with_rfm"] >= 1
        assert body["coverage_pct"] > 0

    @pytest.mark.asyncio
    async def test_rfm_summary_empty(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get("/api/v1/cdp/rfm/summary")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total_profiles"] == 0
        assert body["coverage_pct"] == 0


# =============================================================================
# Funnels
# =============================================================================


def _funnel_payload(name: str | None = None, **extra) -> dict:
    body = {
        "name": name or f"Funnel {uuid4().hex[:8]}",
        "steps": [
            {"step_name": "View", "event_name": "PageView"},
            {"step_name": "Buy", "event_name": "Purchase"},
        ],
        "conversion_window_days": 30,
    }
    body.update(extra)
    return body


async def _create_funnel(client: AsyncClient, **extra) -> dict:
    resp = await client.post("/api/v1/cdp/funnels", json=_funnel_payload(**extra))
    assert resp.status_code == 201, resp.text
    return resp.json()


class TestFunnels:
    """Tests for funnel CRUD endpoints."""

    @pytest.mark.asyncio
    async def test_create_funnel(self, authenticated_client: AsyncClient):
        body = await _create_funnel(authenticated_client, name="Checkout funnel")
        assert body["name"] == "Checkout funnel"
        assert len(body["steps"]) == 2
        assert body["total_entered"] == 0

    @pytest.mark.asyncio
    async def test_create_funnel_single_step_rejected(
        self, authenticated_client: AsyncClient
    ):
        payload = _funnel_payload()
        payload["steps"] = payload["steps"][:1]
        resp = await authenticated_client.post("/api/v1/cdp/funnels", json=payload)
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_list_funnels(self, authenticated_client: AsyncClient):
        await _create_funnel(authenticated_client)

        resp = await authenticated_client.get("/api/v1/cdp/funnels")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] >= 1
        assert len(body["funnels"]) >= 1

    @pytest.mark.asyncio
    async def test_get_funnel_roundtrip(self, authenticated_client: AsyncClient):
        created = await _create_funnel(authenticated_client, name="Detail funnel")

        resp = await authenticated_client.get(f"/api/v1/cdp/funnels/{created['id']}")

        assert resp.status_code == 200
        assert resp.json()["name"] == "Detail funnel"

    @pytest.mark.asyncio
    async def test_get_funnel_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"/api/v1/cdp/funnels/{_MISSING_ID}")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_funnel(self, authenticated_client: AsyncClient):
        created = await _create_funnel(authenticated_client, name="Before update")

        resp = await authenticated_client.patch(
            f"/api/v1/cdp/funnels/{created['id']}",
            json={
                "name": "After update",
                "steps": [
                    {"step_name": "Land", "event_name": "PageView"},
                    {"step_name": "Cart", "event_name": "AddToCart"},
                    {"step_name": "Buy", "event_name": "Purchase"},
                ],
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "After update"
        assert len(body["steps"]) == 3

    @pytest.mark.asyncio
    async def test_update_funnel_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.patch(
            f"/api/v1/cdp/funnels/{_MISSING_ID}", json={"name": "Nope"}
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_funnel_roundtrip(self, authenticated_client: AsyncClient):
        created = await _create_funnel(authenticated_client)
        fid = created["id"]

        deleted = await authenticated_client.delete(f"/api/v1/cdp/funnels/{fid}")
        assert deleted.status_code == 204

        gone = await authenticated_client.get(f"/api/v1/cdp/funnels/{fid}")
        assert gone.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_funnel_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.delete(f"/api/v1/cdp/funnels/{_MISSING_ID}")
        assert resp.status_code == 404


class TestFunnelAnalytics:
    """Tests for funnel compute / analyze / drop-off endpoints."""

    @pytest.mark.asyncio
    async def test_compute_funnel_with_conversion(
        self, authenticated_client: AsyncClient
    ):
        # One profile completing both steps
        await _make_customer_profile(authenticated_client)
        created = await _create_funnel(authenticated_client)

        resp = await authenticated_client.post(
            f"/api/v1/cdp/funnels/{created['id']}/compute"
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["funnel_id"] == created["id"]
        assert body["total_entered"] >= 1
        assert body["total_converted"] >= 1
        assert len(body["step_metrics"]) == 2

    @pytest.mark.asyncio
    async def test_compute_funnel_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            f"/api/v1/cdp/funnels/{_MISSING_ID}/compute"
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_analyze_funnel(self, authenticated_client: AsyncClient):
        await _make_customer_profile(authenticated_client)
        created = await _create_funnel(authenticated_client)
        computed = await authenticated_client.post(
            f"/api/v1/cdp/funnels/{created['id']}/compute"
        )
        assert computed.status_code == 200

        resp = await authenticated_client.post(
            f"/api/v1/cdp/funnels/{created['id']}/analyze",
            json={
                "start_date": (datetime.now(UTC) - timedelta(days=7)).isoformat(),
                "end_date": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            },
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["funnel_id"] == created["id"]

    @pytest.mark.asyncio
    async def test_analyze_funnel_not_found(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            f"/api/v1/cdp/funnels/{_MISSING_ID}/analyze"
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_funnel_drop_offs(self, authenticated_client: AsyncClient):
        # A profile that only completes step 1
        await _make_profile(authenticated_client, _mk_event("PageView"))
        created = await _create_funnel(authenticated_client)
        computed = await authenticated_client.post(
            f"/api/v1/cdp/funnels/{created['id']}/compute"
        )
        assert computed.status_code == 200

        resp = await authenticated_client.get(
            f"/api/v1/cdp/funnels/{created['id']}/drop-offs/1"
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["funnel_id"] == created["id"]
        assert body["step"] == 1
        assert body["total"] >= 1

    @pytest.mark.asyncio
    async def test_funnel_drop_offs_invalid_step(
        self, authenticated_client: AsyncClient
    ):
        created = await _create_funnel(authenticated_client)
        resp = await authenticated_client.get(
            f"/api/v1/cdp/funnels/{created['id']}/drop-offs/99"
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_funnel_drop_offs_funnel_not_found(
        self, authenticated_client: AsyncClient
    ):
        resp = await authenticated_client.get(
            f"/api/v1/cdp/funnels/{_MISSING_ID}/drop-offs/1"
        )
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_profile_funnel_journeys(self, authenticated_client: AsyncClient):
        profile_id = await _make_customer_profile(authenticated_client)
        created = await _create_funnel(authenticated_client)
        computed = await authenticated_client.post(
            f"/api/v1/cdp/funnels/{created['id']}/compute"
        )
        assert computed.status_code == 200

        resp = await authenticated_client.get(
            f"/api/v1/cdp/profiles/{profile_id}/funnels",
            params={"funnel_id": created["id"]},
        )

        assert resp.status_code == 200
        body = resp.json()
        assert body["profile_id"] == profile_id
        assert isinstance(body["journeys"], list)

    @pytest.mark.asyncio
    async def test_profile_funnel_journeys_profile_not_found(
        self, authenticated_client: AsyncClient
    ):
        resp = await authenticated_client.get(
            f"/api/v1/cdp/profiles/{_MISSING_ID}/funnels"
        )
        assert resp.status_code == 404
