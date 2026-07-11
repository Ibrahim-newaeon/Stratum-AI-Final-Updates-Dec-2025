# =============================================================================
# Stratum AI - WhatsApp Send/Broadcast Contract Tests
# =============================================================================
"""
Tests for aligning the WhatsApp async pipeline (Tier 3).

The send endpoint dispatched ``send_whatsapp_message`` with kwargs the task
never declared (message_id/contact_phone/... vs template_name/to_number) → a
runtime TypeError, and imported ``send_whatsapp_broadcast`` which did not exist
→ ImportError/500. The task also wrote ``variables`` / ``external_id`` — not
columns (real: ``template_variables`` / ``wamid``). These tests pin the
endpoint↔task contract and the columns without needing a DB or the Graph API.
"""

import inspect

from app.models import WhatsAppMessage
from app.workers.tasks import send_whatsapp_broadcast, send_whatsapp_message
from app.workers.tasks.whatsapp import _extract_wamid

# The exact kwargs the endpoints dispatch with (endpoints/whatsapp.py).
ENDPOINT_SEND_KWARGS = {
    "tenant_id",
    "message_id",
    "contact_phone",
    "message_type",
    "template_name",
    "template_variables",
    "content",
    "media_url",
}
ENDPOINT_BROADCAST_KWARGS = {
    "tenant_id",
    "template_name",
    "template_variables",
    "contact_ids",
}


def _param_names(task) -> set:
    fn = getattr(task, "run", task)
    return set(inspect.signature(fn).parameters) - {"self"}


def test_send_signature_accepts_endpoint_kwargs():
    # Every kwarg the send endpoint passes must be a declared task param,
    # otherwise .delay(...) raises TypeError at call time.
    assert ENDPOINT_SEND_KWARGS <= _param_names(send_whatsapp_message)


def test_broadcast_exists_and_accepts_endpoint_kwargs():
    # send_whatsapp_broadcast used to not exist (ImportError). It must now be
    # importable from the aggregator and accept the broadcast endpoint's kwargs.
    assert ENDPOINT_BROADCAST_KWARGS <= _param_names(send_whatsapp_broadcast)


def test_message_writes_real_columns():
    cols = set(WhatsAppMessage.__table__.columns.keys())
    assert "template_variables" in cols  # not "variables"
    assert "wamid" in cols  # not "external_id"
    assert "variables" not in cols
    assert "external_id" not in cols


def test_extract_wamid_from_graph_response():
    assert _extract_wamid({"messages": [{"id": "wamid.ABC"}]}) == "wamid.ABC"


def test_extract_wamid_fallback_and_empty():
    assert _extract_wamid({"message_id": "wamid.XYZ"}) == "wamid.XYZ"
    assert _extract_wamid({}) is None
    assert _extract_wamid({"messages": []}) is None
    assert _extract_wamid(None) is None
