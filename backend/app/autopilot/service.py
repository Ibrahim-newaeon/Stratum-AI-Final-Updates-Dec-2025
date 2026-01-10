# =============================================================================
# Stratum AI - Autopilot Service
# =============================================================================
"""
Service for managing autopilot actions and execution.
Handles action queuing, approval workflow, and platform execution.
"""

from datetime import datetime, date, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
import json

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update
from uuid import UUID

from app.models.trust_layer import FactActionsQueue
from app.features.flags import AutopilotLevel, get_autopilot_caps


class ActionStatus(str, Enum):
    """Action lifecycle statuses."""
    QUEUED = "queued"
    APPROVED = "approved"
    APPLIED = "applied"
    FAILED = "failed"
    DISMISSED = "dismissed"


class ActionType(str, Enum):
    """Types of autopilot actions."""
    BUDGET_INCREASE = "budget_increase"
    BUDGET_DECREASE = "budget_decrease"
    PAUSE_CAMPAIGN = "pause_campaign"
    PAUSE_ADSET = "pause_adset"
    PAUSE_CREATIVE = "pause_creative"
    ENABLE_CAMPAIGN = "enable_campaign"
    ENABLE_ADSET = "enable_adset"
    ENABLE_CREATIVE = "enable_creative"
    BID_INCREASE = "bid_increase"
    BID_DECREASE = "bid_decrease"


# Safe actions that can be auto-executed at autopilot level 1
SAFE_ACTIONS = {
    ActionType.BUDGET_DECREASE,
    ActionType.PAUSE_ADSET,
    ActionType.PAUSE_CREATIVE,
    ActionType.BID_DECREASE,
}


class AutopilotService:
    """Service for autopilot action management."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def queue_action(
        self,
        tenant_id: int,
        action_type: str,
        entity_type: str,
        entity_id: str,
        entity_name: str,
        platform: str,
        action_json: Dict[str, Any],
        before_value: Optional[Dict[str, Any]] = None,
        created_by_user_id: Optional[int] = None,
    ) -> FactActionsQueue:
        """
        Queue a new action for processing.

        Args:
            tenant_id: Tenant ID
            action_type: Type of action (budget_increase, pause, etc.)
            entity_type: Type of entity (campaign, adset, creative)
            entity_id: Platform entity ID
            entity_name: Human-readable entity name
            platform: Ad platform (meta, google, etc.)
            action_json: Full action details
            before_value: Current value before change
            created_by_user_id: User who triggered the action (optional)

        Returns:
            Created action record
        """
        action = FactActionsQueue(
            tenant_id=tenant_id,
            date=date.today(),
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            entity_name=entity_name,
            platform=platform,
            action_json=json.dumps(action_json),
            before_value=json.dumps(before_value) if before_value else None,
            status=ActionStatus.QUEUED.value,
            created_by_user_id=created_by_user_id,
        )
        self.db.add(action)
        await self.db.commit()
        await self.db.refresh(action)
        return action

    async def get_queued_actions(
        self,
        tenant_id: int,
        target_date: Optional[date] = None,
        status: Optional[str] = None,
        platform: Optional[str] = None,
        limit: int = 100,
    ) -> List[FactActionsQueue]:
        """Get queued actions for a tenant."""
        query = select(FactActionsQueue).where(
            FactActionsQueue.tenant_id == tenant_id
        )

        if target_date:
            query = query.where(FactActionsQueue.date == target_date)

        if status:
            query = query.where(FactActionsQueue.status == status)

        if platform:
            query = query.where(FactActionsQueue.platform == platform)

        query = query.order_by(FactActionsQueue.created_at.desc()).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_action_by_id(
        self,
        action_id: UUID,
        tenant_id: int,
    ) -> Optional[FactActionsQueue]:
        """Get a specific action by ID."""
        result = await self.db.execute(
            select(FactActionsQueue).where(
                and_(
                    FactActionsQueue.id == action_id,
                    FactActionsQueue.tenant_id == tenant_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def approve_action(
        self,
        action_id: UUID,
        tenant_id: int,
        user_id: int,
    ) -> Optional[FactActionsQueue]:
        """Approve an action for execution."""
        action = await self.get_action_by_id(action_id, tenant_id)
        if not action:
            return None

        if action.status != ActionStatus.QUEUED.value:
            return None

        action.status = ActionStatus.APPROVED.value
        action.approved_by_user_id = user_id
        action.approved_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(action)
        return action

    async def approve_all_queued(
        self,
        tenant_id: int,
        user_id: int,
        action_ids: Optional[List[UUID]] = None,
    ) -> int:
        """Approve multiple actions at once."""
        query = (
            update(FactActionsQueue)
            .where(
                and_(
                    FactActionsQueue.tenant_id == tenant_id,
                    FactActionsQueue.status == ActionStatus.QUEUED.value,
                )
            )
            .values(
                status=ActionStatus.APPROVED.value,
                approved_by_user_id=user_id,
                approved_at=datetime.now(timezone.utc),
            )
        )

        if action_ids:
            query = query.where(FactActionsQueue.id.in_(action_ids))

        result = await self.db.execute(query)
        await self.db.commit()
        return result.rowcount

    async def dismiss_action(
        self,
        action_id: UUID,
        tenant_id: int,
        user_id: int,
    ) -> Optional[FactActionsQueue]:
        """Dismiss an action (won't be executed)."""
        action = await self.get_action_by_id(action_id, tenant_id)
        if not action:
            return None

        if action.status != ActionStatus.QUEUED.value:
            return None

        action.status = ActionStatus.DISMISSED.value
        action.approved_by_user_id = user_id
        action.approved_at = datetime.now(timezone.utc)
        await self.db.commit()
        await self.db.refresh(action)
        return action

    async def mark_applied(
        self,
        action_id: UUID,
        after_value: Dict[str, Any],
        platform_response: Dict[str, Any],
        user_id: Optional[int] = None,
    ) -> Optional[FactActionsQueue]:
        """Mark an action as successfully applied."""
        result = await self.db.execute(
            select(FactActionsQueue).where(FactActionsQueue.id == action_id)
        )
        action = result.scalar_one_or_none()
        if not action:
            return None

        action.status = ActionStatus.APPLIED.value
        action.applied_at = datetime.now(timezone.utc)
        action.applied_by_user_id = user_id
        action.after_value = json.dumps(after_value)
        action.platform_response = json.dumps(platform_response)
        await self.db.commit()
        await self.db.refresh(action)
        return action

    async def mark_failed(
        self,
        action_id: UUID,
        error: str,
        platform_response: Optional[Dict[str, Any]] = None,
    ) -> Optional[FactActionsQueue]:
        """Mark an action as failed."""
        result = await self.db.execute(
            select(FactActionsQueue).where(FactActionsQueue.id == action_id)
        )
        action = result.scalar_one_or_none()
        if not action:
            return None

        action.status = ActionStatus.FAILED.value
        action.error = error
        if platform_response:
            action.platform_response = json.dumps(platform_response)
        await self.db.commit()
        await self.db.refresh(action)
        return action

    async def get_action_summary(
        self,
        tenant_id: int,
        days: int = 7,
    ) -> Dict[str, Any]:
        """Get summary of actions over the past N days."""
        start_date = date.today() - timedelta(days=days)

        # Status counts
        status_query = (
            select(
                FactActionsQueue.status,
                func.count(FactActionsQueue.id).label("count"),
            )
            .where(
                and_(
                    FactActionsQueue.tenant_id == tenant_id,
                    FactActionsQueue.date >= start_date,
                )
            )
            .group_by(FactActionsQueue.status)
        )
        status_result = await self.db.execute(status_query)
        status_counts = {row.status: row.count for row in status_result}

        # Action type counts
        type_query = (
            select(
                FactActionsQueue.action_type,
                func.count(FactActionsQueue.id).label("count"),
            )
            .where(
                and_(
                    FactActionsQueue.tenant_id == tenant_id,
                    FactActionsQueue.date >= start_date,
                )
            )
            .group_by(FactActionsQueue.action_type)
        )
        type_result = await self.db.execute(type_query)
        type_counts = {row.action_type: row.count for row in type_result}

        # Platform counts
        platform_query = (
            select(
                FactActionsQueue.platform,
                func.count(FactActionsQueue.id).label("count"),
            )
            .where(
                and_(
                    FactActionsQueue.tenant_id == tenant_id,
                    FactActionsQueue.date >= start_date,
                )
            )
            .group_by(FactActionsQueue.platform)
        )
        platform_result = await self.db.execute(platform_query)
        platform_counts = {row.platform: row.count for row in platform_result}

        return {
            "days": days,
            "start_date": start_date.isoformat(),
            "status_counts": status_counts,
            "type_counts": type_counts,
            "platform_counts": platform_counts,
            "total": sum(status_counts.values()),
            "pending_approval": status_counts.get(ActionStatus.QUEUED.value, 0),
            "success_rate": (
                status_counts.get(ActionStatus.APPLIED.value, 0)
                / max(
                    status_counts.get(ActionStatus.APPLIED.value, 0)
                    + status_counts.get(ActionStatus.FAILED.value, 0),
                    1,
                )
            ) * 100,
        }

    def can_auto_execute(
        self,
        autopilot_level: int,
        action_type: str,
        action_details: Dict[str, Any],
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if an action can be auto-executed based on autopilot level.

        Returns:
            Tuple of (can_execute, reason_if_blocked)
        """
        if autopilot_level == AutopilotLevel.SUGGEST_ONLY:
            return False, "Autopilot is in suggest-only mode"

        if autopilot_level == AutopilotLevel.APPROVAL_REQUIRED:
            return False, "Approval required for all actions"

        # Level 1: Guarded auto
        if autopilot_level == AutopilotLevel.GUARDED_AUTO:
            caps = get_autopilot_caps()

            # Check if action type is safe
            try:
                action_enum = ActionType(action_type)
                if action_enum not in SAFE_ACTIONS:
                    return False, f"{action_type} requires approval"
            except ValueError:
                return False, f"Unknown action type: {action_type}"

            # Check budget caps for budget actions
            if action_type in [ActionType.BUDGET_INCREASE.value, ActionType.BUDGET_DECREASE.value]:
                amount = action_details.get("amount", 0)
                percentage = action_details.get("percentage", 0)

                if abs(amount) > caps["max_daily_budget_change"]:
                    return False, f"Budget change exceeds ${caps['max_daily_budget_change']} cap"

                if abs(percentage) > caps["max_budget_pct_change"]:
                    return False, f"Budget change exceeds {caps['max_budget_pct_change']}% cap"

            return True, None

        return False, "Unknown autopilot level"


def process_recommendations_to_actions(
    recommendations: Dict[str, Any],
    autopilot_level: int,
) -> List[Dict[str, Any]]:
    """
    Convert recommendations engine output to action queue items.

    Args:
        recommendations: Output from RecommendationsEngine
        autopilot_level: Current autopilot level

    Returns:
        List of action items ready for queuing
    """
    actions = []

    # Process budget actions
    for action in recommendations.get("actions", []):
        action_type = action.get("type")
        if action_type in ["increase", "decrease"]:
            actions.append({
                "action_type": f"budget_{action_type}",
                "entity_type": "campaign",
                "entity_id": action.get("entity_id"),
                "entity_name": action.get("entity_name"),
                "action_json": {
                    "amount": action.get("amount"),
                    "reason": action.get("reason"),
                },
                "requires_approval": autopilot_level >= AutopilotLevel.APPROVAL_REQUIRED,
            })

    # Process recommendations
    for rec in recommendations.get("recommendations", []):
        rec_type = rec.get("type")

        if rec_type == "creative_refresh":
            actions.append({
                "action_type": ActionType.PAUSE_CREATIVE.value,
                "entity_type": "creative",
                "entity_id": rec.get("entity_id"),
                "entity_name": rec.get("entity_name"),
                "action_json": {
                    "reason": rec.get("description"),
                    "fatigue_score": rec.get("expected_impact", {}).get("fatigue_score"),
                },
                "requires_approval": autopilot_level >= AutopilotLevel.APPROVAL_REQUIRED,
            })

        elif rec_type == "fix_campaign":
            # Underperforming campaigns may need budget reduction or pause
            actions.append({
                "action_type": ActionType.BUDGET_DECREASE.value,
                "entity_type": "campaign",
                "entity_id": rec.get("entity_id"),
                "entity_name": rec.get("entity_name"),
                "action_json": {
                    "reason": rec.get("description"),
                    "scaling_score": rec.get("expected_impact", {}).get("scaling_score"),
                    "recommendations": rec.get("action_params", {}).get("recommendations", []),
                },
                "requires_approval": autopilot_level >= AutopilotLevel.APPROVAL_REQUIRED,
            })

    return actions
