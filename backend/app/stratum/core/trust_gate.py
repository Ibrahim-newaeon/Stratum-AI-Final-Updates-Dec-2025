# =============================================================================
# Stratum AI - Trust Gate Evaluation System
# =============================================================================
"""
Trust Gate for Automation Decision Making.

The Trust Gate is the decision checkpoint that evaluates whether an
automation action should proceed based on current signal health.

Gate Decisions:
- PASS: Signal health is good, automation can execute
- HOLD: Signal health is degraded, alert but don't execute
- BLOCK: Signal health is critical, require manual intervention

The gate operates on the principle that automated budget decisions should
NEVER execute when data quality is compromised. This protects advertisers
from making costly mistakes based on unreliable signals.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from app.stratum.models import AutomationAction, SignalHealth

logger = logging.getLogger("stratum.trust_gate")


class GateDecision(str, Enum):
    """Trust gate decision outcomes."""

    PASS = "pass"
    HOLD = "hold"
    BLOCK = "block"


@dataclass
class TrustGateConfig:
    """Configuration for trust gate thresholds."""

    # Score thresholds
    pass_threshold: float = 70.0  # Signal health >= 70 allows execution
    hold_threshold: float = 40.0  # Signal health 40-69 holds for review
    # Below 40 = BLOCK

    # Action-specific overrides
    high_risk_threshold: float = 80.0  # Higher threshold for high-risk actions
    conservative_threshold: float = 60.0  # Lower threshold for conservative actions

    # High-risk actions require higher signal health
    high_risk_actions: list[str] = field(
        default_factory=lambda: [
            "increase_budget",
            "launch_new_campaigns",
            "expand_targeting",
            "increase_bid",
        ]
    )

    # Conservative actions can proceed with lower signal health
    conservative_actions: list[str] = field(
        default_factory=lambda: [
            "pause_underperforming",
            "reduce_budget",
            "reduce_bid",
        ]
    )

    # Actions that are always allowed (safety measures)
    always_allowed_actions: list[str] = field(
        default_factory=lambda: [
            "pause_all",
            "emergency_stop",
        ]
    )


@dataclass
class TrustGateResult:
    """Result of a trust gate evaluation."""

    decision: GateDecision
    signal_health: SignalHealth
    action: AutomationAction
    reason: str
    allowed_actions: list[str]
    restricted_actions: list[str]
    recommendations: list[str]
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for API responses."""
        components = {
            "emq": self.signal_health.emq_score,
            "freshness": self.signal_health.freshness_score,
            "variance": self.signal_health.variance_score,
            "anomaly": self.signal_health.anomaly_score,
        }
        # Include CDP EMQ if available
        if self.signal_health.cdp_emq_score is not None:
            components["cdp"] = self.signal_health.cdp_emq_score

        return {
            "decision": self.decision.value,
            "signalHealth": {
                "score": self.signal_health.overall_score,
                "status": self.signal_health.status,
                "components": components,
                "issues": self.signal_health.issues,
                "hasCdpData": self.signal_health.has_cdp_data(),
            },
            "action": {
                "type": self.action.action_type,
                "entity": f"{self.action.entity_type}/{self.action.entity_id}",
                "platform": self.action.platform,
            },
            "reason": self.reason,
            "allowedActions": self.allowed_actions,
            "restrictedActions": self.restricted_actions,
            "recommendations": self.recommendations,
            "evaluatedAt": self.evaluated_at.isoformat() + "Z",
        }


class TrustGate:
    """
    Trust Gate evaluator for automation decisions.

    The gate evaluates each proposed automation action against current
    signal health and determines whether execution should proceed.

    Usage:
        gate = TrustGate()
        signal_health = calculator.calculate(...)

        action = AutomationAction(
            platform=Platform.META,
            action_type="increase_budget",
            ...
        )

        result = gate.evaluate(signal_health, action)

        if result.decision == GateDecision.PASS:
            # Execute the action
            await adapter.execute_action(action)
        elif result.decision == GateDecision.HOLD:
            # Queue for review
            await queue_for_review(action, result)
        else:
            # Block and alert
            await alert_team(action, result)
    """

    def __init__(self, config: Optional[TrustGateConfig] = None):
        """Initialize with optional custom configuration."""
        self.config = config or TrustGateConfig()

    def evaluate(
        self,
        signal_health: SignalHealth,
        action: AutomationAction,
    ) -> TrustGateResult:
        """
        Evaluate whether an automation action should proceed.

        Args:
            signal_health: Current signal health state
            action: Proposed automation action

        Returns:
            TrustGateResult with decision and context
        """
        # Check for always-allowed actions first
        if action.action_type in self.config.always_allowed_actions:
            return self._create_result(
                decision=GateDecision.PASS,
                signal_health=signal_health,
                action=action,
                reason="Emergency/safety action always allowed",
            )

        # Determine threshold based on action risk level
        threshold = self._get_threshold_for_action(action)

        # Evaluate against threshold
        score = signal_health.overall_score
        decision, reason = self._make_decision(score, threshold, action)

        # Log the evaluation
        logger.info(
            f"Trust gate evaluation: {decision.value} for {action.action_type} "
            f"(score={score:.1f}, threshold={threshold:.1f})"
        )

        return self._create_result(
            decision=decision,
            signal_health=signal_health,
            action=action,
            reason=reason,
        )

    def evaluate_batch(
        self,
        signal_health: SignalHealth,
        actions: list[AutomationAction],
    ) -> list[TrustGateResult]:
        """Evaluate multiple actions at once."""
        return [self.evaluate(signal_health, action) for action in actions]

    def get_allowed_actions(
        self,
        signal_health: SignalHealth,
    ) -> tuple[list[str], list[str]]:
        """
        Get lists of allowed and restricted actions based on signal health.

        Returns:
            Tuple of (allowed_actions, restricted_actions)
        """
        score = signal_health.overall_score

        # Always allowed
        allowed = list(self.config.always_allowed_actions)

        # Conservative actions allowed if above hold threshold
        if score >= self.config.hold_threshold:
            allowed.extend(self.config.conservative_actions)

        # Standard actions allowed if above pass threshold
        if score >= self.config.pass_threshold:
            standard_actions = [
                "update_budget",
                "update_bid",
                "update_status",
                "update_targeting",
            ]
            allowed.extend(standard_actions)

        # High-risk actions only allowed if above high-risk threshold
        if score >= self.config.high_risk_threshold:
            allowed.extend(self.config.high_risk_actions)

        # Calculate restricted
        all_actions = (
            self.config.always_allowed_actions
            + self.config.conservative_actions
            + self.config.high_risk_actions
            + ["update_budget", "update_bid", "update_status", "update_targeting"]
        )
        restricted = [a for a in all_actions if a not in allowed]

        return list(set(allowed)), list(set(restricted))

    def _get_threshold_for_action(self, action: AutomationAction) -> float:
        """Determine the signal health threshold for a given action."""
        if action.action_type in self.config.high_risk_actions:
            return self.config.high_risk_threshold
        elif action.action_type in self.config.conservative_actions:
            return self.config.conservative_threshold
        else:
            return self.config.pass_threshold

    def _make_decision(
        self,
        score: float,
        threshold: float,
        action: AutomationAction,
    ) -> tuple[GateDecision, str]:
        """Make the gate decision based on score and threshold."""
        if score >= threshold:
            return (
                GateDecision.PASS,
                f"Signal health {score:.1f} meets threshold {threshold:.1f} for {action.action_type}",
            )
        elif score >= self.config.hold_threshold:
            return (
                GateDecision.HOLD,
                f"Signal health {score:.1f} below threshold {threshold:.1f} - action queued for review",
            )
        else:
            return (
                GateDecision.BLOCK,
                f"Signal health {score:.1f} critically low - manual intervention required",
            )

    def _create_result(
        self,
        decision: GateDecision,
        signal_health: SignalHealth,
        action: AutomationAction,
        reason: str,
    ) -> TrustGateResult:
        """Create a full trust gate result with recommendations."""
        allowed, restricted = self.get_allowed_actions(signal_health)

        recommendations = self._get_recommendations(decision, signal_health, action)

        return TrustGateResult(
            decision=decision,
            signal_health=signal_health,
            action=action,
            reason=reason,
            allowed_actions=allowed,
            restricted_actions=restricted,
            recommendations=recommendations,
        )

    def _get_recommendations(
        self,
        decision: GateDecision,
        signal_health: SignalHealth,
        action: AutomationAction,
    ) -> list[str]:
        """Generate recommendations based on the gate decision."""
        recommendations = []

        if decision == GateDecision.PASS:
            recommendations.append("Automation can proceed as planned")
            if signal_health.overall_score < 80:
                recommendations.append("Consider monitoring signal health closely")
        elif decision == GateDecision.HOLD:
            recommendations.append("Review signal health issues before proceeding")
            recommendations.append("Consider conservative actions only")
            if signal_health.emq_score < 70:
                recommendations.append("Check platform EMQ/data quality settings")
            if signal_health.freshness_score < 70:
                recommendations.append("Verify data sync is running correctly")
            if signal_health.variance_score < 70:
                recommendations.append("Investigate attribution discrepancies")
        else:  # BLOCK
            recommendations.append("Manual review required before any automation")
            recommendations.append("Check platform API connectivity")
            recommendations.append("Verify tracking implementation")
            recommendations.append("Consider pausing automation until resolved")

        # CDP-specific recommendations
        if signal_health.cdp_emq_score is not None:
            if signal_health.cdp_emq_score < 70:
                recommendations.append("Review CDP data quality and identity resolution")
                recommendations.append("Check CDP event ingestion for missing identifiers")
            elif signal_health.cdp_emq_score < 85:
                recommendations.append("Consider enhancing CDP identifier collection")
        elif signal_health.has_cdp_data() is False and decision != GateDecision.PASS:
            # No CDP data available - recommend integration
            recommendations.append("Consider integrating CDP for improved identity resolution")

        # Add issue-specific recommendations
        for issue in signal_health.issues:
            if "EMQ" in issue or "match" in issue.lower():
                recommendations.append("Review CAPI/pixel implementation")
            elif "freshness" in issue.lower() or "stale" in issue.lower():
                recommendations.append("Check data pipeline and sync jobs")
            elif "variance" in issue.lower() or "attribution" in issue.lower():
                recommendations.append("Compare platform vs GA4 attribution settings")
            elif "anomaly" in issue.lower():
                recommendations.append("Investigate unusual metric patterns")
            elif "CDP" in issue or "cdp" in issue.lower():
                recommendations.append("Review CDP event schema and identifier quality")
            elif "identity" in issue.lower() or "resolution" in issue.lower():
                recommendations.append("Enhance first-party data collection (email, phone)")

        return list(set(recommendations))  # Remove duplicates


def evaluate_automation(
    signal_health: SignalHealth,
    action: AutomationAction,
    config: Optional[TrustGateConfig] = None,
) -> TrustGateResult:
    """
    Convenience function to evaluate a single automation action.

    Args:
        signal_health: Current signal health
        action: Proposed action
        config: Optional custom configuration

    Returns:
        TrustGateResult
    """
    gate = TrustGate(config)
    return gate.evaluate(signal_health, action)


def get_autopilot_mode(signal_health: SignalHealth) -> tuple[str, str]:
    """
    Determine autopilot mode based on signal health.

    Returns:
        Tuple of (mode, reason) where mode is one of:
        - "normal": Full autopilot enabled
        - "limited": Only conservative actions
        - "cuts_only": Only budget reduction/pause
        - "frozen": No automation
    """
    score = signal_health.overall_score

    if score >= 80:
        return "normal", "Signal health excellent - full autopilot enabled"
    elif score >= 70:
        return "normal", "Signal health good - autopilot enabled"
    elif score >= 60:
        return "limited", "Signal health degraded - limited to conservative actions"
    elif score >= 40:
        return "cuts_only", "Signal health low - only pause/reduce actions allowed"
    else:
        return "frozen", "Signal health critical - automation frozen"
