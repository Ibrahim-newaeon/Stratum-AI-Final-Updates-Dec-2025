# =============================================================================
# Stratum AI - Server Events EMQ / Content Unit Tests
# =============================================================================
"""Unit tests for the pure logic in ``app.stratum.events``.

Covers ``UserData.match_quality_score`` (EMQ estimate), gmail-aware
``get_hashed`` normalization, ``ContentItem.to_dict``, and ``ServerEvent``
content helpers. Network senders are out of scope here.
"""

import hashlib

import pytest

from app.stratum.events import ContentItem, ServerEvent, StandardEvent, UserData

pytestmark = pytest.mark.unit


# =============================================================================
# match_quality_score
# =============================================================================
class TestMatchQualityScore:
    def test_empty_is_zero(self):
        assert UserData().match_quality_score() == 0

    def test_email_only(self):
        assert UserData(email="a@b.com").match_quality_score() == 25

    def test_email_and_phone(self):
        assert (
            UserData(email="a@b.com", phone="+15551234567").match_quality_score() == 50
        )

    def test_strong_combo(self):
        # fbc(30) + email(25) + phone(25) + external_id(10) = 90
        ud = UserData(email="a@b.com", phone="1", external_id="x", fbc="fb.1.click")
        assert ud.match_quality_score() == 90

    def test_score_is_capped_at_100(self):
        ud = UserData(
            fbc="c",
            gclid="g",
            ttclid="t",
            email="a@b.com",
            phone="1",
            external_id="x",
            client_ip_address="1.2.3.4",
            client_user_agent="UA",
        )
        # 30+30+30+25+25+10+5+5 = 160 -> capped
        assert ud.match_quality_score() == 100


# =============================================================================
# get_hashed
# =============================================================================
class TestGetHashed:
    def test_gmail_dots_removed(self):
        ud = UserData(email="j.o.h.n@gmail.com")
        expected = hashlib.sha256("john@gmail.com".encode()).hexdigest()
        assert ud.get_hashed("email") == expected

    def test_non_gmail_dots_kept(self):
        ud = UserData(email="j.o.h.n@example.com")
        expected = hashlib.sha256("j.o.h.n@example.com".encode()).hexdigest()
        assert ud.get_hashed("email") == expected

    def test_phone_country_code_added(self):
        ud = UserData(phone="(555) 123-4567")
        expected = hashlib.sha256("15551234567".encode()).hexdigest()
        assert ud.get_hashed("phone") == expected

    def test_missing_returns_none(self):
        assert UserData().get_hashed("email") is None


# =============================================================================
# ContentItem + ServerEvent
# =============================================================================
class TestContentAndEvent:
    def test_content_item_to_dict(self):
        item = ContentItem(
            id="SKU1", name="Sofa", brand="Acme", price=2500.0, quantity=2
        )
        d = item.to_dict()
        assert d["id"] == "SKU1"
        assert d["quantity"] == 2
        assert d["item_name"] == "Sofa"
        assert d["item_brand"] == "Acme"
        assert d["price"] == 2500.0

    def test_content_item_minimal(self):
        d = ContentItem(id="SKU2").to_dict()
        assert d == {"id": "SKU2", "quantity": 1}

    def test_event_content_helpers(self):
        event = ServerEvent(
            event_name=StandardEvent.PURCHASE,
            user_data=UserData(email="a@b.com"),
            contents=[
                ContentItem(id="A", quantity=2),
                ContentItem(id="B", quantity=3),
            ],
            value=100.0,
            currency="USD",
        )
        assert event.get_content_ids() == ["A", "B"]
        assert event.get_num_items() == 5
