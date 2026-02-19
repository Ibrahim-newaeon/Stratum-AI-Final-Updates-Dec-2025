# =============================================================================
# Stratum AI - Celery Tasks (Legacy Compatibility Shim)
# =============================================================================
"""
Legacy compatibility layer for Celery task imports.

Tasks have been refactored into domain-specific modules under
``app.workers.tasks/`` (the package directory). This file re-exports
every public task and helper so that existing import paths like::

    from app.workers.tasks import sync_all_campaigns

continue to work without modification.

The canonical definitions live in:
    - app.workers.tasks.sync        (campaign sync)
    - app.workers.tasks.rules       (automation rules)
    - app.workers.tasks.competitors (competitor intel)
    - app.workers.tasks.forecast    (ML forecasting)
    - app.workers.tasks.creative    (creative fatigue)
    - app.workers.tasks.audit       (audit log processing)
    - app.workers.tasks.whatsapp    (WhatsApp messaging)
    - app.workers.tasks.ml          (live predictions & alerts)
    - app.workers.tasks.billing     (cost allocation & usage)
    - app.workers.tasks.monitoring  (pipeline health checks)
    - app.workers.tasks.scores      (daily scoring)
    - app.workers.tasks.cdp         (Customer Data Platform)
    - app.workers.tasks.cms         (content management)
    - app.workers.tasks.helpers     (shared utilities)

DO NOT add new task definitions here. Create them in the appropriate
domain module under ``app/workers/tasks/`` instead.
"""

# ---------------------------------------------------------------------------
# Re-export everything from the modular tasks package (app.workers.tasks/)
# ---------------------------------------------------------------------------

# Sync tasks
from app.workers.tasks import (  # noqa: F401 – re-exports
    calculate_all_fatigue_scores,
    calculate_cost_allocation,
    calculate_daily_scores,
    calculate_task_confidence,
    calculate_usage_rollup,
    check_pipeline_health,
    compute_all_cdp_funnels,
    compute_all_cdp_segments,
    compute_cdp_funnel,
    compute_cdp_rfm,
    compute_cdp_segment,
    compute_cdp_traits,
    create_cms_post_version,
    evaluate_all_rules,
    evaluate_rules,
    fetch_competitor_data,
    generate_daily_forecasts,
    generate_forecast,
    generate_roas_alerts,
    process_audit_log_queue,
    process_scheduled_whatsapp_messages,
    publish_cms_post,
    publish_event,
    publish_scheduled_cms_posts,
    refresh_all_competitors,
    run_all_tenant_predictions,
    run_live_predictions,
    send_whatsapp_message,
    sync_all_campaigns,
    sync_campaign_data,
)

__all__ = [
    # Sync
    "sync_campaign_data",
    "sync_all_campaigns",
    # Rules
    "evaluate_rules",
    "evaluate_all_rules",
    # Competitors
    "fetch_competitor_data",
    "refresh_all_competitors",
    # Forecast
    "generate_forecast",
    "generate_daily_forecasts",
    # Creative
    "calculate_all_fatigue_scores",
    # Audit
    "process_audit_log_queue",
    # WhatsApp
    "send_whatsapp_message",
    "process_scheduled_whatsapp_messages",
    # ML
    "run_live_predictions",
    "run_all_tenant_predictions",
    "generate_roas_alerts",
    # Billing
    "calculate_cost_allocation",
    "calculate_usage_rollup",
    # Monitoring
    "check_pipeline_health",
    # Scores
    "calculate_daily_scores",
    # CDP
    "compute_cdp_segment",
    "compute_all_cdp_segments",
    "compute_cdp_rfm",
    "compute_cdp_traits",
    "compute_cdp_funnel",
    "compute_all_cdp_funnels",
    # CMS
    "publish_scheduled_cms_posts",
    "publish_cms_post",
    "create_cms_post_version",
    # Helpers
    "publish_event",
    "calculate_task_confidence",
]
