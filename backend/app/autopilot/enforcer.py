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

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field
import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, func, update
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field

from app.models.autopilot import (
    TenantEnforcementSettings as TenantEnforcementSettingsDB,
    TenantEnforcementRule as TenantEnforcementRuleDB,
    EnforcementAuditLog as EnforcementAuditLogDB,
    PendingConfirmationToken as PendingConfirmationTokenDB,
    EnforcementMode as DBEnforcementMode,
    ViolationType as DBViolationType,
    InterventionAction as DBInterventionAction,
)
from app.services.email_service import get_email_service
from app.services.notifications.slack_service import SlackNotificationService


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
        """Get enforcement settings for tenant.

        Uses in-memory cache as fast-path. On cache miss, loads from the
        database. If no database row exists yet, creates one with defaults
        and persists it.

        Args:
            tenant_id: Tenant ID to retrieve settings for.

        Returns:
            EnforcementSettings Pydantic model for the tenant.
        """
        # Fast-path: return from cache
        if tenant_id in self._settings_cache:
            return self._settings_cache[tenant_id]

        # Load from database
        if self.db is not None:
            result = await self.db.execute(
                select(TenantEnforcementSettingsDB)
                .options(selectinload(TenantEnforcementSettingsDB.rules))
                .where(TenantEnforcementSettingsDB.tenant_id == tenant_id)
            )
            db_settings = result.scalars().first()

            if db_settings is not None:
                # Map custom rules from DB rows to Pydantic models
                rules: List[EnforcementRule] = []
                for db_rule in (db_settings.rules or []):
                    rules.append(EnforcementRule(
                        rule_id=db_rule.rule_id,
                        rule_type=ViolationType(db_rule.rule_type.value
                                                if isinstance(db_rule.rule_type, DBViolationType)
                                                else db_rule.rule_type),
                        threshold_value=db_rule.threshold_value,
                        enforcement_mode=EnforcementMode(
                            db_rule.enforcement_mode.value
                            if isinstance(db_rule.enforcement_mode, DBEnforcementMode)
                            else db_rule.enforcement_mode
                        ),
                        enabled=db_rule.enabled,
                        description=db_rule.description,
                    ))

                settings = EnforcementSettings(
                    tenant_id=tenant_id,
                    enforcement_enabled=db_settings.enforcement_enabled,
                    default_mode=EnforcementMode(
                        db_settings.default_mode
                        if isinstance(db_settings.default_mode, DBEnforcementMode)
                        else db_settings.default_mode
                    ),
                    max_daily_budget=db_settings.max_daily_budget,
                    max_campaign_budget=db_settings.max_campaign_budget,
                    budget_increase_limit_pct=db_settings.budget_increase_limit_pct,
                    min_roas_threshold=db_settings.min_roas_threshold,
                    roas_lookback_days=db_settings.roas_lookback_days,
                    max_budget_changes_per_day=db_settings.max_budget_changes_per_day,
                    min_hours_between_changes=db_settings.min_hours_between_changes,
                    rules=rules,
                )
                self._settings_cache[tenant_id] = settings
                return settings

            # No row exists -- create with defaults and persist
            new_db_settings = TenantEnforcementSettingsDB(
                tenant_id=tenant_id,
                enforcement_enabled=True,
                default_mode=DBEnforcementMode.ADVISORY,
                budget_increase_limit_pct=30.0,
                min_roas_threshold=1.0,
                roas_lookback_days=7,
                max_budget_changes_per_day=5,
                min_hours_between_changes=4,
            )
            self.db.add(new_db_settings)
            await self.db.flush()

        # Return defaults (either just persisted or no DB session)
        settings = EnforcementSettings(tenant_id=tenant_id)
        self._settings_cache[tenant_id] = settings
        return settings

    async def update_settings(
        self,
        tenant_id: int,
        updates: Dict[str, Any],
    ) -> EnforcementSettings:
        """Update enforcement settings for tenant.

        Applies updates to both the in-memory Pydantic model and the
        corresponding database row.

        Args:
            tenant_id: Tenant whose settings to update.
            updates: Dictionary of field names to new values. Only fields
                     present on EnforcementSettings are applied.

        Returns:
            Updated EnforcementSettings Pydantic model.
        """
        settings = await self.get_settings(tenant_id)

        # Apply updates to Pydantic model
        for key, value in updates.items():
            if hasattr(settings, key):
                setattr(settings, key, value)

        self._settings_cache[tenant_id] = settings

        # Persist to database
        if self.db is not None:
            # Map Pydantic field names to DB column updates
            db_field_map = {
                "enforcement_enabled",
                "default_mode",
                "max_daily_budget",
                "max_campaign_budget",
                "budget_increase_limit_pct",
                "min_roas_threshold",
                "roas_lookback_days",
                "max_budget_changes_per_day",
                "min_hours_between_changes",
            }
            db_updates: Dict[str, Any] = {}
            for key, value in updates.items():
                if key in db_field_map:
                    if key == "default_mode":
                        db_updates[key] = DBEnforcementMode(value) if isinstance(value, str) else value
                    else:
                        db_updates[key] = value

            # Load or create the DB settings row
            result = await self.db.execute(
                select(TenantEnforcementSettingsDB)
                .options(selectinload(TenantEnforcementSettingsDB.rules))
                .where(TenantEnforcementSettingsDB.tenant_id == tenant_id)
            )
            db_settings = result.scalars().first()

            if db_updates:
                if db_settings is not None:
                    for col, val in db_updates.items():
                        setattr(db_settings, col, val)
                    await self.db.flush()
                else:
                    # Create a new row if missing (edge case)
                    new_row = TenantEnforcementSettingsDB(
                        tenant_id=tenant_id,
                        **db_updates,
                    )
                    self.db.add(new_row)
                    await self.db.flush()
                    db_settings = new_row

            # Sync custom rules to DB if "rules" was in the updates
            if "rules" in updates and db_settings is not None:
                # Remove existing rules
                for existing_rule in list(db_settings.rules or []):
                    await self.db.delete(existing_rule)
                await self.db.flush()

                # Add new rules from the Pydantic models
                for rule in updates["rules"]:
                    rule_dict = rule.dict() if hasattr(rule, 'dict') else rule
                    db_rule = TenantEnforcementRuleDB(
                        settings_id=db_settings.id,
                        tenant_id=tenant_id,
                        rule_id=rule_dict["rule_id"],
                        rule_type=DBViolationType(rule_dict["rule_type"]),
                        threshold_value=rule_dict["threshold_value"],
                        enforcement_mode=DBEnforcementMode(
                            rule_dict.get("enforcement_mode", "advisory")
                        ),
                        enabled=rule_dict.get("enabled", True),
                        description=rule_dict.get("description"),
                    )
                    self.db.add(db_rule)
                await self.db.flush()

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
            import secrets as _secrets
            token = _secrets.token_hex(32)
            now = datetime.now(timezone.utc)
            expires = now + timedelta(seconds=3600)

            confirmation_data = {
                "tenant_id": tenant_id,
                "action_type": action_type,
                "entity_id": entity_id,
                "violations": violations,
                "created_at": now.isoformat(),
                "expires_at": expires.isoformat(),
            }
            self._pending_confirmations[token] = confirmation_data

            # Persist to database so it survives across requests
            if self.db is not None:
                db_token = PendingConfirmationTokenDB(
                    tenant_id=tenant_id,
                    token=token,
                    action_type=action_type,
                    entity_id=entity_id,
                    violations=json.loads(json.dumps(violations, default=str)),
                    created_at=now,
                    expires_at=expires,
                )
                self.db.add(db_token)
                await self.db.flush()

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
        # Try in-memory first, then fall back to database
        confirmation = self._pending_confirmations.get(confirmation_token)

        if confirmation is None and self.db is not None:
            # Look up from database
            result = await self.db.execute(
                select(PendingConfirmationTokenDB).where(
                    PendingConfirmationTokenDB.token == confirmation_token,
                    PendingConfirmationTokenDB.expires_at >= datetime.now(timezone.utc),
                )
            )
            db_token = result.scalars().first()
            if db_token is not None:
                confirmation = {
                    "tenant_id": db_token.tenant_id,
                    "action_type": db_token.action_type,
                    "entity_id": db_token.entity_id,
                    "violations": db_token.violations,
                }
                # Clean up the DB token after use
                await self.db.delete(db_token)
                await self.db.flush()

        if confirmation is None:
            return False, "Invalid or expired confirmation token"

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

        # Remove from in-memory cache if present
        self._pending_confirmations.pop(confirmation_token, None)

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

        Delegates the actual pause operation to the appropriate platform
        executor from the ``PLATFORM_EXECUTORS`` registry.  The platform
        is inferred from ``metrics["platform"]``; if not present the
        method tries each registered executor.

        The call is wrapped in a try/except so that executor failures
        do not break the enforcement flow -- the intervention is still
        logged and the method returns False on failure.

        Returns True if campaign was paused successfully.
        """
        settings = await self.get_settings(tenant_id)

        if not settings.enforcement_enabled:
            return False

        if settings.default_mode != EnforcementMode.HARD_BLOCK:
            return False

        # Log the auto-pause intervention regardless of execution outcome
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

        # Delegate to the platform executor for the actual pause
        try:
            from app.tasks.apply_actions_queue import PLATFORM_EXECUTORS

            platform = metrics.get("platform")

            if platform and platform in PLATFORM_EXECUTORS:
                executor = PLATFORM_EXECUTORS[platform]
            else:
                # If platform is unknown, try meta as a sensible default
                # since it is the most common platform
                executor = PLATFORM_EXECUTORS.get("meta")
                if executor is None:
                    logger.warning(
                        f"No executor available for platform={platform} "
                        f"when auto-pausing campaign {campaign_id}"
                    )
                    return False

            exec_result = await executor.execute_action(
                action_type="pause_campaign",
                entity_type="campaign",
                entity_id=campaign_id,
                action_details=metrics,
            )

            if exec_result.get("success"):
                logger.info(
                    f"Auto-paused campaign {campaign_id} for tenant {tenant_id}: {reason}"
                )
                return True
            else:
                logger.error(
                    f"Platform executor failed to auto-pause campaign {campaign_id}: "
                    f"{exec_result.get('error', 'unknown error')}"
                )
                return False

        except Exception as exc:
            # Do not let executor failures break the enforcement flow
            logger.error(
                f"Error auto-pausing campaign {campaign_id} via platform executor: {exc}",
                exc_info=True,
            )
            return False

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
        """Get intervention audit log for tenant.

        Queries the enforcement_audit_logs table for entries within the
        specified lookback window, ordered by most recent first.

        Args:
            tenant_id: Tenant ID to query.
            days: Number of days to look back (default 30).
            limit: Maximum number of entries to return (default 100).

        Returns:
            List of intervention log dictionaries.
        """
        if self.db is None:
            return []

        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)

        result = await self.db.execute(
            select(EnforcementAuditLogDB)
            .where(
                EnforcementAuditLogDB.tenant_id == tenant_id,
                EnforcementAuditLogDB.timestamp >= cutoff,
            )
            .order_by(EnforcementAuditLogDB.timestamp.desc())
            .limit(limit)
        )
        rows = result.scalars().all()

        return [row.to_dict() for row in rows]

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
                "mode": settings.default_mode,
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
                    "mode": settings.default_mode,
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
                "mode": settings.default_mode,
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
        """Check action frequency rules against recent DB records.

        Queries the enforcement_audit_logs table to count how many
        budget-related interventions have been logged for this entity
        today and checks the minimum time gap between changes.

        Args:
            settings: Current enforcement settings for the tenant.
            tenant_id: Tenant ID.
            entity_id: Platform entity ID being acted upon.

        Returns:
            List of violation dictionaries if frequency caps exceeded.
        """
        violations: List[Dict[str, Any]] = []

        if self.db is None:
            return violations

        from datetime import timedelta

        now = datetime.now(timezone.utc)

        # --- Check max budget changes per day ---
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

        count_result = await self.db.execute(
            select(func.count(EnforcementAuditLogDB.id))
            .where(
                EnforcementAuditLogDB.tenant_id == tenant_id,
                EnforcementAuditLogDB.entity_id == entity_id,
                EnforcementAuditLogDB.timestamp >= day_start,
                EnforcementAuditLogDB.action_type.in_([
                    "budget_increase", "budget_decrease", "set_budget",
                ]),
            )
        )
        daily_count: int = count_result.scalar_one()

        if daily_count >= settings.max_budget_changes_per_day:
            violations.append({
                "type": ViolationType.FREQUENCY_CAP_EXCEEDED.value,
                "message": (
                    f"Entity {entity_id} has reached the daily budget change limit "
                    f"({daily_count}/{settings.max_budget_changes_per_day})"
                ),
                "threshold": settings.max_budget_changes_per_day,
                "actual": daily_count,
                "mode": settings.default_mode
                        if isinstance(settings.default_mode, EnforcementMode)
                        else settings.default_mode,
            })

        # --- Check minimum hours between changes ---
        min_gap_cutoff = now - timedelta(hours=settings.min_hours_between_changes)

        recent_result = await self.db.execute(
            select(EnforcementAuditLogDB.timestamp)
            .where(
                EnforcementAuditLogDB.tenant_id == tenant_id,
                EnforcementAuditLogDB.entity_id == entity_id,
                EnforcementAuditLogDB.timestamp >= min_gap_cutoff,
                EnforcementAuditLogDB.action_type.in_([
                    "budget_increase", "budget_decrease", "set_budget",
                ]),
            )
            .order_by(EnforcementAuditLogDB.timestamp.desc())
            .limit(1)
        )
        last_change_row = recent_result.scalars().first()

        if last_change_row is not None:
            hours_since = (now - last_change_row).total_seconds() / 3600
            violations.append({
                "type": ViolationType.FREQUENCY_CAP_EXCEEDED.value,
                "message": (
                    f"Last budget change for entity {entity_id} was {hours_since:.1f}h ago; "
                    f"minimum gap is {settings.min_hours_between_changes}h"
                ),
                "threshold": settings.min_hours_between_changes,
                "actual": round(hours_since, 2),
                "mode": settings.default_mode
                        if isinstance(settings.default_mode, EnforcementMode)
                        else settings.default_mode,
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
        default_mode,
    ) -> EnforcementMode:
        """Get the strictest enforcement mode from violations."""
        default_val = default_mode.value if hasattr(default_mode, 'value') else default_mode
        modes = [v.get("mode", default_val) for v in violations]

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
        """Log an enforcement intervention to the database.

        Creates an in-memory InterventionLog for structured logging, then
        persists the entry to the enforcement_audit_logs table. Also
        triggers a notification for blocking interventions.

        Args:
            tenant_id: Tenant ID.
            action_type: Type of action being checked.
            entity_type: Entity type (campaign, adset, etc.).
            entity_id: Platform entity ID.
            violation_type: Which rule was violated.
            intervention_action: What the enforcer did.
            enforcement_mode: Active enforcement mode.
            details: Structured context dictionary.
            user_id: Optional user who triggered the action.
            override_reason: Optional reason for an override.
        """
        now = datetime.now(timezone.utc)

        log_entry = InterventionLog(
            tenant_id=tenant_id,
            timestamp=now,
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

        _action_val = intervention_action.value if hasattr(intervention_action, 'value') else intervention_action
        _mode_val = enforcement_mode.value if hasattr(enforcement_mode, 'value') else enforcement_mode
        logger.info(
            f"Enforcement intervention: tenant={tenant_id} action={_action_val} "
            f"entity={entity_type}/{entity_id} mode={_mode_val}"
        )

        # Persist to database
        if self.db is not None:
            # Serialise details to ensure JSONB-safe content
            safe_details = json.loads(json.dumps(details, default=str))

            db_log = EnforcementAuditLogDB(
                tenant_id=tenant_id,
                timestamp=now,
                action_type=action_type,
                entity_type=entity_type,
                entity_id=entity_id,
                violation_type=DBViolationType(violation_type.value)
                    if isinstance(violation_type, ViolationType)
                    else DBViolationType(violation_type),
                intervention_action=DBInterventionAction(intervention_action.value)
                    if isinstance(intervention_action, InterventionAction)
                    else DBInterventionAction(intervention_action),
                enforcement_mode=DBEnforcementMode(enforcement_mode.value)
                    if isinstance(enforcement_mode, EnforcementMode)
                    else DBEnforcementMode(enforcement_mode),
                details=safe_details,
                user_id=user_id,
                override_reason=override_reason,
            )
            self.db.add(db_log)
            await self.db.flush()

        # Send notification for blocking interventions
        if intervention_action in (
            InterventionAction.BLOCKED,
            InterventionAction.AUTO_PAUSED,
        ):
            try:
                await send_enforcement_notification(
                    tenant_id=tenant_id,
                    intervention=log_entry,
                    notification_channels=["email"],
                    db=self.db,
                )
            except Exception as exc:
                logger.error(
                    f"Failed to send enforcement notification: {exc}",
                    exc_info=True,
                )


# =============================================================================
# Notification Service Integration
# =============================================================================

async def send_enforcement_notification(
    tenant_id: int,
    intervention: InterventionLog,
    notification_channels: Optional[List[str]] = None,
    db: Optional[AsyncSession] = None,
) -> bool:
    """
    Send notification for enforcement intervention via email and/or Slack.

    Queries the database for tenant admin users so their email addresses
    can be used for email notifications. For Slack, uses the
    SlackNotificationService with the tenant's configured webhook.

    Args:
        tenant_id: Tenant ID.
        intervention: Intervention log entry with full context.
        notification_channels: Channels to use (email, slack). Defaults to email.
        db: Optional AsyncSession for looking up admin emails.

    Returns:
        True if at least one notification channel succeeded.
    """
    channels = notification_channels or ["email"]
    any_sent = False

    action_label = (
        intervention.intervention_action.value
        if isinstance(intervention.intervention_action, InterventionAction)
        else intervention.intervention_action
    )
    mode_label = (
        intervention.enforcement_mode.value
        if isinstance(intervention.enforcement_mode, EnforcementMode)
        else intervention.enforcement_mode
    )
    violation_label = (
        intervention.violation_type.value
        if isinstance(intervention.violation_type, ViolationType)
        else intervention.violation_type
    )
    timestamp_str = intervention.timestamp.strftime("%Y-%m-%d %H:%M UTC")

    # ---- Email Channel ----
    if "email" in channels and db is not None:
        try:
            from app.base_models import User, UserRole, Tenant

            # Get tenant name
            tenant_result = await db.execute(
                select(Tenant.name).where(Tenant.id == tenant_id)
            )
            tenant_name: str = tenant_result.scalar_one_or_none() or f"Tenant {tenant_id}"

            # Find admin/manager users for this tenant
            admin_result = await db.execute(
                select(User.email, User.full_name)
                .where(
                    User.tenant_id == tenant_id,
                    User.is_active.is_(True),
                    User.role.in_([UserRole.ADMIN, UserRole.MANAGER]),
                )
            )
            admin_rows = admin_result.all()

            if admin_rows:
                email_service = get_email_service()
                subject = (
                    f"[Stratum AI] Enforcement {action_label}: "
                    f"{intervention.entity_type}/{intervention.entity_id}"
                )

                html_content = f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
             line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
  <div style="text-align: center; margin-bottom: 30px;">
    <h1 style="color: #2563eb; margin: 0;">Stratum AI</h1>
  </div>
  <div style="background: #fef2f2; border: 1px solid #fecaca; border-radius: 8px;
              padding: 30px; margin-bottom: 20px;">
    <h2 style="margin-top: 0; color: #dc2626;">Enforcement Intervention</h2>
    <table style="width: 100%; border-collapse: collapse;">
      <tr><td style="padding: 6px 0; font-weight: 600;">Tenant</td>
          <td style="padding: 6px 0;">{tenant_name}</td></tr>
      <tr><td style="padding: 6px 0; font-weight: 600;">Action</td>
          <td style="padding: 6px 0;">{action_label}</td></tr>
      <tr><td style="padding: 6px 0; font-weight: 600;">Mode</td>
          <td style="padding: 6px 0;">{mode_label}</td></tr>
      <tr><td style="padding: 6px 0; font-weight: 600;">Violation</td>
          <td style="padding: 6px 0;">{violation_label}</td></tr>
      <tr><td style="padding: 6px 0; font-weight: 600;">Entity</td>
          <td style="padding: 6px 0;">{intervention.entity_type} / {intervention.entity_id}</td></tr>
      <tr><td style="padding: 6px 0; font-weight: 600;">Timestamp</td>
          <td style="padding: 6px 0;">{timestamp_str}</td></tr>
    </table>
  </div>
  <div style="text-align: center; color: #94a3b8; font-size: 12px;">
    <p>This is an automated notification from the Stratum AI Autopilot Enforcer.</p>
  </div>
</body>
</html>
"""

                text_content = (
                    f"Stratum AI Enforcement Intervention\n\n"
                    f"Tenant: {tenant_name}\n"
                    f"Action: {action_label}\n"
                    f"Mode: {mode_label}\n"
                    f"Violation: {violation_label}\n"
                    f"Entity: {intervention.entity_type} / {intervention.entity_id}\n"
                    f"Timestamp: {timestamp_str}\n"
                )

                for row in admin_rows:
                    email_addr: str = row[0]  # User.email
                    try:
                        message = email_service._create_message(
                            to_email=email_addr,
                            subject=subject,
                            html_content=html_content,
                            text_content=text_content,
                        )
                        sent = email_service._send_email(email_addr, message)
                        if sent:
                            any_sent = True
                    except Exception as email_exc:
                        logger.error(
                            f"Failed to send enforcement email to {email_addr[:20]}...: {email_exc}"
                        )

        except Exception as exc:
            logger.error(f"Error sending enforcement email notifications: {exc}", exc_info=True)

    # ---- Slack Channel ----
    if "slack" in channels:
        try:
            slack_svc = SlackNotificationService()
            # Build a simple Slack alert
            sent = await slack_svc.send_message(
                text=(
                    f"Enforcement {action_label} for tenant {tenant_id}: "
                    f"{violation_label} on {intervention.entity_type}/{intervention.entity_id}"
                ),
            )
            if sent:
                any_sent = True
            await slack_svc.close()
        except Exception as slack_exc:
            logger.error(f"Failed to send Slack enforcement notification: {slack_exc}")

    logger.info(
        f"Enforcement notification result: tenant={tenant_id} "
        f"channels={channels} any_sent={any_sent}"
    )

    return any_sent
