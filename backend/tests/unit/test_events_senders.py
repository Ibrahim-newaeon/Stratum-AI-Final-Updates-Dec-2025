# =============================================================================
# Stratum AI - Server Events Formatter Unit Tests
# =============================================================================
"""Unit tests for the pure formatting helpers in ``app.stratum.events``:

- ``MetaEventsSender._format_event`` / ``_format_user_data`` (CAPI payload
  shaping + PII hashing)
- ``EcommerceTracker._make_user_data`` / ``_make_content_item`` (dict ->
  dataclass builders)

Network senders (requests.post) are out of scope here.
"""

import hashlib
from datetime import datetime, timezone

import pytest

from app.stratum.events import (
    ContentItem,
    EcommerceTracker,
    MetaEventsSender,
    ServerEvent,
    StandardEvent,
    UserData,
)

pytestmark = pytest.mark.unit


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


@pytest.fixture
def sender() -> MetaEventsSender:
    return MetaEventsSender(pixel_id="123", access_token="tok")  # gitleaks:allow


@pytest.fixture
def tracker() -> EcommerceTracker:
    return EcommerceTracker()


# =============================================================================
# MetaEventsSender._format_event
# =============================================================================
class TestFormatEvent:
    def _event(self, **overrides) -> ServerEvent:
        base = dict(
            event_name=StandardEvent.PURCHASE,
            user_data=UserData(email="buyer@example.com"),
            event_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
            value=99.0,
            currency="USD",
            contents=[ContentItem(id="SKU1", quantity=2)],
            order_id="ORD-1",
        )
        base.update(overrides)
        return ServerEvent(**base)

    def test_maps_event_name_and_core_fields(self, sender):
        data = sender._format_event(self._event())
        assert data["event_name"] == "Purchase"
        assert data["event_time"] == int(
            datetime(2026, 6, 1, tzinfo=timezone.utc).timestamp()
        )
        assert "user_data" in data

    def test_custom_data_carries_value_currency_and_contents(self, sender):
        data = sender._format_event(self._event())
        cd = data["custom_data"]
        assert cd["value"] == 99.0
        assert cd["currency"] == "USD"
        assert cd["content_ids"] == ["SKU1"]
        assert cd["num_items"] == 2
        assert cd["order_id"] == "ORD-1"

    def test_minimal_event_omits_optional_custom_data(self, sender):
        ev = ServerEvent(
            event_name=StandardEvent.PAGE_VIEW,
            user_data=UserData(email="x@y.com"),
            event_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
        )
        data = sender._format_event(ev)
        # No value/contents -> no value key in custom_data (may be absent entirely).
        assert "value" not in data.get("custom_data", {})


# =============================================================================
# MetaEventsSender._format_user_data
# =============================================================================
class TestFormatUserData:
    def test_email_is_hashed_under_em(self, sender):
        out = sender._format_user_data(UserData(email="Buyer@Example.com"))
        # Email is normalized (lowercased) then SHA-256 hashed.
        assert out["em"] == _sha("buyer@example.com")

    def test_absent_fields_are_omitted(self, sender):
        out = sender._format_user_data(UserData(email="x@y.com"))
        assert "ph" not in out


# =============================================================================
# EcommerceTracker builders
# =============================================================================
class TestTrackerBuilders:
    def test_make_user_data_maps_aliases(self, tracker):
        ud = tracker._make_user_data(
            {"email": "a@b.com", "customer_id": "cust_9", "ip": "1.2.3.4"}
        )
        assert ud.email == "a@b.com"
        assert ud.external_id == "cust_9"
        assert ud.client_ip_address == "1.2.3.4"

    def test_make_user_data_external_id_fallback(self, tracker):
        ud = tracker._make_user_data({"external_id": "ext_1"})
        assert ud.external_id == "ext_1"

    def test_make_content_item_sku_fallback_and_default_quantity(self, tracker):
        ci = tracker._make_content_item({"sku": "S9", "price": 10.0})
        assert ci.id == "S9"
        assert ci.quantity == 1
        assert ci.price == 10.0

    def test_make_content_item_prefers_id_over_sku(self, tracker):
        ci = tracker._make_content_item({"id": "ID1", "sku": "S9", "quantity": 3})
        assert ci.id == "ID1"
        assert ci.quantity == 3
