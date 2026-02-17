# =============================================================================
# Stratum AI - Automated Budget Reallocation Service
# =============================================================================
"""
Service for intelligent automated budget reallocation across campaigns and platforms.

Provides:
- Performance-based budget optimization
- Cross-platform budget allocation
- Guardrails to prevent over/under-spending
- Simulation before execution
- Rollback capabilities
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import statistics
import uuid

from app.core.logging import get_logger

logger = get_logger(__name__)


class ReallocationStrategy(str, Enum):
    """Budget reallocation strategies."""
    ROAS_MAXIMIZATION = "roas_maximization"
    VOLUME_MAXIMIZATION = "volume_maximization"
    PROFIT_MAXIMIZATION = "profit_maximization"
    BALANCED = "balanced"
    CUSTOM = "custom"


class ReallocationStatus(str, Enum):
    """Status of a reallocation."""
    PROPOSED = "proposed"
    APPROVED = "approved"
    EXECUTING = "executing"
    COMPLETED = "completed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"


class GuardrailViolation(str, Enum):
    """Types of guardrail violations."""
    MAX_CHANGE_EXCEEDED = "max_change_exceeded"
    MIN_BUDGET_VIOLATED = "min_budget_violated"
    MAX_BUDGET_VIOLATED = "max_budget_violated"
    LOW_DATA_QUALITY = "low_data_quality"
    PERFORMANCE_DECLINING = "performance_declining"


@dataclass
class CampaignBudgetState:
    """Current budget state for a campaign."""
    campaign_id: str
    campaign_name: str
    platform: str
    current_daily_budget: float
    current_spend: float  # Actual spend in period
    performance_metrics: Dict[str, float]  # roas, ctr, cvr, cpa
    data_quality_score: float  # 0-1, based on EMQ and data freshness


@dataclass
class BudgetChange:
    """A proposed budget change."""
    campaign_id: str
    campaign_name: str
    platform: str
    current_budget: float
    new_budget: float
    change_amount: float
    change_percent: float
    reason: str
    expected_impact: Dict[str, float]  # Expected change in metrics


@dataclass
class GuardrailCheck:
    """Result of a guardrail check."""
    passed: bool
    violations: List[GuardrailViolation]
    warnings: List[str]
    details: Dict[str, Any]


@dataclass
class ReallocationConfig:
    """Configuration for budget reallocation."""
    strategy: ReallocationStrategy = ReallocationStrategy.BALANCED
    total_budget: Optional[float] = None  # If None, keep current total
    max_change_percent: float = 30.0  # Max budget change per campaign
    min_campaign_budget: float = 10.0  # Minimum daily budget
    max_campaign_budget: float = 10000.0  # Maximum daily budget
    min_data_quality: float = 0.6  # Minimum EMQ score to include
    lookback_days: int = 7  # Days of data to analyze
    require_approval: bool = True  # Require human approval


@dataclass
class ReallocationPlan:
    """A complete budget reallocation plan."""
    plan_id: str
    tenant_id: str
    created_at: datetime
    strategy: ReallocationStrategy
    config: ReallocationConfig

    # Current state
    total_current_budget: float
    total_new_budget: float

    # Proposed changes
    changes: List[BudgetChange]

    # Guardrail results
    guardrail_check: GuardrailCheck

    # Expected outcomes
    expected_roas_change: float
    expected_revenue_change: float
    expected_spend_change: float

    # Status
    status: ReallocationStatus
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    executed_at: Optional[datetime] = None
    rollback_plan: Optional[Dict[str, float]] = None  # campaign_id -> original budget


@dataclass
class ReallocationResult:
    """Result of executing a reallocation."""
    plan_id: str
    success: bool
    changes_applied: List[BudgetChange]
    changes_failed: List[Tuple[BudgetChange, str]]  # (change, error message)
    execution_time: datetime


class BudgetReallocationService:
    """
    Service for automated budget reallocation.

    Usage:
        service = BudgetReallocationService()

        # Create reallocation plan
        plan = service.create_plan(
            tenant_id="tenant_123",
            campaigns=campaign_states,
            config=ReallocationConfig(
                strategy=ReallocationStrategy.ROAS_MAXIMIZATION,
                max_change_percent=25.0,
            )
        )

        # Simulate impact
        simulation = service.simulate(plan)

        # Approve and execute
        if plan.guardrail_check.passed:
            service.approve(plan.plan_id, approved_by="user_123")
            result = service.execute(plan.plan_id)
    """

    def __init__(self):
        self._plans: Dict[str, ReallocationPlan] = {}
        self._execution_history: List[ReallocationResult] = []

    def create_plan(
        self,
        tenant_id: str,
        campaigns: List[CampaignBudgetState],
        config: Optional[ReallocationConfig] = None,
    ) -> ReallocationPlan:
        """
        Create a budget reallocation plan.

        Args:
            tenant_id: Tenant identifier
            campaigns: Current state of campaigns
            config: Reallocation configuration

        Returns:
            ReallocationPlan with proposed changes
        """
        if config is None:
            config = ReallocationConfig()

        plan_id = f"realloc_{uuid.uuid4().hex[:12]}"

        # Filter campaigns by data quality
        eligible_campaigns = [
            c for c in campaigns
            if c.data_quality_score >= config.min_data_quality
        ]

        if not eligible_campaigns:
            logger.warning("No campaigns meet data quality threshold")
            eligible_campaigns = campaigns  # Fall back to all campaigns

        # Calculate current totals
        total_current = sum(c.current_daily_budget for c in eligible_campaigns)
        total_new = config.total_budget if config.total_budget else total_current

        # Calculate optimal allocation based on strategy
        changes = self._calculate_allocation(
            campaigns=eligible_campaigns,
            total_budget=total_new,
            strategy=config.strategy,
            config=config,
        )

        # Check guardrails
        guardrail_check = self._check_guardrails(changes, config)

        # Calculate expected outcomes
        expected_outcomes = self._calculate_expected_outcomes(changes, campaigns)

        plan = ReallocationPlan(
            plan_id=plan_id,
            tenant_id=tenant_id,
            created_at=datetime.now(timezone.utc),
            strategy=config.strategy,
            config=config,
            total_current_budget=total_current,
            total_new_budget=total_new,
            changes=changes,
            guardrail_check=guardrail_check,
            expected_roas_change=expected_outcomes["roas_change"],
            expected_revenue_change=expected_outcomes["revenue_change"],
            expected_spend_change=expected_outcomes["spend_change"],
            status=ReallocationStatus.PROPOSED,
            rollback_plan={c.campaign_id: c.current_budget for c in changes},
        )

        self._plans[plan_id] = plan

        logger.info(f"Created reallocation plan {plan_id} with {len(changes)} changes")

        return plan

    def _calculate_allocation(
        self,
        campaigns: List[CampaignBudgetState],
        total_budget: float,
        strategy: ReallocationStrategy,
        config: ReallocationConfig,
    ) -> List[BudgetChange]:
        """Calculate optimal budget allocation."""
        changes = []

        if not campaigns:
            return changes

        # Calculate performance scores based on strategy
        scores = {}
        for campaign in campaigns:
            metrics = campaign.performance_metrics
            score = self._calculate_campaign_score(metrics, strategy)
            scores[campaign.campaign_id] = score

        # Normalize scores
        total_score = sum(scores.values())
        if total_score == 0:
            # Equal distribution if no performance data
            for campaign in campaigns:
                scores[campaign.campaign_id] = 1.0 / len(campaigns)
            total_score = 1.0

        # Calculate ideal allocation
        for campaign in campaigns:
            ideal_budget = (scores[campaign.campaign_id] / total_score) * total_budget

            # Apply constraints
            min_budget = max(config.min_campaign_budget, campaign.current_daily_budget * 0.5)
            max_budget = min(config.max_campaign_budget, campaign.current_daily_budget * 2.0)

            # Apply max change constraint
            max_increase = campaign.current_daily_budget * (1 + config.max_change_percent / 100)
            max_decrease = campaign.current_daily_budget * (1 - config.max_change_percent / 100)

            new_budget = max(min_budget, min(max_budget, ideal_budget))
            new_budget = max(max_decrease, min(max_increase, new_budget))
            new_budget = round(new_budget, 2)

            change_amount = new_budget - campaign.current_daily_budget
            change_percent = (change_amount / campaign.current_daily_budget * 100) if campaign.current_daily_budget > 0 else 0

            reason = self._generate_change_reason(campaign, scores[campaign.campaign_id], strategy)

            expected_impact = self._estimate_impact(campaign, change_percent)

            changes.append(BudgetChange(
                campaign_id=campaign.campaign_id,
                campaign_name=campaign.campaign_name,
                platform=campaign.platform,
                current_budget=campaign.current_daily_budget,
                new_budget=new_budget,
                change_amount=round(change_amount, 2),
                change_percent=round(change_percent, 1),
                reason=reason,
                expected_impact=expected_impact,
            ))

        return changes

    def _calculate_campaign_score(
        self,
        metrics: Dict[str, float],
        strategy: ReallocationStrategy,
    ) -> float:
        """Calculate campaign score based on strategy."""
        roas = metrics.get("roas", 1.0)
        cvr = metrics.get("cvr", 1.0)
        cpa = metrics.get("cpa", 100.0)
        volume = metrics.get("conversions", 1)

        if strategy == ReallocationStrategy.ROAS_MAXIMIZATION:
            # Prioritize ROAS
            return roas * 0.7 + (cvr / 10) * 0.3

        elif strategy == ReallocationStrategy.VOLUME_MAXIMIZATION:
            # Prioritize conversion volume
            return (volume ** 0.5) * 0.6 + (100 / (cpa + 1)) * 0.4

        elif strategy == ReallocationStrategy.PROFIT_MAXIMIZATION:
            # Balance ROAS and volume
            profit_proxy = (roas - 1) * volume
            return max(0.1, profit_proxy)

        else:  # BALANCED
            # Balanced approach
            roas_score = min(roas, 5) / 5
            efficiency_score = min(100 / (cpa + 1), 1)
            return roas_score * 0.4 + efficiency_score * 0.3 + (cvr / 10) * 0.3

    def _generate_change_reason(
        self,
        campaign: CampaignBudgetState,
        score: float,
        strategy: ReallocationStrategy,
    ) -> str:
        """Generate human-readable reason for budget change."""
        metrics = campaign.performance_metrics
        roas = metrics.get("roas", 0)

        if score > 0.7:
            return f"High performer (ROAS: {roas:.2f}) - increasing budget to capture more value"
        elif score < 0.3:
            return f"Underperforming (ROAS: {roas:.2f}) - reducing budget to reallocate to better performers"
        else:
            return f"Moderate performer (ROAS: {roas:.2f}) - minor adjustment based on {strategy.value} strategy"

    def _estimate_impact(
        self,
        campaign: CampaignBudgetState,
        change_percent: float,
    ) -> Dict[str, float]:
        """Estimate impact of budget change."""
        # Simplified diminishing returns model
        metrics = campaign.performance_metrics

        # Budget elasticity (typically less than 1 due to diminishing returns)
        elasticity = 0.7 if change_percent > 0 else 0.9

        spend_change = change_percent / 100
        volume_change = spend_change * elasticity

        return {
            "spend_change_percent": round(change_percent, 1),
            "conversions_change_percent": round(volume_change * 100, 1),
            "revenue_change_percent": round(volume_change * 100, 1),
            "expected_roas": metrics.get("roas", 1.0),  # ROAS typically stays similar
        }

    def _check_guardrails(
        self,
        changes: List[BudgetChange],
        config: ReallocationConfig,
    ) -> GuardrailCheck:
        """Check all guardrails for the reallocation plan."""
        violations = []
        warnings = []
        details = {}

        for change in changes:
            # Check max change
            if abs(change.change_percent) > config.max_change_percent:
                violations.append(GuardrailViolation.MAX_CHANGE_EXCEEDED)
                details[f"{change.campaign_id}_max_change"] = change.change_percent

            # Check min budget
            if change.new_budget < config.min_campaign_budget:
                violations.append(GuardrailViolation.MIN_BUDGET_VIOLATED)
                details[f"{change.campaign_id}_min_budget"] = change.new_budget

            # Check max budget
            if change.new_budget > config.max_campaign_budget:
                violations.append(GuardrailViolation.MAX_BUDGET_VIOLATED)
                details[f"{change.campaign_id}_max_budget"] = change.new_budget

            # Warnings for significant changes
            if abs(change.change_percent) > 20:
                warnings.append(f"Large change ({change.change_percent:+.1f}%) for {change.campaign_name}")

        return GuardrailCheck(
            passed=len(violations) == 0,
            violations=list(set(violations)),
            warnings=warnings,
            details=details,
        )

    def _calculate_expected_outcomes(
        self,
        changes: List[BudgetChange],
        campaigns: List[CampaignBudgetState],
    ) -> Dict[str, float]:
        """Calculate expected outcomes of the reallocation."""
        campaign_map = {c.campaign_id: c for c in campaigns}

        total_revenue_change = 0
        total_spend_change = 0
        weighted_roas = 0
        total_new_spend = 0

        for change in changes:
            campaign = campaign_map.get(change.campaign_id)
            if campaign:
                metrics = campaign.performance_metrics
                roas = metrics.get("roas", 1.0)

                spend_change = change.change_amount
                revenue_change = spend_change * roas * 0.7  # Elasticity factor

                total_spend_change += spend_change
                total_revenue_change += revenue_change
                weighted_roas += roas * change.new_budget
                total_new_spend += change.new_budget

        avg_roas = weighted_roas / total_new_spend if total_new_spend > 0 else 1.0

        return {
            "roas_change": round((avg_roas - 1) * 100, 1),  # % change from baseline
            "revenue_change": round(total_revenue_change, 2),
            "spend_change": round(total_spend_change, 2),
        }

    def simulate(self, plan_id: str) -> Dict[str, Any]:
        """
        Simulate the impact of a reallocation plan.

        Returns:
            Dict with simulation results
        """
        plan = self._plans.get(plan_id)
        if not plan:
            return {"error": "Plan not found"}

        simulation = {
            "plan_id": plan_id,
            "strategy": plan.strategy.value,
            "total_budget_change": plan.total_new_budget - plan.total_current_budget,
            "num_campaigns_affected": len(plan.changes),
            "campaigns_increasing": len([c for c in plan.changes if c.change_amount > 0]),
            "campaigns_decreasing": len([c for c in plan.changes if c.change_amount < 0]),
            "expected_outcomes": {
                "roas_change_percent": plan.expected_roas_change,
                "revenue_change": plan.expected_revenue_change,
                "spend_change": plan.expected_spend_change,
            },
            "guardrails": {
                "passed": plan.guardrail_check.passed,
                "violations": [v.value for v in plan.guardrail_check.violations],
                "warnings": plan.guardrail_check.warnings,
            },
            "changes_preview": [
                {
                    "campaign": c.campaign_name,
                    "platform": c.platform,
                    "current": c.current_budget,
                    "new": c.new_budget,
                    "change_percent": c.change_percent,
                    "reason": c.reason,
                }
                for c in plan.changes
            ],
        }

        return simulation

    def approve(
        self,
        plan_id: str,
        approved_by: str,
    ) -> bool:
        """Approve a reallocation plan for execution."""
        plan = self._plans.get(plan_id)
        if not plan:
            logger.error(f"Plan not found: {plan_id}")
            return False

        if plan.status != ReallocationStatus.PROPOSED:
            logger.error(f"Plan {plan_id} is not in PROPOSED status")
            return False

        if not plan.guardrail_check.passed:
            logger.error(f"Plan {plan_id} has guardrail violations")
            return False

        plan.status = ReallocationStatus.APPROVED
        plan.approved_at = datetime.now(timezone.utc)
        plan.approved_by = approved_by

        logger.info(f"Plan {plan_id} approved by {approved_by}")

        return True

    def execute(self, plan_id: str) -> ReallocationResult:
        """
        Execute a reallocation plan.

        In production, this would call the platform APIs to update budgets.
        """
        plan = self._plans.get(plan_id)

        if not plan:
            return ReallocationResult(
                plan_id=plan_id,
                success=False,
                changes_applied=[],
                changes_failed=[(None, "Plan not found")],
                execution_time=datetime.now(timezone.utc),
            )

        if plan.status != ReallocationStatus.APPROVED:
            return ReallocationResult(
                plan_id=plan_id,
                success=False,
                changes_applied=[],
                changes_failed=[(None, "Plan not approved")],
                execution_time=datetime.now(timezone.utc),
            )

        plan.status = ReallocationStatus.EXECUTING

        applied = []
        failed = []

        for change in plan.changes:
            try:
                # In production, this would call the platform API
                # For now, simulate success
                logger.info(
                    f"Applying budget change: {change.campaign_name} "
                    f"${change.current_budget:.2f} -> ${change.new_budget:.2f}"
                )
                applied.append(change)

            except Exception as e:
                failed.append((change, str(e)))

        plan.status = ReallocationStatus.COMPLETED if not failed else ReallocationStatus.FAILED
        plan.executed_at = datetime.now(timezone.utc)

        result = ReallocationResult(
            plan_id=plan_id,
            success=len(failed) == 0,
            changes_applied=applied,
            changes_failed=failed,
            execution_time=datetime.now(timezone.utc),
        )

        self._execution_history.append(result)

        logger.info(f"Executed plan {plan_id}: {len(applied)} applied, {len(failed)} failed")

        return result

    def rollback(self, plan_id: str) -> ReallocationResult:
        """Rollback a completed reallocation to original budgets."""
        plan = self._plans.get(plan_id)

        if not plan:
            return ReallocationResult(
                plan_id=plan_id,
                success=False,
                changes_applied=[],
                changes_failed=[(None, "Plan not found")],
                execution_time=datetime.now(timezone.utc),
            )

        if not plan.rollback_plan:
            return ReallocationResult(
                plan_id=plan_id,
                success=False,
                changes_applied=[],
                changes_failed=[(None, "No rollback data available")],
                execution_time=datetime.now(timezone.utc),
            )

        applied = []
        failed = []

        for campaign_id, original_budget in plan.rollback_plan.items():
            try:
                # In production, this would call the platform API
                logger.info(f"Rolling back {campaign_id} to ${original_budget:.2f}")
                applied.append(BudgetChange(
                    campaign_id=campaign_id,
                    campaign_name="",
                    platform="",
                    current_budget=0,
                    new_budget=original_budget,
                    change_amount=0,
                    change_percent=0,
                    reason="Rollback",
                    expected_impact={},
                ))
            except Exception as e:
                failed.append((None, str(e)))

        plan.status = ReallocationStatus.ROLLED_BACK

        return ReallocationResult(
            plan_id=plan_id,
            success=len(failed) == 0,
            changes_applied=applied,
            changes_failed=failed,
            execution_time=datetime.now(timezone.utc),
        )

    def get_plan(self, plan_id: str) -> Optional[ReallocationPlan]:
        """Get a reallocation plan by ID."""
        return self._plans.get(plan_id)

    def list_plans(
        self,
        tenant_id: Optional[str] = None,
        status: Optional[ReallocationStatus] = None,
    ) -> List[ReallocationPlan]:
        """List reallocation plans with optional filtering."""
        plans = list(self._plans.values())

        if tenant_id:
            plans = [p for p in plans if p.tenant_id == tenant_id]

        if status:
            plans = [p for p in plans if p.status == status]

        return sorted(plans, key=lambda p: p.created_at, reverse=True)


# Singleton instance
reallocation_service = BudgetReallocationService()


# =============================================================================
# Convenience Functions
# =============================================================================

def create_reallocation_plan(
    tenant_id: str,
    campaigns: List[Dict[str, Any]],
    strategy: str = "balanced",
    max_change_percent: float = 25.0,
) -> Dict[str, Any]:
    """
    Create a budget reallocation plan.

    Args:
        tenant_id: Tenant identifier
        campaigns: List of campaign data dicts
        strategy: Reallocation strategy
        max_change_percent: Maximum budget change per campaign

    Returns:
        Dict with plan details
    """
    # Convert to CampaignBudgetState objects
    campaign_states = [
        CampaignBudgetState(
            campaign_id=c["campaign_id"],
            campaign_name=c.get("name", c["campaign_id"]),
            platform=c.get("platform", "unknown"),
            current_daily_budget=c["daily_budget"],
            current_spend=c.get("spend", c["daily_budget"]),
            performance_metrics={
                "roas": c.get("roas", 1.0),
                "ctr": c.get("ctr", 1.0),
                "cvr": c.get("cvr", 1.0),
                "cpa": c.get("cpa", 50.0),
                "conversions": c.get("conversions", 0),
            },
            data_quality_score=c.get("data_quality", 0.8),
        )
        for c in campaigns
    ]

    try:
        strategy_enum = ReallocationStrategy(strategy.lower())
    except ValueError:
        strategy_enum = ReallocationStrategy.BALANCED

    config = ReallocationConfig(
        strategy=strategy_enum,
        max_change_percent=max_change_percent,
    )

    plan = reallocation_service.create_plan(
        tenant_id=tenant_id,
        campaigns=campaign_states,
        config=config,
    )

    return {
        "plan_id": plan.plan_id,
        "status": plan.status.value,
        "total_current_budget": plan.total_current_budget,
        "total_new_budget": plan.total_new_budget,
        "guardrails_passed": plan.guardrail_check.passed,
        "expected_roas_change": plan.expected_roas_change,
        "changes": [
            {
                "campaign_id": c.campaign_id,
                "campaign_name": c.campaign_name,
                "current": c.current_budget,
                "new": c.new_budget,
                "change_percent": c.change_percent,
                "reason": c.reason,
            }
            for c in plan.changes
        ],
    }


# =============================================================================
# Advanced Budget Reallocation Features (P2 Enhancement)
# =============================================================================

@dataclass
class ParetoAllocation:
    """Point on Pareto frontier for multi-objective optimization."""
    allocation: Dict[str, float]  # campaign_id -> budget
    expected_roas: float
    expected_volume: float
    expected_profit: float
    trade_off_description: str


@dataclass
class PortfolioAllocation:
    """Portfolio theory-based allocation."""
    allocations: Dict[str, float]
    expected_return: float
    portfolio_risk: float
    sharpe_ratio: float
    diversification_score: float


@dataclass
class AllocationLearning:
    """Learning from historical allocations."""
    recommendation: str
    confidence: float
    supporting_evidence: List[str]
    similar_past_allocations: List[Dict[str, Any]]


class MultiObjectiveOptimizer:
    """
    Multi-objective optimization for budget allocation.

    Optimizes for multiple objectives simultaneously:
    - ROAS (efficiency)
    - Volume (scale)
    - Profit (absolute returns)

    Uses Pareto frontier to present trade-offs.
    """

    def optimize(
        self,
        campaigns: List[CampaignState],
        total_budget: float,
        objectives: List[str] = None,
    ) -> List[ParetoAllocation]:
        """Find Pareto-optimal allocations."""
        if objectives is None:
            objectives = ["roas", "volume", "profit"]

        pareto_frontier = []

        # Generate allocation scenarios
        scenarios = self._generate_scenarios(campaigns, total_budget)

        # Evaluate each scenario
        evaluated = []
        for allocation in scenarios:
            metrics = self._evaluate_allocation(campaigns, allocation)
            evaluated.append((allocation, metrics))

        # Find Pareto frontier
        for alloc, metrics in evaluated:
            is_dominated = False
            for other_alloc, other_metrics in evaluated:
                if self._dominates(other_metrics, metrics, objectives):
                    is_dominated = True
                    break

            if not is_dominated:
                pareto_frontier.append(ParetoAllocation(
                    allocation=alloc,
                    expected_roas=metrics["roas"],
                    expected_volume=metrics["volume"],
                    expected_profit=metrics["profit"],
                    trade_off_description=self._describe_trade_off(metrics, objectives),
                ))

        return pareto_frontier[:5]  # Top 5 Pareto-optimal solutions

    def _generate_scenarios(
        self,
        campaigns: List[CampaignState],
        total_budget: float,
    ) -> List[Dict[str, float]]:
        """Generate allocation scenarios to evaluate."""
        scenarios = []

        # Scenario 1: Proportional (current allocation)
        total_current = sum(c.current_daily_budget for c in campaigns)
        if total_current > 0:
            proportional = {
                c.campaign_id: c.current_daily_budget / total_current * total_budget
                for c in campaigns
            }
            scenarios.append(proportional)

        # Scenario 2: ROAS-weighted
        total_roas = sum(c.performance_metrics.get("roas", 1) for c in campaigns)
        if total_roas > 0:
            roas_weighted = {
                c.campaign_id: c.performance_metrics.get("roas", 1) / total_roas * total_budget
                for c in campaigns
            }
            scenarios.append(roas_weighted)

        # Scenario 3: Volume-weighted (by conversions)
        total_conv = sum(c.performance_metrics.get("conversions", 1) for c in campaigns)
        if total_conv > 0:
            volume_weighted = {
                c.campaign_id: c.performance_metrics.get("conversions", 1) / total_conv * total_budget
                for c in campaigns
            }
            scenarios.append(volume_weighted)

        # Scenario 4: Equal split
        equal_split = {
            c.campaign_id: total_budget / len(campaigns)
            for c in campaigns
        }
        scenarios.append(equal_split)

        # Scenario 5: Top performers only (top 3 by ROAS)
        sorted_by_roas = sorted(
            campaigns,
            key=lambda c: c.performance_metrics.get("roas", 0),
            reverse=True,
        )[:3]
        top_performers = {c.campaign_id: total_budget / 3 for c in sorted_by_roas}
        for c in campaigns:
            if c.campaign_id not in top_performers:
                top_performers[c.campaign_id] = 0
        scenarios.append(top_performers)

        return scenarios

    def _evaluate_allocation(
        self,
        campaigns: List[CampaignState],
        allocation: Dict[str, float],
    ) -> Dict[str, float]:
        """Evaluate expected metrics for an allocation."""
        total_spend = sum(allocation.values())
        total_revenue = 0
        total_conversions = 0

        for c in campaigns:
            budget = allocation.get(c.campaign_id, 0)
            roas = c.performance_metrics.get("roas", 1)
            cvr = c.performance_metrics.get("cvr", 0.01)

            # Simple projection
            revenue = budget * roas
            conversions = budget * cvr / 50  # Assume $50 avg CPA

            total_revenue += revenue
            total_conversions += conversions

        return {
            "roas": total_revenue / total_spend if total_spend > 0 else 0,
            "volume": total_conversions,
            "profit": total_revenue - total_spend,
        }

    def _dominates(
        self,
        metrics_a: Dict[str, float],
        metrics_b: Dict[str, float],
        objectives: List[str],
    ) -> bool:
        """Check if metrics_a dominates metrics_b."""
        at_least_one_better = False
        for obj in objectives:
            if metrics_a[obj] < metrics_b[obj]:
                return False
            if metrics_a[obj] > metrics_b[obj]:
                at_least_one_better = True
        return at_least_one_better

    def _describe_trade_off(
        self,
        metrics: Dict[str, float],
        objectives: List[str],
    ) -> str:
        """Describe the trade-off of this allocation."""
        descriptions = []

        if metrics["roas"] > 3:
            descriptions.append("High efficiency")
        if metrics["volume"] > 100:
            descriptions.append("High volume")
        if metrics["profit"] > 10000:
            descriptions.append("Strong profit")

        if not descriptions:
            descriptions.append("Balanced approach")

        return " | ".join(descriptions)


class PortfolioAllocator:
    """
    Portfolio theory-based budget allocation.

    Applies Modern Portfolio Theory concepts:
    - Expected returns (ROAS)
    - Risk (variance in performance)
    - Diversification benefits
    - Sharpe ratio optimization
    """

    def __init__(self):
        self._historical_returns: Dict[str, List[float]] = {}

    def record_return(self, campaign_id: str, roas: float):
        """Record historical ROAS for a campaign."""
        if campaign_id not in self._historical_returns:
            self._historical_returns[campaign_id] = []

        self._historical_returns[campaign_id].append(roas)

        # Keep last 90 days
        if len(self._historical_returns[campaign_id]) > 90:
            self._historical_returns[campaign_id] = self._historical_returns[campaign_id][-90:]

    def optimize_portfolio(
        self,
        campaigns: List[CampaignState],
        total_budget: float,
        risk_tolerance: float = 0.5,  # 0 = conservative, 1 = aggressive
    ) -> PortfolioAllocation:
        """Optimize allocation using portfolio theory."""
        # Calculate expected returns and risk for each campaign
        campaign_stats = {}
        for c in campaigns:
            returns = self._historical_returns.get(c.campaign_id, [])
            if returns:
                expected = statistics.mean(returns)
                risk = statistics.stdev(returns) if len(returns) > 1 else expected * 0.3
            else:
                expected = c.performance_metrics.get("roas", 1.5)
                risk = expected * 0.4  # Assume 40% volatility

            campaign_stats[c.campaign_id] = {
                "expected": expected,
                "risk": risk,
                "sharpe": expected / risk if risk > 0 else 0,
            }

        # Simple mean-variance optimization
        # Weight by risk-adjusted return (Sharpe ratio)
        total_sharpe = sum(s["sharpe"] for s in campaign_stats.values())

        allocations = {}
        if total_sharpe > 0:
            for cid, stats in campaign_stats.items():
                # Blend between equal weight and Sharpe-weighted
                sharpe_weight = stats["sharpe"] / total_sharpe
                equal_weight = 1 / len(campaigns)
                weight = risk_tolerance * sharpe_weight + (1 - risk_tolerance) * equal_weight
                allocations[cid] = weight * total_budget
        else:
            # Equal allocation if no reliable data
            for c in campaigns:
                allocations[c.campaign_id] = total_budget / len(campaigns)

        # Calculate portfolio metrics
        portfolio_return = sum(
            allocations[cid] / total_budget * campaign_stats[cid]["expected"]
            for cid in allocations
        )

        # Portfolio risk (simplified - ignores correlation)
        portfolio_risk = sum(
            (allocations[cid] / total_budget) ** 2 * campaign_stats[cid]["risk"] ** 2
            for cid in allocations
        ) ** 0.5

        # Diversification score
        weights = [allocations[cid] / total_budget for cid in allocations]
        herfindahl = sum(w ** 2 for w in weights)
        diversification = 1 - herfindahl  # Higher = more diversified

        return PortfolioAllocation(
            allocations=allocations,
            expected_return=round(portfolio_return, 3),
            portfolio_risk=round(portfolio_risk, 3),
            sharpe_ratio=round(portfolio_return / portfolio_risk if portfolio_risk > 0 else 0, 3),
            diversification_score=round(diversification, 3),
        )


class AllocationLearner:
    """
    Learns from historical allocation outcomes.

    Analyzes:
    - Which allocation patterns worked well
    - What to avoid based on past failures
    - Similar situations and their outcomes
    """

    def __init__(self):
        self._allocation_history: List[Dict[str, Any]] = []

    def record_allocation(
        self,
        plan_id: str,
        allocations: Dict[str, float],
        context: Dict[str, Any],
        outcome: Dict[str, float],  # actual results
    ):
        """Record allocation outcome for learning."""
        self._allocation_history.append({
            "plan_id": plan_id,
            "timestamp": datetime.now(timezone.utc),
            "allocations": allocations,
            "context": context,
            "outcome": outcome,
        })

        # Keep last 200 allocations
        if len(self._allocation_history) > 200:
            self._allocation_history = self._allocation_history[-200:]

    def get_recommendation(
        self,
        proposed_allocation: Dict[str, float],
        context: Dict[str, Any],
    ) -> AllocationLearning:
        """Get recommendation based on historical learning."""
        if len(self._allocation_history) < 5:
            return AllocationLearning(
                recommendation="Insufficient historical data for learning-based recommendations",
                confidence=0.3,
                supporting_evidence=["Building historical baseline"],
                similar_past_allocations=[],
            )

        # Find similar past allocations
        similar = self._find_similar_allocations(proposed_allocation, context)

        if not similar:
            return AllocationLearning(
                recommendation="No similar historical allocations found - proceed with caution",
                confidence=0.4,
                supporting_evidence=["Novel allocation pattern"],
                similar_past_allocations=[],
            )

        # Analyze outcomes of similar allocations
        outcomes = [s["outcome"] for s in similar]
        avg_roas = statistics.mean([o.get("roas", 0) for o in outcomes])
        success_rate = sum(1 for o in outcomes if o.get("roas", 0) > 2) / len(outcomes)

        # Generate recommendation
        if success_rate > 0.7:
            recommendation = "Similar allocations performed well historically - recommended to proceed"
            confidence = 0.8
        elif success_rate > 0.4:
            recommendation = "Mixed results from similar allocations - moderate confidence"
            confidence = 0.5
        else:
            recommendation = "Similar allocations often underperformed - consider adjustments"
            confidence = 0.7

        evidence = [
            f"Analyzed {len(similar)} similar past allocations",
            f"Average ROAS: {avg_roas:.2f}",
            f"Success rate (ROAS > 2): {success_rate * 100:.0f}%",
        ]

        return AllocationLearning(
            recommendation=recommendation,
            confidence=round(confidence, 2),
            supporting_evidence=evidence,
            similar_past_allocations=similar[:3],
        )

    def _find_similar_allocations(
        self,
        allocation: Dict[str, float],
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Find historically similar allocations."""
        similar = []

        total_budget = sum(allocation.values())
        allocation_weights = {
            k: v / total_budget if total_budget > 0 else 0
            for k, v in allocation.items()
        }

        for hist in self._allocation_history:
            hist_total = sum(hist["allocations"].values())
            hist_weights = {
                k: v / hist_total if hist_total > 0 else 0
                for k, v in hist["allocations"].items()
            }

            # Calculate similarity (simplified cosine similarity)
            common_keys = set(allocation_weights.keys()) & set(hist_weights.keys())
            if not common_keys:
                continue

            similarity = sum(
                allocation_weights.get(k, 0) * hist_weights.get(k, 0)
                for k in common_keys
            )

            # Context similarity
            context_match = self._context_similarity(context, hist["context"])

            combined_similarity = similarity * 0.6 + context_match * 0.4

            if combined_similarity > 0.5:
                similar.append({
                    **hist,
                    "similarity_score": round(combined_similarity, 3),
                })

        # Sort by similarity
        similar.sort(key=lambda x: x["similarity_score"], reverse=True)

        return similar[:10]

    def _context_similarity(
        self,
        context_a: Dict[str, Any],
        context_b: Dict[str, Any],
    ) -> float:
        """Calculate context similarity."""
        if not context_a or not context_b:
            return 0.5

        matches = 0
        total = 0

        for key in context_a:
            if key in context_b:
                total += 1
                if context_a[key] == context_b[key]:
                    matches += 1

        return matches / total if total > 0 else 0.5


# Singleton instances for P2 enhancements
multi_objective_optimizer = MultiObjectiveOptimizer()
portfolio_allocator = PortfolioAllocator()
allocation_learner = AllocationLearner()
