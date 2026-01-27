# =============================================================================
# Stratum AI - Critical Features Unit Tests
# =============================================================================
"""
Unit tests for critical audit items:
1. CAPI connectors with circuit breaker/retry
2. Enhanced ROAS model with creative/audience features
3. Model retraining pipeline
4. Real EMQ measurement service
5. Offline conversion upload service
"""

from datetime import UTC, datetime, timedelta

import numpy as np
import pandas as pd
import pytest

# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_event():
    """Sample CAPI event for testing."""
    return {
        "event_id": "test_123",
        "event_name": "Purchase",
        "event_time": int(datetime.now(UTC).timestamp()),
        "user_data": {
            "email": "test@example.com",
            "phone": "+1234567890",
        },
        "parameters": {
            "value": 99.99,
            "currency": "USD",
        },
    }


@pytest.fixture
def sample_training_data():
    """Sample training data for ML tests."""
    np.random.seed(42)
    n_samples = 500

    data = {
        "campaign_id": [f"camp_{i % 50}" for i in range(n_samples)],
        "date": pd.date_range(start="2024-01-01", periods=n_samples, freq="D"),
        "platform": np.random.choice(["meta", "google", "tiktok"], n_samples),
        "spend": np.random.uniform(100, 5000, n_samples),
        "impressions": np.random.uniform(10000, 500000, n_samples).astype(int),
        "clicks": np.random.uniform(100, 5000, n_samples).astype(int),
        "conversions": np.random.uniform(5, 200, n_samples).astype(int),
        "creative_type": np.random.choice(["image", "video", "carousel"], n_samples),
        "audience_type": np.random.choice(["broad", "lookalike", "retargeting"], n_samples),
        "objective": np.random.choice(["conversions", "traffic", "awareness"], n_samples),
    }

    df = pd.DataFrame(data)
    df["revenue"] = df["conversions"] * np.random.uniform(20, 100, n_samples)

    return df


@pytest.fixture
def sample_offline_conversions():
    """Sample offline conversions for testing."""
    from app.services.offline_conversion_service import OfflineConversion, OfflineConversionSource

    return [
        OfflineConversion(
            conversion_id="offline_001",
            platform="meta",
            email="customer1@example.com",
            phone="+1234567890",
            event_name="Purchase",
            event_time=datetime.now(UTC),
            conversion_value=149.99,
            currency="USD",
            order_id="ORD-001",
            source=OfflineConversionSource.CRM,
        ),
        OfflineConversion(
            conversion_id="offline_002",
            platform="meta",
            email="customer2@example.com",
            event_name="Purchase",
            event_time=datetime.now(UTC) - timedelta(hours=2),
            conversion_value=299.99,
            currency="USD",
            order_id="ORD-002",
            source=OfflineConversionSource.POS,
        ),
    ]


# =============================================================================
# 1. CAPI Connector Tests
# =============================================================================


class TestCircuitBreaker:
    """Tests for circuit breaker implementation."""

    def test_circuit_breaker_starts_closed(self):
        """Circuit breaker should start in closed state."""
        from app.services.capi.platform_connectors import CircuitBreaker, CircuitState

        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() == True

    def test_circuit_opens_after_failures(self):
        """Circuit should open after threshold failures."""
        from app.services.capi.platform_connectors import CircuitBreaker, CircuitState

        cb = CircuitBreaker(failure_threshold=3)

        for _ in range(3):
            cb.record_failure()

        assert cb.state == CircuitState.OPEN
        assert cb.can_execute() == False

    def test_circuit_resets_on_success(self):
        """Failure count should reset on success."""
        from app.services.capi.platform_connectors import CircuitBreaker

        cb = CircuitBreaker(failure_threshold=5)

        cb.record_failure()
        cb.record_failure()
        assert cb.failure_count == 2

        cb.record_success()
        assert cb.failure_count == 0

    def test_circuit_half_open_after_timeout(self):
        """Circuit should go half-open after recovery timeout."""
        import time

        from app.services.capi.platform_connectors import CircuitBreaker, CircuitState

        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)

        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

        # Wait for recovery timeout
        time.sleep(1.1)

        # Should now be allowed to execute (half-open)
        assert cb.can_execute() == True
        assert cb.state == CircuitState.HALF_OPEN


class TestRateLimiter:
    """Tests for rate limiter implementation."""

    def test_rate_limiter_allows_within_limit(self):
        """Should allow requests within limit."""
        from app.services.capi.platform_connectors import RateLimiter

        rl = RateLimiter(max_tokens=10, refill_rate=1.0)

        # Should be able to acquire tokens
        assert rl.acquire(5) == True
        assert rl.acquire(5) == True

    def test_rate_limiter_blocks_over_limit(self):
        """Should block requests over limit."""
        from app.services.capi.platform_connectors import RateLimiter

        rl = RateLimiter(max_tokens=10, refill_rate=0.1)

        # Exhaust tokens
        assert rl.acquire(10) == True
        # Should now fail
        assert rl.acquire(1) == False


class TestEventDeliveryLog:
    """Tests for event delivery logging."""

    def test_log_event_delivery(self):
        """Should log event delivery for EMQ measurement."""
        from app.services.capi.platform_connectors import (
            EventDeliveryLog,
            get_event_delivery_logs,
            log_event_delivery,
        )

        log = EventDeliveryLog(
            event_id="test_event_123",
            platform="meta",
            event_name="Purchase",
            timestamp=datetime.now(UTC),
            success=True,
            latency_ms=150.0,
        )

        log_event_delivery(log)

        logs = get_event_delivery_logs(platform="meta")
        assert len(logs) > 0
        assert any(log.event_id == "test_event_123" for log in logs)


class TestMetaCAPIConnector:
    """Tests for Meta CAPI connector."""

    @pytest.mark.asyncio
    async def test_connect_validates_credentials(self):
        """Should validate credentials on connect."""
        from app.services.capi.platform_connectors import ConnectionStatus, MetaCAPIConnector

        connector = MetaCAPIConnector()

        # Missing credentials
        result = await connector.connect({})
        assert result.status == ConnectionStatus.ERROR
        assert "Missing" in result.message

    @pytest.mark.asyncio
    async def test_send_events_requires_connection(self):
        """Should fail if not connected."""
        from app.services.capi.platform_connectors import MetaCAPIConnector

        connector = MetaCAPIConnector()

        result = await connector.send_events([{"event_name": "test"}])
        assert result.success == False
        assert "Not connected" in result.errors[0]["message"]


class TestGoogleCAPIConnector:
    """Tests for Google Ads CAPI connector."""

    @pytest.mark.asyncio
    async def test_connect_requires_credentials(self):
        """Should require customer_id and developer_token."""
        from app.services.capi.platform_connectors import ConnectionStatus, GoogleCAPIConnector

        connector = GoogleCAPIConnector()

        result = await connector.connect({"customer_id": "123"})
        assert result.status == ConnectionStatus.ERROR
        assert "Missing" in result.message


# =============================================================================
# 2. Enhanced ML Training Tests
# =============================================================================


class TestEnhancedMLTraining:
    """Tests for enhanced ROAS model with creative/audience features."""

    def test_prepare_data_creates_creative_features(self, sample_training_data):
        """Should create creative type features."""
        from app.ml.train import ModelTrainer

        trainer = ModelTrainer()
        prepared = trainer._prepare_data(sample_training_data)

        # Check creative features exist
        assert "creative_image" in prepared.columns
        assert "creative_video" in prepared.columns
        assert "creative_carousel" in prepared.columns

    def test_prepare_data_creates_audience_features(self, sample_training_data):
        """Should create audience type features."""
        from app.ml.train import ModelTrainer

        trainer = ModelTrainer()
        prepared = trainer._prepare_data(sample_training_data)

        # Check audience features exist
        assert "audience_broad" in prepared.columns
        assert "audience_lookalike" in prepared.columns
        assert "audience_retargeting" in prepared.columns

    def test_prepare_data_creates_objective_features(self, sample_training_data):
        """Should create objective features."""
        from app.ml.train import ModelTrainer

        trainer = ModelTrainer()
        prepared = trainer._prepare_data(sample_training_data)

        # Check objective features exist
        assert "objective_conversions" in prepared.columns
        assert "objective_traffic" in prepared.columns

    def test_prepare_data_creates_platform_features(self, sample_training_data):
        """Should create platform one-hot features."""
        from app.ml.train import ModelTrainer

        trainer = ModelTrainer()
        prepared = trainer._prepare_data(sample_training_data)

        # Check platform features exist
        assert "platform_meta" in prepared.columns
        assert "platform_google" in prepared.columns
        assert "platform_tiktok" in prepared.columns

    def test_prepare_data_calculates_derived_metrics(self, sample_training_data):
        """Should calculate CTR, CVR, ROAS, etc."""
        from app.ml.train import ModelTrainer

        trainer = ModelTrainer()
        prepared = trainer._prepare_data(sample_training_data)

        # Check derived metrics
        assert "ctr" in prepared.columns
        assert "cvr" in prepared.columns
        assert "roas" in prepared.columns
        assert "cpm" in prepared.columns
        assert "cpc" in prepared.columns

    def test_prepare_data_creates_log_transforms(self, sample_training_data):
        """Should create log-transformed features."""
        from app.ml.train import ModelTrainer

        trainer = ModelTrainer()
        prepared = trainer._prepare_data(sample_training_data)

        assert "log_spend" in prepared.columns
        assert "log_impressions" in prepared.columns
        assert "log_clicks" in prepared.columns

    def test_train_roas_predictor_returns_metrics(self, sample_training_data):
        """ROAS predictor training should return metrics."""
        import tempfile

        from app.ml.train import ModelTrainer

        with tempfile.TemporaryDirectory() as tmpdir:
            trainer = ModelTrainer(models_path=tmpdir)
            prepared = trainer._prepare_data(sample_training_data)

            metrics = trainer.train_roas_predictor(prepared)

            assert "r2" in metrics
            assert "mae" in metrics
            assert "rmse" in metrics
            assert metrics["r2"] >= -1  # R2 can be negative for bad fits
            assert metrics["num_features"] > 5  # Should have multiple features


# =============================================================================
# 3. Retraining Pipeline Tests
# =============================================================================


class TestRetrainingPipeline:
    """Tests for model retraining pipeline."""

    def test_retraining_config_defaults(self):
        """Should have sensible default config."""
        from app.ml.retraining_pipeline import RetrainingConfig

        config = RetrainingConfig()

        assert config.retrain_interval_days == 7
        assert config.min_samples_for_retrain == 1000
        assert config.min_r2_improvement == 0.02

    def test_check_retraining_needed_new_model(self):
        """Should need retraining if model doesn't exist."""
        import tempfile

        from app.ml.retraining_pipeline import RetrainingPipeline, RetrainingTrigger

        with tempfile.TemporaryDirectory() as tmpdir:
            pipeline = RetrainingPipeline(
                config=type(
                    "Config",
                    (),
                    {
                        "models_path": tmpdir,
                        "archive_path": f"{tmpdir}/archive",
                        "staging_path": f"{tmpdir}/staging",
                        "retrain_interval_days": 7,
                        "min_samples_for_retrain": 1000,
                        "min_r2_improvement": 0.02,
                        "max_r2_degradation": 0.05,
                        "drift_detection_window_days": 7,
                        "max_model_versions": 5,
                        "staging_validation_hours": 24,
                    },
                )()
            )

            needs, trigger, reason = pipeline.check_retraining_needed("nonexistent_model")

            assert needs == True
            assert trigger == RetrainingTrigger.MANUAL
            assert "does not exist" in reason

    def test_model_version_tracking(self):
        """Should track model versions in history."""
        from app.ml.retraining_pipeline import ModelStatus, ModelVersion, RetrainingTrigger

        version = ModelVersion(
            version_id="20240101_120000",
            model_name="roas_predictor",
            created_at=datetime.now(UTC),
            metrics={"r2": 0.75, "mae": 0.5},
            status=ModelStatus.ACTIVE,
            trigger=RetrainingTrigger.SCHEDULED,
            training_samples=10000,
            features=["log_spend", "ctr", "cvr"],
            path="./models/roas_predictor.pkl",
        )

        assert version.version_id == "20240101_120000"
        assert version.status == ModelStatus.ACTIVE


# =============================================================================
# 4. Real EMQ Measurement Tests
# =============================================================================


class TestRealEMQMeasurement:
    """Tests for real EMQ measurement service."""

    def test_record_pixel_event(self):
        """Should record pixel events for matching."""
        from app.services.emq_measurement_service import (
            PixelEvent,
            _pixel_events,
            record_pixel_event,
        )

        event = PixelEvent(
            event_id="pixel_test_123",
            platform="meta",
            event_name="Purchase",
            timestamp=datetime.now(UTC),
        )

        initial_count = len(_pixel_events)
        record_pixel_event(event)

        assert len(_pixel_events) > initial_count

    def test_real_emq_metrics_calculation(self):
        """Should calculate real EMQ metrics from data."""
        from app.services.emq_measurement_service import (
            PixelEvent,
            calculate_real_emq_metrics,
            record_pixel_event,
        )

        # Record some test events
        for i in range(5):
            record_pixel_event(
                PixelEvent(
                    event_id=f"test_pixel_{i}",
                    platform="meta",
                    event_name="Purchase",
                    timestamp=datetime.now(UTC),
                )
            )

        metrics = calculate_real_emq_metrics("meta", period_hours=1)

        assert metrics.platform == "meta"
        assert metrics.pixel_events_count >= 0

    def test_convert_real_to_platform_metrics(self):
        """Should convert real metrics to PlatformMetrics format."""
        from app.services.emq_measurement_service import (
            RealEMQMetrics,
            convert_real_to_platform_metrics,
        )

        real = RealEMQMetrics(
            platform="meta",
            period_start=datetime.now(UTC) - timedelta(hours=24),
            period_end=datetime.now(UTC),
            pixel_events_count=1000,
            capi_events_count=950,
            matched_events_count=900,
            match_rate=90.0,
            avg_capi_latency_ms=200,
            capi_success_count=950,
            capi_failure_count=50,
            capi_delivery_rate=95.0,
        )

        platform_metrics = convert_real_to_platform_metrics(real)

        assert platform_metrics.platform == "meta"
        assert platform_metrics.pixel_events == 1000
        assert platform_metrics.capi_events == 950
        assert platform_metrics.matched_events == 900

    def test_real_emq_service_caching(self):
        """Should cache EMQ results."""
        from app.services.emq_measurement_service import RealEMQService

        service = RealEMQService()

        # First call
        result1 = service.get_platform_emq("meta", period_hours=24)

        # Second call should use cache
        result2 = service.get_platform_emq("meta", period_hours=24)

        # Same object from cache
        assert result1.calculated_at == result2.calculated_at


# =============================================================================
# 5. Offline Conversion Upload Tests
# =============================================================================


class TestOfflineConversionService:
    """Tests for offline conversion upload service."""

    def test_parse_csv_basic(self):
        """Should parse basic CSV content."""
        from app.services.offline_conversion_service import OfflineConversionService

        service = OfflineConversionService()

        csv_content = """email,phone,value,currency,event_time
test1@example.com,+1234567890,99.99,USD,2024-01-15
test2@example.com,+0987654321,149.99,USD,2024-01-16"""

        conversions = service.parse_csv(csv_content, "meta")

        assert len(conversions) == 2
        assert conversions[0].email == "test1@example.com"
        assert conversions[0].conversion_value == 99.99

    def test_parse_csv_with_mapping(self):
        """Should parse CSV with custom column mapping."""
        from app.services.offline_conversion_service import OfflineConversionService

        service = OfflineConversionService()

        csv_content = """customer_email,mobile_number,order_total
test@example.com,+1234567890,199.99"""

        mapping = {
            "email": ["customer_email"],
            "phone": ["mobile_number"],
            "conversion_value": ["order_total"],
        }

        conversions = service.parse_csv(csv_content, "meta", column_mapping=mapping)

        assert len(conversions) == 1
        assert conversions[0].email == "test@example.com"
        assert conversions[0].conversion_value == 199.99

    def test_parse_csv_skips_invalid_rows(self):
        """Should skip rows without identifiers."""
        from app.services.offline_conversion_service import OfflineConversionService

        service = OfflineConversionService()

        csv_content = """email,phone,value
test@example.com,,99.99
,,49.99
,+1234567890,149.99"""

        conversions = service.parse_csv(csv_content, "meta")

        # First and third rows should be valid (have email or phone)
        assert len(conversions) == 2

    def test_meta_uploader_format_conversion(self, sample_offline_conversions):
        """Should format conversion for Meta API."""
        from app.services.offline_conversion_service import MetaOfflineUploader

        uploader = MetaOfflineUploader()
        conv = sample_offline_conversions[0]

        formatted = uploader._format_conversion(conv)

        assert "match_keys" in formatted
        assert "event_name" in formatted
        assert "event_time" in formatted
        assert "value" in formatted
        assert formatted["event_name"] == "Purchase"

    def test_google_uploader_requires_gclid(self, sample_offline_conversions):
        """Google uploader should skip conversions without GCLID."""
        from app.services.offline_conversion_service import GoogleOfflineUploader

        uploader = GoogleOfflineUploader()
        conv = sample_offline_conversions[0]  # No GCLID

        formatted = uploader._format_conversion(conv, "123456", "conv_001")

        assert formatted is None  # Should skip without GCLID

    def test_upload_history_tracking(self, sample_offline_conversions):
        """Should track upload history."""
        from app.services.offline_conversion_service import OfflineConversionService

        service = OfflineConversionService()

        # Get history (may be empty or have previous test data)
        history = service.get_upload_history(platform="meta", limit=10)

        assert isinstance(history, list)

    def test_batch_status_lookup(self):
        """Should return None for unknown batch."""
        from app.services.offline_conversion_service import OfflineConversionService

        service = OfflineConversionService()

        status = service.get_batch_status("nonexistent_batch_123")

        assert status is None


# =============================================================================
# Integration Tests
# =============================================================================


class TestCriticalFeaturesIntegration:
    """Integration tests for critical features."""

    def test_emq_measurement_with_capi_logs(self):
        """EMQ measurement should use CAPI delivery logs."""
        from app.services.capi.platform_connectors import (
            EventDeliveryLog,
            log_event_delivery,
        )
        from app.services.emq_measurement_service import (
            PixelEvent,
            calculate_real_emq_metrics,
            record_pixel_event,
        )

        # Simulate CAPI events
        for i in range(10):
            log_event_delivery(
                EventDeliveryLog(
                    event_id=f"integration_test_{i}",
                    platform="tiktok",
                    event_name="Purchase",
                    timestamp=datetime.now(UTC),
                    success=i < 9,  # 90% success rate
                    latency_ms=100 + i * 10,
                )
            )

        # Simulate pixel events
        for i in range(10):
            record_pixel_event(
                PixelEvent(
                    event_id=f"integration_test_{i}",
                    platform="tiktok",
                    event_name="Purchase",
                    timestamp=datetime.now(UTC),
                )
            )

        # Calculate EMQ
        metrics = calculate_real_emq_metrics("tiktok", period_hours=1)

        assert metrics.capi_events_count >= 10
        assert metrics.capi_delivery_rate >= 80  # At least 80%

    def test_ml_training_end_to_end(self, sample_training_data):
        """End-to-end ML training test."""
        import tempfile
        from pathlib import Path

        from app.ml.train import ModelTrainer

        with tempfile.TemporaryDirectory() as tmpdir:
            trainer = ModelTrainer(models_path=tmpdir)
            tmpdir_path = Path(tmpdir)

            # Train all models
            results = trainer.train_all(sample_training_data, include_platform_models=False)

            assert "roas_predictor" in results
            assert "conversion_predictor" in results
            assert "budget_impact" in results

            # Check files were created
            assert (tmpdir_path / "roas_predictor.pkl").exists()
            assert (tmpdir_path / "roas_predictor_metadata.json").exists()


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
