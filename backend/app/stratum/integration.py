# =============================================================================
# Stratum AI - Integration Bridge
# =============================================================================
"""
Integration bridge between Stratum multiplatform module and existing services.

Provides compatibility layer to integrate:
- New SignalHealthCalculator with existing EMQ service
- TrustGate with autopilot enforcement
- Platform adapters with CAPI service
"""

import logging
from datetime import UTC, datetime
from typing import Any, Optional

from app.stratum.core.signal_health import SignalHealthCalculator
from app.stratum.core.trust_gate import TrustGate, TrustGateResult
from app.stratum.models import AutomationAction, EMQScore, Platform, SignalHealth

logger = logging.getLogger("stratum.integration")


class StratumIntegration:
    """
    Integration layer for Stratum multiplatform module.

    This class bridges the new Stratum components with existing services,
    providing a unified interface for signal health and trust gate evaluation.
    """

    def __init__(self):
        self.health_calculator = SignalHealthCalculator()
        self.trust_gate = TrustGate()

    def calculate_signal_health_from_emq_response(
        self,
        emq_data: dict[str, Any],
    ) -> SignalHealth:
        """
        Calculate signal health from the existing EMQ service response.

        Args:
            emq_data: Response from EmqService.get_emq_score()

        Returns:
            SignalHealth object
        """
        # Extract driver values from EMQ response
        drivers = {d["name"]: d["value"] for d in emq_data.get("drivers", [])}

        return self.health_calculator.calculate_from_emq_drivers(
            event_match_rate=drivers.get("Event Match Rate", 75.0),
            pixel_coverage=drivers.get("Pixel Coverage", 80.0),
            conversion_latency=drivers.get("Conversion Latency", 65.0),
            attribution_accuracy=drivers.get("Attribution Accuracy", 70.0),
            data_freshness=drivers.get("Data Freshness", 85.0),
        )

    def evaluate_action(
        self,
        emq_data: dict[str, Any],
        action: AutomationAction,
    ) -> TrustGateResult:
        """
        Evaluate an automation action against current signal health.

        Args:
            emq_data: Response from EmqService.get_emq_score()
            action: Proposed automation action

        Returns:
            TrustGateResult with decision
        """
        signal_health = self.calculate_signal_health_from_emq_response(emq_data)
        return self.trust_gate.evaluate(signal_health, action)

    def get_autopilot_config(
        self,
        emq_data: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Get autopilot configuration based on current signal health.

        Returns dict compatible with existing autopilot state response.
        """
        signal_health = self.calculate_signal_health_from_emq_response(emq_data)
        allowed, restricted = self.trust_gate.get_allowed_actions(signal_health)

        # Determine mode
        score = signal_health.overall_score
        if score >= 80:
            mode = "normal"
            reason = "Signal health excellent - full autopilot enabled"
        elif score >= 70:
            mode = "normal"
            reason = "Signal health good - autopilot enabled"
        elif score >= 60:
            mode = "limited"
            reason = "Signal health degraded - limited to conservative actions"
        elif score >= 40:
            mode = "cuts_only"
            reason = "Signal health low - only pause/reduce actions allowed"
        else:
            mode = "frozen"
            reason = "Signal health critical - automation frozen"

        return {
            "mode": mode,
            "reason": reason,
            "signalHealth": {
                "score": signal_health.overall_score,
                "status": signal_health.status,
                "components": {
                    "emq": signal_health.emq_score,
                    "freshness": signal_health.freshness_score,
                    "variance": signal_health.variance_score,
                    "anomaly": signal_health.anomaly_score,
                },
            },
            "allowedActions": allowed,
            "restrictedActions": restricted,
        }


def convert_platform_emq_to_score(
    platform: str,
    emq_value: float,
) -> EMQScore:
    """
    Convert platform EMQ data to EMQScore model.

    Args:
        platform: Platform name (meta, google, tiktok, snapchat)
        emq_value: EMQ score value (0-100 or 0-10)

    Returns:
        EMQScore object
    """
    # Normalize to 0-10 scale
    if emq_value > 10:
        emq_value = emq_value / 10

    platform_enum = Platform(platform.lower())

    return EMQScore(
        platform=platform_enum,
        event_name="aggregate",
        score=min(10, max(0, emq_value)),
        last_updated=datetime.now(UTC),
    )


def create_automation_action(
    platform: str,
    account_id: str,
    entity_type: str,
    entity_id: str,
    action_type: str,
    parameters: Optional[dict[str, Any]] = None,
) -> AutomationAction:
    """
    Create an AutomationAction from individual parameters.

    Args:
        platform: Platform name
        account_id: Account ID
        entity_type: Entity type (campaign, adset, ad)
        entity_id: Entity ID
        action_type: Action type
        parameters: Action parameters

    Returns:
        AutomationAction object
    """
    return AutomationAction(
        platform=Platform(platform.lower()),
        account_id=account_id,
        entity_type=entity_type,
        entity_id=entity_id,
        action_type=action_type,
        parameters=parameters or {},
    )


# Global integration instance
_integration: Optional[StratumIntegration] = None


def get_integration() -> StratumIntegration:
    """Get or create the global integration instance."""
    global _integration
    if _integration is None:
        _integration = StratumIntegration()
    return _integration
