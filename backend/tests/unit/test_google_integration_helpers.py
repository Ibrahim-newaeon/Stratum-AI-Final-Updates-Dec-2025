# =============================================================================
# Stratum AI - Google Ads Integration Pure-Helper Unit Tests
# =============================================================================
"""Unit tests for the pure helpers in
``app.stratum.integrations.google_complete``:

- ``GoogleAdsChangeHistory._map_change_type`` resource/operation -> enum
- ``GoogleAdsChangeHistory._extract_id`` resource-name tail extraction
- ``GoogleOfflineConversions._hash_value`` SHA-256
- ``GoogleOfflineConversions._normalize_phone`` E.164 normalization

The Google-Ads-client-backed API methods are out of scope; these helpers
ignore the client, so it's passed as ``None``.
"""

import hashlib

import pytest

from app.stratum.integrations.google_complete import (
    ChangeEventType,
    GoogleAdsChangeHistory,
    GoogleOfflineConversions,
)

pytestmark = pytest.mark.unit


@pytest.fixture
def history() -> GoogleAdsChangeHistory:
    return GoogleAdsChangeHistory(client=None, customer_id="123")


@pytest.fixture
def conversions() -> GoogleOfflineConversions:
    return GoogleOfflineConversions(client=None, customer_id="123")


# =============================================================================
# _map_change_type
# =============================================================================
class TestMapChangeType:
    @pytest.mark.parametrize(
        "resource,op,event",
        [
            ("campaign", "CREATE", ChangeEventType.CAMPAIGN_CREATED),
            ("campaign", "REMOVE", ChangeEventType.CAMPAIGN_REMOVED),
            ("ad_group", "UPDATE", ChangeEventType.AD_GROUP_UPDATED),
            ("ad", "CREATE", ChangeEventType.AD_CREATED),
        ],
    )
    def test_known_mappings(self, history, resource, op, event):
        assert history._map_change_type(resource, op) == event

    def test_unknown_defaults_to_campaign_updated(self, history):
        assert history._map_change_type("widget", "FROB") == (
            ChangeEventType.CAMPAIGN_UPDATED
        )


# =============================================================================
# _extract_id
# =============================================================================
class TestExtractId:
    def test_extracts_tail_segment(self, history):
        assert history._extract_id("customers/123/campaigns/456") == "456"

    def test_bare_id(self, history):
        assert history._extract_id("789") == "789"


# =============================================================================
# _hash_value / _normalize_phone
# =============================================================================
class TestConversionHelpers:
    def test_hash_value_is_sha256(self, conversions):
        assert conversions._hash_value("test@example.com") == (
            hashlib.sha256(b"test@example.com").hexdigest()
        )

    def test_normalize_us_phone_adds_country_code(self, conversions):
        assert conversions._normalize_phone("(555) 123-4567") == "+15551234567"

    def test_normalize_keeps_existing_country_code(self, conversions):
        assert conversions._normalize_phone("+44 20 7946 0958") == "+442079460958"

    def test_normalize_strips_formatting(self, conversions):
        assert conversions._normalize_phone("555.123.4567") == "+15551234567"
