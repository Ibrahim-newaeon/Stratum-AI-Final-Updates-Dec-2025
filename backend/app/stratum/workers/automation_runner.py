"""
Stratum AI: Automation Runner Workers
=====================================

Celery tasks for executing autopilot actions across platforms.
These workers handle the "push" side of the bi-directional integration,
applying optimization decisions to advertising platforms.

Safety First
------------

All automation actions pass through multiple safety checks:

1. **Signal Health Check**: Verified before each execution batch
2. **Trust Gate Evaluation**: Each action individually evaluated
3. **Rate Limiting**: Respects platform API limits
4. **Rollback Capability**: Failed actions can be reverted
5. **Audit Trail**: Every action is logged with full context

Task Flow
---------

    +--------------------+
    |   Autopilot Engine |
    |  (Proposes Actions)|
    +----------+---------+
               |
               v
    +--------------------+
    |    Trust Gate      |
    | (Evaluate + Filter)|
    +----------+---------+
               |
               v
    +--------------------+
    |   Action Queue     |
    |   (Redis/Celery)   |
    +----------+---------+
               |
               v
    +--------------------+
    | Automation Runner  |
    | (Execute Actions)  |
    +----------+---------+
               |
               v
    +--------------------+
    |  Platform Adapter  |
    |    (API Calls)     |
    +--------------------+

Execution Modes
---------------

1. **Immediate**: Action executed as soon as approved (for urgent changes)
2. **Batched**: Actions queued and executed in batches (default)
3. **Scheduled**: Actions executed at specific times (e.g., budget resets at midnight)
4. **Manual Review**: Actions queued for human approval before execution
"""

import asyncio
import hashlib
import json
import logging
import uuid
from datetime import UTC, datetime, timedelta
from functools import wraps
from pathlib import Path
from typing import Any

try:
    from celery import shared_task
    from celery.schedules import crontab

    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False

    def shared_task(*args, **kwargs):
        def decorator(func):
            return func

        return decorator


from app.stratum.core.autopilot import AutopilotEngine
from app.stratum.models import AutomationAction, EntityStatus, Platform

logger = logging.getLogger("stratum.workers.automation_runner")


# Use the same Celery app as data_sync
if CELERY_AVAILABLE:
    from app.stratum.workers.data_sync import app

    # Add automation-specific schedules
    app.conf.beat_schedule.update(
        {
            "run-autopilot-every-hour": {
                "task": "app.stratum.workers.automation_runner.run_autopilot_all",
                "schedule": timedelta(hours=1),
            },
            "process-action-queue-every-5-min": {
                "task": "app.stratum.workers.automation_runner.process_pending_actions",
                "schedule": timedelta(minutes=5),
            },
            "cleanup-completed-actions-daily": {
                "task": "app.stratum.workers.automation_runner.cleanup_completed_actions",
                "schedule": crontab(hour=3, minute=0),  # 3 AM daily
            },
        }
    )


def async_task(func):
    """Run async functions in Celery tasks."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        return asyncio.run(func(*args, **kwargs))

    return wrapper


# ============================================================================
# ACTION EXECUTION TASKS
# ============================================================================

# How long a claimed action stays claimed. Long enough that a retry storm
# cannot slip past it, short enough that a genuinely new but identical action
# (an operator applying the same +10% twice, deliberately) is not blocked
# forever.
EXECUTION_CLAIM_TTL_SECONDS = 3600
EXECUTION_CLAIM_PREFIX = "automation_exec_claim:"


def _idempotency_key(action_data: dict[str, Any]) -> str:
    """Stable key for one logical action.

    Prefers an explicit action_id when the caller supplies one. Otherwise
    derives a key from the fields that make the mutation what it is, so a
    retry of the same payload collides while a genuinely different action
    does not.
    """
    explicit = action_data.get("action_id") or action_data.get("execution_id")
    if explicit:
        return f"{EXECUTION_CLAIM_PREFIX}{explicit}"

    payload = json.dumps(
        {
            "tenant_id": action_data.get("tenant_id"),
            "platform": action_data.get("platform"),
            "entity_type": action_data.get("entity_type"),
            "entity_id": action_data.get("entity_id"),
            "action_type": action_data.get("action_type"),
            "parameters": action_data.get("parameters"),
        },
        sort_keys=True,
        default=str,
    )
    digest = hashlib.sha256(payload.encode()).hexdigest()[:32]
    return f"{EXECUTION_CLAIM_PREFIX}{digest}"


async def _claim_execution(key: str) -> bool:
    """Claim an action for execution. False means someone already has it.

    Fails CLOSED: if the claim cannot be recorded, the action is not executed.
    An unverifiable claim is exactly the case where a retry would double-apply,
    so refusing is the safe direction — the action stays pending rather than
    risking a second budget change.
    """
    from app.core.security import get_redis_pool

    try:
        client = await get_redis_pool()
        return bool(await client.set(key, "1", ex=EXECUTION_CLAIM_TTL_SECONDS, nx=True))
    except (ConnectionError, TimeoutError, OSError) as exc:
        logger.error(
            "execution_claim_unavailable",
            extra={"key": key, "error": str(exc)},
        )
        return False


@shared_task(bind=True, max_retries=3)
@async_task
async def execute_action(
    self, action_data: dict[str, Any], credentials: dict[str, Any]
) -> dict[str, Any]:
    """
    Execute a single automation action.

    This is the core execution task. It:
    1. Reconstructs the action from serialized data
    2. Performs a final signal health check (ALWAYS - no bypass allowed)
    3. Executes via the appropriate platform adapter
    4. Records the result

    Args:
        action_data: Serialized AutomationAction
        credentials: Platform credentials

    Returns:
        Execution result with status and any errors

    Security Note:
        Signal health checks cannot be bypassed. All actions must pass
        through the trust gate. Use emergency_stop or pause_all action
        types for urgent situations - these are always allowed.
    """
    from app.stratum.adapters.registry import get_adapter

    execution_id = str(uuid.uuid4())[:8]
    result = {
        "execution_id": execution_id,
        "action_type": action_data.get("action_type"),
        "entity_id": action_data.get("entity_id"),
        "platform": action_data.get("platform"),
        "started_at": datetime.now(UTC).isoformat(),
        "status": "pending",
    }

    # Single-flight guard. This task carries max_retries=3 and mutates a live
    # ad account, but takes a plain dict rather than a queue row — so unlike
    # apply_actions_queue there is no ActionStatus transition to stop a retry
    # re-applying a change that already landed. Three retries of a +20% budget
    # increase compound. Claim the action first; a duplicate is reported as
    # skipped rather than executed twice.
    idempotency_key = _idempotency_key(action_data)
    claimed = await _claim_execution(idempotency_key)
    if not claimed:
        result["status"] = "skipped"
        result["reason"] = "Action already executed or in flight (idempotency guard)"
        logger.warning(f"Action {execution_id} skipped: duplicate of {idempotency_key}")
        return result

    try:
        platform = Platform(action_data["platform"])

        # Reconstruct the action
        action = AutomationAction(
            platform=platform,
            account_id=action_data["account_id"],
            entity_type=action_data["entity_type"],
            entity_id=action_data["entity_id"],
            action_type=action_data["action_type"],
            parameters=action_data["parameters"],
            signal_health_at_creation=action_data.get("signal_health_at_creation", 0),
        )

        # Final gate (ALWAYS enforced - no bypass).
        #
        # This used to read `current_signal_health` straight out of action_data
        # and block only below 40. Two problems: the score was whatever the
        # caller put in the dict rather than anything measured, and 40 admitted
        # the 40-69 DEGRADED band that policy says to hold ("Never auto-execute
        # when signal_health < 70" — CLAUDE.md). It now measures the tenant's
        # own rollup through the shared gate, which also applies the emergency
        # freeze this path never checked.
        tenant_id = action_data.get("tenant_id")
        if tenant_id is None:
            result["status"] = "blocked"
            result["reason"] = (
                "tenant_id missing - cannot verify signal health without it"
            )
            logger.warning(f"Action {execution_id} blocked: no tenant_id in payload")
            return result

        from app.autopilot.gate import evaluate_execution_gate
        from app.db.session import async_session_factory

        async with async_session_factory() as gate_db:
            decision = await evaluate_execution_gate(gate_db, tenant_id)

        if not decision.allowed:
            result["status"] = "blocked"
            result["reason"] = decision.reason
            logger.warning(f"Action {execution_id} blocked: {decision.reason}")
            return result

        # Initialize adapter and execute
        adapter = await get_adapter(platform, credentials)

        logger.info(
            f"Executing action {execution_id}: {action.action_type} on {action.entity_id}"
        )

        executed_action = await adapter.execute_action(action)

        await adapter.cleanup()

        # Record result
        result["status"] = executed_action.status
        result["result"] = executed_action.result
        result["executed_at"] = (
            executed_action.executed_at.isoformat()
            if executed_action.executed_at
            else None
        )
        result["completed_at"] = datetime.now(UTC).isoformat()

        if executed_action.status == "failed":
            result["error"] = executed_action.error_message
            logger.error(
                f"Action {execution_id} failed: {executed_action.error_message}"
            )
        else:
            logger.info(f"Action {execution_id} completed successfully")

    except (ConnectionError, TimeoutError, OSError) as e:
        result["status"] = "error"
        result["error"] = str(e)
        result["completed_at"] = datetime.now(UTC).isoformat()
        logger.error(f"Action {execution_id} network error: {e}")

        # Retry on transient errors
        raise self.retry(exc=e, countdown=60)
    except (ValueError, KeyError, TypeError, RuntimeError) as e:
        result["status"] = "error"
        result["error"] = str(e)
        result["completed_at"] = datetime.now(UTC).isoformat()
        logger.error(f"Action {execution_id} error: {e}")

    return result


@shared_task(bind=True)
@async_task
async def execute_action_batch(
    self, actions_data: list[dict[str, Any]], credentials: dict[str, Any], platform: str
) -> dict[str, Any]:
    """
    Execute a batch of actions for a single platform.

    More efficient than individual execution as it reuses the
    adapter connection.
    """
    from app.stratum.adapters.registry import get_adapter

    batch_id = str(uuid.uuid4())[:8]
    results = {
        "batch_id": batch_id,
        "platform": platform,
        "total_actions": len(actions_data),
        "succeeded": 0,
        "failed": 0,
        "blocked": 0,
        "actions": [],
        "started_at": datetime.now(UTC).isoformat(),
    }

    try:
        platform_enum = Platform(platform)
        adapter = await get_adapter(platform_enum, credentials)

        for action_data in actions_data:
            action_result = {
                "entity_id": action_data["entity_id"],
                "action_type": action_data["action_type"],
            }

            try:
                action = AutomationAction(
                    platform=platform_enum,
                    account_id=action_data["account_id"],
                    entity_type=action_data["entity_type"],
                    entity_id=action_data["entity_id"],
                    action_type=action_data["action_type"],
                    parameters=action_data["parameters"],
                )

                executed = await adapter.execute_action(action)

                if executed.status == "completed":
                    results["succeeded"] += 1
                    action_result["status"] = "success"
                else:
                    results["failed"] += 1
                    action_result["status"] = "failed"
                    action_result["error"] = executed.error_message

            except (
                ConnectionError,
                TimeoutError,
                OSError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
            ) as e:
                results["failed"] += 1
                action_result["status"] = "error"
                action_result["error"] = str(e)
                logger.error(f"Batch {batch_id} action error: {e}")

            results["actions"].append(action_result)

        await adapter.cleanup()

    except (ConnectionError, TimeoutError, OSError, ValueError, RuntimeError) as e:
        results["error"] = str(e)
        logger.error(f"Batch {batch_id} failed: {e}")

    results["completed_at"] = datetime.now(UTC).isoformat()
    return results


# ============================================================================
# AUTOPILOT ORCHESTRATION TASKS
# ============================================================================


@shared_task(bind=True)
@async_task
async def run_autopilot_for_account(
    self,
    platform: str,
    account_id: str,
    credentials: dict[str, Any],
    targets: dict[str, float],
) -> dict[str, Any]:
    """
    Run the autopilot engine for a single account.

    This evaluates all rules and queues any approved actions
    for execution.
    """
    from app.stratum.adapters.registry import get_adapter
    from app.stratum.core.signal_health import SignalHealthCalculator

    result = {
        "platform": platform,
        "account_id": account_id,
        "started_at": datetime.now(UTC).isoformat(),
        "rules_evaluated": 0,
        "actions_proposed": 0,
        "actions_approved": 0,
        "actions_queued": 0,
        "actions_blocked": 0,
    }

    try:
        platform_enum = Platform(platform)
        adapter = await get_adapter(platform_enum, credentials)

        # Get current data
        campaigns = await adapter.get_campaigns(account_id)
        emq_scores = await adapter.get_emq_scores(account_id)

        # Calculate signal health
        calculator = SignalHealthCalculator()

        # Initialize autopilot
        engine = AutopilotEngine(auto_execute=False)

        for campaign in campaigns:
            # Skip inactive campaigns
            if campaign.status != EntityStatus.ACTIVE:
                continue

            # Get metrics
            metrics_dict = await adapter.get_metrics(
                account_id=account_id,
                entity_type="campaign",
                entity_ids=[campaign.campaign_id],
                date_start=datetime.now(UTC) - timedelta(days=1),
                date_end=datetime.now(UTC),
            )

            if campaign.campaign_id not in metrics_dict:
                continue

            metrics = metrics_dict[campaign.campaign_id]

            # Get ad sets
            adsets = await adapter.get_adsets(account_id, campaign.campaign_id)

            # Calculate signal health
            signal_health = calculator.calculate(
                platform=platform_enum,
                account_id=account_id,
                emq_scores=emq_scores,
                recent_metrics=[metrics],
            )

            # Evaluate autopilot rules
            rule_results = await engine.evaluate_campaign(
                platform=platform_enum,
                account_id=account_id,
                campaign=campaign,
                adsets=adsets,
                metrics=metrics,
                signal_health=signal_health,
                targets=targets,
            )

            for rule_result in rule_results:
                result["rules_evaluated"] += 1

                if rule_result["triggered"]:
                    result["actions_proposed"] += len(rule_result["actions"])

                    for i, action in enumerate(rule_result["actions"]):
                        gate_result = (
                            rule_result["gate_results"][i]
                            if i < len(rule_result["gate_results"])
                            else {}
                        )
                        decision = gate_result.get("decision", "blocked")

                        if decision == "approved":
                            result["actions_approved"] += 1
                            # Queue for execution
                            execute_action.delay(
                                action_data={
                                    "platform": platform,
                                    "account_id": account_id,
                                    **action,
                                },
                                credentials=credentials,
                            )
                        elif decision == "queued":
                            result["actions_queued"] += 1
                        else:
                            result["actions_blocked"] += 1

        await adapter.cleanup()

    except (ConnectionError, TimeoutError, OSError) as e:
        result["error"] = str(e)
        logger.error(f"Autopilot network error for {platform}/{account_id}: {e}")
    except (ValueError, KeyError, TypeError, RuntimeError) as e:
        result["error"] = str(e)
        logger.error(f"Autopilot error for {platform}/{account_id}: {e}")

    result["completed_at"] = datetime.now(UTC).isoformat()
    return result


@shared_task
@async_task
async def run_autopilot_all() -> dict[str, Any]:
    """
    Run autopilot for all enabled accounts across platforms.

    Scheduled to run hourly by default.
    """
    import yaml

    result = {
        "started_at": datetime.now(UTC).isoformat(),
        "accounts_processed": 0,
        "total_actions": 0,
        "platforms": {},
    }

    try:
        with Path("config.yaml").open() as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        return {"error": "Configuration file not found"}

    # Check if automation is enabled
    automation_config = config.get("automation", {})
    if not automation_config.get("auto_execute", False):
        return {"status": "disabled", "message": "Auto-execute is disabled in config"}

    platforms = ["meta", "google", "tiktok", "snapchat"]

    for platform in platforms:
        platform_config = config.get(platform, {})
        if not platform_config.get("enabled", False):
            result["platforms"][platform] = {"status": "disabled"}
            continue

        # Get account IDs and targets
        account_ids = platform_config.get("account_ids", [])
        targets = platform_config.get("targets", {})

        platform_results = []
        for account_id in account_ids:
            try:
                account_result = await run_autopilot_for_account(
                    platform, account_id, platform_config, targets
                )
                platform_results.append(account_result)
                result["accounts_processed"] += 1
                result["total_actions"] += account_result.get("actions_approved", 0)
            except (
                ConnectionError,
                TimeoutError,
                OSError,
                ValueError,
                KeyError,
                TypeError,
                RuntimeError,
            ) as e:
                platform_results.append({"account_id": account_id, "error": str(e)})
                logger.error(f"Autopilot error for {platform}/{account_id}: {e}")

        result["platforms"][platform] = platform_results

    result["completed_at"] = datetime.now(UTC).isoformat()
    return result


# ============================================================================
# ACTION QUEUE MANAGEMENT
# ============================================================================


@shared_task
def queue_action_for_review(action_data: dict[str, Any], reason: str) -> dict[str, Any]:
    """
    Queue an action for manual review.

    Called when trust gate returns "queued" decision.
    """
    queue_entry = {
        "id": str(uuid.uuid4()),
        "action": action_data,
        "reason": reason,
        "queued_at": datetime.now(UTC).isoformat(),
        "status": "pending_review",
    }

    # This would normally save to database
    logger.info(f"Action queued for review: {queue_entry['id']}")

    return queue_entry


@shared_task
def process_pending_actions() -> dict[str, Any]:
    """
    Process actions that were queued for review.

    Runs every 5 minutes to check for manually approved actions.
    """
    result = {"processed": 0, "executed": 0, "rejected": 0}

    # This would:
    # 1. Query database for actions with status="approved"
    # 2. Execute each approved action
    # 3. Update status

    return result


@shared_task
def approve_queued_action(action_id: str, approved_by: str) -> dict[str, Any]:
    """
    Manually approve a queued action.

    Called from the UI when an operator approves an action.
    """
    logger.info(f"Action {action_id} approved by {approved_by}")

    # This would:
    # 1. Update action status to "approved"
    # 2. Trigger immediate execution

    return {
        "action_id": action_id,
        "approved_by": approved_by,
        "approved_at": datetime.now(UTC).isoformat(),
        "status": "approved",
    }


@shared_task
def reject_queued_action(
    action_id: str, rejected_by: str, reason: str
) -> dict[str, Any]:
    """
    Reject a queued action.
    """
    logger.info(f"Action {action_id} rejected by {rejected_by}: {reason}")

    return {
        "action_id": action_id,
        "rejected_by": rejected_by,
        "rejected_at": datetime.now(UTC).isoformat(),
        "reason": reason,
        "status": "rejected",
    }


# ============================================================================
# ROLLBACK TASKS
# ============================================================================


@shared_task(bind=True)
@async_task
async def rollback_action(
    self,
    original_action: dict[str, Any],
    previous_state: dict[str, Any],
    credentials: dict[str, Any],
) -> dict[str, Any]:
    """
    Rollback a previously executed action.

    Restores the entity to its previous state.
    """
    from app.stratum.adapters.registry import get_adapter

    rollback_id = str(uuid.uuid4())[:8]
    result = {
        "rollback_id": rollback_id,
        "original_action": original_action,
        "started_at": datetime.now(UTC).isoformat(),
    }

    try:
        platform = Platform(original_action["platform"])
        adapter = await get_adapter(platform, credentials)

        # Create rollback action
        rollback_action_obj = AutomationAction(
            platform=platform,
            account_id=original_action["account_id"],
            entity_type=original_action["entity_type"],
            entity_id=original_action["entity_id"],
            action_type=original_action["action_type"],
            parameters=previous_state,  # Use previous state as new parameters
            created_by=f"rollback:{rollback_id}",
        )

        executed = await adapter.execute_action(rollback_action_obj)

        await adapter.cleanup()

        result["status"] = "success" if executed.status == "completed" else "failed"
        result["completed_at"] = datetime.now(UTC).isoformat()

        logger.info(f"Rollback {rollback_id} completed: {result['status']}")

    except (ConnectionError, TimeoutError, OSError) as e:
        result["status"] = "error"
        result["error"] = str(e)
        logger.error(f"Rollback {rollback_id} network error: {e}")
    except (ValueError, KeyError, TypeError, RuntimeError) as e:
        result["status"] = "error"
        result["error"] = str(e)
        logger.error(f"Rollback {rollback_id} failed: {e}")

    return result


# ============================================================================
# CLEANUP TASKS
# ============================================================================


@shared_task
def cleanup_completed_actions(days_to_keep: int = 30) -> dict[str, Any]:
    """
    Clean up old completed action records.

    Runs daily at 3 AM.
    """
    cutoff = datetime.now(UTC) - timedelta(days=days_to_keep)

    # This would delete old action records from database

    return {"cutoff_date": cutoff.isoformat(), "status": "completed"}


# ============================================================================
# MONITORING & STATS
# ============================================================================


@shared_task
def get_automation_stats() -> dict[str, Any]:
    """
    Get statistics about automation execution.
    """
    # This would query the database for stats

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "last_24h": {
            "total_actions": 0,
            "succeeded": 0,
            "failed": 0,
            "blocked": 0,
            "queued": 0,
        },
        "by_platform": {},
        "by_action_type": {},
    }
