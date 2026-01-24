# Testing Guide

## Overview

Stratum AI uses pytest for backend testing with a target of 90%+ coverage for core modules.

---

## Test Stack

| Tool | Purpose |
|------|---------|
| pytest | Test framework |
| pytest-asyncio | Async test support |
| pytest-cov | Coverage reporting |
| httpx | Async HTTP client for API tests |
| factory-boy | Test data factories |
| faker | Fake data generation |

---

## Project Structure

```
tests/
├── conftest.py           # Shared fixtures
├── factories.py          # Data factories
├── test_auth.py          # Authentication tests
├── test_campaigns.py     # Campaign API tests
├── test_cdp.py           # CDP tests
├── test_rules.py         # Rules engine tests
├── test_trust_layer.py   # Trust layer tests
├── integration/          # Integration tests
│   ├── test_meta_api.py
│   └── test_stripe.py
└── unit/                 # Unit tests
    ├── test_services.py
    └── test_utils.py
```

---

## Running Tests

### All Tests

```bash
# Run all tests
pytest

# With verbose output
pytest -v

# Stop on first failure
pytest -x
```

### Specific Tests

```bash
# Single file
pytest tests/test_auth.py

# Single test function
pytest tests/test_auth.py::test_login_success

# By marker
pytest -m "not slow"
pytest -m integration
```

### Coverage

```bash
# Run with coverage
pytest --cov=app

# Generate HTML report
pytest --cov=app --cov-report=html

# View report
open htmlcov/index.html
```

### Parallel Execution

```bash
# Run tests in parallel
pytest -n auto

# Specify number of workers
pytest -n 4
```

---

## Fixtures

### Database Session

```python
# conftest.py

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

@pytest.fixture
async def db_session():
    """Create a test database session."""
    engine = create_async_engine(
        "postgresql+asyncpg://test:test@localhost:5432/test_db"
    )

    async with AsyncSession(engine) as session:
        yield session
        await session.rollback()
```

### Test Client

```python
@pytest.fixture
async def client():
    """Create a test HTTP client."""
    from app.main import app

    async with AsyncClient(
        app=app,
        base_url="http://test"
    ) as client:
        yield client
```

### Authenticated Client

```python
@pytest.fixture
async def auth_client(client, test_user):
    """Create an authenticated test client."""
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": test_user.email, "password": "password123"}
    )
    token = response.json()["access_token"]

    client.headers["Authorization"] = f"Bearer {token}"
    return client
```

### Test User

```python
@pytest.fixture
async def test_user(db_session):
    """Create a test user."""
    user = User(
        email="test@example.com",
        email_hash=hash_email("test@example.com"),
        password_hash=hash_password("password123"),
        role=UserRole.ADMIN,
        tenant_id=1,
    )
    db_session.add(user)
    await db_session.commit()
    return user
```

### Test Tenant

```python
@pytest.fixture
async def test_tenant(db_session):
    """Create a test tenant."""
    tenant = Tenant(
        name="Test Tenant",
        slug="test-tenant",
        plan="professional",
    )
    db_session.add(tenant)
    await db_session.commit()
    return tenant
```

---

## Factories

### User Factory

```python
# tests/factories.py

import factory
from factory.alchemy import SQLAlchemyModelFactory

class UserFactory(SQLAlchemyModelFactory):
    class Meta:
        model = User
        sqlalchemy_session_persistence = "commit"

    email = factory.Faker("email")
    full_name = factory.Faker("name")
    role = UserRole.ANALYST
    is_active = True

    @factory.lazy_attribute
    def email_hash(self):
        return hash_email(self.email)

    @factory.lazy_attribute
    def password_hash(self):
        return hash_password("password123")
```

### Campaign Factory

```python
class CampaignFactory(SQLAlchemyModelFactory):
    class Meta:
        model = Campaign

    name = factory.Faker("catch_phrase")
    platform = factory.Iterator([AdPlatform.META, AdPlatform.GOOGLE])
    status = CampaignStatus.ACTIVE
    external_id = factory.LazyFunction(lambda: str(uuid4()))
    account_id = factory.Faker("uuid4")
    daily_budget_cents = factory.Faker("random_int", min=1000, max=10000)
```

### Using Factories

```python
async def test_campaign_list(auth_client, test_tenant, db_session):
    # Create test data
    campaigns = CampaignFactory.create_batch(
        5,
        tenant_id=test_tenant.id,
        _session=db_session
    )

    # Test endpoint
    response = await auth_client.get("/api/v1/campaigns")

    assert response.status_code == 200
    assert len(response.json()["items"]) == 5
```

---

## Test Patterns

### API Endpoint Test

```python
@pytest.mark.asyncio
async def test_login_success(client, test_user):
    """Test successful login."""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "email": test_user.email,
            "password": "password123"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == test_user.email
```

### Authentication Required Test

```python
@pytest.mark.asyncio
async def test_campaigns_requires_auth(client):
    """Test that campaigns endpoint requires authentication."""
    response = await client.get("/api/v1/campaigns")

    assert response.status_code == 401
```

### Permission Test

```python
@pytest.mark.asyncio
async def test_delete_requires_admin(auth_client, test_user):
    """Test that delete requires admin role."""
    # Create viewer user
    test_user.role = UserRole.VIEWER

    response = await auth_client.delete("/api/v1/campaigns/1")

    assert response.status_code == 403
```

### Validation Test

```python
@pytest.mark.asyncio
async def test_campaign_create_validation(auth_client):
    """Test campaign creation validation."""
    response = await auth_client.post(
        "/api/v1/campaigns",
        json={
            "name": "",  # Invalid: empty name
            "platform": "invalid_platform",  # Invalid enum
        }
    )

    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(e["loc"] == ["body", "name"] for e in errors)
```

### Service Unit Test

```python
@pytest.mark.asyncio
async def test_segment_computation(db_session, test_tenant):
    """Test CDP segment computation."""
    from app.services.cdp.segment_service import compute_segment

    # Create test profiles
    profiles = ProfileFactory.create_batch(10, tenant_id=test_tenant.id)

    # Create segment with conditions
    segment = SegmentFactory.create(
        tenant_id=test_tenant.id,
        conditions={"operator": "and", "conditions": [
            {"type": "trait", "trait": "total_purchases", "operator": "gt", "value": 100}
        ]}
    )

    # Compute
    result = await compute_segment(segment.id)

    assert result["profile_count"] >= 0
```

### Mocking External Services

```python
@pytest.mark.asyncio
async def test_meta_sync_with_mock(auth_client, mocker):
    """Test Meta campaign sync with mocked API."""
    # Mock Meta API response
    mock_response = {
        "data": [
            {"id": "123", "name": "Campaign 1", "status": "ACTIVE"},
            {"id": "456", "name": "Campaign 2", "status": "PAUSED"},
        ]
    }

    mocker.patch(
        "app.services.integrations.meta.fetch_campaigns",
        return_value=mock_response
    )

    # Trigger sync
    response = await auth_client.post("/api/v1/campaigns/sync/meta")

    assert response.status_code == 200
    assert response.json()["synced_count"] == 2
```

---

## Test Markers

### Available Markers

```python
# pytest.ini or pyproject.toml
[tool.pytest.ini_options]
markers = [
    "slow: marks tests as slow",
    "integration: integration tests requiring external services",
    "unit: unit tests",
    "e2e: end-to-end tests",
]
```

### Using Markers

```python
@pytest.mark.slow
async def test_full_sync():
    """This test takes a long time."""
    ...

@pytest.mark.integration
async def test_stripe_webhook():
    """Requires Stripe test environment."""
    ...

@pytest.mark.unit
async def test_password_hash():
    """Fast unit test."""
    ...
```

### Running by Marker

```bash
# Skip slow tests
pytest -m "not slow"

# Only integration tests
pytest -m integration

# Unit tests only
pytest -m unit
```

---

## Coverage Requirements

### Target Coverage

| Module | Target |
|--------|--------|
| `app/core/` | 90% |
| `app/services/` | 90% |
| `app/api/` | 85% |
| `app/workers/` | 80% |
| Overall | 85% |

### Coverage Configuration

```ini
# pyproject.toml
[tool.coverage.run]
source = ["app"]
omit = ["*/tests/*", "*/__pycache__/*"]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
]
fail_under = 85
```

---

## CI/CD Integration

### GitHub Actions

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_DB: test_db
          POSTGRES_USER: test
          POSTGRES_PASSWORD: test
        ports:
          - 5432:5432

      redis:
        image: redis:7
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run tests
        run: pytest --cov=app --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Debugging Tests

### Print Output

```bash
# Show print statements
pytest -s

# Show print + verbose
pytest -sv
```

### Drop into Debugger

```python
def test_something():
    import pdb; pdb.set_trace()  # Breakpoint
    result = do_thing()
```

```bash
# Run with debugger
pytest --pdb
```

### Show Locals on Failure

```bash
pytest --showlocals
```
