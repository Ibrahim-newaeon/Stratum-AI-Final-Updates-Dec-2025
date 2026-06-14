# =============================================================================
# Stratum AI - Pipedrive Client Pure-Logic Unit Tests
# =============================================================================
"""Unit tests for the pure helpers in ``app.services.crm.pipedrive_client``:

- ``hash_email`` / ``hash_phone`` identity hashing
- ``PipedriveClient.get_authorization_url`` OAuth-URL building (including
  the auto-generated CSRF ``state`` and explicit-state passthrough)

The DB/HTTP-backed client methods are out of scope; ``__init__`` only
stores config (no HTTP client until ``__aenter__``).
"""

import hashlib
from urllib.parse import parse_qs, urlparse

import pytest

from app.services.crm.pipedrive_client import (
    PipedriveClient,
    hash_email,
    hash_phone,
)

pytestmark = pytest.mark.unit


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


@pytest.fixture
def client() -> PipedriveClient:
    return PipedriveClient(db=None, tenant_id=1)


# =============================================================================
# hashing
# =============================================================================
class TestHashing:
    def test_email_lowercased_and_trimmed(self):
        assert hash_email("  Sales@Acme.COM ") == _sha("sales@acme.com")

    def test_phone_strips_non_digits(self):
        assert hash_phone("+44 (20) 7946-0958") == _sha("442079460958")

    def test_hashing_is_deterministic(self):
        assert hash_phone("555-1234") == hash_phone("555-1234")


# =============================================================================
# get_authorization_url
# =============================================================================
class TestAuthorizationUrl:
    def test_includes_redirect_and_state(self, client):
        url = client.get_authorization_url("https://app.example.com/cb", state="xyz")
        qs = parse_qs(urlparse(url).query)
        assert qs["redirect_uri"] == ["https://app.example.com/cb"]
        assert qs["state"] == ["xyz"]
        assert "client_id" in qs

    def test_auto_generates_state_when_omitted(self, client):
        url = client.get_authorization_url("https://app.example.com/cb")
        qs = parse_qs(urlparse(url).query)
        # A CSRF state token is generated when not supplied.
        assert qs["state"][0]
        assert len(qs["state"][0]) >= 20

    def test_distinct_state_per_call(self, client):
        u1 = client.get_authorization_url("https://app.example.com/cb")
        u2 = client.get_authorization_url("https://app.example.com/cb")
        s1 = parse_qs(urlparse(u1).query)["state"][0]
        s2 = parse_qs(urlparse(u2).query)["state"][0]
        assert s1 != s2
