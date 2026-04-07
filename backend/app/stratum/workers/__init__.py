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
    "approve_queued_action",
    "calculate_all_signal_health",
    "calculate_signal_health",
    "cleanup_completed_actions",
    "cleanup_old_data",
    # Automation tasks
    "execute_action",
    "execute_action_batch",
    "get_automation_stats",
    "get_task_status",
    "process_pending_actions",
    "queue_action_for_review",
    "refresh_emq",
    "refresh_emq_all",
    "reject_queued_action",
    "rollback_action",
    "run_autopilot_all",
    "run_autopilot_for_account",
    "send_signal_health_alert",
    "send_weekly_digest",
    "sync_all_platforms",
    # Data sync tasks
    "sync_platform_data",
    "trigger_immediate_sync",
    "update_metrics",
    "update_metrics_all",
]
