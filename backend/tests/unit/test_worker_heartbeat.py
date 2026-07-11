# =============================================================================
# Stratum AI - Worker liveness heartbeat tests (INF-003)
# =============================================================================
"""
Celery has no HTTP endpoint, so the worker writes a heartbeat to Redis and the
API reports liveness from it. worker_is_alive() must reflect a fresh heartbeat,
a stale one, a missing key, and Redis being unavailable.
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pytest

from app.workers.tasks import monitoring

pytestmark = pytest.mark.unit


def _now():
    return datetime.now(UTC).timestamp()


def test_alive_with_fresh_heartbeat():
    client = MagicMock()
    client.get.return_value = str(_now()).encode()
    with patch("redis.from_url", return_value=client):
        assert monitoring.worker_is_alive() is True


def test_dead_with_stale_heartbeat():
    client = MagicMock()
    client.get.return_value = str(_now() - 10_000).encode()  # long ago
    with patch("redis.from_url", return_value=client):
        assert monitoring.worker_is_alive() is False


def test_dead_when_no_heartbeat_key():
    client = MagicMock()
    client.get.return_value = None
    with patch("redis.from_url", return_value=client):
        assert monitoring.worker_is_alive() is False


def test_dead_when_redis_unavailable():
    with patch("redis.from_url", side_effect=ConnectionError("redis down")):
        assert monitoring.worker_is_alive() is False


def test_heartbeat_task_writes_key():
    client = MagicMock()
    with patch("redis.from_url", return_value=client):
        result = monitoring.worker_heartbeat()
    client.set.assert_called_once()
    args, kwargs = client.set.call_args
    assert args[0] == monitoring.WORKER_HEARTBEAT_KEY
    assert kwargs.get("ex") == monitoring.WORKER_HEARTBEAT_TTL
    assert "heartbeat" in result
