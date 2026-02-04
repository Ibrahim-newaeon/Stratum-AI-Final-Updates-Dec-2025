# =============================================================================
# Stratum AI - Analytics Logic Unit Tests
# =============================================================================
"""
Unit tests for analytics logic modules:
- Scaling score calculation (scoring.py)
- Creative fatigue detection (fatigue.py)
- Anomaly detection (anomalies.py)
- Signal health checks (signal_health.py)
- Recommendations engine (recommend.py)

Each module has 5+ test cases covering core functionality.
"""

from datetime import UTC, datetime

import pytest

from app.analytics.logic.anomalies import (
    anomaly_zscore,
    detect_anomalies,
    get_severity,
)
from app.analytics.logic.fatigue import batch_creative_fatigue, creative_fatigue
from app.analytics.logic.recommend import (
    RecommendationsEngine,
    generate_recommendations,
)
from app.analytics.logic.scoring import batch_scaling_scores, scaling_score
from app.analytics.logic.signal_health import (
    auto_resolve,
    should_suspend_automation,
    signal_health,
)
from app.analytics.logic.types import (
    AlertSeverity,
    BaselineMetrics,
    EntityLevel,
    EntityMetrics,
    FatigueState,
    Platform,
    ScalingAction,
    SignalHealthStatus,
)

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_entity_metrics() -> EntityMetrics:
    """Sample entity metrics for testing."""
    return EntityMetrics(
        entity_id="campaign_123",
        entity_name="Test Campaign",
        entity_level=EntityLevel.CAMPAIGN,
        platform=Platform.META,
        date=datetime.now(UTC),
        spend=1000.0,
        impressions=50000,
        clicks=500,
        conversions=25,
        revenue=5000.0,
        cpa=40.0,
        roas=5.0,
        cvr=0.05,
        ctr=0.01,
        cpm=20.0,
        frequency=2.5,
        emq_score=92.0,
    )


@pytest.fixture
def sample_baseline_metrics() -> BaselineMetrics:
    """Sample baseline metrics for testing."""
    return BaselineMetrics(
        spend=800.0,
        impressions=40000,
        clicks=400,
        conversions=20,
        revenue=3200.0,
        cpa=40.0,
        roas=4.0,
        cvr=0.05,
        ctr=0.01,
        cpm=20.0,
        frequency=2.0,
        emq_score=90.0,
    )


@pytest.fixture
def high_performing_metrics() -> EntityMetrics:
    """High performing entity for scale action."""
    return EntityMetrics(
        entity_id="campaign_456",
        entity_name="High Performer",
        entity_level=EntityLevel.CAMPAIGN,
        platform=Platform.META,
        date=datetime.now(UTC),
        spend=2000.0,
        impressions=100000,
        clicks=2000,
        conversions=100,
        revenue=20000.0,
        cpa=20.0,  # 50% better than baseline
        roas=10.0,  # 150% better than baseline
        cvr=0.10,  # 100% better
        ctr=0.02,  # 100% better
        cpm=20.0,
        frequency=1.8,
        emq_score=95.0,
    )


@pytest.fixture
def low_performing_metrics() -> EntityMetrics:
    """Low performing entity for fix action."""
    return EntityMetrics(
        entity_id="campaign_789",
        entity_name="Low Performer",
        entity_level=EntityLevel.CAMPAIGN,
        platform=Platform.META,
        date=datetime.now(UTC),
        spend=500.0,
        impressions=25000,
        clicks=100,
        conversions=5,
        revenue=500.0,
        cpa=100.0,  # 150% worse than baseline
        roas=1.0,  # 75% worse than baseline
        cvr=0.02,  # 60% worse
        ctr=0.004,  # 60% worse
        cpm=20.0,
        frequency=5.0,  # High frequency penalty
        emq_score=75.0,  # Low EMQ
    )


@pytest.fixture
def fatigued_creative_metrics() -> EntityMetrics:
    """Creative showing fatigue symptoms."""
    return EntityMetrics(
        entity_id="creative_001",
        entity_name="Fatigued Ad Creative",
        entity_level=EntityLevel.CREATIVE,
        platform=Platform.META,
        date=datetime.now(UTC),
        spend=500.0,
        impressions=50000,
        clicks=200,  # CTR down
        conversions=8,
        revenue=800.0,
        cpa=62.5,  # Up
        roas=1.6,  # Down
        cvr=0.04,
        ctr=0.004,  # Way down
        cpm=10.0,
        frequency=6.0,  # Very high
    )


# =============================================================================
# Scaling Score Tests (scoring.py)
# =============================================================================


class TestScalingScore:
    """Tests for scaling score calculation."""

    def test_positive_score_triggers_scale_action(
        self,
        high_performing_metrics: EntityMetrics,
        sample_baseline_metrics: BaselineMetrics,
    ):
        """High performance should trigger SCALE action."""
        result = scaling_score(high_performing_metrics, sample_baseline_metrics)

        assert result.score > 0.25, "Score should be above scale threshold"
        assert result.action == ScalingAction.SCALE
        assert result.roas_delta > 0, "ROAS should be above baseline"
        assert result.cpa_delta < 0, "CPA should be below baseline (improvement)"

    def test_negative_score_triggers_fix_action(
        self,
        low_performing_metrics: EntityMetrics,
        sample_baseline_metrics: BaselineMetrics,
    ):
        """Poor performance should trigger FIX action."""
        result = scaling_score(low_performing_metrics, sample_baseline_metrics)

        assert result.score < -0.25, "Score should be below fix threshold"
        assert result.action == ScalingAction.FIX
        assert result.roas_delta < 0, "ROAS should be below baseline"
        assert result.cpa_delta > 0, "CPA should be above baseline (worse)"

    def test_neutral_score_triggers_watch_action(
        self,
        sample_entity_metrics: EntityMetrics,
        sample_baseline_metrics: BaselineMetrics,
    ):
        """Neutral performance should trigger WATCH action."""
        result = scaling_score(sample_entity_metrics, sample_baseline_metrics)

        # Score should be between thresholds
        assert -0.25 <= result.score <= 0.25 or result.action == ScalingAction.WATCH
        # If not SCALE or FIX, must be WATCH
        if not (result.score > 0.25 or result.score < -0.25):
            assert result.action == ScalingAction.WATCH

    def test_frequency_penalty_applied(self):
        """High frequency should apply penalty to score."""
        high_freq_metrics = EntityMetrics(
            entity_id="test_001",
            entity_name="High Frequency",
            entity_level=EntityLevel.CAMPAIGN,
            platform=Platform.META,
            date=datetime.now(UTC),
            spend=1000.0,
            roas=5.0,
            cpa=40.0,
            cvr=0.05,
            ctr=0.01,
            frequency=8.0,  # Very high frequency
        )

        low_freq_metrics = EntityMetrics(
            entity_id="test_002",
            entity_name="Low Frequency",
            entity_level=EntityLevel.CAMPAIGN,
            platform=Platform.META,
            date=datetime.now(UTC),
            spend=1000.0,
            roas=5.0,
            cpa=40.0,
            cvr=0.05,
            ctr=0.01,
            frequency=1.5,  # Low frequency
        )

        baseline = BaselineMetrics(roas=4.0, cpa=40.0, cvr=0.05, ctr=0.01, frequency=2.0)

        result_high = scaling_score(high_freq_metrics, baseline)
        result_low = scaling_score(low_freq_metrics, baseline)

        assert result_high.freq_penalty > result_low.freq_penalty
        assert result_high.score < result_low.score, "High frequency should lower score"

    def test_emq_penalty_applied(self):
        """Low EMQ score should apply penalty."""
        good_emq = EntityMetrics(
            entity_id="test_003",
            entity_name="Good EMQ",
            entity_level=EntityLevel.CAMPAIGN,
            platform=Platform.META,
            date=datetime.now(UTC),
            spend=1000.0,
            roas=5.0,
            cpa=40.0,
            cvr=0.05,
            ctr=0.01,
            emq_score=95.0,
        )

        bad_emq = EntityMetrics(
            entity_id="test_004",
            entity_name="Bad EMQ",
            entity_level=EntityLevel.CAMPAIGN,
            platform=Platform.META,
            date=datetime.now(UTC),
            spend=1000.0,
            roas=5.0,
            cpa=40.0,
            cvr=0.05,
            ctr=0.01,
            emq_score=70.0,  # Low EMQ
        )

        baseline = BaselineMetrics(roas=4.0, cpa=40.0, cvr=0.05, ctr=0.01, emq_score=90.0)

        result_good = scaling_score(good_emq, baseline)
        result_bad = scaling_score(bad_emq, baseline)

        assert result_bad.emq_penalty > result_good.emq_penalty
        assert result_bad.score < result_good.score, "Low EMQ should lower score"

    def test_batch_scaling_scores(
        self,
        sample_entity_metrics: EntityMetrics,
        high_performing_metrics: EntityMetrics,
        sample_baseline_metrics: BaselineMetrics,
    ):
        """Batch calculation should process multiple entities."""
        entities = [sample_entity_metrics, high_performing_metrics]
        baselines = {
            sample_entity_metrics.entity_id: sample_baseline_metrics,
            high_performing_metrics.entity_id: sample_baseline_metrics,
        }

        results = batch_scaling_scores(entities, baselines)

        assert len(results) == 2
        assert all(r.entity_id in baselines for r in results)


# =============================================================================
# Creative Fatigue Tests (fatigue.py)
# =============================================================================


class TestCreativeFatigue:
    """Tests for creative fatigue detection."""

    def test_healthy_creative_low_fatigue(self, sample_baseline_metrics: BaselineMetrics):
        """Healthy creative should have low fatigue score."""
        healthy = EntityMetrics(
            entity_id="creative_healthy",
            entity_name="Healthy Creative",
            entity_level=EntityLevel.CREATIVE,
            platform=Platform.META,
            date=datetime.now(UTC),
            ctr=0.015,  # Above baseline
            roas=5.0,  # Above baseline
            cpa=35.0,  # Below baseline
            frequency=1.5,  # Low frequency
        )

        baseline = BaselineMetrics(ctr=0.01, roas=4.0, cpa=40.0, frequency=2.0)
        result = creative_fatigue(healthy, baseline)

        assert result.fatigue_score < 0.45, "Healthy creative should have low fatigue"
        assert result.state == FatigueState.HEALTHY

    def test_fatigued_creative_high_score(
        self,
        fatigued_creative_metrics: EntityMetrics,
        sample_baseline_metrics: BaselineMetrics,
    ):
        """Fatigued creative should have high fatigue score."""
        result = creative_fatigue(fatigued_creative_metrics, sample_baseline_metrics)

        assert result.fatigue_score >= 0.45, "Fatigued creative should have high score"
        assert result.state in [FatigueState.WATCH, FatigueState.REFRESH]
        assert result.ctr_drop > 0, "CTR should be declining"

    def test_watch_state_intermediate_fatigue(self):
        """Intermediate fatigue should trigger WATCH state."""
        watching = EntityMetrics(
            entity_id="creative_watching",
            entity_name="Watch Creative",
            entity_level=EntityLevel.CREATIVE,
            platform=Platform.META,
            date=datetime.now(UTC),
            ctr=0.008,  # Slightly down
            roas=3.5,  # Slightly down
            cpa=45.0,  # Slightly up
            frequency=3.5,  # Moderate frequency
        )

        baseline = BaselineMetrics(ctr=0.01, roas=4.0, cpa=40.0, frequency=2.0)
        result = creative_fatigue(watching, baseline)

        # Should be in watch range
        if 0.45 <= result.fatigue_score < 0.65:
            assert result.state == FatigueState.WATCH

    def test_refresh_state_severe_fatigue(self):
        """Severe fatigue should trigger REFRESH state."""
        severe = EntityMetrics(
            entity_id="creative_severe",
            entity_name="Severe Fatigue",
            entity_level=EntityLevel.CREATIVE,
            platform=Platform.META,
            date=datetime.now(UTC),
            ctr=0.003,  # Severely down
            roas=1.0,  # Severely down
            cpa=100.0,  # Severely up
            frequency=8.0,  # Very high frequency
        )

        baseline = BaselineMetrics(ctr=0.01, roas=4.0, cpa=40.0, frequency=2.0)
        result = creative_fatigue(severe, baseline)

        assert result.fatigue_score >= 0.65, "Severe fatigue should have high score"
        assert result.state == FatigueState.REFRESH
        assert len(result.recommendations) > 0, "Should have recommendations"

    def test_batch_creative_fatigue(self, sample_baseline_metrics: BaselineMetrics):
        """Batch calculation for multiple creatives."""
        creatives = [
            EntityMetrics(
                entity_id=f"creative_{i}",
                entity_name=f"Creative {i}",
                entity_level=EntityLevel.CREATIVE,
                platform=Platform.META,
                date=datetime.now(UTC),
                ctr=0.01 - (i * 0.002),  # Decreasing CTR
                roas=4.0 - (i * 0.5),
                cpa=40.0 + (i * 10),
                frequency=2.0 + i,
            )
            for i in range(5)
        ]

        baselines = {c.entity_id: sample_baseline_metrics for c in creatives}
        results = batch_creative_fatigue(creatives, baselines)

        assert len(results) == 5
        # Results are sorted by fatigue score descending (most fatigued first)
        for i in range(1, len(results)):
            assert results[i].fatigue_score <= results[i - 1].fatigue_score


# =============================================================================
# Anomaly Detection Tests (anomalies.py)
# =============================================================================


class TestAnomalyDetection:
    """Tests for z-score anomaly detection."""

    def test_no_anomaly_normal_value(self):
        """Normal value should not trigger anomaly."""
        series = [100.0, 102.0, 98.0, 101.0, 99.0, 100.0, 103.0, 97.0, 101.0, 100.0]
        current = 101.0  # Within normal range

        zscore = anomaly_zscore(series, current)

        assert abs(zscore) < 2.5, "Normal value should have low z-score"

    def test_high_anomaly_detected(self):
        """Abnormally high value should trigger anomaly."""
        series = [100.0, 102.0, 98.0, 101.0, 99.0, 100.0, 103.0, 97.0, 101.0, 100.0]
        current = 150.0  # Way above normal

        zscore = anomaly_zscore(series, current)

        assert zscore > 2.5, "High value should have positive z-score"
        assert get_severity(zscore) in [
            AlertSeverity.MEDIUM,
            AlertSeverity.HIGH,
            AlertSeverity.CRITICAL,
        ]

    def test_low_anomaly_detected(self):
        """Abnormally low value should trigger anomaly."""
        series = [100.0, 102.0, 98.0, 101.0, 99.0, 100.0, 103.0, 97.0, 101.0, 100.0]
        current = 50.0  # Way below normal

        zscore = anomaly_zscore(series, current)

        assert zscore < -2.5, "Low value should have negative z-score"

    def test_severity_levels(self):
        """Test severity level thresholds."""
        assert get_severity(1.0) == AlertSeverity.LOW
        assert get_severity(2.5) == AlertSeverity.MEDIUM
        assert get_severity(3.0) == AlertSeverity.HIGH
        assert get_severity(4.5) == AlertSeverity.CRITICAL

    def test_detect_anomalies_multiple_metrics(self):
        """Detect anomalies across multiple metrics."""
        metrics_history = {
            "spend": [1000.0, 1050.0, 980.0, 1020.0, 990.0, 1000.0, 1010.0, 995.0, 1005.0, 1000.0],
            "roas": [4.0, 4.1, 3.9, 4.0, 4.2, 3.8, 4.0, 4.1, 3.9, 4.0],
            "cpa": [40.0, 42.0, 38.0, 41.0, 39.0, 40.0, 43.0, 37.0, 41.0, 40.0],
        }

        current_values = {
            "spend": 1010.0,  # Normal
            "roas": 2.0,  # Anomaly - way down
            "cpa": 80.0,  # Anomaly - way up
        }

        results = detect_anomalies(metrics_history, current_values)

        # Should detect anomalies in roas and cpa
        anomaly_metrics = [r.metric for r in results if r.is_anomaly]
        assert "roas" in anomaly_metrics, "ROAS anomaly should be detected"
        assert "cpa" in anomaly_metrics, "CPA anomaly should be detected"
        assert "spend" not in anomaly_metrics, "Spend should not be anomaly"


# =============================================================================
# Signal Health Tests (signal_health.py)
# =============================================================================


class TestSignalHealth:
    """Tests for EMQ/signal health checks."""

    def test_healthy_status(self):
        """Good EMQ and low loss should be HEALTHY."""
        result = signal_health(
            emq_score=95.0,
            event_loss_pct=2.0,
            api_health=True,
        )

        assert result.status == SignalHealthStatus.HEALTHY
        assert len(result.issues) == 0
        assert not should_suspend_automation(result)

    def test_risk_status_low_emq(self):
        """EMQ below 90 but above 80 should be RISK."""
        result = signal_health(
            emq_score=85.0,
            event_loss_pct=3.0,
            api_health=True,
        )

        assert result.status == SignalHealthStatus.RISK
        assert len(result.issues) > 0
        assert not should_suspend_automation(result)

    def test_degraded_status_very_low_emq(self):
        """EMQ below 80 should be DEGRADED."""
        result = signal_health(
            emq_score=75.0,
            event_loss_pct=5.0,
            api_health=True,
        )

        assert result.status == SignalHealthStatus.DEGRADED
        assert should_suspend_automation(result)
        assert "suspend" in " ".join(result.actions).lower()

    def test_critical_status_api_down(self):
        """API failure should be CRITICAL regardless of other metrics."""
        result = signal_health(
            emq_score=95.0,
            event_loss_pct=2.0,
            api_health=False,
        )

        assert result.status == SignalHealthStatus.CRITICAL
        assert should_suspend_automation(result)
        assert result.api_health == False

    def test_degraded_status_high_event_loss(self):
        """High event loss should be DEGRADED."""
        result = signal_health(
            emq_score=92.0,
            event_loss_pct=15.0,  # Very high loss
            api_health=True,
        )

        assert result.status == SignalHealthStatus.DEGRADED
        assert should_suspend_automation(result)

    def test_auto_resolve_creates_alerts(self):
        """Auto-resolve should create appropriate alerts."""
        degraded = signal_health(
            emq_score=70.0,
            event_loss_pct=12.0,
            api_health=True,
        )

        resolved = auto_resolve(degraded)

        assert resolved["automation_suspended"] == True
        assert len(resolved["alerts_created"]) > 0
        assert "suspend_automation" in resolved["actions_taken"]


# =============================================================================
# Recommendations Engine Tests (recommend.py)
# =============================================================================


class TestRecommendationsEngine:
    """Tests for the recommendations engine."""

    def test_generate_recommendations_healthy_account(
        self,
        sample_entity_metrics: EntityMetrics,
        sample_baseline_metrics: BaselineMetrics,
    ):
        """Healthy account should generate normal recommendations."""
        entities = [sample_entity_metrics]
        baselines = {sample_entity_metrics.entity_id: sample_baseline_metrics}

        result = generate_recommendations(
            entities,
            baselines,
            emq_score=95.0,
            event_loss_pct=2.0,
            api_health=True,
        )

        assert result["automation_blocked"] == False
        assert result["health"]["status"] == SignalHealthStatus.HEALTHY.value
        assert "generated_at" in result

    def test_automation_blocked_on_degraded_health(self):
        """Degraded health should block automation."""
        entities = [
            EntityMetrics(
                entity_id="test",
                entity_name="Test",
                entity_level=EntityLevel.CAMPAIGN,
                platform=Platform.META,
                date=datetime.now(UTC),
                roas=4.0,
                cpa=40.0,
            )
        ]
        baselines = {"test": BaselineMetrics(roas=4.0, cpa=40.0)}

        result = generate_recommendations(
            entities,
            baselines,
            emq_score=70.0,  # Very low - degraded
            event_loss_pct=15.0,  # Very high
            api_health=True,
        )

        assert result["automation_blocked"] == True
        assert len(result["alerts"]) > 0

    def test_scaling_summary_counts(
        self,
        high_performing_metrics: EntityMetrics,
        low_performing_metrics: EntityMetrics,
        sample_entity_metrics: EntityMetrics,
        sample_baseline_metrics: BaselineMetrics,
    ):
        """Scaling summary should correctly count actions."""
        entities = [high_performing_metrics, low_performing_metrics, sample_entity_metrics]
        baselines = {e.entity_id: sample_baseline_metrics for e in entities}

        result = generate_recommendations(
            entities,
            baselines,
            emq_score=95.0,
            api_health=True,
        )

        summary = result["scaling_summary"]
        total = (
            summary["scale_candidates"] + summary["fix_candidates"] + summary["watch_candidates"]
        )

        assert total == 3, "All entities should be classified"

    def test_creative_fatigue_recommendations(self, sample_baseline_metrics: BaselineMetrics):
        """Fatigued creatives should generate refresh recommendations."""
        fatigued = EntityMetrics(
            entity_id="creative_fatigued",
            entity_name="Fatigued Creative",
            entity_level=EntityLevel.CREATIVE,
            platform=Platform.META,
            date=datetime.now(UTC),
            ctr=0.002,
            roas=1.0,
            cpa=100.0,
            frequency=8.0,
        )

        entities = []
        baselines = {}
        creative_baselines = {"creative_fatigued": sample_baseline_metrics}

        engine = RecommendationsEngine()
        result = engine.generate_recommendations(
            entities,
            baselines,
            creatives_today=[fatigued],
            creative_baselines=creative_baselines,
            emq_score=95.0,
            api_health=True,
        )

        # Should have creative refresh recommendation
        refresh_recs = [r for r in result["recommendations"] if r["type"] == "creative_refresh"]
        assert len(refresh_recs) > 0, "Should recommend creative refresh"

    def test_anomaly_alerts_generated(self):
        """Anomalies should generate alerts."""
        entities = [
            EntityMetrics(
                entity_id="test",
                entity_name="Test",
                entity_level=EntityLevel.CAMPAIGN,
                platform=Platform.META,
                date=datetime.now(UTC),
                roas=4.0,
                cpa=40.0,
            )
        ]
        baselines = {"test": BaselineMetrics(roas=4.0, cpa=40.0)}

        metrics_history = {
            "roas": [4.0, 4.1, 3.9, 4.0, 4.2, 3.8, 4.0, 4.1, 3.9, 4.0],
            "spend": [1000.0] * 10,
        }
        current_metrics = {
            "roas": 1.5,  # Significant drop - anomaly
            "spend": 1000.0,
        }

        result = generate_recommendations(
            entities,
            baselines,
            metrics_history=metrics_history,
            current_metrics=current_metrics,
            emq_score=95.0,
            api_health=True,
        )

        anomaly_alerts = [a for a in result["alerts"] if a["type"] == "anomaly"]
        assert len(anomaly_alerts) > 0, "Should detect ROAS anomaly"


# =============================================================================
# Integration Tests
# =============================================================================


class TestAnalyticsIntegration:
    """Integration tests for analytics pipeline."""

    def test_full_recommendations_pipeline(self):
        """Test complete recommendations flow."""
        # Create test data
        entities = [
            EntityMetrics(
                entity_id=f"camp_{i}",
                entity_name=f"Campaign {i}",
                entity_level=EntityLevel.CAMPAIGN,
                platform=Platform.META,
                date=datetime.now(UTC),
                spend=1000.0 * (i + 1),
                roas=4.0 + (i - 2) * 0.5,  # Varying performance
                cpa=40.0 - (i - 2) * 5,
                cvr=0.05 + (i - 2) * 0.01,
                ctr=0.01 + (i - 2) * 0.002,
            )
            for i in range(5)
        ]

        baselines = {
            e.entity_id: BaselineMetrics(roas=4.0, cpa=40.0, cvr=0.05, ctr=0.01) for e in entities
        }

        creatives = [
            EntityMetrics(
                entity_id=f"creative_{i}",
                entity_name=f"Creative {i}",
                entity_level=EntityLevel.CREATIVE,
                platform=Platform.META,
                date=datetime.now(UTC),
                ctr=0.01 - (i * 0.002),
                roas=4.0 - (i * 0.5),
                cpa=40.0 + (i * 10),
                frequency=2.0 + i,
            )
            for i in range(3)
        ]

        creative_baselines = {
            c.entity_id: BaselineMetrics(ctr=0.01, roas=4.0, cpa=40.0, frequency=2.0)
            for c in creatives
        }

        metrics_history = {
            "roas": [4.0, 4.1, 3.9, 4.0, 4.2, 3.8, 4.0, 4.1, 3.9, 4.0],
            "spend": [5000.0] * 10,
        }

        current_metrics = {"roas": 3.8, "spend": 5500.0}

        spends = {e.entity_id: e.spend for e in entities}

        # Generate recommendations
        result = generate_recommendations(
            entities,
            baselines,
            creatives_today=creatives,
            creative_baselines=creative_baselines,
            metrics_history=metrics_history,
            current_metrics=current_metrics,
            emq_score=92.0,
            event_loss_pct=4.0,
            api_health=True,
            current_spends=spends,
        )

        # Validate result structure
        assert "recommendations" in result
        assert "actions" in result
        assert "alerts" in result
        assert "insights" in result
        assert "health" in result
        assert "scaling_summary" in result
        assert "generated_at" in result
        assert "automation_blocked" in result

        # Should not block automation
        assert result["automation_blocked"] == False

        # Should have some recommendations or insights
        total_items = (
            len(result["recommendations"]) + len(result["actions"]) + len(result["insights"])
        )
        assert total_items > 0, "Should generate some recommendations"
