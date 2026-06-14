# =============================================================================
# Stratum AI - Zoho CRM Normalization Unit Tests
# =============================================================================
"""Unit tests for the pure module-level helpers in
``app.services.crm.zoho_client``:

- ``hash_email`` / ``hash_phone`` privacy-safe identity hashing
- ``normalize_zoho_contact`` / ``normalize_zoho_deal`` field mapping
  (including nested object flattening)

The DB-backed ``ZohoClient`` is out of scope here.
"""

import hashlib

import pytest

from app.services.crm.zoho_client import (
    hash_email,
    hash_phone,
    normalize_zoho_contact,
    normalize_zoho_deal,
)

pytestmark = pytest.mark.unit


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


# =============================================================================
# hashing
# =============================================================================
class TestHashing:
    def test_email_lowercased_and_trimmed(self):
        assert hash_email("  Buyer@Example.COM ") == _sha("buyer@example.com")

    def test_email_is_deterministic(self):
        assert hash_email("a@b.com") == hash_email("a@b.com")

    def test_phone_strips_non_digits(self):
        assert hash_phone("+1 (555) 123-4567") == _sha("15551234567")

    def test_phone_empty_after_strip(self):
        assert hash_phone("no-digits") == _sha("")


# =============================================================================
# contact normalization
# =============================================================================
class TestNormalizeContact:
    def test_maps_known_fields(self):
        out = normalize_zoho_contact(
            {
                "id": "z123",
                "Email": "x@y.com",
                "First_Name": "Ada",
                "Last_Name": "Lovelace",
                "Phone": "555",
            }
        )
        assert out["zoho_id"] == "z123"
        assert out["email"] == "x@y.com"
        assert out["first_name"] == "Ada"
        assert out["last_name"] == "Lovelace"
        assert out["phone"] == "555"

    def test_flattens_nested_objects_by_name(self):
        out = normalize_zoho_contact(
            {"id": "z1", "Owner": {"name": "Rep A", "id": "u9"}}
        )
        assert out["owner"] == "Rep A"

    def test_nested_object_falls_back_to_id(self):
        out = normalize_zoho_contact({"id": "z1", "Account_Name": {"id": "acc7"}})
        assert out["company"] == "acc7"

    def test_unmapped_fields_are_ignored(self):
        out = normalize_zoho_contact({"id": "z1", "Unknown_Field": "ignored"})
        assert "Unknown_Field" not in out
        assert out == {"zoho_id": "z1"}


# =============================================================================
# deal normalization
# =============================================================================
class TestNormalizeDeal:
    def test_maps_known_fields(self):
        out = normalize_zoho_deal(
            {
                "id": "d1",
                "Deal_Name": "Big Deal",
                "Amount": 50000,
                "Stage": "Closed Won",
            }
        )
        assert out["zoho_id"] == "d1"
        assert out["deal_name"] == "Big Deal"
        assert out["amount"] == 50000
        assert out["stage"] == "Closed Won"

    def test_flattens_contact_object(self):
        out = normalize_zoho_deal({"id": "d1", "Contact_Name": {"name": "Buyer"}})
        assert out["contact"] == "Buyer"

    def test_missing_id_is_none(self):
        out = normalize_zoho_deal({"Deal_Name": "No ID"})
        assert out["zoho_id"] is None
        assert out["deal_name"] == "No ID"
