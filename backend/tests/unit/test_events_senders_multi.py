# =============================================================================
# Stratum AI - Multi-Platform Server Events Formatter Unit Tests
# =============================================================================
"""Unit tests for the pure ``_format_event`` helpers of the Google, TikTok,
and Snapchat senders in ``app.stratum.events``. Each shapes a ``ServerEvent``
into its platform-specific payload (with PII hashing). Network senders
(requests.post) are out of scope here.
"""

import hashlib
from datetime import datetime, timezone

import pytest

from app.stratum.events import (
    ContentItem,
    GoogleEventsSender,
    ServerEvent,
    SnapchatEventsSender,
    StandardEvent,
    TikTokEventsSender,
    UserData,
)

pytestmark = pytest.mark.unit


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _purchase(**overrides) -> ServerEvent:
    base = dict(
        event_name=StandardEvent.PURCHASE,
        user_data=UserData(
            email="buyer@example.com",
            phone="+15551234567",
            external_id="cust_1",
            ttclid="tt_1",
        ),
        event_time=datetime(2026, 6, 1, tzinfo=timezone.utc),
        value=99.0,
        currency="USD",
        contents=[ContentItem(id="SKU1", name="Sofa", quantity=2, price=49.5)],
        order_id="ORD-1",
        search_string="sofa",
    )
    base.update(overrides)
    return ServerEvent(**base)


# =============================================================================
# Google (GA4 Measurement Protocol)
# =============================================================================
class TestGoogle:
    @pytest.fixture
    def sender(self) -> GoogleEventsSender:
        return GoogleEventsSender(
            measurement_id="G-XXX", api_secret="s", client_id="cid"  # gitleaks:allow
        )

    def test_event_envelope(self, sender):
        out = sender._format_event(_purchase())
        assert out["client_id"] == "cid"
        assert out["user_id"] == "cust_1"
        ev = out["events"][0]
        assert ev["name"] == "purchase"
        assert ev["params"]["value"] == 99.0
        assert ev["params"]["currency"] == "USD"
        assert ev["params"]["transaction_id"] == "ORD-1"
        assert ev["params"]["search_term"] == "sofa"

    def test_items_mapped(self, sender):
        items = sender._format_event(_purchase())["events"][0]["params"]["items"]
        assert items[0]["item_id"] == "SKU1"
        assert items[0]["item_name"] == "Sofa"
        assert items[0]["quantity"] == 2

    def test_user_properties_hashed(self, sender):
        props = sender._format_event(_purchase())["user_properties"]
        assert props["email"]["value"] == _sha("buyer@example.com")


# =============================================================================
# TikTok (Events API)
# =============================================================================
class TestTikTok:
    @pytest.fixture
    def sender(self) -> TikTokEventsSender:
        return TikTokEventsSender(pixel_code="px", access_token="tok")  # gitleaks:allow

    def test_event_and_user(self, sender):
        out = sender._format_event(_purchase())
        assert out["event"] == "CompletePayment"
        assert out["user"]["email"] == _sha("buyer@example.com")
        assert out["user"]["external_id"] == "cust_1"
        assert out["user"]["ttclid"] == "tt_1"

    def test_properties(self, sender):
        props = sender._format_event(_purchase())["properties"]
        assert props["value"] == 99.0
        assert props["contents"][0]["content_id"] == "SKU1"
        assert props["query"] == "sofa"


# =============================================================================
# Snapchat (Conversions API)
# =============================================================================
class TestSnapchat:
    @pytest.fixture
    def sender(self) -> SnapchatEventsSender:
        return SnapchatEventsSender(pixel_id="px", access_token="tok")  # gitleaks:allow

    def test_envelope_and_hashed_pii(self, sender):
        out = sender._format_event(_purchase())
        assert out["pixel_id"] == "px"
        assert out["event_conversion_type"] == "WEB"
        assert out["hashed_email"] == _sha("buyer@example.com")
        assert "hashed_phone_number" in out

    def test_purchase_fields_and_items(self, sender):
        out = sender._format_event(_purchase())
        assert out["price"] == "99.0"
        assert out["currency"] == "USD"
        assert out["transaction_id"] == "ORD-1"
        assert out["item_ids"] == ["SKU1"]
        assert out["number_items"] == "2"

    def test_non_purchase_omits_price(self, sender):
        ev = _purchase(event_name=StandardEvent.PAGE_VIEW, value=None)
        out = sender._format_event(ev)
        assert "price" not in out
