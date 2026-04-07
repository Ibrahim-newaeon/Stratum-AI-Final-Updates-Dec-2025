# =============================================================================
# Stratum AI - Celery Tasks Module
# =============================================================================
"""
Background tasks organized by domain.

This module re-exports all tasks for backward compatibility.
Tasks are split into domain-specific modules for maintainability.

Modules:
- sync: Campaign data synchronization
- rules: Automation rules evaluation
- competitors: Competitor intelligence
- forecast: ML forecasting tasks
- creative: Creative fatigue analysis
- audit: Audit logging tasks
- whatsapp: WhatsApp messaging tasks
- ml: Live predictions and alerts
- billing: Cost allocation and usage
- monitoring: Pipeline health checks
- scores: Daily scoring tasks
- cdp: Customer Data Platform tasks
- cms: Content management tasks
"""

# Import all tasks for celery autodiscover
from app.workers.tasks.audit import (
    process_audit_log_queue,
)
from app.workers.tasks.billing import (
    calculate_cost_allocation,
    calculate_usage_rollup,
)
from app.workers.tasks.cdp import (
    compute_all_cdp_funnels,
    compute_all_cdp_segments,
    compute_cdp_funnel,
    compute_cdp_rfm,
    compute_cdp_segment,
    compute_cdp_traits,
)
from app.workers.tasks.cms import (
    create_cms_post_version,
    publish_cms_post,
    publish_scheduled_cms_posts,
)
from app.workers.tasks.competitors import (
    fetch_competitor_data,
    refresh_all_competitors,
)
from app.workers.tasks.creative import (
    calculate_all_fatigue_scores,
)
from app.workers.tasks.forecast import (
    generate_daily_forecasts,
    generate_forecast,
)

# Re-export helpers for external use
from app.workers.tasks.helpers import (
    calculate_task_confidence,
    publish_event,
)
from app.workers.tasks.ml import (
    generate_roas_alerts,
    run_all_tenant_predictions,
    run_live_predictions,
)
from app.workers.tasks.monitoring import (
    check_pipeline_health,
)
from app.workers.tasks.rules import (
    evaluate_all_rules,
    evaluate_rules,
)
from app.workers.tasks.scores import (
    calculate_daily_scores,
)
from app.workers.tasks.sync import (
    sync_all_campaigns,
    sync_campaign_data,
)
from app.workers.tasks.whatsapp import (
    process_scheduled_whatsapp_messages,
    send_whatsapp_message,
)

__all__ = [
    # Creative tasks
    "calculate_all_fatigue_scores",
    # Billing tasks
    "calculate_cost_allocation",
    # Score tasks
    "calculate_daily_scores",
    "calculate_task_confidence",
    "calculate_usage_rollup",
    # Monitoring tasks
    "check_pipeline_health",
    "compute_all_cdp_funnels",
    "compute_all_cdp_segments",
    "compute_cdp_funnel",
    "compute_cdp_rfm",
    # CDP tasks
    "compute_cdp_segment",
    "compute_cdp_traits",
    "create_cms_post_version",
    "evaluate_all_rules",
    # Rules tasks
    "evaluate_rules",
    # Competitor tasks
    "fetch_competitor_data",
    "generate_daily_forecasts",
    # Forecast tasks
    "generate_forecast",
    "generate_roas_alerts",
    # Audit tasks
    "process_audit_log_queue",
    "process_scheduled_whatsapp_messages",
    "publish_cms_post",
    # Helpers
    "publish_event",
    # CMS tasks
    "publish_scheduled_cms_posts",
    "refresh_all_competitors",
    "run_all_tenant_predictions",
    # ML tasks
    "run_live_predictions",
    # WhatsApp tasks
    "send_whatsapp_message",
    "sync_all_campaigns",
    # Sync tasks
    "sync_campaign_data",
]
