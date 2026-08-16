# =============================================================================
# Stratum AI - Readiness probe tests (INF-002)
# =============================================================================
"""
The readiness probe at /health/ready must report ready only when BOTH
Postgres and Redis are up — and must NOT depend on a third-party
(SendGrid) API call. check_readiness() holds that logic.
"""

from unittest.mock import AsyncMock, patch

import pytest

from app.main import check_readiness

pytestmark = pytest.mark.unit


def _redis_ok():
    client = AsyncMock()
    client.ping = AsyncMock()
    client.close = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_ready_when_db_and_redis_up():
    with patch(
        "app.main.check_database_health",
        new=AsyncMock(return_value={"status": "healthy"}),
    ), patch("redis.asyncio.from_url", return_value=_redis_ok()):
        result = await check_readiness()
    assert result["ready"] is True
    assert result["database"] == "healthy"
    assert result["redis"] == "healthy"


@pytest.mark.asyncio
async def test_not_ready_when_db_down():
    with patch(
        "app.main.check_database_health",
        new=AsyncMock(return_value={"status": "unhealthy"}),
    ), patch("redis.asyncio.from_url", return_value=_redis_ok()):
        result = await check_readiness()
    assert result["ready"] is False


@pytest.mark.asyncio
async def test_not_ready_when_redis_down():
    bad = AsyncMock()
    bad.ping = AsyncMock(side_effect=ConnectionError("redis down"))
    with patch(
        "app.main.check_database_health",
        new=AsyncMock(return_value={"status": "healthy"}),
    ), patch("redis.asyncio.from_url", return_value=bad):
        result = await check_readiness()
    assert result["ready"] is False
    assert "unhealthy" in result["redis"]
