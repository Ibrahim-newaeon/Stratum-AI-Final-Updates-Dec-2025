# =============================================================================
# Stratum AI - CAPI Event Mapper unit tests
# =============================================================================
"""Unit tests for app.services.capi.event_mapper.

Pure event-name → standard-event mapping + validation, no I/O. Covers standard
event matching + confidence, parameter normalization, platform event lookup,
event validation, and bulk mapping.
"""

import pytest

from app.services.capi.event_mapper import AIEventMapper, EventMapping, StandardEvent

pytestmark = pytest.mark.unit


@pytest.fixture
def mapper() -> AIEventMapper:
    return AIEventMapper()


# =============================================================================
# map_event
# =============================================================================
class TestMapEvent:
    def test_purchase_recognized(self, mapper):
        m = mapper.map_event("purchase", {"value": 100, "currency": "USD"})
        assert isinstance(m, EventMapping)
        assert m.standard_event == StandardEvent.PURCHASE
        assert m.confidence >= 0.8
        assert "meta" in m.platform_events

    def test_lead_recognized(self, mapper):
        m = mapper.map_event("lead", {})
        assert m.standard_event == StandardEvent.LEAD

    def test_unknown_is_custom_low_confidence(self, mapper):
        m = mapper.map_event("zzz_totally_unknown_event", {})
        assert m.standard_event == StandardEvent.CUSTOM
        assert m.confidence == 0.3

    def test_value_param_coerced_to_float(self, mapper):
        m = mapper.map_event("purchase", {"value": "100"})
        assert m.parameters["value"] == 100.0

    def test_content_ids_wrapped_in_list(self, mapper):
        m = mapper.map_event("view content", {"content_ids": "prod_1"})
        assert m.parameters["content_ids"] == ["prod_1"]


# =============================================================================
# Platform event lookup
# =============================================================================
class TestPlatformEvent:
    def test_known_platform(self, mapper):
        name = mapper.get_platform_event(StandardEvent.PURCHASE, "meta")
        assert isinstance(name, str) and name

    def test_unknown_platform_falls_back(self, mapper):
        # unknown platform falls back to meta's mapping
        name = mapper.get_platform_event(StandardEvent.PURCHASE, "does_not_exist")
        assert isinstance(name, str) and name


# =============================================================================
# Validation
# =============================================================================
class TestValidation:
    def test_purchase_missing_value_is_invalid(self, mapper):
        v = mapper.validate_event_data("purchase", {})
        assert v["valid"] is False
        assert any(i["type"] == "missing_value" for i in v["issues"])

    def test_purchase_zero_value_warns(self, mapper):
        v = mapper.validate_event_data("purchase", {"value": 0})
        assert any(w["type"] == "zero_value" for w in v["warnings"])

    def test_low_confidence_warns(self, mapper):
        v = mapper.validate_event_data("zzz_unknown_event", {})
        assert any(w["type"] == "low_confidence" for w in v["warnings"])

    def test_valid_purchase(self, mapper):
        v = mapper.validate_event_data(
            "purchase", {"value": 100, "currency": "USD", "content_ids": ["x"]}
        )
        assert v["event_mapping"]["standard"] == "Purchase"
        assert "meta" in v["platform_events"]


# =============================================================================
# Bulk mapping
# =============================================================================
class TestBulk:
    def test_bulk_maps_each_event(self, mapper):
        results = mapper.bulk_map_events(
            [
                {"name": "purchase", "parameters": {"value": 100}},
                {"name": "lead", "parameters": {}},
            ]
        )
        assert len(results) == 2

    def test_bulk_handles_alt_keys(self, mapper):
        # accepts 'event_name'/'data' as alternates for 'name'/'parameters'
        results = mapper.bulk_map_events(
            [{"event_name": "purchase", "data": {"value": 50}}]
        )
        assert len(results) == 1
