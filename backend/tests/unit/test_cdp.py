# =============================================================================
# Stratum AI - CDP Unit Tests
# =============================================================================
"""
Unit tests for CDP (Customer Data Platform) module.

Tests:
- Event schema validation
- Identifier normalization
- Identifier hashing (SHA256)
- EMQ score calculation
- Profile resolution logic
- Consent handling
"""

import pytest
import hashlib
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, Any, List
from unittest.mock import MagicMock, patch, AsyncMock
from pydantic import ValidationError


# =============================================================================
# Import CDP Schemas (Pydantic models don't require DB)
# =============================================================================

from app.schemas.cdp import (
    IdentifierInput,
    EventInput,
    EventBatchInput,
    EventContext,
    EventConsent,
    SourceCreate,
    ConsentUpdate,
)


# =============================================================================
# Helper Functions (Extracted from cdp.py for unit testing)
# =============================================================================

def normalize_identifier(identifier_type: str, value: str) -> str:
    """Normalize identifier value before hashing."""
    import re
    if identifier_type == "email":
        # Lowercase, strip whitespace
        return value.lower().strip()
    elif identifier_type == "phone":
        # Remove non-digit characters, keep + prefix if present
        cleaned = re.sub(r"[^\d+]", "", value)
        # Ensure E.164 format (starts with +)
        if not cleaned.startswith("+"):
            cleaned = "+" + cleaned
        return cleaned
    else:
        # Other identifiers: strip whitespace only
        return value.strip()


def hash_identifier(value: str) -> str:
    """Hash identifier value using SHA256."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def calculate_emq_score(
    identifiers: List[Dict[str, str]],
    properties: Dict[str, Any],
    context: Dict[str, Any],
    latency_seconds: float
) -> float:
    """Calculate Event Match Quality score (0-100)."""
    score = 0.0

    # Identifier quality (40%)
    has_email = any(i.get("type") == "email" for i in identifiers)
    has_phone = any(i.get("type") == "phone" for i in identifiers)
    if has_email or has_phone:
        score += 40
    elif identifiers:
        score += 20

    # Data completeness (25%)
    if properties:
        score += 25

    # Timeliness (20%)
    if latency_seconds < 300:  # Within 5 minutes
        score += 20
    elif latency_seconds < 3600:  # Within 1 hour
        score += 10

    # Context richness (15%)
    if context:
        if context.get("campaign"):
            score += 5
        if context.get("user_agent"):
            score += 5
        if context.get("ip"):
            score += 5

    return min(score, 100.0)


# =============================================================================
# Event Schema Validation Tests
# =============================================================================

class TestEventSchemaValidation:
    """Tests for event schema validation (Pydantic models)."""

    def test_valid_event_minimal(self):
        """Valid event with only required fields."""
        event = EventInput(
            event_name="PageView",
            event_time=datetime.now(timezone.utc),
            identifiers=[IdentifierInput(type="anonymous_id", value="anon_123")]
        )
        assert event.event_name == "PageView"
        assert len(event.identifiers) == 1

    def test_valid_event_full(self):
        """Valid event with all fields."""
        event = EventInput(
            event_name="Purchase",
            event_time=datetime.now(timezone.utc),
            idempotency_key="order_12345_1705159800",
            identifiers=[
                IdentifierInput(type="email", value="user@example.com"),
                IdentifierInput(type="anonymous_id", value="anon_xyz789"),
            ],
            properties={"order_id": "ORD-12345", "total": 2499.00},
            context=EventContext(
                user_agent="Mozilla/5.0",
                ip="185.23.45.67",
                campaign={"source": "google", "medium": "cpc"}
            ),
            consent=EventConsent(analytics=True, ads=True)
        )
        assert event.event_name == "Purchase"
        assert len(event.identifiers) == 2
        assert event.properties["total"] == 2499.00

    def test_invalid_event_no_identifiers(self):
        """Event must have at least one identifier."""
        with pytest.raises(ValidationError) as exc_info:
            EventInput(
                event_name="PageView",
                event_time=datetime.now(timezone.utc),
                identifiers=[]  # Empty list
            )
        assert "identifiers" in str(exc_info.value)

    def test_invalid_event_no_event_name(self):
        """Event must have event_name."""
        with pytest.raises(ValidationError):
            EventInput(
                event_time=datetime.now(timezone.utc),
                identifiers=[IdentifierInput(type="anonymous_id", value="anon_123")]
            )

    def test_invalid_event_name_special_chars(self):
        """Event name can only contain alphanumeric, spaces, underscores, dashes."""
        with pytest.raises(ValidationError) as exc_info:
            EventInput(
                event_name="Page<script>View",  # Contains <>
                event_time=datetime.now(timezone.utc),
                identifiers=[IdentifierInput(type="anonymous_id", value="anon_123")]
            )
        assert "event_name" in str(exc_info.value).lower()

    def test_invalid_identifier_type(self):
        """Identifier type must be one of allowed values."""
        with pytest.raises(ValidationError) as exc_info:
            IdentifierInput(type="invalid_type", value="test123")
        assert "Invalid identifier type" in str(exc_info.value)

    def test_valid_identifier_types(self):
        """All valid identifier types should be accepted."""
        valid_types = ["email", "phone", "device_id", "anonymous_id", "external_id"]
        for ident_type in valid_types:
            ident = IdentifierInput(type=ident_type, value="test_value")
            assert ident.type == ident_type

    def test_identifier_type_case_insensitive(self):
        """Identifier type should be normalized to lowercase."""
        ident = IdentifierInput(type="EMAIL", value="user@example.com")
        assert ident.type == "email"

        ident2 = IdentifierInput(type="Phone", value="+971501234567")
        assert ident2.type == "phone"

    def test_batch_max_events(self):
        """Batch should accept up to 1000 events."""
        # Create 1000 valid events
        events = [
            EventInput(
                event_name="PageView",
                event_time=datetime.now(timezone.utc),
                identifiers=[IdentifierInput(type="anonymous_id", value=f"anon_{i}")]
            )
            for i in range(1000)
        ]
        batch = EventBatchInput(events=events)
        assert len(batch.events) == 1000

    def test_batch_exceeds_max_events(self):
        """Batch should reject more than 1000 events."""
        events = [
            EventInput(
                event_name="PageView",
                event_time=datetime.now(timezone.utc),
                identifiers=[IdentifierInput(type="anonymous_id", value=f"anon_{i}")]
            )
            for i in range(1001)
        ]
        with pytest.raises(ValidationError) as exc_info:
            EventBatchInput(events=events)
        assert "events" in str(exc_info.value).lower()

    def test_idempotency_key_max_length(self):
        """Idempotency key should be max 128 characters."""
        # Valid 128 char key
        event = EventInput(
            event_name="PageView",
            event_time=datetime.now(timezone.utc),
            identifiers=[IdentifierInput(type="anonymous_id", value="anon_123")],
            idempotency_key="a" * 128
        )
        assert len(event.idempotency_key) == 128

        # Invalid 129 char key
        with pytest.raises(ValidationError):
            EventInput(
                event_name="PageView",
                event_time=datetime.now(timezone.utc),
                identifiers=[IdentifierInput(type="anonymous_id", value="anon_123")],
                idempotency_key="a" * 129
            )


# =============================================================================
# Identifier Normalization Tests
# =============================================================================

class TestIdentifierNormalization:
    """Tests for identifier normalization."""

    def test_email_lowercase(self):
        """Email should be lowercased."""
        normalized = normalize_identifier("email", "USER@EXAMPLE.COM")
        assert normalized == "user@example.com"

    def test_email_strip_whitespace(self):
        """Email should have whitespace stripped."""
        normalized = normalize_identifier("email", "  user@example.com  ")
        assert normalized == "user@example.com"

    def test_email_mixed_case(self):
        """Email with mixed case should be lowercased."""
        normalized = normalize_identifier("email", "User.Name@Example.COM")
        assert normalized == "user.name@example.com"

    def test_phone_e164_already_valid(self):
        """Phone already in E.164 format."""
        normalized = normalize_identifier("phone", "+971501234567")
        assert normalized == "+971501234567"

    def test_phone_adds_plus_prefix(self):
        """Phone without + prefix gets it added."""
        normalized = normalize_identifier("phone", "971501234567")
        assert normalized == "+971501234567"

    def test_phone_removes_non_digits(self):
        """Phone non-digit characters are removed."""
        normalized = normalize_identifier("phone", "+1 (555) 123-4567")
        assert normalized == "+15551234567"

    def test_phone_with_spaces_and_dashes(self):
        """Phone with various formatting is cleaned."""
        normalized = normalize_identifier("phone", "  +971 50 123 4567  ")
        assert normalized == "+971501234567"

    def test_device_id_strip_only(self):
        """Device ID only gets whitespace stripped."""
        normalized = normalize_identifier("device_id", "  ABC123-DEF456  ")
        assert normalized == "ABC123-DEF456"

    def test_anonymous_id_strip_only(self):
        """Anonymous ID only gets whitespace stripped."""
        normalized = normalize_identifier("anonymous_id", "  anon_abc123  ")
        assert normalized == "anon_abc123"

    def test_external_id_strip_only(self):
        """External ID only gets whitespace stripped."""
        normalized = normalize_identifier("external_id", "  CRM-12345  ")
        assert normalized == "CRM-12345"


# =============================================================================
# Identifier Hashing Tests
# =============================================================================

class TestIdentifierHashing:
    """Tests for SHA256 identifier hashing."""

    def test_hash_email(self):
        """Email is hashed correctly."""
        value = "user@example.com"
        expected = hashlib.sha256(value.encode("utf-8")).hexdigest()
        assert hash_identifier(value) == expected
        # SHA256 produces 64 character hex string
        assert len(hash_identifier(value)) == 64

    def test_hash_phone(self):
        """Phone is hashed correctly."""
        value = "+971501234567"
        expected = hashlib.sha256(value.encode("utf-8")).hexdigest()
        assert hash_identifier(value) == expected

    def test_hash_deterministic(self):
        """Same input always produces same hash."""
        value = "test_value"
        hash1 = hash_identifier(value)
        hash2 = hash_identifier(value)
        assert hash1 == hash2

    def test_hash_different_values(self):
        """Different inputs produce different hashes."""
        hash1 = hash_identifier("value1")
        hash2 = hash_identifier("value2")
        assert hash1 != hash2

    def test_hash_case_sensitive(self):
        """Hashing is case-sensitive (normalize first!)."""
        hash1 = hash_identifier("User@Example.com")
        hash2 = hash_identifier("user@example.com")
        # These are different because hashing doesn't normalize
        assert hash1 != hash2

    def test_normalized_then_hashed_same(self):
        """Normalized emails produce same hash."""
        email1 = normalize_identifier("email", "USER@EXAMPLE.COM")
        email2 = normalize_identifier("email", "user@example.com")
        assert hash_identifier(email1) == hash_identifier(email2)


# =============================================================================
# EMQ Score Calculation Tests
# =============================================================================

class TestEMQScoreCalculation:
    """Tests for Event Match Quality score calculation."""

    def test_max_score_with_email_and_all_context(self):
        """Maximum EMQ score with email identifier and full context."""
        identifiers = [{"type": "email", "value": "user@example.com"}]
        properties = {"page_url": "/products"}
        context = {
            "campaign": {"source": "google"},
            "user_agent": "Mozilla/5.0",
            "ip": "185.23.45.67"
        }
        score = calculate_emq_score(identifiers, properties, context, latency_seconds=60)
        assert score == 100.0

    def test_max_score_with_phone_and_all_context(self):
        """Maximum EMQ score with phone identifier and full context."""
        identifiers = [{"type": "phone", "value": "+971501234567"}]
        properties = {"order_id": "ORD-123"}
        context = {
            "campaign": {"source": "google"},
            "user_agent": "Mozilla/5.0",
            "ip": "185.23.45.67"
        }
        score = calculate_emq_score(identifiers, properties, context, latency_seconds=60)
        assert score == 100.0

    def test_identifier_quality_email_or_phone(self):
        """Email or phone gives 40 points."""
        # Email only
        score1 = calculate_emq_score(
            [{"type": "email", "value": "user@example.com"}],
            {}, {}, latency_seconds=0
        )
        assert score1 >= 40

        # Phone only
        score2 = calculate_emq_score(
            [{"type": "phone", "value": "+971501234567"}],
            {}, {}, latency_seconds=0
        )
        assert score2 >= 40

    def test_identifier_quality_anonymous_only(self):
        """Anonymous ID only gives 20 points for identifier quality."""
        score = calculate_emq_score(
            [{"type": "anonymous_id", "value": "anon_123"}],
            {}, {}, latency_seconds=3700  # Over 1 hour, no timeliness points
        )
        assert score == 20  # Only identifier quality score

    def test_data_completeness_25_points(self):
        """Properties present gives 25 points."""
        score_with = calculate_emq_score(
            [{"type": "anonymous_id", "value": "anon_123"}],
            {"page_url": "/test"},
            {},
            latency_seconds=400
        )
        score_without = calculate_emq_score(
            [{"type": "anonymous_id", "value": "anon_123"}],
            {},
            {},
            latency_seconds=400
        )
        assert score_with - score_without == 25

    def test_timeliness_full_points(self):
        """Event within 5 minutes gets full 20 points."""
        score_fast = calculate_emq_score(
            [{"type": "anonymous_id", "value": "anon_123"}],
            {}, {},
            latency_seconds=60  # 1 minute
        )
        score_slow = calculate_emq_score(
            [{"type": "anonymous_id", "value": "anon_123"}],
            {}, {},
            latency_seconds=3700  # Over 1 hour
        )
        # Fast should be 20 + base (20), slow should be 0 + base (20)
        assert score_fast == 40  # 20 (ident) + 20 (timeliness)
        assert score_slow == 20  # 20 (ident) only

    def test_timeliness_partial_points(self):
        """Event within 1 hour gets partial 10 points."""
        score = calculate_emq_score(
            [{"type": "anonymous_id", "value": "anon_123"}],
            {}, {},
            latency_seconds=600  # 10 minutes
        )
        assert score == 30  # 20 (ident) + 10 (partial timeliness)

    def test_context_richness_individual_components(self):
        """Each context component gives 5 points (max 15)."""
        # Campaign only
        score_campaign = calculate_emq_score(
            [], {}, {"campaign": {"source": "google"}}, latency_seconds=3700
        )
        assert score_campaign == 5

        # User agent only
        score_ua = calculate_emq_score(
            [], {}, {"user_agent": "Mozilla/5.0"}, latency_seconds=3700
        )
        assert score_ua == 5

        # IP only
        score_ip = calculate_emq_score(
            [], {}, {"ip": "1.2.3.4"}, latency_seconds=3700
        )
        assert score_ip == 5

        # All three
        score_all = calculate_emq_score(
            [], {},
            {"campaign": {"source": "google"}, "user_agent": "Mozilla", "ip": "1.2.3.4"},
            latency_seconds=3700
        )
        assert score_all == 15

    def test_emq_score_capped_at_100(self):
        """EMQ score should never exceed 100."""
        # Even with maximum everything
        score = calculate_emq_score(
            [{"type": "email", "value": "test@test.com"}, {"type": "phone", "value": "+1234"}],
            {"lots": "of", "properties": "here", "extra": "data"},
            {"campaign": {}, "user_agent": "test", "ip": "1.2.3.4", "extra": "field"},
            latency_seconds=0
        )
        assert score <= 100


# =============================================================================
# Source Schema Validation Tests
# =============================================================================

class TestSourceSchemaValidation:
    """Tests for source schema validation."""

    def test_valid_source_types(self):
        """All valid source types should be accepted."""
        valid_types = ["website", "server", "sgtm", "import", "crm"]
        for source_type in valid_types:
            source = SourceCreate(name="Test Source", source_type=source_type)
            assert source.source_type == source_type

    def test_invalid_source_type(self):
        """Invalid source type should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            SourceCreate(name="Test Source", source_type="invalid")
        assert "Invalid source type" in str(exc_info.value)

    def test_source_type_case_insensitive(self):
        """Source type should be normalized to lowercase."""
        source = SourceCreate(name="Test Source", source_type="WEBSITE")
        assert source.source_type == "website"

    def test_source_name_required(self):
        """Source name is required."""
        with pytest.raises(ValidationError):
            SourceCreate(source_type="website")

    def test_source_config_optional(self):
        """Source config is optional and defaults to empty dict."""
        source = SourceCreate(name="Test", source_type="website")
        assert source.config == {}


# =============================================================================
# Consent Schema Validation Tests
# =============================================================================

class TestConsentSchemaValidation:
    """Tests for consent schema validation."""

    def test_valid_consent_types(self):
        """All valid consent types should be accepted."""
        valid_types = ["analytics", "ads", "email", "sms", "all"]
        for consent_type in valid_types:
            consent = ConsentUpdate(consent_type=consent_type, granted=True)
            assert consent.consent_type == consent_type

    def test_invalid_consent_type(self):
        """Invalid consent type should be rejected."""
        with pytest.raises(ValidationError) as exc_info:
            ConsentUpdate(consent_type="invalid", granted=True)
        assert "Invalid consent type" in str(exc_info.value)

    def test_consent_type_case_insensitive(self):
        """Consent type should be normalized to lowercase."""
        consent = ConsentUpdate(consent_type="ANALYTICS", granted=True)
        assert consent.consent_type == "analytics"

    def test_consent_granted_required(self):
        """Granted field is required."""
        with pytest.raises(ValidationError):
            ConsentUpdate(consent_type="analytics")


# =============================================================================
# Event Context Validation Tests
# =============================================================================

class TestEventContextValidation:
    """Tests for event context validation."""

    def test_valid_context(self):
        """Valid context with all fields."""
        context = EventContext(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X)",
            ip="185.23.45.67",
            locale="ar-AE",
            timezone="Asia/Dubai",
            screen={"width": 390, "height": 844},
            campaign={"source": "google", "medium": "cpc"}
        )
        assert context.locale == "ar-AE"
        assert context.screen["width"] == 390

    def test_context_all_optional(self):
        """All context fields are optional."""
        context = EventContext()
        assert context.user_agent is None
        assert context.ip is None

    def test_user_agent_max_length(self):
        """User agent should be max 1024 characters."""
        # Valid
        context = EventContext(user_agent="a" * 1024)
        assert len(context.user_agent) == 1024

        # Invalid
        with pytest.raises(ValidationError):
            EventContext(user_agent="a" * 1025)


# =============================================================================
# Event Consent Validation Tests
# =============================================================================

class TestEventConsentValidation:
    """Tests for event consent flags validation."""

    def test_valid_consent_flags(self):
        """Valid consent with all flags."""
        consent = EventConsent(analytics=True, ads=False, email=True, sms=False)
        assert consent.analytics is True
        assert consent.ads is False

    def test_consent_flags_optional(self):
        """All consent flags are optional."""
        consent = EventConsent()
        assert consent.analytics is None

    def test_partial_consent_flags(self):
        """Some consent flags can be set while others are None."""
        consent = EventConsent(analytics=True)
        assert consent.analytics is True
        assert consent.ads is None


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
