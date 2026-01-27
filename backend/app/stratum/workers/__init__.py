# =============================================================================
# Stratum AI - Workers Module
# =============================================================================
"""
Celery workers for automation and data synchronization.

Workers:
- data_sync: Platform data synchronization (pull)
- automation_runner: Automation execution (push)
"""

from app.stratum.workers.automation_runner import (
    approve_queued_action,
    cleanup_completed_actions,
    execute_action,
    execute_action_batch,
    get_automation_stats,
    process_pending_actions,
    queue_action_for_review,
    reject_queued_action,
    rollback_action,
    run_autopilot_all,
    run_autopilot_for_account,
)
from app.stratum.workers.data_sync import (
    calculate_all_signal_health,
    calculate_signal_health,
    cleanup_old_data,
    get_task_status,
    refresh_emq,
    refresh_emq_all,
    send_signal_health_alert,
    send_weekly_digest,
    sync_all_platforms,
    sync_platform_data,
    trigger_immediate_sync,
    update_metrics,
    update_metrics_all,
)

__all__ = [
    # Data sync tasks
    "sync_platform_data",
    "sync_all_platforms",
    "update_metrics",
    "update_metrics_all",
    "refresh_emq",
    "refresh_emq_all",
    "calculate_signal_health",
    "calculate_all_signal_health",
    "send_signal_health_alert",
    "send_weekly_digest",
    "cleanup_old_data",
    "get_task_status",
    "trigger_immediate_sync",
    # Automation tasks
    "execute_action",
    "execute_action_batch",
    "run_autopilot_for_account",
    "run_autopilot_all",
    "queue_action_for_review",
    "process_pending_actions",
    "approve_queued_action",
    "reject_queued_action",
    "rollback_action",
    "cleanup_completed_actions",
    "get_automation_stats",
]
