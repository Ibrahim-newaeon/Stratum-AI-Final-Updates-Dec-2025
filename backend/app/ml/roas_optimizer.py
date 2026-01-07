# =============================================================================
# Stratum AI - ROAS Optimizer
# =============================================================================
"""
Automated ROAS optimization engine.
Analyzes campaigns and provides actionable recommendations for higher ROAS.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from enum import Enum

import numpy as np

from app.core.logging import get_logger
from app.ml.inference import ModelRegistry

logger = get_logger(__name__)


class RecommendationType(str, Enum):
    """Types of optimization recommendations."""
    INCREASE_BUDGET = "increase_budget"
    DECREASE_BUDGET = "decrease_budget"
    PAUSE_CAMPAIGN = "pause_campaign"
    SCALE_CAMPAIGN = "scale_campaign"
    OPTIMIZE_TARGETING = "optimize_targeting"
    IMPROVE_CREATIVE = "improve_creative"
    ADJUST_BIDDING = "adjust_bidding"
    SHIFT_BUDGET = "shift_budget"


class Priority(str, Enum):
    """Recommendation priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ROASOptimizer:
    """
    Analyzes campaign performance and generates recommendations for higher ROAS.

    Features:
    - Identifies underperforming campaigns
    - Suggests budget reallocation
    - Predicts optimal budget levels
    - Detects scaling opportunities
    """

    def __init__(self):
        self.registry = ModelRegistry()

        # ROAS thresholds by platform
        self.platform_targets = {
            "meta": {"min": 1.5, "good": 2.5, "excellent": 4.0},
            "google": {"min": 2.0, "good": 3.0, "excellent": 5.0},
            "tiktok": {"min": 1.2, "good": 2.0, "excellent": 3.5},
            "snapchat": {"min": 1.0, "good": 1.8, "excellent": 3.0},
            "linkedin": {"min": 1.5, "good": 2.5, "excellent": 4.0},
        }

    async def analyze_campaign(self, campaign_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze a single campaign and generate recommendations.

        Args:
            campaign_data: Campaign metrics including:
                - id, name, platform
                - spend, revenue, roas
                - impressions, clicks, conversions
                - ctr, cpc, cpa
                - daily_budget
                - status

        Returns:
            Analysis with score, recommendations, and predictions
        """
        platform = campaign_data.get("platform", "meta").lower()
        current_roas = campaign_data.get("roas", 0)
        spend = campaign_data.get("spend", 0)
        revenue = campaign_data.get("revenue", 0)

        # Get platform thresholds
        thresholds = self.platform_targets.get(platform, self.platform_targets["meta"])

        # Calculate health score (0-100)
        health_score = self._calculate_health_score(campaign_data, thresholds)

        # Generate recommendations
        recommendations = await self._generate_recommendations(campaign_data, thresholds, health_score)

        # Predict optimal budget
        optimal_budget = await self._predict_optimal_budget(campaign_data)

        # Predict ROAS if budget changes
        budget_scenarios = await self._simulate_budget_scenarios(campaign_data)

        return {
            "campaign_id": campaign_data.get("id"),
            "campaign_name": campaign_data.get("name"),
            "platform": platform,
            "current_metrics": {
                "roas": current_roas,
                "spend": spend,
                "revenue": revenue,
            },
            "health_score": health_score,
            "status": self._get_status_from_score(health_score),
            "recommendations": recommendations,
            "optimal_budget": optimal_budget,
            "budget_scenarios": budget_scenarios,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    
    def _compute_recommendation_confidence(
        self,
        campaign: Dict[str, Any],
        recommendation_type: str,
        base_confidence: float,
    ) -> float:
        """
        Compute model-derived confidence for a recommendation.
        
        Factors:
        - Data completeness (spend, revenue, conversions present)
        - Data volume (higher spend/conversions = more reliable)
        - Recommendation type (pause is more certain than scale)
        
        Args:
            campaign: Campaign metrics dict
            recommendation_type: Type of recommendation
            base_confidence: Starting confidence for this recommendation type
            
        Returns:
            Adjusted confidence score 0.0-0.95
        """
        # Data completeness factor
        has_spend = campaign.get("spend", 0) > 0
        has_revenue = campaign.get("revenue", 0) > 0
        has_conversions = campaign.get("conversions", 0) > 0
        has_impressions = campaign.get("impressions", 0) > 0
        
        completeness = sum([has_spend, has_revenue, has_conversions, has_impressions]) / 4
        completeness_adj = completeness * 0.15
        
        # Data volume factor (more data = higher confidence)
        spend = campaign.get("spend", 0)
        conversions = campaign.get("conversions", 0)
        volume_score = min(0.1, (spend / 10000) * 0.05 + (conversions / 100) * 0.05)
        
        # Recommendation type adjustment (some actions are more certain)
        type_adjustments = {
            "pause": 0.1,      # Pausing underperformers is high confidence
            "decrease": 0.05,  # Decreasing budget is fairly certain
            "increase": -0.05, # Scaling has more uncertainty
            "scale": -0.1,     # Aggressive scaling is less certain
        }
        type_adj = type_adjustments.get(recommendation_type, 0)
        
        # Calculate final confidence
        confidence = base_confidence + completeness_adj + volume_score + type_adj
        
        # Clamp to valid range
        return round(max(0.3, min(0.95, confidence)), 2)


    async def analyze_portfolio(self, campaigns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analyze entire campaign portfolio and optimize budget allocation.

        Returns portfolio-level insights and cross-campaign recommendations.
        """
        if not campaigns:
            return {"error": "No campaigns to analyze"}

        # Analyze each campaign
        analyses = []
        for campaign in campaigns:
            analysis = await self.analyze_campaign(campaign)
            analyses.append(analysis)

        # Calculate portfolio metrics
        total_spend = sum(c.get("spend", 0) for c in campaigns)
        total_revenue = sum(c.get("revenue", 0) for c in campaigns)
        portfolio_roas = total_revenue / total_spend if total_spend > 0 else 0

        # Identify top and bottom performers
        sorted_by_roas = sorted(analyses, key=lambda x: x["current_metrics"]["roas"], reverse=True)
        top_performers = sorted_by_roas[:3]
        bottom_performers = sorted_by_roas[-3:] if len(sorted_by_roas) > 3 else []

        # Generate budget reallocation recommendations
        reallocation = self._calculate_budget_reallocation(analyses, total_spend)

        # Calculate potential uplift
        potential_uplift = self._calculate_potential_uplift(analyses, reallocation)

        return {
            "portfolio_metrics": {
                "total_spend": total_spend,
                "total_revenue": total_revenue,
                "portfolio_roas": round(portfolio_roas, 2),
                "campaign_count": len(campaigns),
                "avg_health_score": round(np.mean([a["health_score"] for a in analyses]), 1),
            },
            "campaign_analyses": analyses,
            "top_performers": top_performers,
            "bottom_performers": bottom_performers,
            "budget_reallocation": reallocation,
            "potential_uplift": potential_uplift,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }

    def _calculate_health_score(self, campaign: Dict, thresholds: Dict) -> float:
        """Calculate campaign health score (0-100)."""
        roas = campaign.get("roas", 0)
        ctr = campaign.get("ctr", 0)
        cvr = campaign.get("cvr", 0)

        # ROAS score (0-50 points)
        if roas >= thresholds["excellent"]:
            roas_score = 50
        elif roas >= thresholds["good"]:
            roas_score = 35 + (roas - thresholds["good"]) / (thresholds["excellent"] - thresholds["good"]) * 15
        elif roas >= thresholds["min"]:
            roas_score = 20 + (roas - thresholds["min"]) / (thresholds["good"] - thresholds["min"]) * 15
        else:
            roas_score = max(0, roas / thresholds["min"] * 20)

        # CTR score (0-25 points)
        ctr_benchmark = 1.5  # Average CTR benchmark
        ctr_score = min(25, (ctr / ctr_benchmark) * 25) if ctr_benchmark > 0 else 0

        # Conversion score (0-25 points)
        conversions = campaign.get("conversions", 0)
        spend = campaign.get("spend", 0)
        if spend > 0 and conversions > 0:
            cpa = spend / conversions
            target_cpa = 50  # Default target CPA
            conversion_score = min(25, (target_cpa / cpa) * 25) if cpa > 0 else 0
        else:
            conversion_score = 0

        return round(roas_score + ctr_score + conversion_score, 1)

    def _get_status_from_score(self, score: float) -> str:
        """Convert health score to status label."""
        if score >= 80:
            return "excellent"
        elif score >= 60:
            return "good"
        elif score >= 40:
            return "needs_attention"
        elif score >= 20:
            return "underperforming"
        else:
            return "critical"

    async def _generate_recommendations(
        self,
        campaign: Dict,
        thresholds: Dict,
        health_score: float,
    ) -> List[Dict[str, Any]]:
        """Generate actionable recommendations for the campaign."""
        recommendations = []

        roas = campaign.get("roas", 0)
        ctr = campaign.get("ctr", 0)
        spend = campaign.get("spend", 0)
        daily_budget = campaign.get("daily_budget", 0)
        conversions = campaign.get("conversions", 0)

        # High ROAS - Scale opportunity
        if roas >= thresholds["excellent"]:
            recommendations.append({
                "type": RecommendationType.SCALE_CAMPAIGN,
                "priority": Priority.HIGH,
                "title": "Scale this high-performing campaign",
                "description": f"ROAS of {roas:.2f}x is excellent. Consider increasing budget by 20-50% to capture more conversions.",
                "action": {
                    "suggested_budget_increase": 0.3,  # 30% increase
                    "expected_roas_range": [roas * 0.85, roas * 0.95],
                },
                "expected_impact": {
                    "revenue_increase": spend * 0.3 * roas * 0.9,
                    "confidence": self._compute_recommendation_confidence(campaign, "scale", 0.65),
                },
            })

        # Good ROAS - Optimize
        elif roas >= thresholds["good"]:
            recommendations.append({
                "type": RecommendationType.INCREASE_BUDGET,
                "priority": Priority.MEDIUM,
                "title": "Gradually increase budget",
                "description": f"Campaign is performing well with {roas:.2f}x ROAS. Test 10-20% budget increase.",
                "action": {
                    "suggested_budget_increase": 0.15,
                },
                "expected_impact": {
                    "revenue_increase": spend * 0.15 * roas * 0.95,
                    "confidence": self._compute_recommendation_confidence(campaign, "increase", 0.60),
                },
            })

        # Below minimum - Critical action needed
        elif roas < thresholds["min"]:
            if roas < 0.5:
                recommendations.append({
                    "type": RecommendationType.PAUSE_CAMPAIGN,
                    "priority": Priority.CRITICAL,
                    "title": "Consider pausing this campaign",
                    "description": f"ROAS of {roas:.2f}x is critically low. Pause and review strategy before continuing.",
                    "action": {
                        "pause_campaign": True,
                        "review_areas": ["targeting", "creative", "landing_page"],
                    },
                    "expected_impact": {
                        "cost_savings": spend * 0.8,
                        "confidence": self._compute_recommendation_confidence(campaign, "pause", 0.85),
                    },
                })
            else:
                recommendations.append({
                    "type": RecommendationType.DECREASE_BUDGET,
                    "priority": Priority.HIGH,
                    "title": "Reduce budget while optimizing",
                    "description": f"ROAS of {roas:.2f}x is below target. Reduce budget by 30-50% and focus on optimization.",
                    "action": {
                        "suggested_budget_decrease": 0.4,
                    },
                    "expected_impact": {
                        "cost_savings": spend * 0.4,
                        "confidence": self._compute_recommendation_confidence(campaign, "decrease", 0.75),
                    },
                })

        # Low CTR - Creative/targeting issue
        if ctr < 0.8:
            recommendations.append({
                "type": RecommendationType.IMPROVE_CREATIVE,
                "priority": Priority.HIGH if ctr < 0.5 else Priority.MEDIUM,
                "title": "Improve ad creative or targeting",
                "description": f"CTR of {ctr:.2f}% is below average. Test new creatives or refine audience targeting.",
                "action": {
                    "test_new_creatives": True,
                    "review_targeting": True,
                    "a_b_test_suggestions": ["headline", "image", "cta"],
                },
                "expected_impact": {
                    "ctr_improvement": 0.5,  # 50% CTR improvement potential
                    "confidence": self._compute_recommendation_confidence(campaign, "creative", 0.55),
                },
            })

        # High CPA - Bidding adjustment
        if conversions > 0 and spend > 0:
            cpa = spend / conversions
            if cpa > 100:  # High CPA threshold
                recommendations.append({
                    "type": RecommendationType.ADJUST_BIDDING,
                    "priority": Priority.MEDIUM,
                    "title": "Optimize bidding strategy",
                    "description": f"CPA of ${cpa:.2f} is high. Consider switching to target CPA bidding or reducing bids.",
                    "action": {
                        "suggested_target_cpa": cpa * 0.7,
                        "bidding_strategy": "target_cpa",
                    },
                    "expected_impact": {
                        "cpa_reduction": 0.25,
                        "confidence": self._compute_recommendation_confidence(campaign, "bidding", 0.50),
                    },
                })

        return recommendations

    async def _predict_optimal_budget(self, campaign: Dict) -> Dict[str, Any]:
        """Predict the optimal budget for maximum ROAS."""
        current_spend = campaign.get("spend", 0)
        current_roas = campaign.get("roas", 0)

        if current_spend == 0:
            return {"error": "No spend data available"}

        # Use ML model to predict optimal budget
        features = {
            "current_spend": current_spend,
            "current_roas": current_roas,
            "impressions": campaign.get("impressions", 0),
            "clicks": campaign.get("clicks", 0),
            "conversions": campaign.get("conversions", 0),
            "ctr": campaign.get("ctr", 0),
        }

        # Get prediction from model
        prediction = await self.registry.predict("budget_impact", features)

        # Calculate optimal budget based on diminishing returns curve
        elasticity = prediction.get("value", 0.8)

        # Optimal is where marginal ROAS = 1 (break-even on additional spend)
        if current_roas > 1:
            # Can increase budget
            optimal_multiplier = min(2.0, 1 + (current_roas - 1) * elasticity * 0.5)
        else:
            # Should decrease budget
            optimal_multiplier = max(0.3, current_roas * 0.8)

        optimal_budget = current_spend * optimal_multiplier

        return {
            "current_daily_budget": current_spend / 30,  # Approximate daily
            "optimal_daily_budget": optimal_budget / 30,
            "change_percent": round((optimal_multiplier - 1) * 100, 1),
            "expected_roas_at_optimal": round(current_roas * (1 - (optimal_multiplier - 1) * 0.1), 2),
            "confidence": self._compute_recommendation_confidence(campaign, "budget_opt", 0.60),
        }

    async def _simulate_budget_scenarios(self, campaign: Dict) -> List[Dict[str, Any]]:
        """Simulate different budget scenarios and predict outcomes."""
        current_spend = campaign.get("spend", 0)
        current_roas = campaign.get("roas", 0)

        if current_spend == 0:
            return []

        scenarios = []
        multipliers = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0]

        for mult in multipliers:
            new_spend = current_spend * mult

            # Apply diminishing returns for increases
            if mult > 1:
                roas_adjustment = 1 - (mult - 1) * 0.15  # 15% ROAS decline per 100% increase
            else:
                roas_adjustment = 1 + (1 - mult) * 0.1  # Slight ROAS improvement with decrease

            predicted_roas = current_roas * roas_adjustment
            predicted_revenue = new_spend * predicted_roas

            scenarios.append({
                "budget_change_percent": round((mult - 1) * 100),
                "new_spend": round(new_spend, 2),
                "predicted_roas": round(predicted_roas, 2),
                "predicted_revenue": round(predicted_revenue, 2),
                "profit": round(predicted_revenue - new_spend, 2),
                "is_current": mult == 1.0,
            })

        return scenarios

    def _calculate_budget_reallocation(
        self,
        analyses: List[Dict],
        total_budget: float,
    ) -> List[Dict[str, Any]]:
        """Calculate optimal budget reallocation across campaigns."""
        if not analyses or total_budget == 0:
            return []

        reallocations = []

        # Score each campaign for budget allocation
        scored = []
        for analysis in analyses:
            roas = analysis["current_metrics"]["roas"]
            health = analysis["health_score"]
            current_spend = analysis["current_metrics"]["spend"]

            # Allocation score based on ROAS and health
            score = (roas * 0.6 + health / 100 * 0.4) * 100
            scored.append({
                "campaign_id": analysis["campaign_id"],
                "campaign_name": analysis["campaign_name"],
                "current_spend": current_spend,
                "score": score,
                "roas": roas,
            })

        # Normalize scores and calculate new allocations
        total_score = sum(s["score"] for s in scored)
        if total_score == 0:
            return []

        for s in scored:
            allocation_pct = s["score"] / total_score
            new_budget = total_budget * allocation_pct
            change = new_budget - s["current_spend"]
            change_pct = (change / s["current_spend"] * 100) if s["current_spend"] > 0 else 0

            reallocations.append({
                "campaign_id": s["campaign_id"],
                "campaign_name": s["campaign_name"],
                "current_budget": round(s["current_spend"], 2),
                "recommended_budget": round(new_budget, 2),
                "change_amount": round(change, 2),
                "change_percent": round(change_pct, 1),
                "reason": "higher_roas" if change > 0 else "lower_roas",
            })

        # Sort by change amount (biggest increases first)
        reallocations.sort(key=lambda x: x["change_amount"], reverse=True)

        return reallocations

    def _calculate_potential_uplift(
        self,
        analyses: List[Dict],
        reallocation: List[Dict],
    ) -> Dict[str, Any]:
        """Calculate potential portfolio uplift from recommendations."""
        current_revenue = sum(a["current_metrics"]["revenue"] for a in analyses)
        current_spend = sum(a["current_metrics"]["spend"] for a in analyses)

        # Estimate uplift from reallocation (conservative 10-15%)
        reallocation_uplift = current_revenue * 0.12

        # Estimate uplift from following recommendations
        recommendation_uplift = 0
        for analysis in analyses:
            for rec in analysis.get("recommendations", []):
                impact = rec.get("expected_impact", {})
                if "revenue_increase" in impact:
                    recommendation_uplift += impact["revenue_increase"] * impact.get("confidence", 0.5)

        total_potential = reallocation_uplift + recommendation_uplift

        return {
            "current_revenue": round(current_revenue, 2),
            "current_roas": round(current_revenue / current_spend, 2) if current_spend > 0 else 0,
            "potential_additional_revenue": round(total_potential, 2),
            "potential_new_revenue": round(current_revenue + total_potential, 2),
            "potential_new_roas": round((current_revenue + total_potential) / current_spend, 2) if current_spend > 0 else 0,
            "uplift_percent": round(total_potential / current_revenue * 100, 1) if current_revenue > 0 else 0,
            "from_reallocation": round(reallocation_uplift, 2),
            "from_recommendations": round(recommendation_uplift, 2),
        }


class LivePredictionEngine:
    """
    Engine for generating live predictions and alerts.
    Runs periodically to analyze campaigns and generate alerts.
    """

    def __init__(self):
        self.optimizer = ROASOptimizer()
        self.alert_thresholds = {
            "roas_drop": 0.2,  # 20% ROAS drop triggers alert
            "spend_spike": 0.5,  # 50% spend increase triggers alert
            "conversion_drop": 0.3,  # 30% conversion drop triggers alert
        }

    async def generate_live_predictions(
        self,
        campaigns: List[Dict[str, Any]],
        previous_metrics: Optional[Dict[int, Dict]] = None,
    ) -> Dict[str, Any]:
        """
        Generate live predictions for all campaigns.

        Args:
            campaigns: Current campaign data
            previous_metrics: Previous metrics for comparison (keyed by campaign_id)

        Returns:
            Live predictions with alerts
        """
        predictions = []
        alerts = []

        for campaign in campaigns:
            campaign_id = campaign.get("id")

            # Get prediction
            prediction = await self._predict_campaign_performance(campaign)
            predictions.append(prediction)

            # Check for alerts
            if previous_metrics and campaign_id in previous_metrics:
                prev = previous_metrics[campaign_id]
                campaign_alerts = self._check_alerts(campaign, prev)
                alerts.extend(campaign_alerts)

        # Portfolio-level prediction
        portfolio_prediction = await self._predict_portfolio_performance(campaigns)

        return {
            "campaign_predictions": predictions,
            "portfolio_prediction": portfolio_prediction,
            "alerts": alerts,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def _predict_campaign_performance(self, campaign: Dict) -> Dict[str, Any]:
        """Predict next 24h performance for a campaign."""
        current_roas = campaign.get("roas", 0)
        current_spend = campaign.get("spend", 0)
        trend = campaign.get("trend", 0)  # Historical trend

        # Simple trend-based prediction
        predicted_roas = current_roas * (1 + trend * 0.1)
        predicted_spend = current_spend / 30  # Daily estimate
        predicted_revenue = predicted_spend * predicted_roas

        # Confidence based on data stability
        confidence = min(0.9, 0.5 + (campaign.get("days_active", 0) / 30) * 0.4)

        return {
            "campaign_id": campaign.get("id"),
            "campaign_name": campaign.get("name"),
            "current_roas": current_roas,
            "predicted_roas_24h": round(predicted_roas, 2),
            "predicted_spend_24h": round(predicted_spend, 2),
            "predicted_revenue_24h": round(predicted_revenue, 2),
            "trend": "up" if trend > 0.02 else "down" if trend < -0.02 else "stable",
            "confidence": round(confidence, 2),
        }

    async def _predict_portfolio_performance(self, campaigns: List[Dict]) -> Dict[str, Any]:
        """Predict portfolio-level performance."""
        total_predicted_spend = sum(c.get("spend", 0) / 30 for c in campaigns)
        weighted_roas = sum(
            c.get("roas", 0) * c.get("spend", 0) for c in campaigns
        ) / max(1, sum(c.get("spend", 0) for c in campaigns))

        return {
            "predicted_daily_spend": round(total_predicted_spend, 2),
            "predicted_daily_revenue": round(total_predicted_spend * weighted_roas, 2),
            "predicted_portfolio_roas": round(weighted_roas, 2),
            "active_campaigns": len(campaigns),
        }

    def _check_alerts(self, current: Dict, previous: Dict) -> List[Dict[str, Any]]:
        """Check for alert conditions."""
        alerts = []
        campaign_id = current.get("id")

        # ROAS drop alert
        current_roas = current.get("roas", 0)
        previous_roas = previous.get("roas", 0)
        if previous_roas > 0:
            roas_change = (current_roas - previous_roas) / previous_roas
            if roas_change < -self.alert_thresholds["roas_drop"]:
                alerts.append({
                    "campaign_id": campaign_id,
                    "type": "roas_drop",
                    "severity": "high" if roas_change < -0.4 else "medium",
                    "message": f"ROAS dropped {abs(roas_change)*100:.1f}% (from {previous_roas:.2f} to {current_roas:.2f})",
                    "recommendation": "Review recent changes and consider reducing budget",
                })

        # Conversion drop alert
        current_conv = current.get("conversions", 0)
        previous_conv = previous.get("conversions", 0)
        if previous_conv > 0:
            conv_change = (current_conv - previous_conv) / previous_conv
            if conv_change < -self.alert_thresholds["conversion_drop"]:
                alerts.append({
                    "campaign_id": campaign_id,
                    "type": "conversion_drop",
                    "severity": "high" if conv_change < -0.5 else "medium",
                    "message": f"Conversions dropped {abs(conv_change)*100:.1f}%",
                    "recommendation": "Check tracking, landing pages, and audience fatigue",
                })

        return alerts
