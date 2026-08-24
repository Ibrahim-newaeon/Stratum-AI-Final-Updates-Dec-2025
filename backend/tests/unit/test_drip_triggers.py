# =============================================================================
# Stratum AI - Drip Trigger Matching and Enrollment Construction
# =============================================================================
"""Which sequences an event fires, and what an enrollment looks like when it does.

The seven trigger types were declared as an enum from the first commit and
nothing ever subscribed to any of them, so every rule here is new behaviour
rather than a regression guard.

The recurring theme is refusing to guess. A ``custom_event`` with no configured
name matches nothing; a ``days_since_login`` with no day count is skipped; a
``campaign_roas_drop`` with no recipient is skipped. Each of those could be
given a plausible default, and each default would mail real people on the
strength of an assumption nobody wrote down.
"""

from types import SimpleNamespace

import pytest

from app.services.drip.triggers import (
    TRIGGER_CART_ABANDONED,
    TRIGGER_CUSTOM_EVENT,
    TRIGGER_DAYS_SINCE_LOGIN,
    TRIGGER_MANUAL,
    TRIGGER_POST_PURCHASE,
    TRIGGER_USER_SUBSCRIBED,
    configured_event_names,
    extract_email,
    inactivity_days,
    is_purchase_event,
    matches_event,
    notify_recipients,
    roas_drop_threshold,
    select_sequences,
)


def seq(sequence_id, trigger_type, **config):
    return SimpleNamespace(
        id=sequence_id, trigger_type=trigger_type, trigger_config=dict(config)
    )


# ---------------------------------------------------------------------------
# Event matching
# ---------------------------------------------------------------------------


class TestDefaultEventNames:
    @pytest.mark.parametrize(
        "trigger,event",
        [
            (TRIGGER_USER_SUBSCRIBED, "subscribed"),
            (TRIGGER_USER_SUBSCRIBED, "signup"),
            (TRIGGER_POST_PURCHASE, "purchase"),
            (TRIGGER_POST_PURCHASE, "order_completed"),
            (TRIGGER_CART_ABANDONED, "add_to_cart"),
        ],
    )
    def test_common_event_names_match_out_of_the_box(self, trigger, event):
        # The CDP has no fixed vocabulary, so the defaults cover the names
        # tenants actually send.
        assert matches_event(trigger, {}, event) is True

    def test_matching_is_case_and_whitespace_insensitive(self):
        assert matches_event(TRIGGER_POST_PURCHASE, {}, "  Purchase ") is True

    def test_custom_event_matches_nothing_by_default(self):
        # No default on purpose: an accidental match enrolls real people into
        # the wrong sequence.
        assert configured_event_names(TRIGGER_CUSTOM_EVENT, {}) == frozenset()
        assert matches_event(TRIGGER_CUSTOM_EVENT, {}, "anything") is False

    def test_non_event_triggers_never_match_an_event(self):
        for trigger in (TRIGGER_MANUAL, TRIGGER_DAYS_SINCE_LOGIN):
            assert matches_event(trigger, {}, "purchase") is False


class TestConfiguredEventNames:
    def test_explicit_name_replaces_the_defaults(self):
        """Naming an event means *that* one, not that one plus our guesses."""
        names = configured_event_names(
            TRIGGER_POST_PURCHASE, {"event_name": "checkout_v2"}
        )
        assert names == frozenset({"checkout_v2"})
        assert (
            matches_event(
                TRIGGER_POST_PURCHASE, {"event_name": "checkout_v2"}, "purchase"
            )
            is False
        )

    def test_accepts_a_list(self):
        config = {"event_names": ["a_event", "B_Event"]}
        assert configured_event_names(TRIGGER_CUSTOM_EVENT, config) == frozenset(
            {"a_event", "b_event"}
        )

    def test_ignores_blank_and_non_string_entries(self):
        config = {"event_names": ["  ", None, 5, "real"]}
        assert configured_event_names(TRIGGER_CUSTOM_EVENT, config) == frozenset(
            {"real"}
        )

    def test_blank_config_falls_back_to_defaults(self):
        assert matches_event(TRIGGER_POST_PURCHASE, {"event_name": "  "}, "purchase")


class TestSelectSequences:
    def test_returns_only_matching_sequences(self):
        sequences = [
            seq("s1", TRIGGER_POST_PURCHASE),
            seq("s2", TRIGGER_USER_SUBSCRIBED),
            seq("s3", TRIGGER_CUSTOM_EVENT, event_name="purchase"),
        ]
        picked = {s.id for s in select_sequences(sequences, "purchase")}
        assert picked == {"s1", "s3"}

    def test_no_match_returns_empty(self):
        assert select_sequences([seq("s1", TRIGGER_POST_PURCHASE)], "page_view") == []

    def test_handles_an_empty_sequence_list(self):
        assert select_sequences([], "purchase") == []


class TestPurchaseCancelsAbandonedCart:
    def test_purchase_events_are_recognised(self):
        assert is_purchase_event("order_completed") is True
        assert is_purchase_event("Purchase") is True

    def test_other_events_are_not(self):
        assert is_purchase_event("add_to_cart") is False
        assert is_purchase_event("") is False


# ---------------------------------------------------------------------------
# Identifier extraction
# ---------------------------------------------------------------------------


class TestExtractEmail:
    def test_reads_dict_identifiers(self):
        identifiers = [
            {"type": "device_id", "value": "d1"},
            {"type": "email", "value": " Person@Example.com "},
        ]
        assert extract_email(identifiers) == "Person@Example.com"

    def test_reads_object_identifiers(self):
        identifiers = [SimpleNamespace(type="email", value="a@b.io")]
        assert extract_email(identifiers) == "a@b.io"

    def test_returns_none_when_anonymous(self):
        # Plenty of CDP events have no email. Not an error — just nothing to mail.
        assert extract_email([{"type": "device_id", "value": "d1"}]) is None
        assert extract_email([]) is None
        assert extract_email(None) is None

    def test_ignores_blank_values(self):
        assert extract_email([{"type": "email", "value": "   "}]) is None


# ---------------------------------------------------------------------------
# Scan-driven trigger config
# ---------------------------------------------------------------------------


class TestScanTriggerConfig:
    def test_roas_threshold_is_read_from_several_key_names(self):
        assert roas_drop_threshold({"threshold": "1.5"}) == 1.5
        assert roas_drop_threshold({"roas_below": 2}) == 2.0
        assert roas_drop_threshold({"value": 0.5}) == 0.5

    def test_missing_roas_threshold_is_none_not_zero(self):
        # Zero would make every tenant look like they had crashed.
        assert roas_drop_threshold({}) is None
        assert roas_drop_threshold({"threshold": "not a number"}) is None

    def test_notify_recipients_accepts_string_or_list(self):
        assert notify_recipients({"notify_email": "a@b.io"}) == ["a@b.io"]
        assert notify_recipients({"notify_emails": ["a@b.io", " c@d.io "]}) == [
            "a@b.io",
            "c@d.io",
        ]

    def test_no_notify_recipient_is_empty(self):
        # A ROAS drop does not happen to a customer, so there is nobody to
        # derive. The caller skips the sequence rather than firing at no one.
        assert notify_recipients({}) == []
        assert notify_recipients({"notify_emails": []}) == []

    def test_inactivity_days_is_read_and_validated(self):
        assert inactivity_days({"days": 30}) == 30
        assert inactivity_days({"days_since_login": "14"}) == 14
        assert inactivity_days({}) is None
        assert inactivity_days({"days": 0}) is None
        assert inactivity_days({"days": -5}) is None


# ---------------------------------------------------------------------------
# Enrollment construction
# ---------------------------------------------------------------------------


class TestBuildEnrollment:
    """``_build_enrollment`` is pure, so the invariants are checkable directly."""

    def _build(self, email="Person@Example.com"):
        from datetime import datetime, timezone

        from app.services.drip.enrollment import EnrollmentRequest, _build_enrollment

        version = SimpleNamespace(id="dripv_1", entry_node_id="t1")
        request = EnrollmentRequest(
            tenant_id=9,
            sequence_id="drip_1",
            recipient_email=email,
            entry_trigger="manual",
            entry_context={"source": "test"},
        )
        now = datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc)
        return _build_enrollment(request, version, None, now), now

    def test_starts_on_the_trigger_node_and_is_due_immediately(self):
        enrollment, now = self._build()
        assert enrollment.current_node_id == "t1"
        assert enrollment.next_due_at == now
        assert enrollment.status == "pending"

    def test_pins_the_version_it_entered_on(self):
        # The whole reason versions exist: an edit must not move someone
        # mid-sequence onto a node that no longer exists.
        enrollment, _ = self._build()
        assert enrollment.version_id == "dripv_1"

    def test_address_is_encrypted_and_hashed(self):
        enrollment, _ = self._build()
        assert enrollment.recipient_email == "person@example.com"
        assert enrollment._recipient_email_encrypted != "person@example.com"
        assert len(enrollment.recipient_hash) == 64

    def test_hash_is_stable_across_formatting(self):
        # The partial unique index dedupes on this, so " A@B.io " and "a@b.io"
        # must not be two different people.
        a, _ = self._build(" Person@Example.COM ")
        b, _ = self._build("person@example.com")
        assert a.recipient_hash == b.recipient_hash

    def test_entry_provenance_is_recorded(self):
        enrollment, _ = self._build()
        assert enrollment.entry_trigger == "manual"
        assert enrollment.entry_context == {"source": "test"}
