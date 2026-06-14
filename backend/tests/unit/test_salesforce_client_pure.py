# =============================================================================
# Stratum AI - Salesforce Client Pure-Logic Unit Tests
# =============================================================================
"""Unit tests for the pure helpers in ``app.services.crm.salesforce_client``:

- ``hash_email`` / ``hash_phone`` identity hashing
- ``SalesforceClient.auth_url`` / ``token_url`` sandbox-aware OAuth endpoints

The DB/HTTP-backed client methods are out of scope; ``__init__`` only
stores config (no session is opened until ``__aenter__``).
"""

import hashlib

import pytest

from app.services.crm.salesforce_client import (
    SALESFORCE_AUTH_URL,
    SALESFORCE_TOKEN_URL,
    SANDBOX_AUTH_URL,
    SANDBOX_TOKEN_URL,
    SalesforceClient,
    hash_email,
    hash_phone,
)

pytestmark = pytest.mark.unit


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


# =============================================================================
# hashing
# =============================================================================
class TestHashing:
    def test_email_lowercased_and_trimmed(self):
        assert hash_email("  Rep@Acme.COM ") == _sha("rep@acme.com")

    def test_phone_strips_non_digits(self):
        assert hash_phone("+1 (555) 987-6543") == _sha("15559876543")

    def test_hashing_is_deterministic(self):
        assert hash_email("a@b.com") == hash_email("a@b.com")


# =============================================================================
# sandbox-aware OAuth endpoints
# =============================================================================
class TestOAuthUrls:
    def test_production_urls(self):
        client = SalesforceClient(db=None, tenant_id=1, is_sandbox=False)
        assert client.auth_url == SALESFORCE_AUTH_URL
        assert client.token_url == SALESFORCE_TOKEN_URL

    def test_sandbox_urls(self):
        client = SalesforceClient(db=None, tenant_id=1, is_sandbox=True)
        assert client.auth_url == SANDBOX_AUTH_URL
        assert client.token_url == SANDBOX_TOKEN_URL

    def test_sandbox_differs_from_production(self):
        prod = SalesforceClient(db=None, tenant_id=1, is_sandbox=False)
        sandbox = SalesforceClient(db=None, tenant_id=1, is_sandbox=True)
        assert prod.auth_url != sandbox.auth_url
        assert "test.salesforce.com" in sandbox.token_url
