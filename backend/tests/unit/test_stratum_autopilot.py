# =============================================================================
# Stratum AI - Autopilot Rule Engine unit tests
# =============================================================================
"""Unit tests for app.stratum.core.autopilot.

Pure rule-evaluation logic (the one async entry point is exercised via
asyncio.run with a real TrustGate). Covers the budget-pacing,
performance-scaling, and status-management rules, plus engine rule
management and the trust-gated evaluate_campaign integration.
"""

import asyncio
from datetime import datetime, timezone

import pytest

from app.stratum.core.autopilot import (
    AutopilotEngine,
    BudgetPacingRule,
    PerformanceScalingRule,
    RuleContext,
    RuleType,
    StatusManagementRule,
)
from app.stratum.models import (
    AutomationAction,
    PerformanceMetrics,
    Platform,
    SignalHealth,
    UnifiedCampaign,
)

pytestmark = pytest.mark.unit


def _campaign(daily_budget=100.0):
    return UnifiedCampaign(
        platform=Platform.META,
        account_id="acct_1",
        campaign_id="camp_1",
        campaign_name="Test Campaign",
        daily_budget=daily_budget,
    )


def _metrics(spend=50.0, conversions=10, roas=None, cpa=None):
    return PerformanceMetrics(
        spend=spend,
        conversions=conversions,
        roas=roas,
        cpa=cpa,
    )


def _health(score=85.0):
    return SignalHealth(
        overall_score=score,
        emq_score=score,
        freshness_score=score,
        variance_score=score,
        anomaly_score=score,
    )


def _context(campaign=None, metrics=None, hour=12, **kwargs):
    defaults = dict(
        platform=Platform.META,
        account_id="acct_1",
        campaign=campaign or _campaign(),
        adsets=[],
        metrics=metrics or _metrics(),
        signal_health=_health(),
        historical_metrics=[],
        current_time=datetime(2026, 6, 1, hour, 0, tzinfo=timezone.utc),
        days_since_last_change=10,  # past cooldown by default
    )
    defaults.update(kwargs)
    return RuleContext(**defaults)


# =============================================================================
# BudgetPacingRule
# =============================================================================
class TestBudgetPacing:
    def test_insufficient_data(self):
        rule = BudgetPacingRule()
        result = rule.evaluate(_context(campaign=_campaign(daily_budget=0)))
        assert result.triggered is False
        assert "Insufficient data" in result.reasoning

    def test_underpacing_increases_budget(self):
        # hour 12 -> expected ~54% spend; actual 10% -> pace ratio ~0.19 < 0.7
        rule = BudgetPacingRule()
        ctx = _context(metrics=_metrics(spend=10.0), hour=12)
        result = rule.evaluate(ctx)
        assert result.triggered is True
        assert result.actions[0].action_type == "update_budget"
        # +20% from 100 -> 120
        assert result.actions[0].parameters["daily_budget"] == 120.0
        assert result.confidence == 0.8

    def test_underpacing_respects_max_budget(self):
        rule = BudgetPacingRule()
        ctx = _context(metrics=_metrics(spend=10.0), hour=12, max_daily_budget=110.0)
        result = rule.evaluate(ctx)
        assert result.actions[0].parameters["daily_budget"] == 110.0

    def test_overpacing_flags_no_action(self):
        # hour 0 -> expected ~4% spend; actual 90% -> huge overpace
        rule = BudgetPacingRule()
        ctx = _context(metrics=_metrics(spend=90.0), hour=0)
        result = rule.evaluate(ctx)
        assert result.triggered is True
        assert result.actions == []  # over-pacing logged, not auto-adjusted
        assert "Over-pacing" in result.reasoning

    def test_on_pace_no_trigger(self):
        # hour 12 (~54% expected), spend 54 -> pace ~1.0
        rule = BudgetPacingRule()
        ctx = _context(metrics=_metrics(spend=54.0), hour=12)
        result = rule.evaluate(ctx)
        assert result.triggered is False


# =============================================================================
# PerformanceScalingRule
# =============================================================================
class TestPerformanceScaling:
    def test_cooldown_blocks(self):
        rule = PerformanceScalingRule(cooldown_days=2)
        result = rule.evaluate(_context(days_since_last_change=1))
        assert result.triggered is False
        assert "cooldown" in result.reasoning

    def test_insufficient_conversions(self):
        rule = PerformanceScalingRule(min_conversions=5)
        result = rule.evaluate(_context(metrics=_metrics(conversions=2)))
        assert result.triggered is False
        assert "Insufficient conversions" in result.reasoning

    def test_high_roas_scales_up(self):
        rule = PerformanceScalingRule()
        ctx = _context(metrics=_metrics(conversions=10, roas=4.0), target_roas=2.0)
        result = rule.evaluate(ctx)
        assert result.triggered is True
        # +20% from 100 -> 120
        assert result.actions[0].parameters["daily_budget"] == 120.0

    def test_scale_up_capped_by_max_change_percent(self):
        rule = PerformanceScalingRule(scale_up_multiplier=2.0)
        ctx = _context(
            metrics=_metrics(conversions=10, roas=5.0),
            target_roas=2.0,
            max_budget_change_percent=10.0,  # cap rise at +10% -> 110
        )
        result = rule.evaluate(ctx)
        assert result.actions[0].parameters["daily_budget"] == 110.0

    def test_low_roas_scales_down(self):
        rule = PerformanceScalingRule()
        ctx = _context(metrics=_metrics(conversions=10, roas=1.0), target_roas=2.0)
        result = rule.evaluate(ctx)
        assert result.triggered is True
        # -20% from 100 -> 80
        assert result.actions[0].parameters["daily_budget"] == 80.0

    def test_low_roas_respects_min_budget(self):
        rule = PerformanceScalingRule()
        ctx = _context(
            metrics=_metrics(conversions=10, roas=1.0),
            target_roas=2.0,
            min_daily_budget=90.0,
        )
        result = rule.evaluate(ctx)
        assert result.actions[0].parameters["daily_budget"] == 90.0

    def test_efficient_cpa_scales_up(self):
        rule = PerformanceScalingRule()
        ctx = _context(metrics=_metrics(conversions=10, cpa=8.0), target_cpa=20.0)
        result = rule.evaluate(ctx)
        assert result.triggered is True
        assert result.actions[0].parameters["daily_budget"] == 120.0

    def test_no_targets_no_action(self):
        rule = PerformanceScalingRule()
        result = rule.evaluate(_context(metrics=_metrics(conversions=10)))
        assert result.triggered is False
        assert "No performance targets" in result.reasoning


# =============================================================================
# StatusManagementRule
# =============================================================================
class TestStatusManagement:
    def test_low_roas_pauses(self):
        rule = StatusManagementRule(min_roas_multiplier=0.5)
        ctx = _context(metrics=_metrics(roas=0.4), min_roas=2.0)  # 0.4 < 2*0.5=1.0
        result = rule.evaluate(ctx)
        assert result.triggered is True
        assert result.actions[0].action_type == "update_status"
        assert result.actions[0].parameters["status"] == "paused"

    def test_high_cpa_pauses(self):
        rule = StatusManagementRule(max_cpa_multiplier=2.0)
        ctx = _context(metrics=_metrics(cpa=50.0), max_cpa=20.0)  # 50 > 20*2=40
        result = rule.evaluate(ctx)
        assert result.triggered is True
        assert result.actions[0].parameters["status"] == "paused"

    def test_consistent_poor_history_pauses(self):
        rule = StatusManagementRule(pause_after_days=3)
        poor = [_metrics(roas=1.0) for _ in range(3)]  # all < target*0.7
        ctx = _context(target_roas=2.0, historical_metrics=poor)
        result = rule.evaluate(ctx)
        assert result.triggered is True

    def test_healthy_no_action(self):
        rule = StatusManagementRule()
        ctx = _context(metrics=_metrics(roas=3.0), min_roas=2.0, max_cpa=20.0)
        result = rule.evaluate(ctx)
        assert result.triggered is False
        assert "No status issues" in result.reasoning


# =============================================================================
# AutopilotEngine management
# =============================================================================
class TestEngineManagement:
    def test_default_rules_loaded(self):
        engine = AutopilotEngine()
        names = {r.name for r in engine.rules}
        assert names == {"budget_pacing", "performance_scaling", "status_management"}

    def test_add_get_remove_rule(self):
        engine = AutopilotEngine()
        custom = BudgetPacingRule()
        custom.name = "custom_pacer"
        engine.add_rule(custom)
        assert engine.get_rule("custom_pacer") is custom
        assert engine.remove_rule("custom_pacer") is True
        assert engine.get_rule("custom_pacer") is None
        assert engine.remove_rule("nonexistent") is False

    def test_list_rules(self):
        rules = AutopilotEngine().list_rules()
        assert len(rules) == 3
        assert all({"name", "type", "enabled"} <= set(r) for r in rules)

    def test_get_stats(self):
        stats = AutopilotEngine().get_stats()
        assert stats["total_rules"] == 3
        assert stats["enabled_rules"] == 3
        assert stats["rules_by_type"]["budget_pacing"] == 1
        assert "trust_gate_stats" in stats


# =============================================================================
# evaluate_campaign (rules + trust gate integration)
# =============================================================================
class TestEvaluateCampaign:
    def test_evaluate_campaign_structure_and_gate_integration(self):
        # status_management triggers a pause deterministically (low ROAS), and
        # a healthy signal sends its action through the trust gate.
        engine = AutopilotEngine()
        results = asyncio.run(
            engine.evaluate_campaign(
                platform=Platform.META,
                account_id="acct_1",
                campaign=_campaign(),
                adsets=[],
                metrics=_metrics(spend=10.0, conversions=10, roas=0.3),
                signal_health=_health(90.0),
                targets={"min_roas": 2.0},
            )
        )
        # one result per rule, each well-formed and error-free
        assert len(results) == 3
        for r in results:
            assert {"rule_name", "triggered", "reasoning", "gate_results"} <= set(r)
            assert not r["reasoning"].startswith("Error")
        status = next(r for r in results if r["rule_name"] == "status_management")
        assert status["triggered"] is True
        assert status["actions"][0]["action_type"] == "update_status"
        # healthy signal -> each triggered action evaluated by the trust gate
        assert status["gate_results"][0]["decision"] in {"pass", "hold", "block"}

    def test_disabled_rule_skipped(self):
        engine = AutopilotEngine()
        engine.get_rule("status_management").enabled = False
        results = asyncio.run(
            engine.evaluate_campaign(
                platform=Platform.META,
                account_id="acct_1",
                campaign=_campaign(),
                adsets=[],
                metrics=_metrics(),
                signal_health=_health(),
            )
        )
        names = {r["rule_name"] for r in results}
        assert "status_management" not in names
        assert len(results) == 2

    def test_create_action_stamps_signal_health(self):
        # Regression: _create_action used signal_health.score (AttributeError)
        # and passed dropped kwargs; now stamps the real field + records the rule.
        rule = BudgetPacingRule()
        action = rule._create_action(
            _context(),
            entity_type="campaign",
            entity_id="camp_1",
            action_type="update_budget",
            parameters={"daily_budget": 120.0},
        )
        assert isinstance(action, AutomationAction)
        assert action.signal_health_at_execution == 85.0
        assert action.parameters["created_by"] == "autopilot:budget_pacing"
        assert action.parameters["daily_budget"] == 120.0
