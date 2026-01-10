"""
Stratum AI: Autopilot Engine
============================

The Autopilot Engine is where automation rules live. It evaluates campaign
performance and generates optimization actions that are then passed through
the Trust Gate before execution.

Philosophy
----------

The autopilot doesn't blindly execute rules. It follows a three-stage process:

1. **Observe**: Collect current performance data and signal health
2. **Decide**: Apply rules to determine what actions might improve performance
3. **Gate**: Pass proposed actions through the Trust Gate for approval

Only after the Trust Gate approves an action does it actually execute.

Built-in Rules
--------------

The autopilot comes with several pre-built optimization strategies:

1. **Budget Pacing**: Ensure campaigns spend their budget evenly throughout
   the day/month without front-loading or trailing off.

2. **Performance Scaling**: Increase budget on high-performing campaigns,
   decrease on underperformers based on ROAS/CPA targets.

3. **Bid Optimization**: Adjust bids to hit target CPA/ROAS while
   maintaining volume.

4. **Status Management**: Pause campaigns that hit spending limits or
   have poor performance for extended periods.

Custom Rules
------------

You can define custom rules by subclassing AutopilotRule and implementing
the evaluate() method. Rules return a list of proposed AutomationActions.

Example:

    class MyCustomRule(AutopilotRule):
        def evaluate(self, context: RuleContext) -> List[AutomationAction]:
            # Your optimization logic here
            if context.metrics.roas > 5.0:
                return [create_budget_increase_action(...)]
            return []
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Protocol
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
import uuid

from app.stratum.models import (
    Platform,
    UnifiedCampaign,
    UnifiedAdSet,
    PerformanceMetrics,
    SignalHealth,
    AutomationAction,
    EntityStatus,
)
from app.stratum.core.trust_gate import TrustGate, GateDecision, TrustGateResult


logger = logging.getLogger("stratum.core.autopilot")


class RuleType(str, Enum):
    """Categories of automation rules."""
    BUDGET_PACING = "budget_pacing"
    PERFORMANCE_SCALING = "performance_scaling"
    BID_OPTIMIZATION = "bid_optimization"
    STATUS_MANAGEMENT = "status_management"
    CUSTOM = "custom"


@dataclass
class RuleContext:
    """
    Context provided to rules for making decisions.

    This contains all the information a rule needs to evaluate
    whether an action should be taken.
    """
    platform: Platform
    account_id: str
    campaign: UnifiedCampaign
    adsets: List[UnifiedAdSet]
    metrics: PerformanceMetrics
    signal_health: SignalHealth
    historical_metrics: List[PerformanceMetrics]

    # Targets and thresholds
    target_cpa: Optional[float] = None
    target_roas: Optional[float] = None
    max_cpa: Optional[float] = None
    min_roas: Optional[float] = None

    # Budget constraints
    max_daily_budget: Optional[float] = None
    min_daily_budget: Optional[float] = None
    max_budget_change_percent: float = 50.0

    # Timing
    current_time: datetime = field(default_factory=datetime.utcnow)
    days_since_last_change: int = 0


@dataclass
class RuleResult:
    """Result of evaluating a rule."""
    rule_name: str
    rule_type: RuleType
    triggered: bool
    actions: List[AutomationAction]
    reasoning: str
    confidence: float = 1.0  # 0.0 to 1.0


class AutopilotRule(ABC):
    """
    Base class for autopilot rules.

    Subclass this to create custom optimization rules.
    """

    def __init__(self, name: str, rule_type: RuleType, enabled: bool = True):
        self.name = name
        self.rule_type = rule_type
        self.enabled = enabled

    @abstractmethod
    def evaluate(self, context: RuleContext) -> RuleResult:
        """
        Evaluate the rule and return proposed actions.

        Args:
            context: All information needed for decision making

        Returns:
            RuleResult with any proposed actions
        """
        pass

    def _create_action(
        self,
        context: RuleContext,
        entity_type: str,
        entity_id: str,
        action_type: str,
        parameters: Dict[str, Any]
    ) -> AutomationAction:
        """Helper to create a properly formatted action."""
        return AutomationAction(
            platform=context.platform,
            account_id=context.account_id,
            entity_type=entity_type,
            entity_id=entity_id,
            action_type=action_type,
            parameters=parameters,
            signal_health_at_creation=context.signal_health.score,
            created_by=f"autopilot:{self.name}"
        )


class BudgetPacingRule(AutopilotRule):
    """
    Ensures campaigns spend their budget evenly.

    If a campaign is significantly under-pacing (spending too slowly),
    this rule will suggest increasing the budget or bid. If over-pacing,
    it may suggest decreasing to avoid exhausting budget too early.
    """

    def __init__(
        self,
        underpace_threshold: float = 0.7,  # Trigger if spending <70% of expected
        overpace_threshold: float = 1.3,   # Trigger if spending >130% of expected
        adjustment_percent: float = 20.0
    ):
        super().__init__("budget_pacing", RuleType.BUDGET_PACING)
        self.underpace_threshold = underpace_threshold
        self.overpace_threshold = overpace_threshold
        self.adjustment_percent = adjustment_percent

    def evaluate(self, context: RuleContext) -> RuleResult:
        """Evaluate budget pacing and suggest adjustments."""
        actions = []
        reasoning_parts = []

        # Calculate expected spend based on time of day/month
        campaign = context.campaign
        current_hour = context.current_time.hour
        hours_elapsed = current_hour + 1  # 1-24
        expected_pct = hours_elapsed / 24.0

        if not campaign.daily_budget or not context.metrics.spend:
            return RuleResult(
                rule_name=self.name,
                rule_type=self.rule_type,
                triggered=False,
                actions=[],
                reasoning="Insufficient data for pacing analysis"
            )

        actual_pct = context.metrics.spend / campaign.daily_budget
        pace_ratio = actual_pct / expected_pct if expected_pct > 0 else 1.0

        reasoning_parts.append(
            f"Expected {expected_pct*100:.0f}% spend, actual {actual_pct*100:.0f}% "
            f"(pace ratio: {pace_ratio:.2f})"
        )

        triggered = False

        if pace_ratio < self.underpace_threshold:
            # Under-pacing: campaign not spending enough
            triggered = True
            new_budget = campaign.daily_budget * (1 + self.adjustment_percent / 100)

            # Respect max budget constraint
            if context.max_daily_budget:
                new_budget = min(new_budget, context.max_daily_budget)

            if new_budget > campaign.daily_budget:
                actions.append(self._create_action(
                    context,
                    entity_type="campaign",
                    entity_id=campaign.campaign_id,
                    action_type="update_budget",
                    parameters={"daily_budget": round(new_budget, 2)}
                ))
                reasoning_parts.append(
                    f"Under-pacing detected. Suggesting budget increase to ${new_budget:.2f}"
                )

        elif pace_ratio > self.overpace_threshold:
            # Over-pacing: campaign spending too fast
            triggered = True
            reasoning_parts.append(
                f"Over-pacing detected ({pace_ratio:.2f}x expected). "
                f"Consider reducing bid or monitoring for budget exhaustion."
            )
            # Note: We don't automatically decrease budget as it might hurt performance
            # This is logged as a warning for manual review

        return RuleResult(
            rule_name=self.name,
            rule_type=self.rule_type,
            triggered=triggered,
            actions=actions,
            reasoning=" | ".join(reasoning_parts),
            confidence=0.8 if triggered else 1.0
        )


class PerformanceScalingRule(AutopilotRule):
    """
    Scales budget based on campaign performance.

    High-performing campaigns (above target ROAS/below target CPA) get
    budget increases. Poor performers get decreases or pauses.
    """

    def __init__(
        self,
        scale_up_multiplier: float = 1.2,    # +20% for good performance
        scale_down_multiplier: float = 0.8,  # -20% for poor performance
        min_conversions: int = 5,            # Need at least 5 conversions to act
        cooldown_days: int = 1               # Wait 1 day between changes
    ):
        super().__init__("performance_scaling", RuleType.PERFORMANCE_SCALING)
        self.scale_up_multiplier = scale_up_multiplier
        self.scale_down_multiplier = scale_down_multiplier
        self.min_conversions = min_conversions
        self.cooldown_days = cooldown_days

    def evaluate(self, context: RuleContext) -> RuleResult:
        """Evaluate performance and suggest budget scaling."""
        actions = []
        reasoning_parts = []

        # Check cooldown
        if context.days_since_last_change < self.cooldown_days:
            return RuleResult(
                rule_name=self.name,
                rule_type=self.rule_type,
                triggered=False,
                actions=[],
                reasoning=f"In cooldown period ({context.days_since_last_change}/{self.cooldown_days} days)"
            )

        # Check minimum conversions
        conversions = context.metrics.conversions or 0
        if conversions < self.min_conversions:
            return RuleResult(
                rule_name=self.name,
                rule_type=self.rule_type,
                triggered=False,
                actions=[],
                reasoning=f"Insufficient conversions ({conversions}/{self.min_conversions})"
            )

        campaign = context.campaign
        metrics = context.metrics
        triggered = False

        # ROAS-based scaling
        if context.target_roas and metrics.roas:
            roas_ratio = metrics.roas / context.target_roas
            reasoning_parts.append(f"ROAS: {metrics.roas:.2f}x (target: {context.target_roas:.2f}x)")

            if roas_ratio >= 1.2 and campaign.daily_budget:
                # Performing 20%+ above target ROAS - scale up
                triggered = True
                new_budget = campaign.daily_budget * self.scale_up_multiplier

                # Apply constraints
                if context.max_daily_budget:
                    new_budget = min(new_budget, context.max_daily_budget)

                max_change = campaign.daily_budget * (1 + context.max_budget_change_percent / 100)
                new_budget = min(new_budget, max_change)

                if new_budget > campaign.daily_budget:
                    actions.append(self._create_action(
                        context,
                        entity_type="campaign",
                        entity_id=campaign.campaign_id,
                        action_type="update_budget",
                        parameters={"daily_budget": round(new_budget, 2)}
                    ))
                    reasoning_parts.append(f"Strong performance -> budget increase to ${new_budget:.2f}")

            elif roas_ratio <= 0.7 and campaign.daily_budget:
                # Performing 30%+ below target ROAS - scale down
                triggered = True
                new_budget = campaign.daily_budget * self.scale_down_multiplier

                # Apply minimum constraint
                if context.min_daily_budget:
                    new_budget = max(new_budget, context.min_daily_budget)

                if new_budget < campaign.daily_budget:
                    actions.append(self._create_action(
                        context,
                        entity_type="campaign",
                        entity_id=campaign.campaign_id,
                        action_type="update_budget",
                        parameters={"daily_budget": round(new_budget, 2)}
                    ))
                    reasoning_parts.append(f"Poor performance -> budget decrease to ${new_budget:.2f}")

        # CPA-based scaling (if no ROAS target)
        elif context.target_cpa and metrics.cpa:
            cpa_ratio = metrics.cpa / context.target_cpa
            reasoning_parts.append(f"CPA: ${metrics.cpa:.2f} (target: ${context.target_cpa:.2f})")

            if cpa_ratio <= 0.8 and campaign.daily_budget:
                # CPA 20%+ below target - scale up
                triggered = True
                new_budget = campaign.daily_budget * self.scale_up_multiplier

                if context.max_daily_budget:
                    new_budget = min(new_budget, context.max_daily_budget)

                if new_budget > campaign.daily_budget:
                    actions.append(self._create_action(
                        context,
                        entity_type="campaign",
                        entity_id=campaign.campaign_id,
                        action_type="update_budget",
                        parameters={"daily_budget": round(new_budget, 2)}
                    ))
                    reasoning_parts.append(f"Efficient CPA -> budget increase to ${new_budget:.2f}")

            elif cpa_ratio >= 1.3 and campaign.daily_budget:
                # CPA 30%+ above target - scale down
                triggered = True
                new_budget = campaign.daily_budget * self.scale_down_multiplier

                if context.min_daily_budget:
                    new_budget = max(new_budget, context.min_daily_budget)

                if new_budget < campaign.daily_budget:
                    actions.append(self._create_action(
                        context,
                        entity_type="campaign",
                        entity_id=campaign.campaign_id,
                        action_type="update_budget",
                        parameters={"daily_budget": round(new_budget, 2)}
                    ))
                    reasoning_parts.append(f"High CPA -> budget decrease to ${new_budget:.2f}")

        if not reasoning_parts:
            reasoning_parts.append("No performance targets configured")

        return RuleResult(
            rule_name=self.name,
            rule_type=self.rule_type,
            triggered=triggered,
            actions=actions,
            reasoning=" | ".join(reasoning_parts),
            confidence=0.9 if triggered else 1.0
        )


class StatusManagementRule(AutopilotRule):
    """
    Manages campaign/adset status based on performance.

    Pauses entities that have consistently poor performance or
    have exceeded budget limits.
    """

    def __init__(
        self,
        pause_after_days: int = 7,           # Days of poor performance before pause
        max_cpa_multiplier: float = 2.0,     # Pause if CPA is 2x target
        min_roas_multiplier: float = 0.5     # Pause if ROAS is 0.5x target
    ):
        super().__init__("status_management", RuleType.STATUS_MANAGEMENT)
        self.pause_after_days = pause_after_days
        self.max_cpa_multiplier = max_cpa_multiplier
        self.min_roas_multiplier = min_roas_multiplier

    def evaluate(self, context: RuleContext) -> RuleResult:
        """Evaluate and suggest status changes."""
        actions = []
        reasoning_parts = []

        metrics = context.metrics
        triggered = False

        # Check for extremely poor ROAS
        if context.min_roas and metrics.roas:
            if metrics.roas < context.min_roas * self.min_roas_multiplier:
                triggered = True
                actions.append(self._create_action(
                    context,
                    entity_type="campaign",
                    entity_id=context.campaign.campaign_id,
                    action_type="update_status",
                    parameters={"status": EntityStatus.PAUSED.value}
                ))
                reasoning_parts.append(
                    f"ROAS {metrics.roas:.2f}x is below minimum threshold "
                    f"({context.min_roas * self.min_roas_multiplier:.2f}x). Suggesting pause."
                )

        # Check for extremely high CPA
        if context.max_cpa and metrics.cpa:
            if metrics.cpa > context.max_cpa * self.max_cpa_multiplier:
                triggered = True
                actions.append(self._create_action(
                    context,
                    entity_type="campaign",
                    entity_id=context.campaign.campaign_id,
                    action_type="update_status",
                    parameters={"status": EntityStatus.PAUSED.value}
                ))
                reasoning_parts.append(
                    f"CPA ${metrics.cpa:.2f} exceeds maximum threshold "
                    f"(${context.max_cpa * self.max_cpa_multiplier:.2f}). Suggesting pause."
                )

        # Check for consistent poor performance
        if len(context.historical_metrics) >= self.pause_after_days:
            poor_days = 0
            for hist_metrics in context.historical_metrics[-self.pause_after_days:]:
                if context.target_roas and hist_metrics.roas:
                    if hist_metrics.roas < context.target_roas * 0.7:
                        poor_days += 1
                elif context.target_cpa and hist_metrics.cpa:
                    if hist_metrics.cpa > context.target_cpa * 1.5:
                        poor_days += 1

            if poor_days >= self.pause_after_days:
                triggered = True
                actions.append(self._create_action(
                    context,
                    entity_type="campaign",
                    entity_id=context.campaign.campaign_id,
                    action_type="update_status",
                    parameters={"status": EntityStatus.PAUSED.value}
                ))
                reasoning_parts.append(
                    f"Consistently poor performance for {poor_days} days. Suggesting pause."
                )

        if not reasoning_parts:
            reasoning_parts.append("No status issues detected")

        return RuleResult(
            rule_name=self.name,
            rule_type=self.rule_type,
            triggered=triggered,
            actions=actions,
            reasoning=" | ".join(reasoning_parts),
            confidence=0.95 if triggered else 1.0
        )


class AutopilotEngine:
    """
    The main autopilot engine that orchestrates rule evaluation.

    This class brings together rules and the trust gate to create
    a complete automation system.

    Usage:

        engine = AutopilotEngine()

        # Add custom rules
        engine.add_rule(MyCustomRule())

        # Evaluate all rules for a campaign
        results = await engine.evaluate_campaign(
            campaign=campaign,
            adsets=adsets,
            metrics=metrics,
            signal_health=health
        )

        # Execute approved actions
        for result in results:
            for action in result.actions:
                if result.gate_result.decision == GateDecision.APPROVED:
                    await adapter.execute_action(action)
    """

    def __init__(
        self,
        trust_gate: Optional[TrustGate] = None,
        auto_execute: bool = False
    ):
        """
        Initialize the autopilot engine.

        Args:
            trust_gate: Custom trust gate (creates default if None)
            auto_execute: Whether to automatically execute approved actions
        """
        self.trust_gate = trust_gate or TrustGate()
        self.auto_execute = auto_execute
        self.rules: List[AutopilotRule] = []

        # Add default rules
        self._add_default_rules()

        # Execution history for cooldown tracking
        self._execution_history: Dict[str, datetime] = {}

        logger.info("AutopilotEngine initialized with %d rules", len(self.rules))

    def _add_default_rules(self) -> None:
        """Add the built-in optimization rules."""
        self.rules.extend([
            BudgetPacingRule(),
            PerformanceScalingRule(),
            StatusManagementRule(),
        ])

    def add_rule(self, rule: AutopilotRule) -> None:
        """Add a custom rule to the engine."""
        self.rules.append(rule)
        logger.info(f"Added rule: {rule.name} ({rule.rule_type.value})")

    def remove_rule(self, rule_name: str) -> bool:
        """Remove a rule by name."""
        for i, rule in enumerate(self.rules):
            if rule.name == rule_name:
                del self.rules[i]
                logger.info(f"Removed rule: {rule_name}")
                return True
        return False

    def get_rule(self, rule_name: str) -> Optional[AutopilotRule]:
        """Get a rule by name."""
        for rule in self.rules:
            if rule.name == rule_name:
                return rule
        return None

    def list_rules(self) -> List[Dict[str, Any]]:
        """List all registered rules."""
        return [
            {
                "name": rule.name,
                "type": rule.rule_type.value,
                "enabled": rule.enabled
            }
            for rule in self.rules
        ]

    async def evaluate_campaign(
        self,
        platform: Platform,
        account_id: str,
        campaign: UnifiedCampaign,
        adsets: List[UnifiedAdSet],
        metrics: PerformanceMetrics,
        signal_health: SignalHealth,
        historical_metrics: Optional[List[PerformanceMetrics]] = None,
        targets: Optional[Dict[str, float]] = None
    ) -> List[Dict[str, Any]]:
        """
        Evaluate all rules for a campaign and return results.

        This is the main entry point for the autopilot. It:
        1. Builds the rule context
        2. Evaluates each enabled rule
        3. Passes triggered actions through trust gate
        4. Optionally executes approved actions

        Returns:
            List of results including rule output and gate decisions
        """
        targets = targets or {}
        historical_metrics = historical_metrics or []

        # Calculate days since last change
        entity_key = f"{platform.value}:{account_id}:{campaign.campaign_id}"
        last_change = self._execution_history.get(entity_key)
        days_since = 0
        if last_change:
            days_since = (datetime.utcnow() - last_change).days

        # Build context
        context = RuleContext(
            platform=platform,
            account_id=account_id,
            campaign=campaign,
            adsets=adsets,
            metrics=metrics,
            signal_health=signal_health,
            historical_metrics=historical_metrics,
            target_cpa=targets.get("target_cpa"),
            target_roas=targets.get("target_roas"),
            max_cpa=targets.get("max_cpa"),
            min_roas=targets.get("min_roas"),
            max_daily_budget=targets.get("max_daily_budget"),
            min_daily_budget=targets.get("min_daily_budget"),
            max_budget_change_percent=targets.get("max_budget_change_percent", 50.0),
            days_since_last_change=days_since
        )

        results = []

        for rule in self.rules:
            if not rule.enabled:
                continue

            try:
                rule_result = rule.evaluate(context)

                # If rule triggered and has actions, evaluate through trust gate
                gate_results = []
                if rule_result.triggered and rule_result.actions:
                    for action in rule_result.actions:
                        gate_result = self.trust_gate.evaluate(action, signal_health)
                        gate_results.append(gate_result)

                        # Execute if auto_execute is on and approved
                        if self.auto_execute and gate_result.decision == GateDecision.APPROVED:
                            # Record execution time for cooldown
                            self._execution_history[entity_key] = datetime.utcnow()

                results.append({
                    "rule_name": rule_result.rule_name,
                    "rule_type": rule_result.rule_type.value,
                    "triggered": rule_result.triggered,
                    "reasoning": rule_result.reasoning,
                    "confidence": rule_result.confidence,
                    "actions": [
                        {
                            "action_type": a.action_type,
                            "entity_id": a.entity_id,
                            "parameters": a.parameters
                        }
                        for a in rule_result.actions
                    ],
                    "gate_results": [
                        {
                            "decision": gr.decision.value,
                            "reason": gr.reason
                        }
                        for gr in gate_results
                    ]
                })

            except Exception as e:
                logger.error(f"Error evaluating rule {rule.name}: {e}")
                results.append({
                    "rule_name": rule.name,
                    "rule_type": rule.rule_type.value,
                    "triggered": False,
                    "reasoning": f"Error: {str(e)}",
                    "confidence": 0.0,
                    "actions": [],
                    "gate_results": []
                })

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get autopilot statistics."""
        return {
            "total_rules": len(self.rules),
            "enabled_rules": sum(1 for r in self.rules if r.enabled),
            "rules_by_type": {
                rt.value: sum(1 for r in self.rules if r.rule_type == rt)
                for rt in RuleType
            },
            "auto_execute": self.auto_execute,
            "execution_history_size": len(self._execution_history),
            "trust_gate_stats": self.trust_gate.get_stats()
        }


class TrustGatedAutopilot:
    """
    High-level interface for trust-gated automation.

    This combines signal health calculation, trust gate evaluation,
    and autopilot rule execution into a single interface.
    """

    def __init__(self):
        from app.stratum.core.signal_health import SignalHealthCalculator

        self.health_calculator = SignalHealthCalculator()
        self.trust_gate = TrustGate()
        self.autopilot = AutopilotEngine(trust_gate=self.trust_gate)

    async def can_execute(
        self,
        action: AutomationAction,
        emq_scores: list,
        recent_metrics: list
    ) -> tuple:
        """
        Check if an action can be executed based on current signal health.

        Returns:
            Tuple of (can_proceed: bool, gate_result: TrustGateResult)
        """
        # Calculate signal health
        signal_health = self.health_calculator.calculate(
            platform=action.platform,
            account_id=action.account_id,
            emq_scores=emq_scores,
            recent_metrics=recent_metrics
        )

        # Evaluate through trust gate
        result = self.trust_gate.evaluate(action, signal_health)

        can_proceed = result.decision in [GateDecision.APPROVED, GateDecision.OVERRIDE]

        return can_proceed, result
