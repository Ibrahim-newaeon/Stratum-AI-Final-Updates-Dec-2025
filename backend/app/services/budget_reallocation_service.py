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
