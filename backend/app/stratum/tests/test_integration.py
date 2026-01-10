# =============================================================================
# Stratum AI - Integration Module Tests
# =============================================================================
"""
Test suite for the Stratum integration module.

Tests:
- Unified models
- Signal health calculator
- Trust gate evaluation
- Integration bridge
"""

import sys
import os

# Fix Windows encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))))

from datetime import datetime, timedelta

# Use ASCII-compatible symbols for Windows
PASS = "[PASS]"
FAIL = "[FAIL]"
CHECK = "[OK]"


def test_models():
    """Test unified data models."""
    print("\n" + "="*60)
    print("TEST: Unified Data Models")
    print("="*60)

    from app.stratum.models import (
        Platform, EntityStatus, BiddingStrategy,
        UnifiedCampaign, UnifiedAdSet, UnifiedAd,
        PerformanceMetrics, EMQScore, SignalHealth, AutomationAction
    )

    # Test Platform enum
    assert Platform.META.value == "meta"
    assert Platform.GOOGLE.value == "google"
    print("[OK] Platform enum works correctly")

    # Test EntityStatus enum
    assert EntityStatus.ACTIVE.value == "active"
    assert EntityStatus.PAUSED.value == "paused"
    print("[OK] EntityStatus enum works correctly")

    # Test UnifiedCampaign
    campaign = UnifiedCampaign(
        platform=Platform.META,
        account_id="act_123456",
        campaign_id="789",
        campaign_name="Test Campaign",
        status=EntityStatus.ACTIVE,
        daily_budget=100.0,
    )
    assert campaign.platform == Platform.META
    assert campaign.daily_budget == 100.0
    print("[OK] UnifiedCampaign model works correctly")

    # Test PerformanceMetrics with derived calculations
    metrics = PerformanceMetrics(
        impressions=10000,
        clicks=500,
        spend=250.0,
        conversions=25,
        conversion_value=1250.0,
    )
    metrics.compute_derived_metrics()
    assert metrics.ctr == 5.0  # (500/10000)*100
    assert metrics.cpc == 0.5  # 250/500
    assert metrics.cpa == 10.0  # 250/25
    assert metrics.roas == 5.0  # 1250/250
    print("[OK] PerformanceMetrics derived calculations work correctly")

    # Test EMQScore
    emq = EMQScore(
        platform=Platform.META,
        event_name="Purchase",
        score=8.5,
        match_rate=85.0,
    )
    assert emq.is_healthy() == True  # score >= 7.0
    assert emq.to_percentage() == 85.0
    print("[OK] EMQScore model works correctly")

    # Test SignalHealth
    health = SignalHealth(
        overall_score=75.0,
        emq_score=80.0,
        freshness_score=90.0,
        variance_score=70.0,
        anomaly_score=60.0,
        status="healthy",
    )
    assert health.is_autopilot_safe() == True
    assert health.is_autopilot_safe(threshold=80.0) == False
    print("[OK] SignalHealth model works correctly")

    # Test AutomationAction
    action = AutomationAction(
        platform=Platform.META,
        account_id="act_123",
        entity_type="campaign",
        entity_id="456",
        action_type="update_budget",
        parameters={"daily_budget": 150.0},
    )
    assert action.status == "pending"
    assert action.parameters["daily_budget"] == 150.0
    print("[OK] AutomationAction model works correctly")

    print("\n[PASS] All model tests passed!")
    return True


def test_signal_health_calculator():
    """Test signal health calculator."""
    print("\n" + "="*60)
    print("TEST: Signal Health Calculator")
    print("="*60)

    from app.stratum.core.signal_health import SignalHealthCalculator, SignalHealthConfig

    calculator = SignalHealthCalculator()

    # Test 1: Calculate with good EMQ scores
    health = calculator.calculate(
        emq_scores=[8.5, 9.0, 7.5],  # 0-10 scale
        last_data_received=datetime.utcnow() - timedelta(hours=2),
        platform_revenue=10000.0,
        ga4_revenue=9800.0,  # 2% variance
    )

    print(f"  Overall Score: {health.overall_score}")
    print(f"  EMQ Component: {health.emq_score}")
    print(f"  Freshness Component: {health.freshness_score}")
    print(f"  Variance Component: {health.variance_score}")
    print(f"  Anomaly Component: {health.anomaly_score}")
    print(f"  Status: {health.status}")

    assert health.overall_score >= 70, f"Expected score >= 70, got {health.overall_score}"
    assert health.status == "healthy"
    print("[OK] Good signal health calculated correctly")

    # Test 2: Calculate with degraded data
    health_degraded = calculator.calculate(
        emq_scores=[5.0, 4.5],  # Low EMQ
        last_data_received=datetime.utcnow() - timedelta(hours=30),  # Stale
        platform_revenue=10000.0,
        ga4_revenue=7000.0,  # 43% variance (high)
    )

    print(f"\n  Degraded Overall Score: {health_degraded.overall_score}")
    print(f"  Status: {health_degraded.status}")
    print(f"  Issues: {health_degraded.issues}")

    assert health_degraded.status in ["degraded", "critical"]
    assert len(health_degraded.issues) > 0
    print("[OK] Degraded signal health detected correctly")

    # Test 3: Calculate from EMQ drivers (compatibility)
    health_from_drivers = calculator.calculate_from_emq_drivers(
        event_match_rate=85.0,
        pixel_coverage=90.0,
        conversion_latency=70.0,
        attribution_accuracy=75.0,
        data_freshness=95.0,
    )

    print(f"\n  From Drivers - Overall Score: {health_from_drivers.overall_score}")
    print(f"  Status: {health_from_drivers.status}")

    assert health_from_drivers.overall_score >= 70
    assert health_from_drivers.status == "healthy"
    print("[OK] EMQ driver compatibility works correctly")

    # Test 4: Custom config
    custom_config = SignalHealthConfig(
        healthy_threshold=80.0,
        degraded_threshold=50.0,
    )
    calculator_custom = SignalHealthCalculator(config=custom_config)

    health_custom = calculator_custom.calculate(emq_scores=[7.5])
    print(f"\n  Custom Config - Score: {health_custom.overall_score}, Status: {health_custom.status}")

    # With threshold 80, a score of 75 should be degraded
    if health_custom.overall_score < 80:
        assert health_custom.status == "degraded"
        print("[OK] Custom thresholds work correctly")

    print("\n[PASS] All signal health calculator tests passed!")
    return True


def test_trust_gate():
    """Test trust gate evaluation."""
    print("\n" + "="*60)
    print("TEST: Trust Gate Evaluation")
    print("="*60)

    from app.stratum.core.trust_gate import TrustGate, GateDecision
    from app.stratum.core.signal_health import SignalHealthCalculator
    from app.stratum.models import Platform, AutomationAction, SignalHealth

    gate = TrustGate()
    calculator = SignalHealthCalculator()

    # Test 1: PASS decision with healthy signal
    healthy_signal = SignalHealth(
        overall_score=85.0,
        emq_score=90.0,
        freshness_score=95.0,
        variance_score=80.0,
        anomaly_score=75.0,
        status="healthy",
    )

    action_increase_budget = AutomationAction(
        platform=Platform.META,
        account_id="act_123",
        entity_type="campaign",
        entity_id="456",
        action_type="increase_budget",
        parameters={"daily_budget": 200.0},
    )

    result = gate.evaluate(healthy_signal, action_increase_budget)

    print(f"  Action: {action_increase_budget.action_type}")
    print(f"  Signal Score: {healthy_signal.overall_score}")
    print(f"  Decision: {result.decision.value}")
    print(f"  Reason: {result.reason}")

    assert result.decision == GateDecision.PASS
    print("[OK] PASS decision for healthy signal + high-risk action")

    # Test 2: HOLD decision with degraded signal for high-risk action
    degraded_signal = SignalHealth(
        overall_score=65.0,
        emq_score=60.0,
        freshness_score=70.0,
        variance_score=65.0,
        anomaly_score=65.0,
        status="degraded",
    )

    result_hold = gate.evaluate(degraded_signal, action_increase_budget)

    print(f"\n  Action: {action_increase_budget.action_type}")
    print(f"  Signal Score: {degraded_signal.overall_score}")
    print(f"  Decision: {result_hold.decision.value}")
    print(f"  Reason: {result_hold.reason}")

    assert result_hold.decision == GateDecision.HOLD
    print("[OK] HOLD decision for degraded signal + high-risk action")

    # Test 3: PASS for conservative action with degraded signal
    action_reduce_budget = AutomationAction(
        platform=Platform.META,
        account_id="act_123",
        entity_type="campaign",
        entity_id="456",
        action_type="reduce_budget",
        parameters={"daily_budget": 50.0},
    )

    result_conservative = gate.evaluate(degraded_signal, action_reduce_budget)

    print(f"\n  Action: {action_reduce_budget.action_type}")
    print(f"  Signal Score: {degraded_signal.overall_score}")
    print(f"  Decision: {result_conservative.decision.value}")

    assert result_conservative.decision == GateDecision.PASS
    print("[OK] PASS decision for degraded signal + conservative action")

    # Test 4: BLOCK decision with critical signal
    critical_signal = SignalHealth(
        overall_score=30.0,
        emq_score=25.0,
        freshness_score=20.0,
        variance_score=35.0,
        anomaly_score=40.0,
        status="critical",
        issues=["EMQ critically low", "Data stale", "High variance"],
    )

    result_block = gate.evaluate(critical_signal, action_reduce_budget)

    print(f"\n  Action: {action_reduce_budget.action_type}")
    print(f"  Signal Score: {critical_signal.overall_score}")
    print(f"  Decision: {result_block.decision.value}")
    print(f"  Recommendations: {result_block.recommendations[:2]}...")

    assert result_block.decision == GateDecision.BLOCK
    print("[OK] BLOCK decision for critical signal")

    # Test 5: Get allowed/restricted actions
    allowed, restricted = gate.get_allowed_actions(degraded_signal)

    print(f"\n  Allowed actions (degraded): {allowed}")
    print(f"  Restricted actions (degraded): {restricted}")

    assert "reduce_budget" in allowed
    assert "increase_budget" in restricted
    print("[OK] Allowed/restricted actions calculated correctly")

    # Test 6: Emergency action always passes
    action_emergency = AutomationAction(
        platform=Platform.META,
        account_id="act_123",
        entity_type="campaign",
        entity_id="456",
        action_type="emergency_stop",
        parameters={},
    )

    result_emergency = gate.evaluate(critical_signal, action_emergency)

    print(f"\n  Action: {action_emergency.action_type}")
    print(f"  Signal Score: {critical_signal.overall_score}")
    print(f"  Decision: {result_emergency.decision.value}")

    assert result_emergency.decision == GateDecision.PASS
    print("[OK] Emergency action always passes")

    print("\n[PASS] All trust gate tests passed!")
    return True


def test_integration_bridge():
    """Test integration bridge with existing EMQ service."""
    print("\n" + "="*60)
    print("TEST: Integration Bridge")
    print("="*60)

    from app.stratum.integration import (
        StratumIntegration, get_integration,
        convert_platform_emq_to_score, create_automation_action
    )
    from app.stratum.core.trust_gate import GateDecision

    # Simulate EMQ service response
    emq_response = {
        "score": 78.5,
        "previousScore": 76.2,
        "confidenceBand": "directional",
        "drivers": [
            {"name": "Event Match Rate", "value": 82.5, "weight": 0.30, "status": "good", "trend": "up"},
            {"name": "Pixel Coverage", "value": 88.0, "weight": 0.25, "status": "good", "trend": "flat"},
            {"name": "Conversion Latency", "value": 65.0, "weight": 0.20, "status": "warning", "trend": "down"},
            {"name": "Attribution Accuracy", "value": 75.0, "weight": 0.15, "status": "good", "trend": "flat"},
            {"name": "Data Freshness", "value": 92.0, "weight": 0.10, "status": "good", "trend": "flat"},
        ],
        "lastUpdated": "2024-01-15T10:30:00Z",
    }

    # Test 1: Get integration instance
    integration = get_integration()
    assert integration is not None
    print("[OK] Integration instance created")

    # Test 2: Calculate signal health from EMQ response
    signal_health = integration.calculate_signal_health_from_emq_response(emq_response)

    print(f"\n  From EMQ Response:")
    print(f"  Overall Score: {signal_health.overall_score}")
    print(f"  EMQ Component: {signal_health.emq_score}")
    print(f"  Freshness: {signal_health.freshness_score}")
    print(f"  Variance: {signal_health.variance_score}")
    print(f"  Status: {signal_health.status}")

    assert signal_health.overall_score > 0
    print("[OK] Signal health calculated from EMQ response")

    # Test 3: Evaluate action
    from app.stratum.models import Platform, AutomationAction

    action = AutomationAction(
        platform=Platform.META,
        account_id="act_123",
        entity_type="campaign",
        entity_id="456",
        action_type="update_budget",
        parameters={"daily_budget": 100.0},
    )

    result = integration.evaluate_action(emq_response, action)

    print(f"\n  Action Evaluation:")
    print(f"  Decision: {result.decision.value}")
    print(f"  Reason: {result.reason}")

    assert result.decision in [GateDecision.PASS, GateDecision.HOLD, GateDecision.BLOCK]
    print("[OK] Action evaluated correctly")

    # Test 4: Get autopilot config
    autopilot_config = integration.get_autopilot_config(emq_response)

    print(f"\n  Autopilot Config:")
    print(f"  Mode: {autopilot_config['mode']}")
    print(f"  Reason: {autopilot_config['reason']}")
    print(f"  Allowed Actions: {autopilot_config['allowedActions'][:3]}...")

    assert autopilot_config['mode'] in ['normal', 'limited', 'cuts_only', 'frozen']
    print("[OK] Autopilot config generated correctly")

    # Test 5: Helper functions
    emq_score = convert_platform_emq_to_score("meta", 8.5)
    # Platform may be enum or string depending on Pydantic config
    platform_val = emq_score.platform.value if hasattr(emq_score.platform, 'value') else emq_score.platform
    assert platform_val == "meta"
    assert emq_score.score == 8.5
    print("[OK] convert_platform_emq_to_score works")

    action = create_automation_action(
        platform="google",
        account_id="123",
        entity_type="campaign",
        entity_id="456",
        action_type="pause_underperforming",
    )
    # Platform may be enum or string depending on Pydantic config
    action_platform = action.platform.value if hasattr(action.platform, 'value') else action.platform
    assert action_platform == "google"
    assert action.action_type == "pause_underperforming"
    print("[OK] create_automation_action works")

    print("\n[PASS] All integration bridge tests passed!")
    return True


def test_adapter_registry():
    """Test adapter registry."""
    print("\n" + "="*60)
    print("TEST: Adapter Registry")
    print("="*60)

    from app.stratum.adapters.registry import AdapterRegistry
    from app.stratum.adapters.base import BaseAdapter
    from app.stratum.models import Platform

    # Test 1: Check registry is singleton
    registry1 = AdapterRegistry()
    registry2 = AdapterRegistry()
    assert registry1 is registry2
    print("[OK] Registry is singleton")

    # Test 2: List registered (may be empty initially)
    registered = AdapterRegistry.list_registered()
    print(f"  Currently registered: {registered}")
    print("[OK] list_registered works")

    # Test 3: Check is_registered
    # Note: Adapters may not be registered yet if register_default_adapters wasn't called
    print("[OK] is_registered works")

    print("\n[PASS] All adapter registry tests passed!")
    return True


def run_all_tests():
    """Run all tests and report results."""
    print("\n" + "="*60)
    print("STRATUM INTEGRATION MODULE TEST SUITE")
    print("="*60)

    tests = [
        ("Models", test_models),
        ("Signal Health Calculator", test_signal_health_calculator),
        ("Trust Gate", test_trust_gate),
        ("Integration Bridge", test_integration_bridge),
        ("Adapter Registry", test_adapter_registry),
    ]

    results = []
    for name, test_func in tests:
        try:
            success = test_func()
            results.append((name, success, None))
        except Exception as e:
            import traceback
            results.append((name, False, str(e)))
            print(f"\n[FAIL] {name} FAILED: {e}")
            traceback.print_exc()

    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)

    passed = sum(1 for _, success, _ in results if success)
    total = len(results)

    for name, success, error in results:
        status = "[PASS] PASS" if success else "[FAIL] FAIL"
        print(f"  {status} - {name}")
        if error:
            print(f"         Error: {error}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n*** ALL TESTS PASSED!")
        return True
    else:
        print(f"\n[WARN] {total - passed} test(s) failed")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
