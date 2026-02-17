# =============================================================================
# Stratum AI - Apply Actions Queue Task
# =============================================================================
"""
Celery task for processing and applying approved autopilot actions.
Handles safe execution of budget changes, pauses, and other campaign modifications.
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import logging
import json

from celery import shared_task
from sqlalchemy import select, and_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import async_session_factory
from app.models.trust_layer import FactActionsQueue, FactSignalHealthDaily, SignalHealthStatus
from app.autopilot.service import ActionStatus, ActionType, SAFE_ACTIONS
from app.features.flags import get_autopilot_caps, AutopilotLevel
from app.core.websocket import publish_action_status_update


logger = logging.getLogger(__name__)


# =============================================================================
# Platform Executors
# =============================================================================

class PlatformExecutor:
    """Base class for platform-specific action execution."""

    async def execute_action(
        self,
        action_type: str,
        entity_type: str,
        entity_id: str,
        action_details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute an action on the platform.

        Returns:
            Dict with keys: success, before_value, after_value, platform_response, error
        """
        raise NotImplementedError


class MetaExecutor(PlatformExecutor):
    """Executor for Meta (Facebook/Instagram) platform actions."""

    async def execute_action(
        self,
        action_type: str,
        entity_type: str,
        entity_id: str,
        action_details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute action on Meta platform."""
        # In production, this would use the Meta Marketing API
        # For now, simulate successful execution

        logger.info(f"[META] Executing {action_type} on {entity_type} {entity_id}")

        # Simulate API call
        before_value = {"status": "ACTIVE", "daily_budget": 10000}
        after_value = before_value.copy()

        if action_type == ActionType.BUDGET_INCREASE.value:
            amount = action_details.get("amount", 0)
            after_value["daily_budget"] = before_value["daily_budget"] + amount

        elif action_type == ActionType.BUDGET_DECREASE.value:
            amount = action_details.get("amount", 0)
            after_value["daily_budget"] = max(0, before_value["daily_budget"] - amount)

        elif action_type in [ActionType.PAUSE_CAMPAIGN.value, ActionType.PAUSE_ADSET.value, ActionType.PAUSE_CREATIVE.value]:
            after_value["status"] = "PAUSED"

        elif action_type in [ActionType.ENABLE_CAMPAIGN.value, ActionType.ENABLE_ADSET.value, ActionType.ENABLE_CREATIVE.value]:
            after_value["status"] = "ACTIVE"

        return {
            "success": True,
            "before_value": before_value,
            "after_value": after_value,
            "platform_response": {"request_id": "meta_123", "status": "success"},
            "error": None,
        }


class GoogleExecutor(PlatformExecutor):
    """Executor for Google Ads platform actions."""

    async def execute_action(
        self,
        action_type: str,
        entity_type: str,
        entity_id: str,
        action_details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute action on Google Ads platform."""
        logger.info(f"[GOOGLE] Executing {action_type} on {entity_type} {entity_id}")

        before_value = {"status": "ENABLED", "budget_micros": 10000000}
        after_value = before_value.copy()

        if action_type == ActionType.BUDGET_INCREASE.value:
            amount = action_details.get("amount", 0)
            after_value["budget_micros"] = before_value["budget_micros"] + (amount * 1000000)

        elif action_type == ActionType.BUDGET_DECREASE.value:
            amount = action_details.get("amount", 0)
            after_value["budget_micros"] = max(0, before_value["budget_micros"] - (amount * 1000000))

        elif action_type in [ActionType.PAUSE_CAMPAIGN.value, ActionType.PAUSE_ADSET.value]:
            after_value["status"] = "PAUSED"

        elif action_type in [ActionType.ENABLE_CAMPAIGN.value, ActionType.ENABLE_ADSET.value]:
            after_value["status"] = "ENABLED"

        return {
            "success": True,
            "before_value": before_value,
            "after_value": after_value,
            "platform_response": {"operation_name": "operations/123", "status": "DONE"},
            "error": None,
        }


class TikTokExecutor(PlatformExecutor):
    """Executor for TikTok Ads platform actions."""

    async def execute_action(
        self,
        action_type: str,
        entity_type: str,
        entity_id: str,
        action_details: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute action on TikTok Ads platform."""
        logger.info(f"[TIKTOK] Executing {action_type} on {entity_type} {entity_id}")

        before_value = {"operation_status": "ENABLE", "budget": 100.00}
        after_value = before_value.copy()

        if action_type == ActionType.BUDGET_INCREASE.value:
            amount = action_details.get("amount", 0)
            after_value["budget"] = before_value["budget"] + amount

        elif action_type == ActionType.BUDGET_DECREASE.value:
            amount = action_details.get("amount", 0)
            after_value["budget"] = max(0, before_value["budget"] - amount)

        elif action_type in [ActionType.PAUSE_CAMPAIGN.value, ActionType.PAUSE_ADSET.value]:
            after_value["operation_status"] = "DISABLE"

        return {
            "success": True,
            "before_value": before_value,
            "after_value": after_value,
            "platform_response": {"code": 0, "message": "success"},
            "error": None,
        }


# Platform executor registry
PLATFORM_EXECUTORS = {
    "meta": MetaExecutor(),
    "google": GoogleExecutor(),
    "tiktok": TikTokExecutor(),
    "snapchat": MetaExecutor(),  # Use similar executor for now
}


# =============================================================================
# Helper Functions
# =============================================================================

async def check_signal_health(db: AsyncSession, tenant_id: int) -> bool:
    """
    Check if signal health allows action execution.
    Returns True if OK/Risk, False if Degraded/Critical.
    """
    from datetime import date

    result = await db.execute(
        select(FactSignalHealthDaily).where(
            and_(
                FactSignalHealthDaily.tenant_id == tenant_id,
                FactSignalHealthDaily.date == date.today(),
            )
        )
    )
    records = result.scalars().all()

    if not records:
        # No data means we proceed cautiously
        return True

    # Check if any platform has degraded/critical status
    for record in records:
        if record.status in [SignalHealthStatus.DEGRADED, SignalHealthStatus.CRITICAL]:
            return False

    return True


async def get_tenant_autopilot_level(db: AsyncSession, tenant_id: int) -> int:
    """Get the autopilot level for a tenant."""
    from app.features.service import get_tenant_features

    features = await get_tenant_features(db, tenant_id)
    return features.get("autopilot_level", 0)


def validate_action_caps(action_type: str, action_details: Dict[str, Any]) -> tuple[bool, Optional[str]]:
    """
    Validate that an action doesn't exceed caps.

    Returns:
        Tuple of (is_valid, error_message)
    """
    caps = get_autopilot_caps()

    if action_type in [ActionType.BUDGET_INCREASE.value, ActionType.BUDGET_DECREASE.value]:
        amount = action_details.get("amount", 0)
        percentage = action_details.get("percentage", 0)

        if abs(amount) > caps["max_daily_budget_change"]:
            return False, f"Budget change ${amount} exceeds max ${caps['max_daily_budget_change']}"

        if abs(percentage) > caps["max_budget_pct_change"]:
            return False, f"Budget change {percentage}% exceeds max {caps['max_budget_pct_change']}%"

    return True, None


# =============================================================================
# Main Task
# =============================================================================

@shared_task(
    name="tasks.apply_actions_queue",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def apply_actions_queue(self, tenant_id: Optional[int] = None):
    """
    Process and apply approved actions from the queue.

    This task:
    1. Fetches approved actions that haven't been applied yet
    2. Validates signal health before execution
    3. Applies actions to platforms
    4. Records results and audit logs

    Args:
        tenant_id: Optional tenant ID to process (None = all tenants)
    """
    import asyncio

    async def run_apply():
        async with async_session_factory() as db:
            try:
                logger.info(f"Starting action queue processing for tenant_id={tenant_id}")

                # Build query for approved actions
                query = select(FactActionsQueue).where(
                    FactActionsQueue.status == ActionStatus.APPROVED.value
                )

                if tenant_id:
                    query = query.where(FactActionsQueue.tenant_id == tenant_id)

                # Order by creation time
                query = query.order_by(FactActionsQueue.created_at)

                result = await db.execute(query)
                actions = result.scalars().all()

                if not actions:
                    logger.info("No approved actions to process")
                    return {"status": "success", "processed": 0, "failed": 0}

                processed = 0
                failed = 0

                for action in actions:
                    try:
                        # Check signal health for this tenant
                        health_ok = await check_signal_health(db, action.tenant_id)
                        if not health_ok:
                            logger.warning(f"Skipping action {action.id}: Signal health degraded")
                            action.error = "Signal health degraded - action deferred"
                            continue

                        # Parse action details
                        action_details = json.loads(action.action_json) if action.action_json else {}

                        # Validate against caps
                        is_valid, cap_error = validate_action_caps(action.action_type, action_details)
                        if not is_valid:
                            logger.warning(f"Action {action.id} exceeds caps: {cap_error}")
                            action.status = ActionStatus.FAILED.value
                            action.error = cap_error
                            failed += 1
                            continue

                        # Get platform executor
                        executor = PLATFORM_EXECUTORS.get(action.platform)
                        if not executor:
                            logger.error(f"No executor for platform: {action.platform}")
                            action.status = ActionStatus.FAILED.value
                            action.error = f"Unsupported platform: {action.platform}"
                            failed += 1
                            continue

                        # Execute the action
                        exec_result = await executor.execute_action(
                            action_type=action.action_type,
                            entity_type=action.entity_type,
                            entity_id=action.entity_id,
                            action_details=action_details,
                        )

                        if exec_result["success"]:
                            action.status = ActionStatus.APPLIED.value
                            action.applied_at = datetime.now(timezone.utc)
                            action.after_value = json.dumps(exec_result["after_value"])
                            action.platform_response = json.dumps(exec_result["platform_response"])
                            processed += 1

                            logger.info(f"Successfully applied action {action.id}")

                            # Log to audit (in production, write to audit_log table)
                            await log_action_audit(
                                db=db,
                                action=action,
                                result=exec_result,
                            )

                            # Publish WebSocket notification
                            await publish_action_status_update(
                                tenant_id=action.tenant_id,
                                action_id=str(action.id),
                                status="applied",
                                before_value=exec_result.get("before_value"),
                                after_value=exec_result.get("after_value"),
                            )
                        else:
                            action.status = ActionStatus.FAILED.value
                            action.error = exec_result.get("error", "Unknown error")
                            action.platform_response = json.dumps(exec_result.get("platform_response"))
                            failed += 1

                            logger.error(f"Failed to apply action {action.id}: {exec_result.get('error')}")

                            # Publish WebSocket notification for failure
                            await publish_action_status_update(
                                tenant_id=action.tenant_id,
                                action_id=str(action.id),
                                status="failed",
                            )

                    except Exception as e:
                        logger.error(f"Error processing action {action.id}: {str(e)}")
                        action.status = ActionStatus.FAILED.value
                        action.error = str(e)
                        failed += 1

                await db.commit()

                logger.info(f"Action queue processing complete: {processed} applied, {failed} failed")

                return {
                    "status": "success",
                    "processed": processed,
                    "failed": failed,
                }

            except Exception as e:
                logger.error(f"Action queue processing failed: {str(e)}")
                await db.rollback()
                raise self.retry(exc=e)

    return asyncio.get_event_loop().run_until_complete(run_apply())


async def log_action_audit(db: AsyncSession, action: FactActionsQueue, result: Dict[str, Any]):
    """
    Log action execution to audit trail.

    In production, this would write to a dedicated audit_log table.
    """
    audit_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tenant_id": action.tenant_id,
        "action_id": str(action.id),
        "action_type": action.action_type,
        "entity_type": action.entity_type,
        "entity_id": action.entity_id,
        "entity_name": action.entity_name,
        "platform": action.platform,
        "before_value": result.get("before_value"),
        "after_value": result.get("after_value"),
        "approved_by": action.approved_by_user_id,
        "applied_at": action.applied_at.isoformat() if action.applied_at else None,
        "platform_response": result.get("platform_response"),
    }

    logger.info(f"AUDIT: {json.dumps(audit_entry)}")


# =============================================================================
# Scheduled Task
# =============================================================================

@shared_task(name="tasks.schedule_apply_actions_queue")
def schedule_apply_actions_queue():
    """
    Scheduled task to process action queue.
    Should run every 5 minutes to pick up newly approved actions.
    """
    return apply_actions_queue.delay()


# =============================================================================
# Single Action Execution
# =============================================================================

@shared_task(
    name="tasks.apply_single_action",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def apply_single_action(self, action_id: str, user_id: Optional[int] = None):
    """
    Apply a single action immediately.

    Used for immediate execution when approval is granted.

    Args:
        action_id: UUID of the action to apply
        user_id: ID of user triggering the execution
    """
    import asyncio
    from uuid import UUID

    async def run_single():
        async with async_session_factory() as db:
            try:
                uuid_id = UUID(action_id)

                result = await db.execute(
                    select(FactActionsQueue).where(FactActionsQueue.id == uuid_id)
                )
                action = result.scalar_one_or_none()

                if not action:
                    return {"status": "error", "error": "Action not found"}

                if action.status != ActionStatus.APPROVED.value:
                    return {"status": "error", "error": f"Action status is {action.status}, expected approved"}

                # Check signal health
                health_ok = await check_signal_health(db, action.tenant_id)
                if not health_ok:
                    return {"status": "error", "error": "Signal health degraded"}

                # Parse and validate
                action_details = json.loads(action.action_json) if action.action_json else {}
                is_valid, cap_error = validate_action_caps(action.action_type, action_details)

                if not is_valid:
                    action.status = ActionStatus.FAILED.value
                    action.error = cap_error
                    await db.commit()
                    return {"status": "error", "error": cap_error}

                # Execute
                executor = PLATFORM_EXECUTORS.get(action.platform)
                if not executor:
                    action.status = ActionStatus.FAILED.value
                    action.error = f"Unsupported platform: {action.platform}"
                    await db.commit()
                    return {"status": "error", "error": action.error}

                exec_result = await executor.execute_action(
                    action_type=action.action_type,
                    entity_type=action.entity_type,
                    entity_id=action.entity_id,
                    action_details=action_details,
                )

                if exec_result["success"]:
                    action.status = ActionStatus.APPLIED.value
                    action.applied_at = datetime.now(timezone.utc)
                    action.applied_by_user_id = user_id
                    action.after_value = json.dumps(exec_result["after_value"])
                    action.platform_response = json.dumps(exec_result["platform_response"])

                    await log_action_audit(db, action, exec_result)
                    await db.commit()

                    # Publish WebSocket notification
                    await publish_action_status_update(
                        tenant_id=action.tenant_id,
                        action_id=action_id,
                        status="applied",
                        before_value=exec_result.get("before_value"),
                        after_value=exec_result.get("after_value"),
                    )

                    return {"status": "success", "action_id": action_id}
                else:
                    action.status = ActionStatus.FAILED.value
                    action.error = exec_result.get("error", "Unknown error")
                    action.platform_response = json.dumps(exec_result.get("platform_response"))
                    await db.commit()

                    # Publish WebSocket notification for failure
                    await publish_action_status_update(
                        tenant_id=action.tenant_id,
                        action_id=action_id,
                        status="failed",
                    )

                    return {"status": "error", "error": action.error}

            except Exception as e:
                logger.error(f"Single action execution failed: {str(e)}")
                await db.rollback()
                raise self.retry(exc=e)

    return asyncio.get_event_loop().run_until_complete(run_single())
