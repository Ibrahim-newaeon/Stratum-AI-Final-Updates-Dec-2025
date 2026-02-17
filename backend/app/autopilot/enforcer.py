# =============================================================================
# Stratum AI - Autopilot Enforcer Service
# =============================================================================
"""
Enforcement layer for autopilot restrictions.
Implements budget/ROAS threshold enforcement with configurable modes.

Enforcement Modes:
- advisory: Warn only, no blocking
- soft_block: Warn + require confirmation to proceed
- hard_block: Prevent action via API, log override attempts
"""

from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


# =============================================================================
# Enforcement Types
# =============================================================================

class EnforcementMode(str, Enum):
    """Autopilot enforcement modes."""
    ADVISORY = "advisory"      # Warn only, no blocking
    SOFT_BLOCK = "soft_block"  # Warn + require confirmation to proceed
    HARD_BLOCK = "hard_block"  # Prevent action via API, log override attempts


class ViolationType(str, Enum):
    """Types of enforcement rule violations."""
    BUDGET_EXCEEDED = "budget_exceeded"
    ROAS_BELOW_THRESHOLD = "roas_below_threshold"
    DAILY_SPEND_LIMIT = "daily_spend_limit"
    CAMPAIGN_PAUSE_REQUIRED = "campaign_pause_required"
    FREQUENCY_CAP_EXCEEDED = "frequency_cap_exceeded"


class InterventionAction(str, Enum):
    """Actions taken by enforcer."""
    WARNED = "warned"
    BLOCKED = "blocked"
    AUTO_PAUSED = "auto_paused"
    OVERRIDE_LOGGED = "override_logged"
    NOTIFICATION_SENT = "notification_sent"


# =============================================================================
# Enforcement Settings Model
# =============================================================================

class EnforcementRule(BaseModel):
    """Single enforcement rule configuration."""
    rule_id: str
    rule_type: ViolationType
    threshold_value: float
    enforcement_mode: EnforcementMode = EnforcementMode.ADVISORY
    enabled: bool = True
    description: Optional[str] = None


class EnforcementSettings(BaseModel):
    """Tenant-level enforcement configuration."""
    tenant_id: int
    enforcement_enabled: bool = True  # Kill switch
    default_mode: EnforcementMode = EnforcementMode.ADVISORY

    # Budget thresholds
    max_daily_budget: Optional[float] = None
    max_campaign_budget: Optional[float] = None
    budget_increase_limit_pct: float = 30.0

    # ROAS thresholds
    min_roas_threshold: float = 1.0
    roas_lookback_days: int = 7

    # Frequency settings
    max_budget_changes_per_day: int = 5
    min_hours_between_changes: int = 4

    # Custom rules
    rules: List[EnforcementRule] = Field(default_factory=list)

    class Config:
        use_enum_values = True


# =============================================================================
# Enforcement Result
# =============================================================================

@dataclass
class EnforcementResult:
    """Result of enforcement check."""
    allowed: bool
    mode: EnforcementMode
    violations: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    requires_confirmation: bool = False
    confirmation_token: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "mode": self.mode.value if isinstance(self.mode, EnforcementMode) else self.mode,
            "violations": self.violations,
            "warnings": self.warnings,
            "requires_confirmation": self.requires_confirmation,
            "confirmation_token": self.confirmation_token,
        }


@dataclass
class InterventionLog:
    """Log entry for enforcement intervention."""
    tenant_id: int
    timestamp: datetime
    action_type: str
    entity_type: str
    entity_id: str
    violation_type: ViolationType
    intervention_action: InterventionAction
    enforcement_mode: EnforcementMode
    details: Dict[str, Any]
    user_id: Optional[int] = None
    override_reason: Optional[str] = None


# =============================================================================
# Autopilot Enforcer Service
# =============================================================================

class AutopilotEnforcer:
    """
    Enforcement service for autopilot restrictions.

    Checks proposed actions against configured thresholds and rules,
    then enforces based on the configured mode (advisory/soft_block/hard_block).
    """

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db
        self._settings_cache: Dict[int, EnforcementSettings] = {}
        self._pending_confirmations: Dict[str, Dict[str, Any]] = {}

    async def get_settings(self, tenant_id: int) -> EnforcementSettings:
        """Get enforcement settings for tenant."""
        if tenant_id in self._settings_cache:
            return self._settings_cache[tenant_id]

        # TODO: Load from database when table exists
        # For now, return defaults
        settings = EnforcementSettings(tenant_id=tenant_id)
        self._settings_cache[tenant_id] = settings
        return settings

    async def update_settings(
        self,
        tenant_id: int,
        updates: Dict[str, Any],
    ) -> EnforcementSettings:
        """Update enforcement settings for tenant."""
        settings = await self.get_settings(tenant_id)

        for key, value in updates.items():
            if hasattr(settings, key):
                setattr(settings, key, value)

        self._settings_cache[tenant_id] = settings
        # TODO: Persist to database

        return settings

    async def check_action(
        self,
        tenant_id: int,
        action_type: str,
        entity_type: str,
        entity_id: str,
        proposed_value: Dict[str, Any],
        current_value: Optional[Dict[str, Any]] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> EnforcementResult:
        """
        Check if proposed action is allowed under enforcement rules.

        Args:
            tenant_id: Tenant ID
            action_type: Type of action (budget_increase, pause_campaign, etc.)
            entity_type: Type of entity (campaign, adset, creative)
            entity_id: Platform entity ID
            proposed_value: New value being set
            current_value: Current value before change
            metrics: Current performance metrics (ROAS, spend, etc.)

        Returns:
            EnforcementResult with allowed status and any violations
        """
        settings = await self.get_settings(tenant_id)

        # Check kill switch
        if not settings.enforcement_enabled:
            return EnforcementResult(
                allowed=True,
                mode=EnforcementMode.ADVISORY,
                warnings=["Enforcement is disabled for this tenant"],
            )

        violations = []
        warnings = []

        # Check budget rules
        if action_type in ["budget_increase", "budget_decrease", "set_budget"]:
            budget_violations = await self._check_budget_rules(
                settings, action_type, proposed_value, current_value
            )
            violations.extend(budget_violations)

        # Check ROAS threshold
        if metrics and "roas" in metrics:
            roas_violations = await self._check_roas_rules(
                settings, metrics["roas"], entity_type, entity_id
            )
            violations.extend(roas_violations)

        # Check frequency limits
        freq_violations = await self._check_frequency_rules(
            settings, tenant_id, entity_id
        )
        violations.extend(freq_violations)

        # Check custom rules
        for rule in settings.rules:
            if rule.enabled:
                rule_violations = await self._check_custom_rule(
                    rule, action_type, proposed_value, current_value, metrics
                )
                violations.extend(rule_violations)

        # Determine result based on violations and mode
        if not violations:
            return EnforcementResult(
                allowed=True,
                mode=settings.default_mode,
            )

        # Get strictest mode from violations
        strictest_mode = self._get_strictest_mode(violations, settings.default_mode)

        for v in violations:
            warnings.append(v.get("message", str(v.get("type"))))

        if strictest_mode == EnforcementMode.ADVISORY:
            return EnforcementResult(
                allowed=True,
                mode=strictest_mode,
                violations=violations,
                warnings=warnings,
            )

        elif strictest_mode == EnforcementMode.SOFT_BLOCK:
            # Generate confirmation token
            import uuid
            token = str(uuid.uuid4())
            self._pending_confirmations[token] = {
                "tenant_id": tenant_id,
                "action_type": action_type,
                "entity_id": entity_id,
                "violations": violations,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": (datetime.now(timezone.utc).replace(hour=23, minute=59)).isoformat(),
            }

            return EnforcementResult(
                allowed=False,
                mode=strictest_mode,
                violations=violations,
                warnings=warnings,
                requires_confirmation=True,
                confirmation_token=token,
            )

        else:  # HARD_BLOCK
            # Log the blocked attempt
            await self._log_intervention(
                tenant_id=tenant_id,
                action_type=action_type,
                entity_type=entity_type,
                entity_id=entity_id,
                violation_type=violations[0].get("type", ViolationType.BUDGET_EXCEEDED),
                intervention_action=InterventionAction.BLOCKED,
                enforcement_mode=strictest_mode,
                details={"violations": violations, "proposed_value": proposed_value},
            )

            return EnforcementResult(
                allowed=False,
                mode=strictest_mode,
                violations=violations,
                warnings=warnings,
            )

    async def confirm_action(
        self,
        tenant_id: int,
        confirmation_token: str,
        user_id: int,
        override_reason: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """
        Confirm a soft-blocked action.

        Args:
            tenant_id: Tenant ID
            confirmation_token: Token from EnforcementResult
            user_id: User confirming the action
            override_reason: Optional reason for override

        Returns:
            Tuple of (success, error_message)
        """
        if confirmation_token not in self._pending_confirmations:
            return False, "Invalid or expired confirmation token"

        confirmation = self._pending_confirmations[confirmation_token]

        if confirmation["tenant_id"] != tenant_id:
            return False, "Token does not belong to this tenant"

        # Log the override
        await self._log_intervention(
            tenant_id=tenant_id,
            action_type=confirmation["action_type"],
            entity_type="campaign",
            entity_id=confirmation["entity_id"],
            violation_type=ViolationType.BUDGET_EXCEEDED,
            intervention_action=InterventionAction.OVERRIDE_LOGGED,
            enforcement_mode=EnforcementMode.SOFT_BLOCK,
            details={"confirmation": confirmation},
            user_id=user_id,
            override_reason=override_reason,
        )

        # Remove used token
        del self._pending_confirmations[confirmation_token]

        return True, None

    async def auto_pause_campaign(
        self,
        tenant_id: int,
        campaign_id: str,
        reason: str,
        metrics: Dict[str, Any],
    ) -> bool:
        """
        Auto-pause a campaign that violates ROAS/budget thresholds.

        Returns True if campaign was paused.
        """
        settings = await self.get_settings(tenant_id)

        if not settings.enforcement_enabled:
            return False

        if settings.default_mode != EnforcementMode.HARD_BLOCK:
            return False

        # Log the auto-pause
        await self._log_intervention(
            tenant_id=tenant_id,
            action_type="auto_pause",
            entity_type="campaign",
            entity_id=campaign_id,
            violation_type=ViolationType.CAMPAIGN_PAUSE_REQUIRED,
            intervention_action=InterventionAction.AUTO_PAUSED,
            enforcement_mode=EnforcementMode.HARD_BLOCK,
            details={"reason": reason, "metrics": metrics},
        )

        logger.info(f"Auto-paused campaign {campaign_id} for tenant {tenant_id}: {reason}")

        # TODO: Actually pause the campaign via platform API
        return True

    async def set_kill_switch(
        self,
        tenant_id: int,
        enabled: bool,
        user_id: int,
        reason: Optional[str] = None,
    ) -> EnforcementSettings:
        """
        Enable/disable enforcement kill switch for tenant.

        Args:
            tenant_id: Tenant ID
            enabled: True to enable enforcement, False to disable
            user_id: User making the change
            reason: Optional reason for change
        """
        settings = await self.update_settings(
            tenant_id,
            {"enforcement_enabled": enabled},
        )

        # Log the change
        await self._log_intervention(
            tenant_id=tenant_id,
            action_type="kill_switch",
            entity_type="tenant",
            entity_id=str(tenant_id),
            violation_type=ViolationType.BUDGET_EXCEEDED,
            intervention_action=InterventionAction.WARNED,
            enforcement_mode=settings.default_mode,
            details={"enabled": enabled, "reason": reason},
            user_id=user_id,
        )

        return settings

    async def get_intervention_log(
        self,
        tenant_id: int,
        days: int = 30,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get intervention audit log for tenant."""
        # TODO: Query from database
        # For now, return empty list
        return []

    # =========================================================================
    # Private Methods
    # =========================================================================

    async def _check_budget_rules(
        self,
        settings: EnforcementSettings,
        action_type: str,
        proposed_value: Dict[str, Any],
        current_value: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Check budget-related rules."""
        violations = []

        proposed_budget = proposed_value.get("budget", 0)
        current_budget = (current_value or {}).get("budget", 0)

        # Check max campaign budget
        if settings.max_campaign_budget and proposed_budget > settings.max_campaign_budget:
            violations.append({
                "type": ViolationType.BUDGET_EXCEEDED.value,
                "message": f"Budget ${proposed_budget:.2f} exceeds max ${settings.max_campaign_budget:.2f}",
                "threshold": settings.max_campaign_budget,
                "actual": proposed_budget,
                "mode": settings.default_mode.value,
            })

        # Check budget increase limit
        if action_type == "budget_increase" and current_budget > 0:
            increase_pct = ((proposed_budget - current_budget) / current_budget) * 100
            if increase_pct > settings.budget_increase_limit_pct:
                violations.append({
                    "type": ViolationType.BUDGET_EXCEEDED.value,
                    "message": f"Budget increase {increase_pct:.1f}% exceeds limit {settings.budget_increase_limit_pct}%",
                    "threshold": settings.budget_increase_limit_pct,
                    "actual": increase_pct,
                    "mode": settings.default_mode.value,
                })

        return violations

    async def _check_roas_rules(
        self,
        settings: EnforcementSettings,
        current_roas: float,
        entity_type: str,
        entity_id: str,
    ) -> List[Dict[str, Any]]:
        """Check ROAS threshold rules."""
        violations = []

        if current_roas < settings.min_roas_threshold:
            violations.append({
                "type": ViolationType.ROAS_BELOW_THRESHOLD.value,
                "message": f"ROAS {current_roas:.2f} is below minimum threshold {settings.min_roas_threshold:.2f}",
                "threshold": settings.min_roas_threshold,
                "actual": current_roas,
                "mode": settings.default_mode.value,
                "entity_type": entity_type,
                "entity_id": entity_id,
            })

        return violations

    async def _check_frequency_rules(
        self,
        settings: EnforcementSettings,
        tenant_id: int,
        entity_id: str,
    ) -> List[Dict[str, Any]]:
        """Check action frequency rules."""
        # TODO: Query recent actions from database
        # For now, assume no violations
        return []

    async def _check_custom_rule(
        self,
        rule: EnforcementRule,
        action_type: str,
        proposed_value: Dict[str, Any],
        current_value: Optional[Dict[str, Any]],
        metrics: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Check a custom enforcement rule."""
        violations = []

        # Evaluate rule based on type
        if rule.rule_type == ViolationType.BUDGET_EXCEEDED:
            budget = proposed_value.get("budget", 0)
            if budget > rule.threshold_value:
                violations.append({
                    "type": rule.rule_type.value,
                    "message": rule.description or f"Custom rule violation: {rule.rule_id}",
                    "threshold": rule.threshold_value,
                    "actual": budget,
                    "mode": rule.enforcement_mode.value,
                    "rule_id": rule.rule_id,
                })

        elif rule.rule_type == ViolationType.ROAS_BELOW_THRESHOLD:
            roas = (metrics or {}).get("roas", 0)
            if roas < rule.threshold_value:
                violations.append({
                    "type": rule.rule_type.value,
                    "message": rule.description or f"ROAS below threshold for rule {rule.rule_id}",
                    "threshold": rule.threshold_value,
                    "actual": roas,
                    "mode": rule.enforcement_mode.value,
                    "rule_id": rule.rule_id,
                })

        return violations

    def _get_strictest_mode(
        self,
        violations: List[Dict[str, Any]],
        default_mode: EnforcementMode,
    ) -> EnforcementMode:
        """Get the strictest enforcement mode from violations."""
        modes = [v.get("mode", default_mode.value) for v in violations]

        if EnforcementMode.HARD_BLOCK.value in modes:
            return EnforcementMode.HARD_BLOCK
        elif EnforcementMode.SOFT_BLOCK.value in modes:
            return EnforcementMode.SOFT_BLOCK
        else:
            return EnforcementMode.ADVISORY

    async def _log_intervention(
        self,
        tenant_id: int,
        action_type: str,
        entity_type: str,
        entity_id: str,
        violation_type: ViolationType,
        intervention_action: InterventionAction,
        enforcement_mode: EnforcementMode,
        details: Dict[str, Any],
        user_id: Optional[int] = None,
        override_reason: Optional[str] = None,
    ) -> None:
        """Log an enforcement intervention."""
        log_entry = InterventionLog(
            tenant_id=tenant_id,
            timestamp=datetime.now(timezone.utc),
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            violation_type=violation_type,
            intervention_action=intervention_action,
            enforcement_mode=enforcement_mode,
            details=details,
            user_id=user_id,
            override_reason=override_reason,
        )

        logger.info(
            f"Enforcement intervention: tenant={tenant_id} action={intervention_action.value} "
            f"entity={entity_type}/{entity_id} mode={enforcement_mode.value}"
        )

        # TODO: Persist to database
        # TODO: Send notification if configured


# =============================================================================
# Notification Service Integration
# =============================================================================

async def send_enforcement_notification(
    tenant_id: int,
    intervention: InterventionLog,
    notification_channels: List[str] = None,
) -> bool:
    """
    Send notification for enforcement intervention.

    Args:
        tenant_id: Tenant ID
        intervention: Intervention log entry
        notification_channels: List of channels (email, slack, webhook)

    Returns:
        True if notification sent successfully
    """
    channels = notification_channels or ["email"]

    # TODO: Implement actual notification sending
    logger.info(
        f"Sending enforcement notification to tenant {tenant_id} "
        f"via {channels}: {intervention.intervention_action.value}"
    )

    return True
