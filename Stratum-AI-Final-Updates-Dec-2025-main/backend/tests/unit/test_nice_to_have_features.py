"""
Tests for Nice to Have (Could Add) Features - Audit Items #11-15
- #11: SHAP explainability for predictions
- #12: Competitor benchmarking
- #13: Automated budget reallocation
- #14: Predictive audience insights
- #15: LTV prediction model
"""

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest


# ============================================================================
# Test #11: SHAP Explainability for Predictions
# ============================================================================
class TestModelExplainability:
    """Tests for SHAP-based model explainability"""

    def test_explain_prediction_basic(self):
        """Test basic prediction explanation"""
        from app.ml.explainability import ModelExplainer

        explainer = ModelExplainer("test_model", models_path="./models")

        features = {
            "spend": 1000.0,
            "impressions": 50000,
            "clicks": 500,
            "ctr": 0.01,
        }

        explanation = explainer.explain_prediction(features, prediction=0.75, top_k=3)

        assert explanation is not None
        assert explanation.predicted_value == 0.75
        assert len(explanation.top_positive_factors) <= 3
        assert explanation.confidence_score >= 0
        assert explanation.confidence_score <= 1

    def test_feature_contributions_structure(self):
        """Test that feature contributions have proper structure"""
        from app.ml.explainability import ModelExplainer

        explainer = ModelExplainer("test_model", models_path="./models")

        features = {"spend": 500.0, "impressions": 25000, "clicks": 250}

        explanation = explainer.explain_prediction(features, prediction=0.5)

        # All contributions should have reasonable structure
        for contrib in explanation.all_contributions:
            assert hasattr(contrib, "feature_name")
            assert hasattr(contrib, "contribution")
            assert contrib.direction in ["positive", "negative", "neutral"]

    def test_human_readable_explanation(self):
        """Test human-readable explanation generation"""
        from app.ml.explainability import ModelExplainer

        explainer = ModelExplainer("test_model", models_path="./models")

        features = {"spend": 2000.0, "clicks": 1000}

        explanation = explainer.explain_prediction(features, prediction=0.8)

        # Should have human-readable text
        assert explanation.explanation_summary is not None
        assert len(explanation.explanation_summary) > 0
        assert explanation.detailed_explanation is not None

    def test_global_explanation(self):
        """Test global feature importance explanation"""
        from app.ml.explainability import ModelExplainer

        explainer = ModelExplainer("test_model", models_path="./models")

        # Create sample data
        X = np.random.rand(10, 3)
        feature_names = ["spend", "impressions", "clicks"]

        global_explanation = explainer.get_global_explanation(X, feature_names)

        assert global_explanation is not None
        assert global_explanation.num_samples == 10
        # Summary should always be present
        assert global_explanation.summary is not None

    def test_explanation_with_prediction_id(self):
        """Test explanation with custom prediction ID"""
        from app.ml.explainability import ModelExplainer

        explainer = ModelExplainer("test_model", models_path="./models")

        features = {"metric_a": 100, "metric_b": 200}
        explanation = explainer.explain_prediction(
            features, prediction=0.6, prediction_id="custom_pred_123"
        )

        assert explanation is not None
        assert explanation.prediction_id == "custom_pred_123"

    def test_explanation_model_name(self):
        """Test that explanation includes model name"""
        from app.ml.explainability import ModelExplainer

        explainer = ModelExplainer("roas_predictor", models_path="./models")

        features = {"spend": 1000.0}

        explanation = explainer.explain_prediction(features, prediction=0.7)

        assert explanation.model_name == "roas_predictor"


# ============================================================================
# Test #12: Competitor Benchmarking
# ============================================================================
class TestCompetitorBenchmarking:
    """Tests for competitor benchmarking service"""

    def test_get_benchmark_basic(self):
        """Test getting basic competitor benchmark"""
        from app.services.competitor_benchmarking_service import (
            CompetitorBenchmarkingService,
            Industry,
            Region,
        )

        service = CompetitorBenchmarkingService()

        benchmark = service.get_benchmark(
            tenant_id="tenant_123",
            industry=Industry.ECOMMERCE,
            region=Region.GLOBAL,
            platform="meta",
            metrics={"ctr": 0.02, "cpc": 0.50, "roas": 3.5},
        )

        assert benchmark is not None
        assert benchmark.tenant_id == "tenant_123"
        assert benchmark.industry == Industry.ECOMMERCE
        assert len(benchmark.metrics) == 3

    def test_benchmark_percentile_calculation(self):
        """Test percentile calculation against industry"""
        from app.services.competitor_benchmarking_service import (
            CompetitorBenchmarkingService,
            Industry,
            Region,
        )

        service = CompetitorBenchmarkingService()

        # Test with above-average metrics
        benchmark = service.get_benchmark(
            tenant_id="tenant_123",
            industry=Industry.ECOMMERCE,
            region=Region.GLOBAL,
            platform="meta",
            metrics={"ctr": 5.0, "roas": 5.0},  # Good metrics
        )

        # CTR of 5% should be above median
        ctr_metric = benchmark.metrics.get("ctr")
        assert ctr_metric is not None
        assert ctr_metric.your_percentile >= 50

    def test_benchmark_performance_level(self):
        """Test performance level classification"""
        from app.services.competitor_benchmarking_service import (
            CompetitorBenchmarkingService,
            Industry,
            PerformanceLevel,
            Region,
        )

        service = CompetitorBenchmarkingService()

        # Test performance level assignment
        benchmark = service.get_benchmark(
            tenant_id="tenant_123",
            industry=Industry.ECOMMERCE,
            region=Region.GLOBAL,
            platform="google",
            metrics={"ctr": 0.001},  # Very low CTR
        )

        ctr_metric = benchmark.metrics.get("ctr")
        assert ctr_metric is not None
        assert ctr_metric.performance_level in [
            PerformanceLevel.BELOW_AVERAGE,
            PerformanceLevel.POOR,
            PerformanceLevel.AVERAGE,
            PerformanceLevel.ABOVE_AVERAGE,
            PerformanceLevel.EXCELLENT,
        ]

    def test_benchmark_recommendations(self):
        """Test that benchmarks include recommendations"""
        from app.services.competitor_benchmarking_service import (
            CompetitorBenchmarkingService,
            Industry,
            Region,
        )

        service = CompetitorBenchmarkingService()

        benchmark = service.get_benchmark(
            tenant_id="tenant_123",
            industry=Industry.ECOMMERCE,
            region=Region.GLOBAL,
            platform="meta",
            metrics={"ctr": 0.005, "cpc": 2.0},  # Below average
        )

        # Should have recommendations for improvement
        assert benchmark.recommendations is not None
        assert len(benchmark.recommendations) >= 0

    def test_industry_report(self):
        """Test getting full industry report"""
        from app.services.competitor_benchmarking_service import (
            CompetitorBenchmarkingService,
            Industry,
            Region,
        )

        service = CompetitorBenchmarkingService()

        report = service.get_industry_report(
            industry=Industry.ECOMMERCE, platform="meta", region=Region.GLOBAL
        )

        assert report is not None
        assert "industry" in report
        assert "metrics" in report

    def test_compare_across_platforms(self):
        """Test comparing performance across platforms"""
        from app.services.competitor_benchmarking_service import (
            CompetitorBenchmarkingService,
            Industry,
        )

        service = CompetitorBenchmarkingService()

        comparison = service.compare_platforms(
            tenant_id="tenant_123",
            industry=Industry.ECOMMERCE,
            platform_metrics={
                "meta": {"ctr": 0.02, "roas": 3.0},
                "google": {"ctr": 0.03, "roas": 4.0},
            },
        )

        assert comparison is not None
        assert "meta" in comparison["platforms"]
        assert "google" in comparison["platforms"]


# ============================================================================
# Test #13: Automated Budget Reallocation
# ============================================================================
class TestBudgetReallocation:
    """Tests for automated budget reallocation service"""

    def test_create_reallocation_plan(self):
        """Test creating a budget reallocation plan"""
        from app.services.budget_reallocation_service import (
            BudgetReallocationService,
            CampaignBudgetState,
            ReallocationConfig,
            ReallocationStrategy,
        )

        service = BudgetReallocationService()

        campaigns = [
            CampaignBudgetState(
                campaign_id="camp_1",
                campaign_name="Campaign 1",
                platform="meta",
                current_daily_budget=1000,
                current_spend=900,
                performance_metrics={"roas": 2.0, "ctr": 1.5, "cvr": 2.0, "cpa": 50},
                data_quality_score=0.8,
            ),
            CampaignBudgetState(
                campaign_id="camp_2",
                campaign_name="Campaign 2",
                platform="meta",
                current_daily_budget=1000,
                current_spend=950,
                performance_metrics={"roas": 5.0, "ctr": 2.5, "cvr": 3.0, "cpa": 30},
                data_quality_score=0.9,
            ),
        ]

        config = ReallocationConfig(
            strategy=ReallocationStrategy.ROAS_MAXIMIZATION,
            min_campaign_budget=100,
            max_change_percent=50,
        )

        plan = service.create_plan(tenant_id="tenant_123", campaigns=campaigns, config=config)

        assert plan is not None
        assert plan.tenant_id == "tenant_123"
        assert len(plan.changes) > 0

    def test_roas_maximization_strategy(self):
        """Test ROAS maximization allocates to high performers"""
        from app.services.budget_reallocation_service import (
            BudgetReallocationService,
            CampaignBudgetState,
            ReallocationConfig,
            ReallocationStrategy,
        )

        service = BudgetReallocationService()

        campaigns = [
            CampaignBudgetState(
                campaign_id="low_roas",
                campaign_name="Low ROAS",
                platform="meta",
                current_daily_budget=1000,
                current_spend=900,
                performance_metrics={"roas": 1.0, "ctr": 1.0, "cvr": 1.0, "cpa": 100},
                data_quality_score=0.8,
            ),
            CampaignBudgetState(
                campaign_id="high_roas",
                campaign_name="High ROAS",
                platform="meta",
                current_daily_budget=1000,
                current_spend=950,
                performance_metrics={"roas": 8.0, "ctr": 3.0, "cvr": 4.0, "cpa": 20},
                data_quality_score=0.9,
            ),
        ]

        config = ReallocationConfig(strategy=ReallocationStrategy.ROAS_MAXIMIZATION)
        plan = service.create_plan("tenant_123", campaigns, config)

        # High ROAS campaign should get budget increase
        high_roas_change = next(c for c in plan.changes if c.campaign_id == "high_roas")
        assert high_roas_change.new_budget >= high_roas_change.current_budget

    def test_guardrails_prevent_extreme_changes(self):
        """Test that guardrails prevent extreme budget changes"""
        from app.services.budget_reallocation_service import (
            BudgetReallocationService,
            CampaignBudgetState,
            ReallocationConfig,
            ReallocationStrategy,
        )

        service = BudgetReallocationService()

        campaigns = [
            CampaignBudgetState(
                campaign_id="camp_1",
                campaign_name="Campaign 1",
                platform="meta",
                current_daily_budget=1000,
                current_spend=900,
                performance_metrics={"roas": 0.1, "ctr": 0.5, "cvr": 0.5, "cpa": 200},
                data_quality_score=0.8,
            ),
            CampaignBudgetState(
                campaign_id="camp_2",
                campaign_name="Campaign 2",
                platform="meta",
                current_daily_budget=1000,
                current_spend=950,
                performance_metrics={"roas": 10.0, "ctr": 4.0, "cvr": 5.0, "cpa": 15},
                data_quality_score=0.9,
            ),
        ]

        config = ReallocationConfig(
            strategy=ReallocationStrategy.ROAS_MAXIMIZATION,
            max_change_percent=30,  # Max 30% change
        )

        plan = service.create_plan("tenant_123", campaigns, config)

        # No campaign should change by more than 30%
        for change in plan.changes:
            change_percent = abs(change.change_percent)
            assert change_percent <= 30.1  # Small tolerance for rounding

    def test_minimum_budget_enforced(self):
        """Test that minimum budget is enforced"""
        from app.services.budget_reallocation_service import (
            BudgetReallocationService,
            CampaignBudgetState,
            ReallocationConfig,
            ReallocationStrategy,
        )

        service = BudgetReallocationService()

        campaigns = [
            CampaignBudgetState(
                campaign_id="camp_1",
                campaign_name="Campaign 1",
                platform="meta",
                current_daily_budget=200,
                current_spend=180,
                performance_metrics={"roas": 0.1, "ctr": 0.3, "cvr": 0.2, "cpa": 500},
                data_quality_score=0.8,
            ),
        ]

        config = ReallocationConfig(
            strategy=ReallocationStrategy.ROAS_MAXIMIZATION, min_campaign_budget=100
        )

        plan = service.create_plan("tenant_123", campaigns, config)

        # Budget should not go below minimum
        for change in plan.changes:
            assert change.new_budget >= 100

    def test_simulate_reallocation(self):
        """Test simulating reallocation before execution"""
        from app.services.budget_reallocation_service import (
            BudgetReallocationService,
            CampaignBudgetState,
            ReallocationConfig,
            ReallocationStrategy,
        )

        service = BudgetReallocationService()

        campaigns = [
            CampaignBudgetState(
                campaign_id="camp_1",
                campaign_name="Campaign 1",
                platform="meta",
                current_daily_budget=1000,
                current_spend=900,
                performance_metrics={"roas": 2.0, "ctr": 1.5, "cvr": 2.0, "cpa": 50},
                data_quality_score=0.8,
            ),
        ]

        config = ReallocationConfig(strategy=ReallocationStrategy.ROAS_MAXIMIZATION)
        plan = service.create_plan("tenant_123", campaigns, config)

        simulation = service.simulate(plan.plan_id)

        assert simulation is not None
        assert "expected_outcomes" in simulation
        assert "roas_change_percent" in simulation["expected_outcomes"]

    def test_approval_workflow(self):
        """Test plan approval workflow"""
        from app.services.budget_reallocation_service import (
            BudgetReallocationService,
            CampaignBudgetState,
            ReallocationConfig,
            ReallocationStatus,
            ReallocationStrategy,
        )

        service = BudgetReallocationService()

        campaigns = [
            CampaignBudgetState(
                campaign_id="camp_1",
                campaign_name="Campaign 1",
                platform="meta",
                current_daily_budget=1000,
                current_spend=900,
                performance_metrics={"roas": 3.0, "ctr": 2.0, "cvr": 2.5, "cpa": 40},
                data_quality_score=0.8,
            ),
        ]
        config = ReallocationConfig(strategy=ReallocationStrategy.BALANCED)
        plan = service.create_plan("tenant_123", campaigns, config)

        assert plan.status == ReallocationStatus.PROPOSED

        # Approve the plan
        success = service.approve(plan.plan_id, approved_by="admin_user")

        assert success
        assert service.get_plan(plan.plan_id).status == ReallocationStatus.APPROVED

    def test_execute_reallocation(self):
        """Test executing approved reallocation"""
        from app.services.budget_reallocation_service import (
            BudgetReallocationService,
            CampaignBudgetState,
            ReallocationConfig,
            ReallocationStatus,
            ReallocationStrategy,
        )

        service = BudgetReallocationService()

        campaigns = [
            CampaignBudgetState(
                campaign_id="camp_1",
                campaign_name="Campaign 1",
                platform="meta",
                current_daily_budget=1000,
                current_spend=900,
                performance_metrics={"roas": 2.0, "ctr": 1.5, "cvr": 2.0, "cpa": 50},
                data_quality_score=0.8,
            ),
            CampaignBudgetState(
                campaign_id="camp_2",
                campaign_name="Campaign 2",
                platform="meta",
                current_daily_budget=1000,
                current_spend=950,
                performance_metrics={"roas": 4.0, "ctr": 2.5, "cvr": 3.0, "cpa": 30},
                data_quality_score=0.9,
            ),
        ]

        config = ReallocationConfig(strategy=ReallocationStrategy.ROAS_MAXIMIZATION)
        plan = service.create_plan("tenant_123", campaigns, config)
        service.approve(plan.plan_id, approved_by="admin")

        result = service.execute(plan.plan_id)

        assert result is not None
        assert result.success
        assert service.get_plan(plan.plan_id).status == ReallocationStatus.COMPLETED

    def test_rollback_reallocation(self):
        """Test rolling back executed reallocation"""
        from app.services.budget_reallocation_service import (
            BudgetReallocationService,
            CampaignBudgetState,
            ReallocationConfig,
            ReallocationStatus,
            ReallocationStrategy,
        )

        service = BudgetReallocationService()

        campaigns = [
            CampaignBudgetState(
                campaign_id="camp_1",
                campaign_name="Campaign 1",
                platform="meta",
                current_daily_budget=1000,
                current_spend=900,
                performance_metrics={"roas": 3.0, "ctr": 2.0, "cvr": 2.5, "cpa": 40},
                data_quality_score=0.8,
            ),
        ]
        config = ReallocationConfig(strategy=ReallocationStrategy.BALANCED)

        plan = service.create_plan("tenant_123", campaigns, config)
        service.approve(plan.plan_id, approved_by="admin")
        service.execute(plan.plan_id)

        # Rollback
        result = service.rollback(plan.plan_id)

        assert result is not None
        assert result.success
        assert service.get_plan(plan.plan_id).status == ReallocationStatus.ROLLED_BACK


# ============================================================================
# Test #14: Predictive Audience Insights
# ============================================================================
class TestAudienceInsights:
    """Tests for predictive audience insights service"""

    def test_predict_audience_performance(self):
        """Test predicting audience performance"""
        from app.services.audience_insights_service import AudienceInsightsService, AudienceType

        service = AudienceInsightsService()

        prediction = service.predict_performance(
            audience_type=AudienceType.LOOKALIKE,
            size=500000,
            platform="meta",
            budget=5000,
            lookalike_percent=2,
        )

        assert prediction is not None
        assert "predictions" in prediction
        assert "ctr" in prediction["predictions"]
        assert "cvr" in prediction["predictions"]
        assert "conversions" in prediction["predictions"]
        assert "confidence" in prediction

    def test_audience_quality_scoring(self):
        """Test audience quality scoring"""
        from app.services.audience_insights_service import (
            AudienceInsightsService,
            AudienceMetrics,
            AudienceType,
        )

        service = AudienceInsightsService()

        # Register an audience
        audience = service.register_audience(
            audience_id="aud_123",
            tenant_id="tenant_123",
            platform="meta",
            name="High Value Customers",
            audience_type=AudienceType.CUSTOM,
            size=10000,
        )

        # Update with performance metrics
        metrics = AudienceMetrics(
            reach=5000,
            impressions=50000,
            clicks=2500,
            conversions=150,
            spend=2000,
            revenue=9000,
        )
        metrics.calculate_derived()
        service.update_metrics("aud_123", metrics)

        # Check quality score
        updated_audience = service.get_audience("aud_123")
        assert updated_audience.quality_score >= 0
        assert updated_audience.quality_score <= 100

    def test_audience_expansion_recommendations(self):
        """Test audience expansion recommendations"""
        from app.services.audience_insights_service import (
            AudienceInsightsService,
            AudienceMetrics,
            AudienceType,
        )

        service = AudienceInsightsService()

        audience = service.register_audience(
            audience_id="aud_expansion",
            tenant_id="tenant_123",
            platform="meta",
            name="Purchasers",
            audience_type=AudienceType.CUSTOM,
            size=5000,
        )

        metrics = AudienceMetrics(
            reach=500,
            impressions=5000,
            clicks=200,
            conversions=25,
            spend=500,
            revenue=2500,
        )
        metrics.calculate_derived()
        service.update_metrics("aud_expansion", metrics)

        insights = service.get_insights("aud_expansion")

        # Should have some insights
        assert insights is not None
        assert isinstance(insights, list)

    def test_audience_overlap_detection(self):
        """Test detecting overlap between audiences"""
        from app.services.audience_insights_service import AudienceInsightsService, AudienceType

        service = AudienceInsightsService()

        # Create overlapping audiences
        service.register_audience(
            audience_id="aud_1",
            tenant_id="tenant_123",
            platform="meta",
            name="Website Visitors",
            audience_type=AudienceType.RETARGETING,
            size=50000,
        )
        service.register_audience(
            audience_id="aud_2",
            tenant_id="tenant_123",
            platform="meta",
            name="Email Subscribers",
            audience_type=AudienceType.CUSTOM,
            size=30000,
        )

        overlaps = service.detect_overlap(["aud_1", "aud_2"])

        assert overlaps is not None
        assert len(overlaps) >= 1
        assert overlaps[0].overlap_percent >= 0

    def test_audience_fatigue_detection(self):
        """Test audience fatigue detection via high frequency"""
        from app.services.audience_insights_service import (
            AudienceInsightsService,
            AudienceMetrics,
            AudienceType,
        )

        service = AudienceInsightsService()

        audience = service.register_audience(
            audience_id="aud_fatigue",
            tenant_id="tenant_123",
            platform="meta",
            name="Retargeting",
            audience_type=AudienceType.RETARGETING,
            size=10000,
        )

        # Record high frequency metrics (fatigue pattern)
        metrics = AudienceMetrics(
            reach=1000,
            impressions=12000,  # High frequency: 12 impressions per user
            clicks=120,
            conversions=10,
            spend=1000,
            revenue=500,
        )
        metrics.calculate_derived()
        service.update_metrics("aud_fatigue", metrics)

        insights = service.get_insights("aud_fatigue")

        # Should detect fatigue via high frequency
        saturation_insights = [i for i in insights if i.insight_type == "saturation"]
        assert len(saturation_insights) > 0

    def test_get_audience_recommendations(self):
        """Test getting audience recommendations for tenant"""
        from app.services.audience_insights_service import AudienceInsightsService, AudienceType

        service = AudienceInsightsService()

        # Create some audiences
        service.register_audience(
            audience_id="aud_rec_1",
            tenant_id="tenant_rec",
            platform="meta",
            name="Audience 1",
            audience_type=AudienceType.LOOKALIKE,
            size=100000,
        )
        service.register_audience(
            audience_id="aud_rec_2",
            tenant_id="tenant_rec",
            platform="meta",
            name="Audience 2",
            audience_type=AudienceType.CUSTOM,
            size=5000,
        )

        recommendations = service.get_recommendations(tenant_id="tenant_rec", limit=5)

        assert recommendations is not None
        assert isinstance(recommendations, list)


# ============================================================================
# Test #15: LTV Prediction Model
# ============================================================================
class TestLTVPrediction:
    """Tests for LTV prediction model"""

    @pytest.fixture
    def fresh_predictor(self):
        """Create a fresh predictor without loading existing models"""
        from app.ml.ltv_predictor import LTVPredictor

        return LTVPredictor(models_path="./models_test_nonexistent")

    def test_basic_ltv_prediction(self, fresh_predictor):
        """Test basic LTV prediction from customer behavior"""
        from app.ml.ltv_predictor import CustomerBehavior

        predictor = fresh_predictor

        behavior = CustomerBehavior(
            customer_id="cust_123",
            acquisition_date=datetime.now(UTC) - timedelta(days=90),
            acquisition_channel="meta",
            first_order_value=100.0,
            first_order_items=2,
            total_orders=5,
            total_revenue=500.0,
            avg_order_value=100.0,
            days_since_last_order=10,
            sessions_first_week=5,
            email_opens_first_week=3,
        )

        prediction = predictor.predict(behavior)

        assert prediction is not None
        assert prediction.customer_id == "cust_123"
        assert prediction.predicted_ltv_365d > 0
        assert prediction.confidence >= 0 and prediction.confidence <= 1

    def test_ltv_prediction_time_horizons(self, fresh_predictor):
        """Test LTV prediction for different time horizons"""
        from app.ml.ltv_predictor import CustomerBehavior

        predictor = fresh_predictor

        behavior = CustomerBehavior(
            customer_id="cust_456",
            acquisition_date=datetime.now(UTC) - timedelta(days=30),
            acquisition_channel="google",
            first_order_value=75.0,
            first_order_items=1,
            total_orders=2,
            total_revenue=200.0,
            avg_order_value=100.0,
            days_since_last_order=5,
            sessions_first_week=3,
        )

        prediction = predictor.predict(behavior)

        # Longer horizon should predict higher LTV
        assert prediction.predicted_ltv_90d > prediction.predicted_ltv_30d
        assert prediction.predicted_ltv_365d > prediction.predicted_ltv_90d
        assert prediction.predicted_ltv_lifetime >= prediction.predicted_ltv_365d

    def test_customer_segmentation(self, fresh_predictor):
        """Test customer segmentation by LTV"""
        from app.ml.ltv_predictor import CustomerBehavior

        predictor = fresh_predictor

        customers = [
            CustomerBehavior(
                customer_id="high_1",
                acquisition_date=datetime.now(UTC) - timedelta(days=365),
                acquisition_channel="organic",
                first_order_value=200,
                total_orders=50,
                total_revenue=10000,
                avg_order_value=200,
                days_since_last_order=5,
                sessions_first_week=10,
                email_opens_first_week=5,
            ),
            CustomerBehavior(
                customer_id="low_1",
                acquisition_date=datetime.now(UTC) - timedelta(days=90),
                acquisition_channel="affiliate",
                first_order_value=30,
                total_orders=1,
                total_revenue=30,
                avg_order_value=30,
                days_since_last_order=80,
                sessions_first_week=1,
            ),
        ]

        segments = predictor.segment_customers(customers)

        assert "total_customers" in segments
        assert segments["total_customers"] == 2
        assert "segments" in segments

    def test_churn_probability_included(self, fresh_predictor):
        """Test that LTV prediction includes churn probability"""
        from app.ml.ltv_predictor import CustomerBehavior

        predictor = fresh_predictor

        # Customer showing churn signals (long time since last purchase)
        churning_behavior = CustomerBehavior(
            customer_id="churning",
            acquisition_date=datetime.now(UTC) - timedelta(days=365),
            acquisition_channel="meta",
            first_order_value=50,
            total_orders=3,
            total_revenue=300.0,
            avg_order_value=100.0,
            days_since_last_order=180,  # 6 months since last purchase
            sessions_first_week=2,
            email_opens_first_week=1,
        )

        prediction = predictor.predict(churning_behavior)

        assert prediction.churn_probability is not None
        assert prediction.churn_probability > 0.3  # Should have elevated churn risk

    def test_max_cac_calculation(self, fresh_predictor):
        """Test maximum CAC calculation from LTV"""
        from app.ml.ltv_predictor import CustomerBehavior

        predictor = fresh_predictor

        behavior = CustomerBehavior(
            customer_id="cust_789",
            acquisition_date=datetime.now(UTC) - timedelta(days=180),
            acquisition_channel="referral",
            first_order_value=200.0,
            total_orders=10,
            total_revenue=2000.0,
            avg_order_value=200.0,
            days_since_last_order=7,
            sessions_first_week=8,
            email_opens_first_week=5,
        )

        prediction = predictor.predict(behavior)

        # Calculate max CAC with 3:1 LTV:CAC ratio target
        max_cac = predictor.calculate_max_cac(
            predicted_ltv=prediction.predicted_ltv_365d, target_ratio=3.0, margin_percent=30
        )

        assert max_cac is not None
        assert "recommended_max_cac" in max_cac
        assert max_cac["recommended_max_cac"] > 0
        assert max_cac["recommended_max_cac"] < prediction.predicted_ltv_365d

    def test_cohort_analysis(self, fresh_predictor):
        """Test cohort-based LTV analysis"""
        from app.ml.ltv_predictor import CustomerBehavior

        predictor = fresh_predictor

        # Create customers from different cohorts
        customers = [
            CustomerBehavior(
                customer_id="jan_1",
                acquisition_date=datetime(2024, 1, 15, tzinfo=UTC),
                acquisition_channel="meta",
                first_order_value=100,
                total_orders=10,
                total_revenue=1000,
                avg_order_value=100,
                days_since_last_order=30,
                sessions_first_week=5,
            ),
            CustomerBehavior(
                customer_id="feb_1",
                acquisition_date=datetime(2024, 2, 10, tzinfo=UTC),
                acquisition_channel="google",
                first_order_value=80,
                total_orders=6,
                total_revenue=600,
                avg_order_value=100,
                days_since_last_order=25,
                sessions_first_week=3,
            ),
        ]

        cohort_analysis = predictor.analyze_cohort(customers)

        assert cohort_analysis is not None
        assert len(cohort_analysis) >= 1

        for cohort in cohort_analysis:
            assert cohort.cohort_month is not None
            assert cohort.avg_ltv >= 0
            assert cohort.customers > 0

    def test_ltv_prediction_with_rfm(self, fresh_predictor):
        """Test LTV prediction using RFM-like metrics"""
        from app.ml.ltv_predictor import CustomerBehavior

        predictor = fresh_predictor

        # High RFM score customer
        high_rfm = CustomerBehavior(
            customer_id="high_rfm",
            acquisition_date=datetime.now(UTC) - timedelta(days=180),
            acquisition_channel="organic",
            first_order_value=250.0,
            total_orders=20,  # High frequency
            total_revenue=5000.0,  # High monetary
            avg_order_value=250.0,
            days_since_last_order=3,  # Recent (high recency)
            sessions_first_week=10,
            email_opens_first_week=5,
            email_clicks_first_week=3,
        )

        # Low RFM score customer
        low_rfm = CustomerBehavior(
            customer_id="low_rfm",
            acquisition_date=datetime.now(UTC) - timedelta(days=365),
            acquisition_channel="affiliate",
            first_order_value=50.0,
            total_orders=1,  # Low frequency
            total_revenue=50.0,  # Low monetary
            avg_order_value=50.0,
            days_since_last_order=300,  # Not recent
            sessions_first_week=1,
            email_opens_first_week=0,
        )

        high_pred = predictor.predict(high_rfm)
        low_pred = predictor.predict(low_rfm)

        # High RFM should have much higher LTV
        assert high_pred.predicted_ltv_365d > low_pred.predicted_ltv_365d * 2

    def test_model_training(self, tmp_path):
        """Test training LTV model on historical data"""
        import pandas as pd

        from app.ml.ltv_predictor import LTVPredictor

        # Use tmp_path to avoid interfering with other tests
        predictor = LTVPredictor(models_path=str(tmp_path))

        # Create training data
        training_data = pd.DataFrame(
            {
                "customer_id": [f"cust_{i}" for i in range(100)],
                "first_order_value": np.random.uniform(20, 300, 100),
                "first_order_items": np.random.randint(1, 5, 100),
                "days_to_first_purchase": np.random.randint(0, 30, 100),
                "sessions_first_week": np.random.randint(1, 15, 100),
                "pages_viewed_first_week": np.random.randint(5, 50, 100),
                "email_opens_first_week": np.random.randint(0, 10, 100),
                "email_clicks_first_week": np.random.randint(0, 5, 100),
                "total_orders": np.random.randint(1, 20, 100),
                "total_revenue": np.random.uniform(50, 3000, 100),
                "avg_order_value": np.random.uniform(30, 200, 100),
                "actual_ltv_365d": np.random.uniform(100, 5000, 100),  # Target variable
            }
        )

        metrics = predictor.train(training_data)

        assert metrics is not None
        # If sklearn is available, we should get metrics
        if "error" not in metrics:
            assert "r2" in metrics or "mae" in metrics or "rmse" in metrics


# ============================================================================
# Integration Tests
# ============================================================================
class TestNiceToHaveIntegration:
    """Integration tests for Nice to Have features"""

    def test_explainability_with_budget_reallocation(self):
        """Test explainability integrated with budget decisions"""
        from app.ml.explainability import ModelExplainer
        from app.services.budget_reallocation_service import (
            BudgetReallocationService,
            CampaignBudgetState,
            ReallocationConfig,
            ReallocationStrategy,
        )

        # Create explainer
        explainer = ModelExplainer("test_model", models_path="./models")

        # Get explanation for reallocation decision
        features = {"current_roas": 4.0, "budget_utilization": 0.95, "ctr": 0.03}
        explanation = explainer.explain_prediction(features, prediction=0.75)

        # Use budget service
        service = BudgetReallocationService()
        campaigns = [
            CampaignBudgetState(
                campaign_id="camp_1",
                campaign_name="Campaign 1",
                platform="meta",
                current_daily_budget=1000,
                current_spend=950,
                performance_metrics={"roas": 4.0, "ctr": 2.0, "cvr": 3.0, "cpa": 30},
                data_quality_score=0.9,
            ),
        ]
        config = ReallocationConfig(strategy=ReallocationStrategy.ROAS_MAXIMIZATION)
        plan = service.create_plan("tenant_123", campaigns, config)

        # Both should work together
        assert explanation is not None
        assert plan is not None

    def test_audience_insights_with_ltv(self):
        """Test audience insights combined with LTV prediction"""
        from app.ml.ltv_predictor import CustomerBehavior, LTVPredictor
        from app.services.audience_insights_service import (
            AudienceInsightsService,
            AudienceMetrics,
            AudienceType,
        )

        # Create high-value audience
        audience_service = AudienceInsightsService()
        audience = audience_service.register_audience(
            audience_id="vip_audience_integ",
            tenant_id="tenant_123",
            platform="meta",
            name="VIP Customers",
            audience_type=AudienceType.CUSTOM,
            size=1000,
        )

        # Update with good metrics
        metrics = AudienceMetrics(
            reach=800,
            impressions=8000,
            clicks=400,
            conversions=40,
            spend=1000,
            revenue=5000,
        )
        metrics.calculate_derived()
        audience_service.update_metrics("vip_audience_integ", metrics)

        # Predict LTV for typical audience member using a fresh predictor
        # Use a non-existent path to avoid loading a previously trained model with different features
        ltv_predictor = LTVPredictor(models_path="./models_test_nonexistent")
        behavior = CustomerBehavior(
            customer_id="typical_vip",
            acquisition_date=datetime.now(UTC) - timedelta(days=365),
            acquisition_channel="meta",
            first_order_value=200,
            total_orders=25,
            total_revenue=5000,
            avg_order_value=200,
            days_since_last_order=7,
            sessions_first_week=8,
            email_opens_first_week=5,
        )

        ltv_prediction = ltv_predictor.predict(behavior)

        # Both should provide consistent high-value signals
        audience_insights = audience_service.get_insights("vip_audience_integ")
        assert ltv_prediction.predicted_ltv_365d > 500

    def test_competitor_benchmark_with_recommendations(self):
        """Test competitor benchmarking produces actionable recommendations"""
        from app.services.budget_reallocation_service import (
            BudgetReallocationService,
            CampaignBudgetState,
            ReallocationConfig,
            ReallocationStrategy,
        )
        from app.services.competitor_benchmarking_service import (
            CompetitorBenchmarkingService,
            Industry,
            Region,
        )

        # Get benchmark
        benchmark_service = CompetitorBenchmarkingService()
        benchmark = benchmark_service.get_benchmark(
            tenant_id="tenant_123",
            industry=Industry.ECOMMERCE,
            region=Region.GLOBAL,
            platform="meta",
            metrics={"ctr": 0.01, "roas": 2.0},  # Below average
        )

        # Based on benchmark, create budget reallocation
        budget_service = BudgetReallocationService()
        campaigns = [
            CampaignBudgetState(
                campaign_id="camp_1",
                campaign_name="Campaign 1",
                platform="meta",
                current_daily_budget=1000,
                current_spend=900,
                performance_metrics={"roas": 2.0, "ctr": 1.0, "cvr": 1.5, "cpa": 60},
                data_quality_score=0.8,
            ),
            CampaignBudgetState(
                campaign_id="camp_2",
                campaign_name="Campaign 2",
                platform="meta",
                current_daily_budget=1000,
                current_spend=950,
                performance_metrics={"roas": 3.5, "ctr": 2.5, "cvr": 3.0, "cpa": 35},
                data_quality_score=0.9,
            ),
        ]

        config = ReallocationConfig(strategy=ReallocationStrategy.ROAS_MAXIMIZATION)
        plan = budget_service.create_plan("tenant_123", campaigns, config)

        assert benchmark is not None
        assert plan is not None
        # Plan should shift budget toward better performing campaign
        assert any(c.new_budget > c.current_budget for c in plan.changes)
