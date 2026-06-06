# =============================================================================
# Stratum AI - Audit Queue Key Contract Tests
# =============================================================================
"""
Regression tests for the audit-log pipeline (P0-3).

The middleware (producer) and the ``process_audit_log_queue`` worker
(consumer) previously hardcoded *different* Redis keys
(``audit_log_queue`` vs ``audit:log:queue``), so every audited event was
silently dropped. Both must now reference the single shared constant.
"""

from app.core.constants import AUDIT_LOG_QUEUE_KEY


def test_constant_is_non_empty_string():
    assert isinstance(AUDIT_LOG_QUEUE_KEY, str) and AUDIT_LOG_QUEUE_KEY


def test_producer_and_consumer_share_the_same_key():
    """Middleware and worker must drain the exact key the middleware fills."""
    from app.middleware import audit as producer
    from app.workers.tasks import audit as consumer

    assert producer.AUDIT_LOG_QUEUE_KEY == AUDIT_LOG_QUEUE_KEY
    assert consumer.AUDIT_LOG_QUEUE_KEY == AUDIT_LOG_QUEUE_KEY


def test_no_legacy_hardcoded_key_remains():
    """The old mismatched literal must not survive in either module's source."""
    import inspect

    from app.middleware import audit as producer
    from app.workers.tasks import audit as consumer

    for mod in (producer, consumer):
        src = inspect.getsource(mod)
        assert '"audit_log_queue"' not in src, f"legacy key in {mod.__name__}"
