# =============================================================================
# Stratum AI - CAPI Delivery Log Persistence (P0 Gap Fix)
# =============================================================================
"""
Database-backed delivery logging for CAPI events.

Fixes the P0 gap: In-memory delivery logs are lost on restart and
cannot be used for investigation or compliance auditing.

Features:
- Persistent storage of all CAPI delivery attempts
- Queryable history for debugging and compliance
- Aggregated metrics for monitoring
- Retention management
- Integration with DLQ for failed events
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import and_, desc, func, select

from app.db.session import async_session_factory

logger = logging.getLogger(__name__)


class DeliveryStatus(str, Enum):
    """CAPI delivery status."""

    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    RATE_LIMITED = "rate_limited"
    CIRCUIT_OPEN = "circuit_open"


@dataclass
class DeliveryLogEntry:
    """
    Represents a CAPI delivery log entry.
    """

    id: str
    tenant_id: int
    platform: str
    event_id: Optional[str]
    event_name: str
    event_time: datetime
    delivery_time: datetime
    status: DeliveryStatus
    latency_ms: float
    retry_count: int
    error_message: Optional[str]
    request_id: Optional[str]
    platform_response: Optional[dict[str, Any]]
    user_data_hash: Optional[str]  # Hashed PII for correlation without storing PII
    event_value: Optional[float]
    currency: Optional[str]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "tenant_id": self.tenant_id,
            "platform": self.platform,
            "event_id": self.event_id,
            "event_name": self.event_name,
            "event_time": self.event_time.isoformat(),
            "delivery_time": self.delivery_time.isoformat(),
            "status": self.status.value,
            "latency_ms": self.latency_ms,
            "retry_count": self.retry_count,
            "error_message": self.error_message,
            "request_id": self.request_id,
            "event_value": self.event_value,
            "currency": self.currency,
        }


@dataclass
class DeliveryMetrics:
    """Aggregated delivery metrics."""

    total_events: int = 0
    successful: int = 0
    failed: int = 0
    retrying: int = 0
    success_rate_pct: float = 0.0
    avg_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    by_platform: dict[str, dict[str, int]] = None
    by_event_type: dict[str, dict[str, int]] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None

    def __post_init__(self):
        if self.by_platform is None:
            self.by_platform = {}
        if self.by_event_type is None:
            self.by_event_type = {}


class DeliveryLogger:
    """
    Database-backed CAPI delivery logger.

    Logs all delivery attempts to database for persistence,
    auditing, and analysis.
    """

    # In-memory buffer for batch inserts
    _buffer: list[DeliveryLogEntry] = []
    _buffer_max_size: int = 100
    _last_flush: datetime = None

    def __init__(self, buffer_size: int = 100):
        """
        Initialize the delivery logger.

        Args:
            buffer_size: Number of entries to buffer before flushing
        """
        self._buffer_max_size = buffer_size
        self._last_flush = datetime.now(UTC)

    async def log_delivery(
        self,
        tenant_id: int,
        platform: str,
        event_name: str,
        status: DeliveryStatus,
        latency_ms: float,
        event_id: Optional[str] = None,
        event_time: Optional[datetime] = None,
        retry_count: int = 0,
        error_message: Optional[str] = None,
        request_id: Optional[str] = None,
        platform_response: Optional[dict[str, Any]] = None,
        user_data_hash: Optional[str] = None,
        event_value: Optional[float] = None,
        currency: Optional[str] = None,
    ) -> DeliveryLogEntry:
        """
        Log a CAPI delivery attempt.

        Args:
            tenant_id: Tenant ID
            platform: Platform name
            event_name: Event name
            status: Delivery status
            latency_ms: Delivery latency in milliseconds
            event_id: Optional event ID
            event_time: Original event timestamp
            retry_count: Number of retries
            error_message: Error message if failed
            request_id: Platform request ID
            platform_response: Platform API response
            user_data_hash: Hash of user data for correlation
            event_value: Event value (e.g., purchase amount)
            currency: Currency code

        Returns:
            Created DeliveryLogEntry
        """
        now = datetime.now(UTC)

        entry = DeliveryLogEntry(
            id=str(uuid4()),
            tenant_id=tenant_id,
            platform=platform,
            event_id=event_id,
            event_name=event_name,
            event_time=event_time or now,
            delivery_time=now,
            status=status,
            latency_ms=latency_ms,
            retry_count=retry_count,
            error_message=error_message,
            request_id=request_id,
            platform_response=platform_response,
            user_data_hash=user_data_hash,
            event_value=event_value,
            currency=currency,
        )

        # Add to buffer
        self._buffer.append(entry)

        # Flush if buffer is full or enough time has passed
        if (
            len(self._buffer) >= self._buffer_max_size
            or (now - self._last_flush).total_seconds() > 30
        ):
            await self.flush()

        # Log for immediate visibility
        log_level = logging.INFO if status == DeliveryStatus.SUCCESS else logging.WARNING
        logger.log(
            log_level,
            f"CAPI Delivery: platform={platform} event={event_name} "
            f"status={status.value} latency={latency_ms:.0f}ms "
            f"event_id={event_id or 'N/A'}",
        )

        return entry

    async def flush(self):
        """Flush buffered entries to database."""
        if not self._buffer:
            return

        entries_to_flush = self._buffer.copy()
        self._buffer.clear()
        self._last_flush = datetime.now(UTC)

        try:
            async with async_session_factory() as db:
                for entry in entries_to_flush:
                    # Import here to avoid circular imports
                    from app.models.capi_delivery import CAPIDeliveryLog

                    db_entry = CAPIDeliveryLog(
                        id=entry.id,
                        tenant_id=entry.tenant_id,
                        platform=entry.platform,
                        event_id=entry.event_id,
                        event_name=entry.event_name,
                        event_time=entry.event_time,
                        delivery_time=entry.delivery_time,
                        status=entry.status.value,
                        latency_ms=entry.latency_ms,
                        retry_count=entry.retry_count,
                        error_message=entry.error_message,
                        request_id=entry.request_id,
                        platform_response=entry.platform_response,
                        user_data_hash=entry.user_data_hash,
                        event_value_cents=int(entry.event_value * 100)
                        if entry.event_value
                        else None,
                        currency=entry.currency,
                    )
                    db.add(db_entry)

                await db.commit()
                logger.debug(f"Flushed {len(entries_to_flush)} delivery log entries to database")

        except Exception as e:
            logger.error(f"Failed to flush delivery logs to database: {e}")
            # Re-add entries to buffer for retry
            self._buffer.extend(entries_to_flush)

    async def get_delivery_history(
        self,
        tenant_id: int,
        platform: Optional[str] = None,
        event_name: Optional[str] = None,
        status: Optional[DeliveryStatus] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[DeliveryLogEntry]:
        """
        Get delivery history with filters.

        Args:
            tenant_id: Tenant ID
            platform: Filter by platform
            event_name: Filter by event name
            status: Filter by status
            start_time: Filter by start time
            end_time: Filter by end time
            limit: Maximum entries to return
            offset: Pagination offset

        Returns:
            List of DeliveryLogEntry objects
        """
        try:
            from app.models.capi_delivery import CAPIDeliveryLog

            async with async_session_factory() as db:
                query = select(CAPIDeliveryLog).where(CAPIDeliveryLog.tenant_id == tenant_id)

                if platform:
                    query = query.where(CAPIDeliveryLog.platform == platform)
                if event_name:
                    query = query.where(CAPIDeliveryLog.event_name == event_name)
                if status:
                    query = query.where(CAPIDeliveryLog.status == status.value)
                if start_time:
                    query = query.where(CAPIDeliveryLog.delivery_time >= start_time)
                if end_time:
                    query = query.where(CAPIDeliveryLog.delivery_time <= end_time)

                query = query.order_by(desc(CAPIDeliveryLog.delivery_time))
                query = query.offset(offset).limit(limit)

                result = await db.execute(query)
                rows = result.scalars().all()

                return [
                    DeliveryLogEntry(
                        id=str(row.id),
                        tenant_id=row.tenant_id,
                        platform=row.platform,
                        event_id=row.event_id,
                        event_name=row.event_name,
                        event_time=row.event_time,
                        delivery_time=row.delivery_time,
                        status=DeliveryStatus(row.status),
                        latency_ms=row.latency_ms,
                        retry_count=row.retry_count,
                        error_message=row.error_message,
                        request_id=row.request_id,
                        platform_response=row.platform_response,
                        user_data_hash=row.user_data_hash,
                        event_value=row.event_value_cents / 100 if row.event_value_cents else None,
                        currency=row.currency,
                    )
                    for row in rows
                ]

        except Exception as e:
            logger.error(f"Failed to get delivery history: {e}")
            return []

    async def get_metrics(
        self,
        tenant_id: int,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> DeliveryMetrics:
        """
        Get aggregated delivery metrics.

        Args:
            tenant_id: Tenant ID
            start_time: Period start (default: last 24 hours)
            end_time: Period end (default: now)

        Returns:
            DeliveryMetrics object
        """
        if not end_time:
            end_time = datetime.now(UTC)
        if not start_time:
            start_time = end_time - timedelta(hours=24)

        metrics = DeliveryMetrics(
            period_start=start_time,
            period_end=end_time,
        )

        try:
            from app.models.capi_delivery import CAPIDeliveryLog

            async with async_session_factory() as db:
                # Base query
                base_filter = and_(
                    CAPIDeliveryLog.tenant_id == tenant_id,
                    CAPIDeliveryLog.delivery_time >= start_time,
                    CAPIDeliveryLog.delivery_time <= end_time,
                )

                # Total counts
                result = await db.execute(
                    select(
                        func.count(CAPIDeliveryLog.id).label("total"),
                        func.count(CAPIDeliveryLog.id)
                        .filter(CAPIDeliveryLog.status == "success")
                        .label("successful"),
                        func.count(CAPIDeliveryLog.id)
                        .filter(CAPIDeliveryLog.status == "failed")
                        .label("failed"),
                        func.avg(CAPIDeliveryLog.latency_ms).label("avg_latency"),
                    ).where(base_filter)
                )
                row = result.one()

                metrics.total_events = row.total or 0
                metrics.successful = row.successful or 0
                metrics.failed = row.failed or 0
                metrics.avg_latency_ms = float(row.avg_latency or 0)

                if metrics.total_events > 0:
                    metrics.success_rate_pct = (metrics.successful / metrics.total_events) * 100

                # Latency percentiles
                latency_result = await db.execute(
                    select(CAPIDeliveryLog.latency_ms)
                    .where(base_filter)
                    .where(CAPIDeliveryLog.status == "success")
                    .order_by(CAPIDeliveryLog.latency_ms)
                )
                latencies = [r[0] for r in latency_result.all()]

                if latencies:
                    n = len(latencies)
                    metrics.p50_latency_ms = latencies[int(n * 0.50)]
                    metrics.p95_latency_ms = latencies[int(n * 0.95)] if n > 20 else latencies[-1]
                    metrics.p99_latency_ms = latencies[int(n * 0.99)] if n > 100 else latencies[-1]

                # By platform
                platform_result = await db.execute(
                    select(
                        CAPIDeliveryLog.platform,
                        CAPIDeliveryLog.status,
                        func.count(CAPIDeliveryLog.id).label("count"),
                    )
                    .where(base_filter)
                    .group_by(CAPIDeliveryLog.platform, CAPIDeliveryLog.status)
                )

                for row in platform_result.all():
                    if row.platform not in metrics.by_platform:
                        metrics.by_platform[row.platform] = {"success": 0, "failed": 0}
                    metrics.by_platform[row.platform][row.status] = row.count

                # By event type
                event_result = await db.execute(
                    select(
                        CAPIDeliveryLog.event_name,
                        CAPIDeliveryLog.status,
                        func.count(CAPIDeliveryLog.id).label("count"),
                    )
                    .where(base_filter)
                    .group_by(CAPIDeliveryLog.event_name, CAPIDeliveryLog.status)
                )

                for row in event_result.all():
                    if row.event_name not in metrics.by_event_type:
                        metrics.by_event_type[row.event_name] = {"success": 0, "failed": 0}
                    metrics.by_event_type[row.event_name][row.status] = row.count

        except Exception as e:
            logger.error(f"Failed to get delivery metrics: {e}")

        return metrics

    async def cleanup_old_logs(self, retention_days: int = 90) -> int:
        """
        Remove logs older than retention period.

        Args:
            retention_days: Number of days to retain logs

        Returns:
            Number of entries deleted
        """
        cutoff = datetime.now(UTC) - timedelta(days=retention_days)

        try:
            from sqlalchemy import delete

            from app.models.capi_delivery import CAPIDeliveryLog

            async with async_session_factory() as db:
                result = await db.execute(
                    delete(CAPIDeliveryLog).where(CAPIDeliveryLog.delivery_time < cutoff)
                )
                await db.commit()

                deleted = result.rowcount
                logger.info(f"Cleaned up {deleted} delivery logs older than {retention_days} days")
                return deleted

        except Exception as e:
            logger.error(f"Failed to cleanup old delivery logs: {e}")
            return 0


# =============================================================================
# Singleton Instance
# =============================================================================

# Global delivery logger instance
delivery_logger = DeliveryLogger()


def get_delivery_logger() -> DeliveryLogger:
    """Get the delivery logger instance."""
    return delivery_logger
