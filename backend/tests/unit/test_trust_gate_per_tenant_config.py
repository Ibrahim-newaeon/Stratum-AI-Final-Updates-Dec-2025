# =============================================================================
# Stratum AI - Per-tenant trust-gate thresholds (TRUST-007)
# =============================================================================
"""
Onboarding collects per-tenant trust thresholds but the gate ignored them.
TrustGateConfig.from_tenant_settings maps them on, defaulting + clamping safely.
"""

import pytest

from app.stratum.core.trust_gate import TrustGateConfig

pytestmark = pytest.mark.unit


def test_defaults_when_no_settings():
    c = TrustGateConfig.from_tenant_settings(None)
    assert c.pass_threshold == 70.0
    assert c.hold_threshold == 40.0
    # An empty dict is also the default path.
    assert TrustGateConfig.from_tenant_settings({}).pass_threshold == 70.0


def test_overrides_from_tenant_settings():
    c = TrustGateConfig.from_tenant_settings(
        {"trust_threshold_autopilot": 85, "trust_threshold_alert": 55}
    )
    assert c.pass_threshold == 85.0
    assert c.hold_threshold == 55.0


def test_clamps_to_0_100():
    c = TrustGateConfig.from_tenant_settings(
        {"trust_threshold_autopilot": 250, "trust_threshold_alert": -10}
    )
    assert c.pass_threshold == 100.0
    assert c.hold_threshold == 0.0


def test_keeps_hold_below_or_equal_pass():
    c = TrustGateConfig.from_tenant_settings(
        {"trust_threshold_autopilot": 30, "trust_threshold_alert": 60}
    )
    assert c.pass_threshold == 30.0
    assert c.hold_threshold == 30.0  # clamped down to pass


def test_ignores_non_numeric_and_bool():
    c = TrustGateConfig.from_tenant_settings(
        {"trust_threshold_autopilot": "high", "trust_threshold_alert": True}
    )
    assert c.pass_threshold == 70.0  # unchanged
    assert c.hold_threshold == 40.0  # bool is not accepted


def test_partial_settings_keep_other_default():
    c = TrustGateConfig.from_tenant_settings({"trust_threshold_autopilot": 90})
    assert c.pass_threshold == 90.0
    assert c.hold_threshold == 40.0  # default
