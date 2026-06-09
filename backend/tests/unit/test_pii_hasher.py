# =============================================================================
# Stratum AI - PII Hasher unit tests
# =============================================================================
"""Unit tests for app.services.capi.pii_hasher (pure logic, no I/O)."""

import hashlib

import pytest

from app.services.capi.pii_hasher import PIIField, PIIHasher

pytestmark = pytest.mark.unit


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@pytest.fixture
def hasher() -> PIIHasher:
    return PIIHasher()


class TestNormalizationAndHashing:
    def test_email_is_lowercased_and_trimmed(self, hasher: PIIHasher):
        assert hasher.hash_value("  Test@Example.COM ", PIIField.EMAIL) == _sha(
            "test@example.com"
        )

    def test_phone_strips_non_digits_and_leading_plus(self, hasher: PIIHasher):
        assert hasher.hash_value("+1 (202) 555-0143", PIIField.PHONE) == _sha(
            "12025550143"
        )

    def test_name_keeps_only_lowercase_letters(self, hasher: PIIHasher):
        assert hasher.hash_value("O'Brien-7", PIIField.LAST_NAME) == _sha("obrien")

    def test_zip_keeps_first_five_digits(self, hasher: PIIHasher):
        assert hasher.hash_value("94105-1234", PIIField.ZIP_CODE) == _sha("94105")

    def test_country_two_letter_lower(self, hasher: PIIHasher):
        assert hasher.hash_value("USA", PIIField.COUNTRY) == _sha("us")

    def test_gender_single_letter(self, hasher: PIIHasher):
        assert hasher.hash_value("Female", PIIField.GENDER) == _sha("f")

    def test_dob_digits_only_eight(self, hasher: PIIHasher):
        assert hasher.hash_value("1990-12-25", PIIField.DATE_OF_BIRTH) == _sha(
            "19901225"
        )

    def test_hash_is_deterministic(self, hasher: PIIHasher):
        a = hasher.hash_value("a@b.com", PIIField.EMAIL)
        b = hasher.hash_value("A@B.com", PIIField.EMAIL)
        assert a == b == _sha("a@b.com")


class TestDetection:
    def test_detects_email_and_phone_by_key(self, hasher: PIIHasher):
        results = hasher.detect_pii_fields(
            {"customer_email": "x@y.com", "mobile": "+12025550143"}
        )
        types = {r.detected_type for r in results}
        assert PIIField.EMAIL in types
        assert PIIField.PHONE in types

    def test_ignores_empty_values(self, hasher: PIIHasher):
        assert hasher.detect_pii_fields({"email": "", "phone": None}) == []

    def test_recognizes_already_hashed_value(self, hasher: PIIHasher):
        already = _sha("x@y.com")
        results = hasher.detect_pii_fields({"email": already})
        assert results[0].is_hashed is True
        assert results[0].needs_hashing is False


class TestHashData:
    def test_hash_data_replaces_with_platform_field_name(self, hasher: PIIHasher):
        out = hasher.hash_data({"user_email": "Person@Example.com"})
        # Original key removed, standardized "em" key added with the hash.
        assert "user_email" not in out
        assert out["em"] == _sha("person@example.com")

    def test_non_pii_fields_are_preserved(self, hasher: PIIHasher):
        out = hasher.hash_data({"order_total": 42, "email": "a@b.com"})
        assert out["order_total"] == 42


class TestCompleteness:
    def test_meta_completeness_scores_and_missing(self, hasher: PIIHasher):
        result = hasher.calculate_data_completeness(
            {"email": "a@b.com", "phone": "+12025550143"}, platform="meta"
        )
        assert result["platform"] == "meta"
        assert 0 < result["score"] <= 100
        assert result["total_fields_detected"] == 2
        assert isinstance(result["missing_fields"], list)

    def test_unknown_platform_falls_back_to_meta(self, hasher: PIIHasher):
        result = hasher.calculate_data_completeness(
            {"email": "a@b.com"}, platform="xyz"
        )
        assert result["platform"] == "xyz"
        assert result["score"] > 0

    def test_get_missing_fields(self, hasher: PIIHasher):
        missing = hasher.get_missing_fields(
            {"email": "a@b.com"}, {PIIField.EMAIL, PIIField.PHONE}
        )
        assert PIIField.PHONE in missing
        assert PIIField.EMAIL not in missing
