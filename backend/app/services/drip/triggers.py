# =============================================================================
# Stratum AI - Drip Trigger Matching
# =============================================================================
"""Decides which sequences a CDP event should enroll someone into.

The seven trigger types were declared as an enum from the start and nothing
ever subscribed to any of them. This module is the missing half: given an event
name, which active sequences want it.

Kept pure — dicts in, decisions out — so the matching rules are testable
without a database, a broker or a CDP.
"""

from typing import Any, Iterable, Optional

TRIGGER_USER_SUBSCRIBED = "user_subscribed"
TRIGGER_CART_ABANDONED = "cart_abandoned"
TRIGGER_CAMPAIGN_ROAS_DROP = "campaign_roas_drop"
TRIGGER_DAYS_SINCE_LOGIN = "days_since_login"
TRIGGER_POST_PURCHASE = "post_purchase"
TRIGGER_CUSTOM_EVENT = "custom_event"
TRIGGER_MANUAL = "manual"

#: Event names each trigger listens for when the sequence does not say.
#:
#: Defaults exist because the CDP has no fixed vocabulary — one tenant sends
#: ``purchase``, another ``order_completed``. A sequence can always override
#: with ``trigger_config["event_name"]`` or ``["event_names"]``.
DEFAULT_TRIGGER_EVENTS: dict[str, frozenset[str]] = {
    TRIGGER_USER_SUBSCRIBED: frozenset(
        {"subscribed", "newsletter_subscribed", "signup", "sign_up", "registered"}
    ),
    TRIGGER_POST_PURCHASE: frozenset(
        {"purchase", "order_completed", "checkout_completed", "order_placed"}
    ),
    TRIGGER_CART_ABANDONED: frozenset({"add_to_cart", "cart_updated"}),
    # No default: a custom event that matched something by accident would
    # enroll real people into the wrong sequence.
    TRIGGER_CUSTOM_EVENT: frozenset(),
}

#: Events that mean a cart was not abandoned after all, so any
#: ``cart_abandoned`` enrollment for that recipient should stop.
PURCHASE_EVENTS = DEFAULT_TRIGGER_EVENTS[TRIGGER_POST_PURCHASE]

#: Triggers fired by a CDP event rather than by a scan or a person.
EVENT_DRIVEN_TRIGGERS = frozenset(
    {
        TRIGGER_USER_SUBSCRIBED,
        TRIGGER_POST_PURCHASE,
        TRIGGER_CART_ABANDONED,
        TRIGGER_CUSTOM_EVENT,
    }
)


def _normalise(name: Optional[str]) -> str:
    return (name or "").strip().lower()


def configured_event_names(
    trigger_type: str, trigger_config: Optional[dict[str, Any]]
) -> frozenset[str]:
    """Event names a sequence listens for.

    An explicit configuration replaces the defaults rather than adding to them:
    a marketer who names their event is saying *that* one, not that one plus
    whatever we guessed.
    """
    config = trigger_config or {}

    names: set[str] = set()
    single = config.get("event_name")
    if isinstance(single, str) and single.strip():
        names.add(_normalise(single))

    multiple = config.get("event_names")
    if isinstance(multiple, (list, tuple, set, frozenset)):
        names.update(
            _normalise(n) for n in multiple if isinstance(n, str) and n.strip()
        )

    if names:
        return frozenset(names)
    return DEFAULT_TRIGGER_EVENTS.get(trigger_type, frozenset())


def matches_event(
    trigger_type: str, trigger_config: Optional[dict[str, Any]], event_name: str
) -> bool:
    """Whether a sequence with this trigger should fire for this event."""
    if trigger_type not in EVENT_DRIVEN_TRIGGERS:
        return False
    return _normalise(event_name) in configured_event_names(
        trigger_type, trigger_config
    )


def is_purchase_event(event_name: str) -> bool:
    """Whether this event cancels an in-flight abandoned-cart sequence."""
    return _normalise(event_name) in PURCHASE_EVENTS


def select_sequences(sequences: Iterable[Any], event_name: str) -> list[Any]:
    """Every sequence whose trigger matches ``event_name``.

    Takes anything with ``trigger_type`` and ``trigger_config`` attributes, so
    the caller can pass ORM rows and the tests can pass simple stand-ins.
    """
    return [
        sequence
        for sequence in sequences
        if matches_event(
            getattr(sequence, "trigger_type", ""),
            getattr(sequence, "trigger_config", None),
            event_name,
        )
    ]


def extract_email(identifiers: Optional[Iterable[Any]]) -> Optional[str]:
    """Pull the email address out of a CDP event's identifier list.

    Accepts the dict form the ingestion endpoint stores and the pydantic form
    it receives, since the hook runs on whichever the caller has to hand.
    """
    for identifier in identifiers or []:
        if isinstance(identifier, dict):
            id_type, value = identifier.get("type"), identifier.get("value")
        else:
            id_type, value = (
                getattr(identifier, "type", None),
                getattr(identifier, "value", None),
            )
        if _normalise(id_type) == "email" and isinstance(value, str) and value.strip():
            return value.strip()
    return None


def roas_drop_threshold(trigger_config: Optional[dict[str, Any]]) -> Optional[float]:
    """The ROAS a ``campaign_roas_drop`` sequence fires below."""
    for key in ("threshold", "roas_below", "value"):
        raw = (trigger_config or {}).get(key)
        if raw is None:
            continue
        try:
            return float(raw)
        except (TypeError, ValueError):
            continue
    return None


def notify_recipients(trigger_config: Optional[dict[str, Any]]) -> list[str]:
    """Who a non-customer trigger emails.

    A ROAS drop is not something that happens to a customer, so there is no
    recipient to derive — the sequence has to name one. Without this, such a
    sequence would activate and then fire at nobody.
    """
    config = trigger_config or {}
    raw = config.get("notify_emails") or config.get("notify_email")
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, (list, tuple)):
        return []
    return [r.strip() for r in raw if isinstance(r, str) and r.strip()]


def inactivity_days(trigger_config: Optional[dict[str, Any]]) -> Optional[int]:
    """Days of silence a ``days_since_login`` sequence waits for."""
    for key in ("days", "days_since_login", "threshold"):
        raw = (trigger_config or {}).get(key)
        if raw is None:
            continue
        try:
            value = int(float(raw))
        except (TypeError, ValueError):
            continue
        if value > 0:
            return value
    return None
