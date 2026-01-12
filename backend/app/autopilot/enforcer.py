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

from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
import json
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


# =============================================================================
# Module-level cache for fallback when DB not available (unit tests)
# =============================================================================
_global_settings_cache: Dict[int, "EnforcementSettings"] = {}
_global_pending_confirmations: Dict[str, Dict[str, Any]] = {}


def clear_enforcement_cache(tenant_id: Optional[int] = None) -> None:
    """
    Clear the enforcement settings cache.

    Args:
        tenant_id: If provided, only clear cache for this tenant.
                   If None, clear all cached settings.

    For use in testing to ensure clean state between tests.
    """
    global _global_settings_cache, _global_pending_confirmations
    if tenant_id is not None:
        _global_settings_cache.pop(tenant_id, None)
    else:
        _global_settings_cache.clear()
        _global_pending_confirmations.clear()


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
# Enforcement Settings Model (Pydantic for API layer)
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

    Supports both database persistence and in-memory fallback for testing.
    """

    def __init__(self, db: Optional[AsyncSession] = None):
        self.db = db

    async def get_settings(self, tenant_id: int) -> EnforcementSettings:
        """Get enforcement settings for tenant."""
        # Try database first if available
        if self.db is not None:
            return await self._get_settings_from_db(tenant_id)

        # Fallback to in-memory cache (for unit tests)
        global _global_settings_cache
        if tenant_id in _global_settings_cache:
            return _global_settings_cache[tenant_id]

        settings = EnforcementSettings(tenant_id=tenant_id)
        _global_settings_cache[tenant_id] = settings
        return settings

    async def _get_settings_from_db(self, tenant_id: int) -> EnforcementSettings:
        """Load settings from database."""
        from app.models.autopilot import (
            TenantEnforcementSettings,
            TenantEnforcementRule,
            EnforcementMode as DBEnforcementMode,
            ViolationType as DBViolationType,
        )

        # Query settings with rules
        result = await self.db.execute(
            select(TenantEnforcementSettings)
            .where(TenantEnforcementSettings.tenant_id == tenant_id)
        )
        db_settings = result.scalar_one_or_none()

        if db_settings is None:
            # Return defaults without persisting (will be created on first update)
            return EnforcementSettings(tenant_id=tenant_id)

        # Load rules separately to avoid lazy loading issues
        rules_result = await self.db.execute(
            select(TenantEnforcementRule)
            .where(TenantEnforcementRule.settings_id == db_settings.id)
        )
        db_rules = rules_result.scalars().all()

        # Convert DB model to Pydantic model
        rules = []
        for db_rule in db_rules:
            rules.append(EnforcementRule(
                rule_id=db_rule.rule_id,
                rule_type=ViolationType(db_rule.rule_type.value if hasattr(db_rule.rule_type, 'value') else db_rule.rule_type),
                threshold_value=db_rule.threshold_value,
                enforcement_mode=EnforcementMode(db_rule.enforcement_mode.value if hasattr(db_rule.enforcement_mode, 'value') else db_rule.enforcement_mode),
                enabled=db_rule.enabled,
                description=db_rule.description,
            ))

        default_mode_value = db_settings.default_mode.value if hasattr(db_settings.default_mode, 'value') else db_settings.default_mode

        return EnforcementSettings(
            tenant_id=db_settings.tenant_id,
            enforcement_enabled=db_settings.enforcement_enabled,
            default_mode=EnforcementMode(default_mode_value),
            max_daily_budget=db_settings.max_daily_budget,
            max_campaign_budget=db_settings.max_campaign_budget,
            budget_increase_limit_pct=db_settings.budget_increase_limit_pct,
            min_roas_threshold=db_settings.min_roas_threshold,
            roas_lookback_days=db_settings.roas_lookback_days,
            max_budget_changes_per_day=db_settings.max_budget_changes_per_day,
            min_hours_between_changes=db_settings.min_hours_between_changes,
            rules=rules,
        )

    async def update_settings(
        self,
        tenant_id: int,
        updates: Dict[str, Any],
    ) -> EnforcementSettings:
        """Update enforcement settings for tenant."""
        # Try database first if available
        if self.db is not None:
            return await self._update_settings_in_db(tenant_id, updates)

        # Fallback to in-memory cache (for unit tests)
        global _global_settings_cache
        settings = await self.get_settings(tenant_id)

        for key, value in updates.items():
            if hasattr(settings, key):
                setattr(settings, key, value)

        _global_settings_cache[tenant_id] = settings
        return settings

    async def _update_settings_in_db(
        self,
        tenant_id: int,
        updates: Dict[str, Any],
    ) -> EnforcementSettings:
        """Update settings in database."""
        from app.models.autopilot import (
            TenantEnforcementSettings,
            TenantEnforcementRule,
            EnforcementMode as DBEnforcementMode,
            ViolationType as DBViolationType,
        )

        # Get or create settings
        result = await self.db.execute(
            select(TenantEnforcementSettings)
            .where(TenantEnforcementSettings.tenant_id == tenant_id)
        )
        db_settings = result.scalar_one_or_none()

        created_new = False
        if db_settings is None:
            db_settings = TenantEnforcementSettings(tenant_id=tenant_id)
            self.db.add(db_settings)
            created_new = True
            # Flush to get the ID for rules
            await self.db.flush()

        # Update scalar fields
        scalar_fields = [
            'enforcement_enabled', 'max_daily_budget', 'max_campaign_budget',
            'budget_increase_limit_pct', 'min_roas_threshold', 'roas_lookback_days',
            'max_budget_changes_per_day', 'min_hours_between_changes'
        ]
        for field_name in scalar_fields:
            if field_name in updates:
                setattr(db_settings, field_name, updates[field_name])

        # Handle default_mode enum
        if 'default_mode' in updates:
            mode = updates['default_mode']
            if isinstance(mode, EnforcementMode):
                db_settings.default_mode = DBEnforcementMode(mode.value)
            elif isinstance(mode, str):
                db_settings.default_mode = DBEnforcementMode(mode)
            else:
                db_settings.default_mode = mode

        # Handle rules update
        if 'rules' in updates and db_settings.id is not None:
            # Clear existing rules
            await self.db.execute(
                delete(TenantEnforcementRule)
                .where(TenantEnforcementRule.settings_id == db_settings.id)
            )

            # Add new rules
            for rule in updates['rules']:
                if isinstance(rule, EnforcementRule):
                    db_rule = TenantEnforcementRule(
                        settings_id=db_settings.id,
                        tenant_id=tenant_id,
                        rule_id=rule.rule_id,
                        rule_type=DBViolationType(rule.rule_type.value if hasattr(rule.rule_type, 'value') else rule.rule_type),
                        threshold_value=rule.threshold_value,
                        enforcement_mode=DBEnforcementMode(rule.enforcement_mode.value if hasattr(rule.enforcement_mode, 'value') else rule.enforcement_mode),
                        enabled=rule.enabled,
                        description=rule.description,
                    )
                    self.db.add(db_rule)

        await self.db.commit()

        return await self._get_settings_from_db(tenant_id)

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
            token = str(uuid.uuid4())

            if self.db is not None:
                await self._store_confirmation_token(
                    tenant_id=tenant_id,
                    token=token,
                    action_type=action_type,
                    entity_id=entity_id,
                    violations=violations,
                )
            else:
                # Fallback to in-memory
                global _global_pending_confirmations
                _global_pending_confirmations[token] = {
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

    async def _store_confirmation_token(
        self,
        tenant_id: int,
        token: str,
        action_type: str,
        entity_id: str,
        violations: List[Dict[str, Any]],
    ) -> None:
        """Store confirmation token in database."""
        from app.models.autopilot import PendingConfirmationToken

        now = datetime.now(timezone.utc)
        expires_at = now.replace(hour=23, minute=59, second=59)

        db_token = PendingConfirmationToken(
            tenant_id=tenant_id,
            token=token,
            action_type=action_type,
            entity_id=entity_id,
            violations=violations,
            created_at=now,
            expires_at=expires_at,
        )
        self.db.add(db_token)
        await self.db.commit()

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
        if self.db is not None:
            return await self._confirm_action_from_db(
                tenant_id, confirmation_token, user_id, override_reason
            )

        # Fallback to in-memory
        global _global_pending_confirmations
        if confirmation_token not in _global_pending_confirmations:
            return False, "Invalid or expired confirmation token"

        confirmation = _global_pending_confirmations[confirmation_token]

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
        del _global_pending_confirmations[confirmation_token]

        return True, None

    async def _confirm_action_from_db(
        self,
        tenant_id: int,
        confirmation_token: str,
        user_id: int,
        override_reason: Optional[str] = None,
    ) -> Tuple[bool, Optional[str]]:
        """Confirm action using database."""
        from app.models.autopilot import PendingConfirmationToken

        # Find token
        result = await self.db.execute(
            select(PendingConfirmationToken)
            .where(PendingConfirmationToken.token == confirmation_token)
        )
        db_token = result.scalar_one_or_none()

        if db_token is None:
            return False, "Invalid or expired confirmation token"

        if db_token.tenant_id != tenant_id:
            return False, "Token does not belong to this tenant"

        if db_token.expires_at < datetime.now(timezone.utc):
            # Clean up expired token
            await self.db.delete(db_token)
            await self.db.commit()
            return False, "Confirmation token has expired"

        # Log the override
        await self._log_intervention(
            tenant_id=tenant_id,
            action_type=db_token.action_type,
            entity_type="campaign",
            entity_id=db_token.entity_id,
            violation_type=ViolationType.BUDGET_EXCEEDED,
            intervention_action=InterventionAction.OVERRIDE_LOGGED,
            enforcement_mode=EnforcementMode.SOFT_BLOCK,
            details={"violations": db_token.violations},
            user_id=user_id,
            override_reason=override_reason,
        )

        # Delete used token
        await self.db.delete(db_token)
        await self.db.commit()

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
        if self.db is None:
            return []

        from app.models.autopilot import EnforcementAuditLog

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        result = await self.db.execute(
            select(EnforcementAuditLog)
            .where(EnforcementAuditLog.tenant_id == tenant_id)
            .where(EnforcementAuditLog.timestamp >= cutoff)
            .order_by(EnforcementAuditLog.timestamp.desc())
            .limit(limit)
        )
        logs = result.scalars().all()

        return [log.to_dict() for log in logs]

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
                "mode": settings.default_mode.value if hasattr(settings.default_mode, 'value') else settings.default_mode,
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
                    "mode": settings.default_mode.value if hasattr(settings.default_mode, 'value') else settings.default_mode,
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
                "mode": settings.default_mode.value if hasattr(settings.default_mode, 'value') else settings.default_mode,
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
        if self.db is None:
            return []

        from app.models.autopilot import EnforcementAuditLog

        # Check actions in last N hours
        cutoff = datetime.now(timezone.utc) - timedelta(hours=settings.min_hours_between_changes)

        result = await self.db.execute(
            select(EnforcementAuditLog)
            .where(EnforcementAuditLog.tenant_id == tenant_id)
            .where(EnforcementAuditLog.entity_id == entity_id)
            .where(EnforcementAuditLog.timestamp >= cutoff)
        )
        recent_actions = result.scalars().all()

        violations = []
        if len(recent_actions) >= settings.max_budget_changes_per_day:
            violations.append({
                "type": ViolationType.FREQUENCY_CAP_EXCEEDED.value,
                "message": f"Too many changes in last {settings.min_hours_between_changes} hours ({len(recent_actions)}/{settings.max_budget_changes_per_day})",
                "threshold": settings.max_budget_changes_per_day,
                "actual": len(recent_actions),
                "mode": settings.default_mode.value if hasattr(settings.default_mode, 'value') else settings.default_mode,
            })

        return violations

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
                    "mode": rule.enforcement_mode.value if hasattr(rule.enforcement_mode, 'value') else rule.enforcement_mode,
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
                    "mode": rule.enforcement_mode.value if hasattr(rule.enforcement_mode, 'value') else rule.enforcement_mode,
                    "rule_id": rule.rule_id,
                })

        return violations

    def _get_strictest_mode(
        self,
        violations: List[Dict[str, Any]],
        default_mode: EnforcementMode,
    ) -> EnforcementMode:
        """Get the strictest enforcement mode from violations."""
        modes = [v.get("mode", default_mode.value if hasattr(default_mode, 'value') else default_mode) for v in violations]

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

        # Persist to database if available
        if self.db is not None:
            await self._persist_intervention_log(log_entry)

    async def _persist_intervention_log(self, log_entry: InterventionLog) -> None:
        """Persist intervention log to database."""
        from app.models.autopilot import (
            EnforcementAuditLog,
            ViolationType as DBViolationType,
            InterventionAction as DBInterventionAction,
            EnforcementMode as DBEnforcementMode,
        )

        # Convert violation_type
        vtype = log_entry.violation_type
        if isinstance(vtype, str):
            db_violation_type = DBViolationType(vtype)
        else:
            db_violation_type = DBViolationType(vtype.value)

        # Convert intervention_action
        iaction = log_entry.intervention_action
        if isinstance(iaction, str):
            db_intervention_action = DBInterventionAction(iaction)
        else:
            db_intervention_action = DBInterventionAction(iaction.value)

        # Convert enforcement_mode
        emode = log_entry.enforcement_mode
        if isinstance(emode, str):
            db_enforcement_mode = DBEnforcementMode(emode)
        else:
            db_enforcement_mode = DBEnforcementMode(emode.value)

        db_log = EnforcementAuditLog(
            tenant_id=log_entry.tenant_id,
            timestamp=log_entry.timestamp,
            action_type=log_entry.action_type,
            entity_type=log_entry.entity_type,
            entity_id=log_entry.entity_id,
            violation_type=db_violation_type,
            intervention_action=db_intervention_action,
            enforcement_mode=db_enforcement_mode,
            details=log_entry.details,
            user_id=log_entry.user_id,
            override_reason=log_entry.override_reason,
        )
        self.db.add(db_log)
        await self.db.commit()


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
