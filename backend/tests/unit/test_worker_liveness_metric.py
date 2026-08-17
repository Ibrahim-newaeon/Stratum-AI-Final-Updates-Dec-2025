# =============================================================================
# Stratum AI - Worker Liveness Metric
# =============================================================================
"""Worker liveness reaches Prometheus, so WorkerDown can actually fire.

#661 removed a ``WorkerDown`` rule whose expression was
``up{job="stratum-worker"} == 0``. Nothing scrapes the worker — it serves no
HTTP and has no ``/metrics`` — so ``up{job="stratum-worker"}`` never existed and
the rule could not fire in either direction. That is why the heartbeat exists at
all: the worker writes an epoch to Redis every minute
(``stratum:worker:heartbeat``, TTL 300) and the API reads it.

``/health`` already reports that reading as ``worker: alive|down|unknown``, but
nothing exported it, so the only machine-readable signal was absent and the
alert stayed deleted.

These tests pin the two halves that make the alert real:

1. the gauge maps liveness onto 1/0, and
2. the ``/metrics`` handler refreshes it on every scrape.

(2) is the half that matters. A gauge that is declared but never set reads 0
forever, which is indistinguishable from a permanently dead worker — an alert
that fires always is as useless as one that fires never, and this repo has
produced both.
"""

from unittest.mock import MagicMock, patch

import pytest
from prometheus_client import REGISTRY

from app.core.metrics import refresh_worker_up_metric, set_worker_up_metric

pytestmark = pytest.mark.asyncio

_METRIC = "stratum_celery_worker_up"


def _gauge():
    return REGISTRY.get_sample_value(_METRIC)


class TestGaugeValue:
    async def test_alive_worker_reads_one(self):
        set_worker_up_metric(True)
        assert _gauge() == 1.0

    async def test_dead_worker_reads_zero(self):
        set_worker_up_metric(False)
        assert _gauge() == 0.0


class TestRefreshReadsTheHeartbeat:
    async def test_refresh_reflects_a_live_heartbeat(self):
        set_worker_up_metric(False)
        with patch("app.workers.tasks.monitoring.worker_is_alive", return_value=True):
            refresh_worker_up_metric()
        assert _gauge() == 1.0

    async def test_refresh_reflects_a_missing_heartbeat(self):
        set_worker_up_metric(True)
        with patch("app.workers.tasks.monitoring.worker_is_alive", return_value=False):
            refresh_worker_up_metric()
        assert _gauge() == 0.0

    async def test_unreadable_heartbeat_reads_zero_not_stale_one(self):
        """Failing to read Redis must not leave a reassuring 1 in place.

        A stale 1 hides a genuinely dead worker; a spurious 0 costs a page that
        the alert's `for:` window largely absorbs. Fail toward noticing.
        """
        set_worker_up_metric(True)
        with patch(
            "app.workers.tasks.monitoring.worker_is_alive",
            side_effect=OSError("redis unreachable"),
        ):
            refresh_worker_up_metric()
        assert _gauge() == 0.0


class TestMetricsEndpointRefreshesOnScrape:
    async def test_scrape_exports_the_current_worker_state(self):
        """The handler must refresh before serialising, or the exported value
        is whatever the last unrelated caller happened to leave behind."""
        from app.main import app

        route = next(r for r in app.routes if getattr(r, "path", None) == "/metrics")
        request = MagicMock()
        request.headers.get.return_value = ""

        set_worker_up_metric(True)
        with patch("app.workers.tasks.monitoring.worker_is_alive", return_value=False):
            response = await route.endpoint(request)

        body = response.body.decode()
        assert f"{_METRIC} 0.0" in body, "scrape did not refresh the gauge"
