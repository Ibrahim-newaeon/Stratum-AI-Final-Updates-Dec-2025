# =============================================================================
# Stratum AI - Rules Engine Tasks
# =============================================================================
"""
Background tasks for automation rules evaluation and execution.

Security: Beat-scheduled tasks use distributed locks to prevent
duplicate execution across multiple Celery workers.
"""

from datetime import UTC, datetime
from typing import Any

from celery import shared_task
from celery.utils.log import get_task_logger
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SyncSessionLocal
from app.models import (
    Campaign,
    Rule,
    RuleExecution,
    RuleOperator,
    RuleStatus,
)
from app.workers.locks import with_distributed_lock
from app.workers.tasks.helpers import publish_event

logger = get_task_logger(__name__)


@shared_task(bind=True)
def evaluate_rules(self, tenant_id: int, rule_id: int):
    """
    Evaluate a specific rule against matching campaigns.

    Args:
        tenant_id: Tenant ID for isolation
        rule_id: Rule ID to evaluate
    """
    logger.info(f"Evaluating rule {rule_id} for tenant {tenant_id}")

    with SyncSessionLocal() as db:
        rule = db.execute(
            select(Rule).where(
                Rule.id == rule_id,
                Rule.tenant_id == tenant_id,
                Rule.status == RuleStatus.ACTIVE,
            )
        ).scalar_one_or_none()

        if not rule:
            logger.warning(f"Rule {rule_id} not found or inactive")
            return {"status": "not_found"}

        # Get campaigns matching rule scope
        campaigns = (
            db.execute(
                select(Campaign).where(
                    Campaign.tenant_id == tenant_id,
                    Campaign.is_deleted == False,
                )
            )
            .scalars()
            .all()
        )

        matches = 0
        executions = 0

        for campaign in campaigns:
            # Evaluate rule conditions
            result = _evaluate_condition(rule, campaign)

            if result["matched"]:
                matches += 1

                # Execute rule action
                action_result = _execute_action(rule, campaign, db)

                # Log execution (columns per RuleExecution model:
                # triggered/condition_result/action_result, not the old
                # triggered_at/condition_values/action_taken kwargs).
                execution = RuleExecution(
                    tenant_id=tenant_id,
                    rule_id=rule.id,
                    campaign_id=campaign.id,
                    triggered=True,
                    condition_result=result["values"],
                    action_result=action_result,
                )
                db.add(execution)
                executions += 1

        db.commit()

        # Publish event if any actions taken
        if executions > 0:
            publish_event(
                tenant_id,
                "rule_triggered",
                {
                    "rule_id": rule_id,
                    "rule_name": rule.name,
                    "matches": matches,
                    "executions": executions,
                },
            )

        logger.info(f"Rule {rule_id}: {matches} matches, {executions} executions")
        return {"matches": matches, "executions": executions}


# Explicit name: this module was split out of the old app/workers/tasks.py;
# without it the auto-generated name gains the submodule segment and the
# beat schedule's task reference silently dispatches to nothing.
@shared_task(name="app.workers.tasks.evaluate_all_rules")
@with_distributed_lock(timeout=900)  # 15 minute lock timeout
def evaluate_all_rules():
    """
    Evaluate all active rules across all tenants.
    Scheduled by Celery beat (typically every 15 minutes).

    Uses distributed lock to prevent duplicate execution across workers.
    """
    logger.info("Starting evaluation of all rules")

    with SyncSessionLocal() as db:
        # Get all active rules
        rules = (
            db.execute(
                select(Rule).where(
                    Rule.status == RuleStatus.ACTIVE,
                    Rule.is_deleted == False,
                )
            )
            .scalars()
            .all()
        )

        task_count = 0
        for rule in rules:
            evaluate_rules.delay(rule.tenant_id, rule.id)
            task_count += 1

    logger.info(f"Queued {task_count} rule evaluation tasks")
    return {"tasks_queued": task_count}


def _evaluate_condition(rule: Rule, campaign: Campaign) -> dict[str, Any]:
    """
    Evaluate a rule's condition against a campaign.

    The Rule model stores a single flat condition
    (``condition_field`` / ``condition_operator`` / ``condition_value``), not a
    ``conditions`` list — reading the latter raised AttributeError and killed
    the beat task. This mirrors the canonical async ``RulesEngine`` so the
    scheduled evaluator and the API dry-run agree.

    Returns:
        Dict with 'matched' bool and 'values' dict describing the evaluation.
    """
    field = rule.condition_field
    operator = rule.condition_operator
    expected_raw = rule.condition_value

    actual = _get_field_value(campaign, field)
    if actual is None:
        return {
            "matched": False,
            "values": {"field": field, "reason": "field not found or null"},
        }

    try:
        expected = _parse_value(expected_raw, type(actual))
    except (ValueError, TypeError) as e:
        return {
            "matched": False,
            "values": {"field": field, "reason": f"invalid condition value: {e}"},
        }

    matched = _compare_values(actual, operator, expected)
    return {
        "matched": matched,
        "values": {
            "field": field,
            "operator": getattr(operator, "value", operator),
            "expected": expected,
            "actual": actual,
        },
    }


def _get_field_value(campaign: Campaign, field: str) -> Any:
    """Resolve a metric value from a campaign, including computed metrics."""
    if hasattr(campaign, field):
        return getattr(campaign, field)

    computed = {
        "spend": lambda c: c.total_spend_cents / 100,
        "revenue": lambda c: c.revenue_cents / 100,
        "cpc": lambda c: (
            (c.total_spend_cents / c.clicks / 100) if c.clicks > 0 else None
        ),
        "cpm": lambda c: (
            (c.total_spend_cents / c.impressions * 1000 / 100)
            if c.impressions > 0
            else None
        ),
        "cpa": lambda c: (
            (c.total_spend_cents / c.conversions / 100) if c.conversions > 0 else None
        ),
        "conversion_rate": lambda c: (
            (c.conversions / c.clicks * 100) if c.clicks > 0 else None
        ),
    }
    if field in computed:
        return computed[field](campaign)
    return None


def _parse_value(value: str, target_type: type) -> Any:
    """Parse a string condition value to match the actual value's type."""
    if target_type == float:
        return float(value)
    elif target_type == int:
        return int(float(value))
    elif target_type == bool:
        return value.lower() in ("true", "1", "yes")
    return value


def _compare_values(actual: Any, operator: RuleOperator, expected: Any) -> bool:
    """Compare actual vs expected using the rule operator."""
    if operator == RuleOperator.EQUALS:
        return actual == expected
    elif operator == RuleOperator.NOT_EQUALS:
        return actual != expected
    elif operator == RuleOperator.GREATER_THAN:
        return actual > expected
    elif operator == RuleOperator.LESS_THAN:
        return actual < expected
    elif operator == RuleOperator.GREATER_THAN_OR_EQUAL:
        return actual >= expected
    elif operator == RuleOperator.LESS_THAN_OR_EQUAL:
        return actual <= expected
    elif operator == RuleOperator.CONTAINS:
        return str(expected) in str(actual)
    elif operator == RuleOperator.IN:
        return actual in expected
    return False


def _execute_action(rule: Rule, campaign: Campaign, db: Session) -> dict[str, Any]:
    """
    Execute rule action on a campaign.

    Returns:
        Dict with action details and result
    """
    action_type = rule.action_type
    action_config = rule.action_config or {}

    result = {
        "action": action_type,
        "success": True,
        "timestamp": datetime.now(UTC).isoformat(),
    }

    try:
        if action_type == "apply_label":
            labels = campaign.labels or []
            new_label = action_config.get("label")
            if new_label and new_label not in labels:
                campaign.labels = labels + [new_label]
                result["label_added"] = new_label

        elif action_type == "pause_campaign":
            result["previous_status"] = campaign.status
            campaign.status = "paused"

        elif action_type == "send_alert":
            # Queue alert notification
            from app.workers.tasks.whatsapp import send_whatsapp_message

            if action_config.get("whatsapp"):
                send_whatsapp_message.delay(
                    tenant_id=campaign.tenant_id,
                    template_name="rule_alert",
                    to_number=action_config.get("phone"),
                    variables={
                        "rule_name": rule.name,
                        "campaign_name": campaign.name,
                    },
                )
            result["alert_sent"] = True

        elif action_type == "adjust_budget":
            adjustment = action_config.get("adjustment_percent", 0)
            if campaign.daily_budget_cents:
                old_budget = campaign.daily_budget_cents
                campaign.daily_budget_cents = int(old_budget * (1 + adjustment / 100))
                result["budget_change"] = {
                    "old": old_budget,
                    "new": campaign.daily_budget_cents,
                }

    except (ValueError, TypeError, KeyError, AttributeError) as e:
        result["success"] = False
        result["error"] = str(e)
        logger.error(f"Action execution failed: {e}")

    return result
