# =============================================================================
# Stratum AI - Audit Logging Tasks
# =============================================================================
"""
Background tasks for processing audit log queues and compliance.
"""

import json
from datetime import UTC, datetime

from celery import shared_task
from celery.utils.log import get_task_logger

from app.core.config import settings
from app.db.session import SyncSessionLocal
from app.models import AuditAction, AuditLog

logger = get_task_logger(__name__)


@shared_task
def process_audit_log_queue():
    """
    Process queued audit log entries from Redis.
    Batch inserts for performance.
    """
    logger.info("Processing audit log queue")

    try:
        import redis

        redis_client = redis.from_url(settings.redis_url)
        queue_key = "audit:log:queue"

        # Get batch of entries
        batch_size = 100
        entries = []

        for _ in range(batch_size):
            entry = redis_client.lpop(queue_key)
            if not entry:
                break
            entries.append(json.loads(entry))

        if not entries:
            logger.debug("No audit entries to process")
            return {"processed": 0}

        # Batch insert to database
        with SyncSessionLocal() as db:
            for entry in entries:
                log = AuditLog(
                    tenant_id=entry.get("tenant_id"),
                    user_id=entry.get("user_id"),
                    action=AuditAction(entry.get("action", "update")),
                    resource_type=entry.get("resource_type"),
                    resource_id=entry.get("resource_id"),
                    old_values=entry.get("old_values"),
                    new_values=entry.get("new_values"),
                    ip_address=entry.get("ip_address"),
                    user_agent=entry.get("user_agent"),
                    created_at=datetime.fromisoformat(entry.get("timestamp"))
                    if entry.get("timestamp")
                    else datetime.now(UTC),
                )
                db.add(log)

            db.commit()

        logger.info(f"Processed {len(entries)} audit log entries")
        return {"processed": len(entries)}

    except Exception as e:
        logger.error(f"Failed to process audit queue: {e}")
        raise
