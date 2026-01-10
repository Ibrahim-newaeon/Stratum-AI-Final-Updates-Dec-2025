# =============================================================================
# Stratum AI - Workers Package
# =============================================================================
"""
Celery workers for background task processing.

Tasks:
- Data synchronization from ad platforms
- Rules engine evaluation
- ML job processing
- Report generation
"""

from app.workers.celery_app import celery_app
from app.workers.tasks import (
    sync_campaign_data,
    evaluate_rules,
    fetch_competitor_data,
    generate_forecast,
)

__all__ = [
    "celery_app",
    "sync_campaign_data",
    "evaluate_rules",
    "fetch_competitor_data",
    "generate_forecast",
]
