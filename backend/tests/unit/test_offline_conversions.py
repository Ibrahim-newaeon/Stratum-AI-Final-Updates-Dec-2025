# =============================================================================
# Stratum AI - Offline Conversion Service unit tests
# =============================================================================
"""Unit tests for app.services.offline_conversion_service.

Covers the pure logic only — PII hashing, per-platform payload
formatting, CSV parsing, batch bookkeeping, the credential-guard
early-return paths of the uploaders (no HTTP is issued), and the P0
enhancements (match-rate predictor, data-quality scorer, platform
reconciler).
"""

import asyncio
import hashlib
from datetime import datetime, timedelta, timezone

import pytest

from app.services.offline_conversion_service import (
    DataQualityScorer,
    GoogleOfflineUploader,
    MatchRatePredictor,
    MetaOfflineUploader,
    OfflineConversion,
    OfflineConversionService,
    OfflineConversionSource,
    OfflineConversionStatus,
    PlatformReconciler,
    TikTokOfflineUploader,
)

pytestmark = pytest.mark.unit


def _now():
    return datetime.now(timezone.utc)


def _conversion(**overrides):
    defaults = dict(
        conversion_id="c1",
        platform="meta",
        email="user@example.com",
        phone="+1 555-123-4567",
        first_name="Ada",
        last_name="Lovelace",
        external_id="ext_1",
        click_id="click_1",
        event_time=datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc),
        conversion_value=99.5,
        currency="USD",
        order_id="order_1",
        item_count=2,
    )
    defaults.update(overrides)
    return OfflineConversion(**defaults)


# =============================================================================
# PII hashing
# =============================================================================
class TestHashing:
    def test_email_normalized_before_hash(self):
        uploader = MetaOfflineUploader()
        assert uploader._hash_email("  User@Example.COM ") == uploader._hash_email(
            "user@example.com"
        )
        assert (
            uploader._hash_email("user@example.com")
            == hashlib.sha256(b"user@example.com").hexdigest()
        )
        assert uploader._hash_email(None) is None

    def test_phone_normalized_before_hash(self):
        uploader = MetaOfflineUploader()
        assert uploader._hash_phone("+1 555-123-4567") == uploader._hash_phone(
            "15551234567"
        )
        assert uploader._hash_phone(None) is None


# =============================================================================
# Platform payload formatting
# =============================================================================
class TestMetaFormat:
    def test_full_event(self):
        event = MetaOfflineUploader()._format_conversion(_conversion())
        assert set(event["match_keys"]) == {"em", "ph", "fn", "ln", "external_id"}
        assert event["event_time"] == int(
            datetime(2026, 6, 1, 12, 0, tzinfo=timezone.utc).timestamp()
        )
        assert event["value"] == 99.5
        assert event["order_id"] == "order_1"
        assert event["contents"] == [{"quantity": 2}]

    def test_minimal_event(self):
        conv = OfflineConversion(conversion_id="c", platform="meta", email="a@b.com")
        event = MetaOfflineUploader()._format_conversion(conv)
        assert set(event["match_keys"]) == {"em"}
        assert "order_id" not in event
        assert "contents" not in event


class TestGoogleFormat:
    def test_uses_click_id_as_gclid(self):
        formatted = GoogleOfflineUploader()._format_conversion(
            _conversion(), "123", "456"
        )
        assert formatted["gclid"] == "click_1"
        assert formatted["conversionAction"] == "customers/123/conversionActions/456"
        assert formatted["conversionValue"] == 99.5
        assert formatted["currencyCode"] == "USD"
        assert formatted["orderId"] == "order_1"

    def test_gclid_extracted_from_external_id(self):
        conv = _conversion(click_id=None, external_id="gclid:abc123")
        formatted = GoogleOfflineUploader()._format_conversion(conv, "123", "456")
        assert formatted["gclid"] == "abc123"

    def test_no_gclid_returns_none(self):
        conv = _conversion(click_id=None, external_id=None)
        assert GoogleOfflineUploader()._format_conversion(conv, "123", "456") is None

    def test_zero_value_omits_value_fields(self):
        conv = _conversion(conversion_value=0.0)
        formatted = GoogleOfflineUploader()._format_conversion(conv, "123", "456")
        assert "conversionValue" not in formatted


class TestTikTokFormat:
    def test_structure(self):
        event = TikTokOfflineUploader()._format_conversion(_conversion())
        assert event["event"] == "Purchase"
        assert event["user"]["email"] is not None  # hashed
        assert event["user"]["email"] != "user@example.com"
        assert event["properties"]["value"] == 99.5
        assert event["properties"]["order_id"] == "order_1"


# =============================================================================
# Credential-guard upload paths (no HTTP issued)
# =============================================================================
class TestUploadGuards:
    @pytest.mark.parametrize(
        "uploader_cls,message_fragment",
        [
            (MetaOfflineUploader, "offline_event_set_id"),
            (GoogleOfflineUploader, "Missing required credentials"),
            (TikTokOfflineUploader, "pixel_code"),
        ],
    )
    def test_missing_credentials_fail_fast(self, uploader_cls, message_fragment):
        uploader = uploader_cls()
        result = asyncio.run(uploader.upload([_conversion()]))
        assert result.success is False
        assert result.failed_records == 1
        assert message_fragment in result.errors[0]["message"]

    def test_google_requires_gclid_conversions(self):
        uploader = GoogleOfflineUploader()
        uploader.set_credentials(
            {
                "customer_id": "123-456",
                "conversion_action_id": "789",
                "developer_token": "tok",
                "access_token": "at",
            }
        )
        conv = _conversion(click_id=None, external_id=None)
        result = asyncio.run(uploader.upload([conv]))
        assert result.success is False
        assert "GCLID required" in result.errors[0]["message"]


# =============================================================================
# CSV parsing
# =============================================================================
class TestParseCsv:
    def test_happy_path(self):
        svc = OfflineConversionService()
        csv_content = (
            "email,phone,value,currency,date,order_id,event\n"
            'a@b.com,555-1234,"$1,234.56",EUR,2026-01-15,ord_9,Lead\n'
        )
        conversions = svc.parse_csv(csv_content, "meta")
        assert len(conversions) == 1
        conv = conversions[0]
        assert conv.email == "a@b.com"
        assert conv.conversion_value == 1234.56
        assert conv.currency == "EUR"
        assert conv.event_time == datetime(2026, 1, 15, tzinfo=timezone.utc)
        assert conv.order_id == "ord_9"
        assert conv.event_name == "Lead"
        assert conv.source == OfflineConversionSource.CSV_UPLOAD

    def test_alternate_column_names(self):
        svc = OfflineConversionService()
        csv_content = "user_email,revenue,transaction_id\nx@y.com,50,t1\n"
        conv = svc.parse_csv(csv_content, "meta")[0]
        assert conv.email == "x@y.com"
        assert conv.conversion_value == 50.0
        assert conv.order_id == "t1"

    def test_row_without_identifiers_skipped(self):
        svc = OfflineConversionService()
        csv_content = "value,order_id\n100,ord_1\n"
        assert svc.parse_csv(csv_content, "meta") == []

    def test_click_id_only_accepted(self):
        svc = OfflineConversionService()
        csv_content = "gclid,value\nabc123,10\n"
        conv = svc.parse_csv(csv_content, "google")[0]
        assert conv.click_id == "abc123"
        assert conv.email is None

    def test_unparseable_value_and_date_defaults(self):
        svc = OfflineConversionService()
        csv_content = "email,value,date\na@b.com,not_a_number,not_a_date\n"
        conv = svc.parse_csv(csv_content, "meta")[0]
        assert conv.conversion_value == 0.0
        assert conv.event_time is None
        assert conv.event_name == "Purchase"  # default

    def test_us_date_format(self):
        svc = OfflineConversionService()
        csv_content = "email,date\na@b.com,06/15/2026\n"
        conv = svc.parse_csv(csv_content, "meta")[0]
        assert conv.event_time == datetime(2026, 6, 15, tzinfo=timezone.utc)


# =============================================================================
# Service batch bookkeeping
# =============================================================================
class TestServiceBatches:
    def test_unknown_platform_rejected(self):
        svc = OfflineConversionService()
        result = asyncio.run(svc.upload_conversions([_conversion()], "linkedin"))
        assert result.success is False
        assert "Unknown platform" in result.errors[0]["message"]

    def test_failed_upload_tracked_in_batch(self):
        svc = OfflineConversionService()
        result = asyncio.run(svc.upload_conversions([_conversion()], "meta"))
        assert result.success is False  # no credentials
        status = svc.get_batch_status(result.batch_id)
        assert status["status"] == OfflineConversionStatus.FAILED.value
        assert status["total_records"] == 1
        assert "offline_event_set_id" in status["error_summary"]

    def test_unknown_batch_status_none(self):
        assert OfflineConversionService().get_batch_status("ghost") is None

    def test_empty_csv_upload_short_circuits(self):
        svc = OfflineConversionService()
        result = asyncio.run(svc.upload_csv("value\n100\n", "meta", {}))
        assert result.success is False
        assert "No valid conversions" in result.errors[0]["message"]

    def test_history_and_listing_filters(self):
        svc = OfflineConversionService()
        asyncio.run(svc.upload_conversions([_conversion()], "meta"))
        asyncio.run(svc.upload_conversions([_conversion(platform="tiktok")], "tiktok"))
        assert len(svc.get_upload_history()) == 2
        assert len(svc.get_upload_history(platform="meta")) == 1
        failed = svc.list_batches("t1", status="failed")
        assert len(failed) == 2
        assert svc.list_batches("t1", platform="tiktok")[0]["platform"] == "tiktok"


# =============================================================================
# MatchRatePredictor
# =============================================================================
def _rich_conversion():
    return {
        "event_time": _now() - timedelta(days=1),
        "user_data": {
            "email": "a@b.com",
            "phone": "555",
            "first_name": "Ada",
            "last_name": "Lovelace",
            "postal_code": "12345",
            "country": "US",
        },
    }


class TestMatchRatePredictor:
    def test_empty_batch_high_risk(self):
        prediction = MatchRatePredictor().predict("meta", [])
        assert prediction.predicted_match_rate == 0.0
        assert prediction.risk_level == "high"
        assert prediction.recommendations == ["Provide conversion data"]

    def test_rich_data_capped_at_95(self):
        prediction = MatchRatePredictor().predict("meta", [_rich_conversion()] * 4)
        assert prediction.predicted_match_rate == 95.0
        assert prediction.risk_level == "low"
        assert prediction.recommendations == ["Data quality looks good for upload"]

    def test_poor_data_floors_at_5(self):
        poor = {"user_data": {}}  # no identifiers, no event_time -> stale
        prediction = MatchRatePredictor().predict("meta", [poor] * 4)
        assert prediction.predicted_match_rate == 5.0
        assert prediction.risk_level == "high"
        joined = " ".join(prediction.recommendations)
        assert "Include email" in joined
        assert "phone numbers" in joined
        assert ">7 days old" in joined

    def test_history_blends_and_boosts_confidence(self):
        predictor = MatchRatePredictor()
        for _ in range(10):
            predictor.record_match_rate("meta", 50.0, {})
        prediction = predictor.predict("meta", [_rich_conversion()])
        # (100 + 50) / 2 = 75
        assert prediction.predicted_match_rate == 75.0
        assert prediction.confidence == 0.8
        assert prediction.risk_level == "low"

    def test_staleness_helpers(self):
        predictor = MatchRatePredictor()
        assert predictor._is_stale({}) is True
        assert predictor._is_stale({"event_time": int(_now().timestamp())}) is False
        assert predictor._has_complete_address({"first_name": "A"}) is False


# =============================================================================
# DataQualityScorer
# =============================================================================
def _quality_conversion(**overrides):
    conv = {
        "event_name": "Purchase",
        "event_time": _now() - timedelta(days=1),
        "user_data": {"email": "a@b.com"},
    }
    conv.update(overrides)
    return conv


class TestDataQualityScorer:
    def test_empty_fails(self):
        score = DataQualityScorer().score([])
        assert score.overall_score == 0
        assert score.passed_validation is False
        assert score.issues[0]["severity"] == "critical"

    def test_perfect_batch(self):
        score = DataQualityScorer().score([_quality_conversion()] * 3)
        assert score.overall_score == 100.0
        assert score.passed_validation is True
        assert score.issues == []

    def test_missing_required_fields(self):
        score = DataQualityScorer().score([{"user_data": {"email": "a@b.com"}}])
        assert score.completeness_score == 0.0
        assert score.passed_validation is False
        assert any("missing required" in i["message"] for i in score.issues)

    def test_bad_email_format_flagged(self):
        bad = _quality_conversion(user_data={"email": "not-an-email"})
        score = DataQualityScorer().score([bad])
        assert score.format_score == 0.0
        assert any("format issues" in i["message"] for i in score.issues)

    def test_very_stale_double_penalty(self):
        old = _quality_conversion(event_time=_now() - timedelta(days=40))
        score = DataQualityScorer().score([old])
        assert score.freshness_score == 0.0  # max(0, (1 - 2) / 1 * 100)
        assert any(">30 days old" in i["message"] for i in score.issues)

    @pytest.mark.parametrize(
        "conversion,valid",
        [
            ({"event_time": 1700000000, "user_data": {}}, True),
            ({"event_time": 999, "user_data": {}}, False),  # implausible epoch
            ({"event_time": "2026-01-01", "user_data": {}}, False),  # wrong type
            ({"user_data": "not_a_dict"}, False),
            ({"user_data": {"email": "ok@x.com"}}, True),
        ],
    )
    def test_validate_format(self, conversion, valid):
        assert DataQualityScorer()._validate_format(conversion) is valid


# =============================================================================
# PlatformReconciler
# =============================================================================
class TestPlatformReconciler:
    def test_clean_reconciliation(self):
        result = PlatformReconciler().reconcile(
            "b1",
            "meta",
            our_conversions=[{}] * 100,
            platform_report={"total_conversions": 100, "matched_conversions": 80},
        )
        assert result.status == "matched"
        assert result.discrepancies == []
        assert result.discrepancy_rate == 0.0

    def test_count_mismatch_and_low_match(self):
        result = PlatformReconciler().reconcile(
            "b2",
            "meta",
            our_conversions=[{}] * 100,
            platform_report={"total_conversions": 90, "matched_conversions": 30},
        )
        assert result.status == "discrepancy"
        types = {d["type"] for d in result.discrepancies}
        assert types == {"count_mismatch", "low_match_rate"}

    def test_pending_when_platform_has_no_data(self):
        result = PlatformReconciler().reconcile(
            "b3",
            "meta",
            our_conversions=[],
            platform_report={"total_conversions": 0, "matched_conversions": 0},
        )
        assert result.status == "pending"

    def test_summary_aggregates(self):
        reconciler = PlatformReconciler()
        reconciler.reconcile(
            "b1",
            "meta",
            [{}] * 100,
            {"total_conversions": 100, "matched_conversions": 80},
        )
        reconciler.reconcile(
            "b2",
            "google",
            [{}] * 50,
            {"total_conversions": 40, "matched_conversions": 10},
        )
        summary = reconciler.get_reconciliation_summary()
        assert summary["total_batches"] == 2
        assert summary["matched_batches"] == 1
        assert summary["discrepancy_batches"] == 1
        assert summary["avg_match_rate"] == 60.0  # 90/150
        meta_only = reconciler.get_reconciliation_summary(platform="meta")
        assert meta_only["total_batches"] == 1

    def test_summary_empty(self):
        summary = PlatformReconciler().get_reconciliation_summary()
        assert summary["total_batches"] == 0
        assert summary["avg_match_rate"] == 0
