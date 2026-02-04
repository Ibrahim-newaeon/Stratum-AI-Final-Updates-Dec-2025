# =============================================================================
# Stratum AI - Core Trust Engine Components
# =============================================================================
"""
Core components for the Trust-Gated Autopilot system.

- SignalHealthCalculator: Computes signal health from multiple sources
- TrustGate: Evaluates whether automation should proceed
- AutopilotEngine: Automated campaign optimization with rules
- TrustGatedAutopilot: High-level autopilot interface with trust gates
"""

from app.stratum.core.autopilot import (
    AutopilotEngine,
    AutopilotRule,
    BudgetPacingRule,
    PerformanceScalingRule,
    RuleContext,
    RuleType,
    StatusManagementRule,
    TrustGatedAutopilot,
)
from app.stratum.core.signal_health import SignalHealthCalculator
from app.stratum.core.trust_gate import GateDecision, TrustGate, TrustGateResult

__all__ = [
    # Signal Health
    "SignalHealthCalculator",
    # Trust Gate
    "TrustGate",
    "TrustGateResult",
    "GateDecision",
    # Autopilot
    "RuleType",
    "RuleContext",
    "AutopilotRule",
    "BudgetPacingRule",
    "PerformanceScalingRule",
    "StatusManagementRule",
    "AutopilotEngine",
    "TrustGatedAutopilot",
]
