# =============================================================================
# Stratum AI - Budget Reallocation Service unit tests
# =============================================================================
"""Unit tests for app.services.budget_reallocation_service.

Pure in-memory budget optimization, no I/O. Covers plan creation with
data-quality filtering, strategy scoring, guardrail checks, the
approve/execute/rollback lifecycle, simulation, and the P2 enhancement
optimizers (multi-objective Pareto, portfolio theory, allocation
learning).
"""

import pytest

from app.services.budget_reallocation_service import (
    AllocationLearner,
    BudgetChange,
    BudgetReallocationService,
    CampaignBudgetState,
    GuardrailViolation,
    MultiObjectiveOptimizer,
    PortfolioAllocator,
    ReallocationConfig,
    ReallocationStatus,
    ReallocationStrategy,
    create_reallocation_plan,
)

pytestmark = pytest.mark.unit


def _campaign(
    campaign_id="c1",
    budget=100.0,
    roas=2.0,
    cvr=2.0,
    cpa=50.0,
    conversions=20,
    quality=0.9,
    platform="meta",
):
    return CampaignBudgetState(
        campaign_id=campaign_id,
        campaign_name=f"Campaign {campaign_id}",
        platform=platform,
        current_daily_budget=budget,
        current_spend=budget,
        performance_metrics={
            "roas": roas,
            "ctr": 1.0,
            "cvr": cvr,
            "cpa": cpa,
            "conversions": conversions,
        },
        data_quality_score=quality,
    )


def _change(campaign_id="c1", current=100.0, new=110.0, percent=10.0):
    return BudgetChange(
        campaign_id=campaign_id,
        campaign_name=f"Campaign {campaign_id}",
        platform="meta",
        current_budget=current,
        new_budget=new,
        change_amount=new - current,
        change_percent=percent,
        reason="test",
        expected_impact={},
    )


# =============================================================================
# Plan creation
# =============================================================================
class TestCreatePlan:
    def test_basic_plan(self):
        svc = BudgetReallocationService()
        plan = svc.create_plan("t1", [_campaign("a"), _campaign("b")])
        assert plan.status == ReallocationStatus.PROPOSED
        assert plan.total_current_budget == 200.0
        assert plan.total_new_budget == 200.0
        assert len(plan.changes) == 2
        assert svc.get_plan(plan.plan_id) is plan
        assert plan.rollback_plan == {"a": 100.0, "b": 100.0}

    def test_low_quality_campaigns_excluded(self):
        svc = BudgetReallocationService()
        plan = svc.create_plan(
            "t1",
            [_campaign("good", quality=0.9), _campaign("bad", quality=0.3)],
        )
        assert [c.campaign_id for c in plan.changes] == ["good"]

    def test_all_low_quality_falls_back_to_all(self):
        svc = BudgetReallocationService()
        plan = svc.create_plan(
            "t1",
            [_campaign("a", quality=0.1), _campaign("b", quality=0.2)],
        )
        assert len(plan.changes) == 2

    def test_explicit_total_budget(self):
        svc = BudgetReallocationService()
        config = ReallocationConfig(total_budget=500.0)
        plan = svc.create_plan("t1", [_campaign("a"), _campaign("b")], config)
        assert plan.total_new_budget == 500.0

    def test_changes_respect_max_change_percent(self):
        svc = BudgetReallocationService()
        config = ReallocationConfig(max_change_percent=30.0)
        plan = svc.create_plan(
            "t1",
            [_campaign("hot", roas=10.0), _campaign("cold", roas=0.5)],
            config,
        )
        for change in plan.changes:
            assert abs(change.change_percent) <= 30.0
        assert plan.guardrail_check.passed is True


# =============================================================================
# Strategy scoring
# =============================================================================
class TestCampaignScore:
    def _score(self, strategy, **kwargs):
        svc = BudgetReallocationService()
        return svc._calculate_campaign_score(
            _campaign(**kwargs).performance_metrics, strategy
        )

    def test_roas_maximization(self):
        score = self._score(ReallocationStrategy.ROAS_MAXIMIZATION, roas=3.0, cvr=5.0)
        assert score == pytest.approx(3.0 * 0.7 + 0.5 * 0.3)

    def test_volume_maximization(self):
        score = self._score(
            ReallocationStrategy.VOLUME_MAXIMIZATION, conversions=100, cpa=49.0
        )
        assert score == pytest.approx(10 * 0.6 + 2 * 0.4)

    def test_profit_maximization(self):
        score = self._score(
            ReallocationStrategy.PROFIT_MAXIMIZATION, roas=3.0, conversions=100
        )
        assert score == pytest.approx(200.0)

    def test_profit_floor_for_losing_campaigns(self):
        score = self._score(
            ReallocationStrategy.PROFIT_MAXIMIZATION, roas=0.5, conversions=100
        )
        assert score == 0.1

    def test_balanced(self):
        score = self._score(ReallocationStrategy.BALANCED, roas=5.0, cpa=99.0, cvr=10.0)
        assert score == pytest.approx(1.0 * 0.4 + (100 / 100) * 0.3 + 1.0 * 0.3)


class TestReasonsAndImpact:
    def test_reason_tiers(self):
        svc = BudgetReallocationService()
        campaign = _campaign(roas=4.0)
        assert "High performer" in svc._generate_change_reason(
            campaign, 0.9, ReallocationStrategy.BALANCED
        )
        assert "Underperforming" in svc._generate_change_reason(
            campaign, 0.1, ReallocationStrategy.BALANCED
        )
        moderate = svc._generate_change_reason(
            campaign, 0.5, ReallocationStrategy.BALANCED
        )
        assert "balanced strategy" in moderate

    def test_impact_elasticity_asymmetric(self):
        svc = BudgetReallocationService()
        up = svc._estimate_impact(_campaign(), 30.0)
        assert up["conversions_change_percent"] == 21.0  # 30 * 0.7
        down = svc._estimate_impact(_campaign(), -20.0)
        assert down["conversions_change_percent"] == -18.0  # -20 * 0.9


# =============================================================================
# Guardrails
# =============================================================================
class TestGuardrails:
    def test_violations_detected_and_deduped(self):
        svc = BudgetReallocationService()
        config = ReallocationConfig(max_change_percent=30.0)
        check = svc._check_guardrails(
            [
                _change("a", new=150.0, percent=50.0),
                _change("b", new=180.0, percent=80.0),
                _change("c", new=5.0, percent=-95.0),
                _change("d", new=20000.0, percent=10.0),
            ],
            config,
        )
        assert check.passed is False
        assert set(check.violations) == {
            GuardrailViolation.MAX_CHANGE_EXCEEDED,
            GuardrailViolation.MIN_BUDGET_VIOLATED,
            GuardrailViolation.MAX_BUDGET_VIOLATED,
        }
        assert "a_max_change" in check.details

    def test_large_change_warning_only(self):
        svc = BudgetReallocationService()
        check = svc._check_guardrails(
            [_change("a", new=125.0, percent=25.0)], ReallocationConfig()
        )
        assert check.passed is True
        assert len(check.warnings) == 1
        assert "+25.0%" in check.warnings[0]

    def test_clean_changes_pass(self):
        svc = BudgetReallocationService()
        check = svc._check_guardrails(
            [_change("a", new=110.0, percent=10.0)], ReallocationConfig()
        )
        assert check.passed is True
        assert check.warnings == []


# =============================================================================
# Lifecycle: approve / execute / rollback / simulate / list
# =============================================================================
class TestLifecycle:
    def _approved_plan(self, svc):
        plan = svc.create_plan("t1", [_campaign("a", roas=3.0), _campaign("b")])
        assert svc.approve(plan.plan_id, approved_by="alice") is True
        return plan

    def test_approve_happy_path(self):
        svc = BudgetReallocationService()
        plan = self._approved_plan(svc)
        assert plan.status == ReallocationStatus.APPROVED
        assert plan.approved_by == "alice"
        assert plan.approved_at is not None

    def test_approve_unknown_plan(self):
        assert BudgetReallocationService().approve("ghost", "alice") is False

    def test_approve_twice_rejected(self):
        svc = BudgetReallocationService()
        plan = self._approved_plan(svc)
        assert svc.approve(plan.plan_id, "bob") is False

    def test_approve_blocked_by_guardrails(self):
        svc = BudgetReallocationService()
        plan = svc.create_plan("t1", [_campaign("a")])
        plan.guardrail_check.passed = False
        assert svc.approve(plan.plan_id, "alice") is False

    def test_execute_requires_approval(self):
        svc = BudgetReallocationService()
        plan = svc.create_plan("t1", [_campaign("a")])
        result = svc.execute(plan.plan_id)
        assert result.success is False
        assert result.changes_failed[0][1] == "Plan not approved"

    def test_execute_unknown_plan(self):
        result = BudgetReallocationService().execute("ghost")
        assert result.success is False
        assert result.changes_failed[0][1] == "Plan not found"

    def test_execute_happy_path(self):
        svc = BudgetReallocationService()
        plan = self._approved_plan(svc)
        result = svc.execute(plan.plan_id)
        assert result.success is True
        assert len(result.changes_applied) == len(plan.changes)
        assert plan.status == ReallocationStatus.COMPLETED
        assert plan.executed_at is not None
        assert svc._execution_history[-1] is result

    def test_rollback_restores_original_budgets(self):
        svc = BudgetReallocationService()
        plan = self._approved_plan(svc)
        svc.execute(plan.plan_id)
        result = svc.rollback(plan.plan_id)
        assert result.success is True
        assert plan.status == ReallocationStatus.ROLLED_BACK
        restored = {c.campaign_id: c.new_budget for c in result.changes_applied}
        assert restored == {"a": 100.0, "b": 100.0}

    def test_rollback_unknown_plan(self):
        result = BudgetReallocationService().rollback("ghost")
        assert result.success is False

    def test_rollback_without_rollback_data(self):
        svc = BudgetReallocationService()
        plan = svc.create_plan("t1", [_campaign("a")])
        plan.rollback_plan = None
        result = svc.rollback(plan.plan_id)
        assert result.success is False
        assert result.changes_failed[0][1] == "No rollback data available"

    def test_simulate_unknown_plan(self):
        assert BudgetReallocationService().simulate("ghost") == {
            "error": "Plan not found"
        }

    def test_simulate_summarizes_plan(self):
        svc = BudgetReallocationService()
        plan = svc.create_plan(
            "t1", [_campaign("hot", roas=8.0), _campaign("cold", roas=0.5)]
        )
        sim = svc.simulate(plan.plan_id)
        assert sim["plan_id"] == plan.plan_id
        assert sim["num_campaigns_affected"] == 2
        assert sim["campaigns_increasing"] >= 1
        assert sim["campaigns_decreasing"] >= 1
        assert sim["guardrails"]["passed"] is True
        assert len(sim["changes_preview"]) == 2

    def test_list_plans_filters(self):
        svc = BudgetReallocationService()
        plan1 = svc.create_plan("t1", [_campaign("a")])
        svc.create_plan("t2", [_campaign("b")])
        svc.approve(plan1.plan_id, "alice")
        assert len(svc.list_plans()) == 2
        assert len(svc.list_plans(tenant_id="t1")) == 1
        approved = svc.list_plans(status=ReallocationStatus.APPROVED)
        assert [p.plan_id for p in approved] == [plan1.plan_id]


# =============================================================================
# Convenience wrapper (module singleton)
# =============================================================================
class TestConvenience:
    def test_create_reallocation_plan_dict_api(self):
        result = create_reallocation_plan(
            tenant_id="ut_realloc_t1",
            campaigns=[
                {"campaign_id": "x", "daily_budget": 100.0, "roas": 3.0},
                {"campaign_id": "y", "daily_budget": 100.0, "roas": 1.0},
            ],
            strategy="not_a_strategy",  # falls back to balanced
        )
        assert result["plan_id"].startswith("realloc_")
        assert result["status"] == "proposed"
        assert result["total_current_budget"] == 200.0
        assert len(result["changes"]) == 2


# =============================================================================
# MultiObjectiveOptimizer
# =============================================================================
class TestMultiObjectiveOptimizer:
    def test_evaluate_allocation_math(self):
        optimizer = MultiObjectiveOptimizer()
        campaigns = [_campaign("a", roas=2.0, cvr=5.0)]
        metrics = optimizer._evaluate_allocation(campaigns, {"a": 100.0})
        assert metrics["roas"] == 2.0
        assert metrics["volume"] == 10.0  # 100 * 5 / 50
        assert metrics["profit"] == 100.0

    def test_dominates(self):
        optimizer = MultiObjectiveOptimizer()
        objectives = ["roas", "volume", "profit"]
        better = {"roas": 3.0, "volume": 10.0, "profit": 100.0}
        worse = {"roas": 2.0, "volume": 10.0, "profit": 90.0}
        assert optimizer._dominates(better, worse, objectives) is True
        assert optimizer._dominates(worse, better, objectives) is False
        assert optimizer._dominates(better, dict(better), objectives) is False

    def test_optimize_returns_pareto_frontier(self):
        optimizer = MultiObjectiveOptimizer()
        campaigns = [
            _campaign("a", roas=4.0, conversions=10),
            _campaign("b", roas=1.0, conversions=200),
            _campaign("c", roas=2.0, conversions=50),
        ]
        frontier = optimizer.optimize(campaigns, total_budget=300.0)
        assert 0 < len(frontier) <= 5
        for point in frontier:
            assert set(point.allocation) <= {"a", "b", "c"}
            assert point.trade_off_description

    def test_trade_off_descriptions(self):
        optimizer = MultiObjectiveOptimizer()
        rich = optimizer._describe_trade_off(
            {"roas": 4.0, "volume": 200.0, "profit": 20000.0}, []
        )
        assert rich == "High efficiency | High volume | Strong profit"
        assert (
            optimizer._describe_trade_off(
                {"roas": 1.0, "volume": 5.0, "profit": 10.0}, []
            )
            == "Balanced approach"
        )


# =============================================================================
# PortfolioAllocator
# =============================================================================
class TestPortfolioAllocator:
    def test_equal_split_without_history(self):
        allocator = PortfolioAllocator()
        campaigns = [_campaign("a", roas=2.0), _campaign("b", roas=2.0)]
        portfolio = allocator.optimize_portfolio(
            campaigns, total_budget=100.0, risk_tolerance=0.5
        )
        assert portfolio.allocations["a"] == pytest.approx(50.0)
        assert portfolio.expected_return == 2.0
        assert portfolio.diversification_score == 0.5  # 1 - 2*(0.5^2)

    def test_aggressive_tolerance_favors_sharpe(self):
        allocator = PortfolioAllocator()
        for roas in [3.0, 4.0, 5.0]:  # mean 4, stdev 1 -> sharpe 4
            allocator.record_return("steady", roas)
        campaigns = [
            _campaign("steady", roas=4.0),
            _campaign("untested", roas=1.0),  # sharpe 1/0.4 = 2.5
        ]
        portfolio = allocator.optimize_portfolio(
            campaigns, total_budget=100.0, risk_tolerance=1.0
        )
        assert portfolio.allocations["steady"] > portfolio.allocations["untested"]

    def test_history_capped_at_90(self):
        allocator = PortfolioAllocator()
        for i in range(100):
            allocator.record_return("a", float(i))
        assert len(allocator._historical_returns["a"]) == 90
        assert allocator._historical_returns["a"][0] == 10.0


# =============================================================================
# AllocationLearner
# =============================================================================
class TestAllocationLearner:
    def _seed(self, learner, roas, n=5):
        for i in range(n):
            learner.record_allocation(
                plan_id=f"p{i}",
                allocations={"c1": 50.0, "c2": 50.0},
                context={"season": "q4"},
                outcome={"roas": roas},
            )

    def test_insufficient_history(self):
        learning = AllocationLearner().get_recommendation({"c1": 100.0}, {})
        assert "Insufficient historical data" in learning.recommendation
        assert learning.confidence == 0.3

    def test_successful_pattern_recommended(self):
        learner = AllocationLearner()
        self._seed(learner, roas=3.0)
        learning = learner.get_recommendation(
            {"c1": 50.0, "c2": 50.0}, {"season": "q4"}
        )
        assert "performed well" in learning.recommendation
        assert learning.confidence == 0.8
        assert any("Average ROAS: 3.00" in e for e in learning.supporting_evidence)
        assert len(learning.similar_past_allocations) == 3

    def test_failing_pattern_flagged(self):
        learner = AllocationLearner()
        self._seed(learner, roas=1.0)
        learning = learner.get_recommendation(
            {"c1": 50.0, "c2": 50.0}, {"season": "q4"}
        )
        assert "underperformed" in learning.recommendation
        assert learning.confidence == 0.7

    def test_novel_allocation_cautioned(self):
        learner = AllocationLearner()
        self._seed(learner, roas=3.0)
        learning = learner.get_recommendation({"brand_new": 100.0}, {"season": "q4"})
        assert "No similar" in learning.recommendation
        assert learning.confidence == 0.4

    def test_context_similarity(self):
        learner = AllocationLearner()
        assert learner._context_similarity({}, {"a": 1}) == 0.5
        assert learner._context_similarity({"a": 1}, {"a": 1}) == 1.0
        assert learner._context_similarity({"a": 1}, {"b": 2}) == 0.5
        assert learner._context_similarity({"a": 1, "b": 2}, {"a": 1, "b": 9}) == 0.5
