# =============================================================================
# Stratum AI - Task Helpers
# =============================================================================
"""
Shared helper functions for Celery tasks.
"""

import json
from typing import Any, Dict

from celery.utils.log import get_task_logger

from app.core.config import settings

logger = get_task_logger(__name__)


def calculate_task_confidence(
    campaign_data: list, analysis_type: str = "portfolio"
) -> float:
    """
    Calculate model-derived confidence for background task predictions.

    Args:
        campaign_data: List of campaign dicts with metrics
        analysis_type: Type of analysis (portfolio, campaign, alerts)

    Returns:
        Confidence score between 0.0 and 0.95
    """
    if not campaign_data:
        return 0.3  # Minimum confidence for empty data

    n = len(campaign_data)

    # Base confidence from sample size
    sample_conf = min(0.5, 0.25 + (n / 40))

    # Data completeness
    complete = sum(
        1 for c in campaign_data if c.get("roas", 0) > 0 and c.get("spend", 0) > 0
    )
    completeness_conf = (complete / n) * 0.25 if n > 0 else 0

    # Analysis type adjustments
    type_bonus = {"portfolio": 0.1, "campaign": 0.15, "alerts": 0.2}.get(
        analysis_type, 0.1
    )

    return round(min(0.95, sample_conf + completeness_conf + type_bonus), 2)


def publish_event(tenant_id: int, event_type: str, payload: Dict[str, Any]) -> None:
    """
    Publish real-time event to Redis pub/sub for WebSocket distribution.

    Args:
        tenant_id: Tenant ID for channel routing
        event_type: Type of event (sync_complete, rule_triggered, etc.)
        payload: Event data to send
    """
    try:
        import redis

        redis_client = redis.from_url(settings.redis_url)
        channel = f"events:tenant:{tenant_id}"

        message = json.dumps(
            {
                "type": event_type,
                "tenant_id": tenant_id,
                "payload": payload,
            }
        )

        redis_client.publish(channel, message)
        logger.debug(f"Published {event_type} event to {channel}")

    except Exception as e:
        logger.warning(f"Failed to publish event: {e}")
