# =============================================================================
# Stratum AI - Test Configuration (conftest.py)
# =============================================================================
"""
Pytest configuration for unit tests.

Unit tests should not require database connections. Integration tests have
their own conftest.py in the integration/ directory.
"""

import os
import pytest
from datetime import datetime, date, timezone


# Set test environment variables before any imports
os.environ["APP_ENV"] = "development"
os.environ["DEBUG"] = "true"


# =============================================================================
# Markers Configuration
# =============================================================================

def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test (requires database)"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as an end-to-end test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )


# =============================================================================
# Mock Data Fixtures (No Database Required)
# =============================================================================

@pytest.fixture
def sample_emq_metrics():
    """Sample EMQ metrics for testing."""
    return {
        "event_match_rate": 87.5,
        "pixel_coverage": 92.3,
        "conversion_latency": 68.2,
        "attribution_accuracy": 78.9,
        "data_freshness": 95.1,
    }


@pytest.fixture
def sample_tenant_data():
    """Sample tenant data for unit testing."""
    return {
        "id": 1,
        "name": "Test Tenant",
        "slug": "test-tenant",
        "plan": "professional",
        "is_active": True,
    }


@pytest.fixture
def sample_user_data():
    """Sample user data for unit testing."""
    return {
        "id": 1,
        "email": "test@example.com",
        "full_name": "Test User",
        "role": "admin",
        "tenant_id": 1,
    }
