# =============================================================================
# Stratum AI - CAPI Resilience Primitives Unit Tests
# =============================================================================
"""Unit tests for the pure resilience primitives in
``app.services.capi.platform_connectors``:

- ``CircuitBreaker`` state machine (closed -> open -> half-open -> closed)
- ``RateLimiter`` token-bucket acquire/refill
- ``BatchOptimizer`` history-driven batch-size recommendation

These are standalone dataclasses / in-memory helpers — no network, no
credentials, no PIIHasher/AIEventMapper construction.
"""

import time

import pytest

from app.services.capi.platform_connectors import (
    BatchOptimizer,
    CircuitBreaker,
    CircuitState,
    RateLimiter,
)

pytestmark = pytest.mark.unit


# =============================================================================
# CircuitBreaker
# =============================================================================
class TestCircuitBreaker:
    def test_starts_closed_and_executes(self):
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED
        assert cb.can_execute() is True

    def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker(failure_threshold=3)
        for _ in range(3):
            cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.can_execute() is False

    def test_success_resets_failure_count_when_closed(self):
        cb = CircuitBreaker(failure_threshold=3)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED

    def test_open_transitions_to_half_open_after_timeout(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=60)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        # Pretend the last failure was well beyond the recovery window.
        cb.last_failure_time = time.time() - 61
        assert cb.can_execute() is True
        assert cb.state == CircuitState.HALF_OPEN

    def test_half_open_closes_after_enough_successes(self):
        cb = CircuitBreaker(half_open_max_calls=2)
        cb.state = CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    def test_half_open_reopens_on_failure(self):
        cb = CircuitBreaker()
        cb.state = CircuitState.HALF_OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_half_open_limits_concurrent_calls(self):
        cb = CircuitBreaker(half_open_max_calls=1)
        cb.state = CircuitState.HALF_OPEN
        cb.half_open_calls = 1
        assert cb.can_execute() is False


# =============================================================================
# RateLimiter
# =============================================================================
class TestRateLimiter:
    def test_acquire_within_budget_succeeds(self):
        rl = RateLimiter(max_tokens=10, refill_rate=0.0, tokens=10.0)
        assert rl.acquire(3) is True
        assert rl.tokens == pytest.approx(7.0)

    def test_acquire_over_budget_fails(self):
        # refill_rate=0 keeps the bucket from topping up between calls.
        rl = RateLimiter(max_tokens=5, refill_rate=0.0, tokens=2.0)
        assert rl.acquire(3) is False
        # Tokens are untouched on a failed acquire.
        assert rl.tokens == pytest.approx(2.0)

    def test_refill_is_capped_at_max(self):
        rl = RateLimiter(max_tokens=10, refill_rate=1000.0, tokens=0.0)
        rl.last_refill = time.time() - 5  # would refill 5000 tokens uncapped
        assert rl.acquire(1) is True
        # Capped at max_tokens (10) before the single-token spend.
        assert rl.tokens == pytest.approx(9.0)


# =============================================================================
# BatchOptimizer
# =============================================================================
class TestBatchOptimizer:
    def test_insufficient_history_returns_platform_default(self):
        opt = BatchOptimizer()
        result = opt.optimize_batch_size("meta", current_batch_size=500)
        assert result.optimized_batch_size == BatchOptimizer.DEFAULT_BATCH_SIZES["meta"]
        assert result.estimated_throughput_improvement == 0
        assert "default" in result.recommendation.lower()

    def test_unknown_platform_falls_back_to_500(self):
        opt = BatchOptimizer()
        result = opt.optimize_batch_size("does-not-exist", current_batch_size=100)
        assert result.optimized_batch_size == 500

    def test_record_trims_and_computes_throughput(self):
        opt = BatchOptimizer()
        opt.record_batch_performance(
            "tiktok",
            batch_size=100,
            success=True,
            latency_ms=1000.0,
            events_processed=50,
        )
        rec = opt._performance_history["tiktok"][-1]
        # 50 events / (1000ms / 1000) = 50 events/sec.
        assert rec["throughput"] == pytest.approx(50.0)

    def test_optimizes_toward_higher_throughput_bucket(self):
        opt = BatchOptimizer()
        # Low-throughput small batches ...
        for _ in range(5):
            opt.record_batch_performance("meta", 100, True, 1000.0, 50)
        # ... high-throughput larger batches.
        for _ in range(5):
            opt.record_batch_performance("meta", 500, True, 1000.0, 400)
        result = opt.optimize_batch_size("meta", current_batch_size=100)
        # The 500 bucket has the better throughput, capped at 80% of rate limit.
        max_batch = int(BatchOptimizer.RATE_LIMITS["meta"] * 0.8)
        assert result.optimized_batch_size == min(500, max_batch)
        assert result.optimized_batch_size > result.original_batch_size
