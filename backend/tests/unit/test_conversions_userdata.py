# =============================================================================
# Stratum AI - Conversions UserData / CAPI Formatting Unit Tests
# =============================================================================
"""Unit tests for the pure PII-normalization and CAPI-formatting logic in
``app.stratum.conversions``.

Covers ``UserData.get_hashed`` / ``_normalize`` (deterministic SHA-256 of
normalized PII) and ``MetaConversionsAPI._format_user_data`` (hashed +
pass-through fields). Network sends are out of scope here.
"""

import hashlib
from datetime import datetime, timezone

import pytest

from app.stratum.conversions import (
    ConversionEvent,
    EventType,
    MetaConversionsAPI,
    UserData,
)

pytestmark = pytest.mark.unit


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


# =============================================================================
# UserData normalization + hashing
# =============================================================================
class TestUserDataHashing:
    def test_email_lowercased_and_hashed(self):
        ud = UserData(email="  Test@Example.COM ")
        assert ud.get_hashed("email") == _sha("test@example.com")

    def test_phone_strips_formatting_and_adds_country_code(self):
        ud = UserData(phone="(555) 123-4567")
        assert ud.get_hashed("phone") == _sha("15551234567")

    def test_phone_keeps_existing_country_code(self):
        ud = UserData(phone="+44 7700 900123")
        assert ud.get_hashed("phone") == _sha("447700900123")

    def test_name_strips_non_alpha(self):
        ud = UserData(first_name="O'Brien-3")
        assert ud.get_hashed("first_name") == _sha("obrien")

    def test_state_truncated_to_two_chars(self):
        ud = UserData(state="California")
        assert ud.get_hashed("state") == _sha("ca")

    def test_zip_first_five_digits(self):
        ud = UserData(zip_code="94105-1234")
        assert ud.get_hashed("zip_code") == _sha("94105")

    def test_missing_field_returns_none(self):
        assert UserData().get_hashed("email") is None

    def test_empty_string_returns_none(self):
        assert UserData(email="").get_hashed("email") is None


# =============================================================================
# MetaConversionsAPI._format_user_data
# =============================================================================
class TestFormatUserData:
    @pytest.fixture
    def capi(self) -> MetaConversionsAPI:
        return MetaConversionsAPI(
            pixel_id="123456789", access_token="tok"
        )  # gitleaks:allow

    def test_hashes_pii_and_passes_through_identifiers(self, capi):
        ud = UserData(
            email="buyer@example.com",
            external_id="cust_42",
            fbc="fb.1.click",
            client_ip_address="203.0.113.7",
        )
        out = capi._format_user_data(ud)
        # Non-PII identifiers pass through unhashed.
        assert out["external_id"] == "cust_42"
        assert out["fbc"] == "fb.1.click"
        assert out["client_ip_address"] == "203.0.113.7"
        # The hashed email value appears somewhere in the payload.
        assert _sha("buyer@example.com") in out.values()

    def test_omits_absent_fields(self, capi):
        out = capi._format_user_data(UserData(external_id="only_id"))
        assert out["external_id"] == "only_id"
        # No email field was provided, so no hashed email is present.
        assert _sha("") not in out.values()


# =============================================================================
# ConversionEvent construction
# =============================================================================
class TestConversionEvent:
    def test_constructs_with_event_type(self):
        event = ConversionEvent(
            event_name=EventType.PURCHASE,
            event_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
            user_data=UserData(email="x@example.com"),
            custom_data={"currency": "USD", "value": 99.99},
        )
        assert event.event_name == EventType.PURCHASE
        assert event.custom_data["value"] == 99.99
