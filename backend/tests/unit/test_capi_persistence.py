# =============================================================================
# Stratum AI - CAPI Delivery Persistence Tests
# =============================================================================
"""
Tests for wiring CAPI delivery persistence (Tier 3).

`CAPIService.stream_events` sent events but never recorded a delivery — the
persistence code (`delivery_logger` -> `capi_delivery_logs`) was dead (zero
importers). The service is now tenant-aware and logs one delivery per
(event, platform) result via the shared DeliveryLogger, best-effort so audit
logging can never fail the actual send.

Pure/mock tests — no DB, no network.
"""

from app.services.capi.capi_service import CAPIService, _build_delivery_kwargs
from app.services.capi.delivery_logger import DeliveryStatus
from app.services.capi.platform_connectors import CAPIResponse


def _ok_result(platform="meta"):
    return CAPIResponse(
        success=True,
        events_received=1,
        events_processed=1,
        errors=[],
        platform=platform,
    )


def _fail_result(platform="meta"):
    return CAPIResponse(
        success=False,
        events_received=1,
        events_processed=0,
        errors=[{"message": "bad token"}],
        platform=platform,
    )


_EVENT = {
    "event_name": "Purchase",
    "event_id": "evt-1",
    "event_time": 1_700_000_000,
    "parameters": {"value": 50.0, "currency": "USD"},
}


# --- tenant awareness ---
def test_service_stores_tenant_id():
    assert CAPIService(tenant_id=5).tenant_id == 5
    assert CAPIService().tenant_id is None


# --- pure mapping ---
def test_build_delivery_kwargs_success():
    kw = _build_delivery_kwargs(
        tenant_id=7, platform="meta", event=_EVENT, result=_ok_result(), latency_ms=12.5
    )
    assert kw["tenant_id"] == 7
    assert kw["platform"] == "meta"
    assert kw["event_name"] == "Purchase"
    assert kw["status"] == DeliveryStatus.SUCCESS
    assert kw["latency_ms"] == 12.5
    assert kw["event_id"] == "evt-1"
    assert kw["error_message"] is None
    assert kw["event_value"] == 50.0
    assert kw["currency"] == "USD"
    assert kw["event_time"] is not None  # unix -> datetime


def test_build_delivery_kwargs_failure_maps_error():
    kw = _build_delivery_kwargs(
        tenant_id=1,
        platform="meta",
        event=_EVENT,
        result=_fail_result(),
        latency_ms=9.0,
    )
    assert kw["status"] == DeliveryStatus.FAILED
    assert "bad token" in kw["error_message"]


# --- _log_deliveries fans out one record per (event, platform), best-effort ---
async def test_log_deliveries_records_each(monkeypatch):
    calls = []

    class FakeDL:
        async def log_delivery(self, **kw):
            calls.append(kw)

    monkeypatch.setattr(
        "app.services.capi.capi_service.get_delivery_logger", lambda: FakeDL()
    )
    svc = CAPIService(tenant_id=5)
    results = [
        ("meta", _ok_result("meta"), 10.0),
        ("google", _fail_result("google"), 20.0),
    ]
    await svc._log_deliveries([_EVENT], results)

    assert len(calls) == 2  # one per (event, platform)
    assert {c["platform"] for c in calls} == {"meta", "google"}
    assert all(c["tenant_id"] == 5 for c in calls)


async def test_log_deliveries_never_raises(monkeypatch):
    class BoomDL:
        async def log_delivery(self, **kw):
            raise RuntimeError("db down")

    monkeypatch.setattr(
        "app.services.capi.capi_service.get_delivery_logger", lambda: BoomDL()
    )
    svc = CAPIService(tenant_id=1)
    # Must not raise — audit logging is best-effort.
    await svc._log_deliveries([_EVENT], [("meta", _ok_result(), 1.0)])
