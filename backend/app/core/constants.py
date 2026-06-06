# =============================================================================
# Stratum AI - Shared Constants
# =============================================================================
"""
Cross-cutting constants shared between producers and consumers.

Keeping queue keys (and similar string contracts) in one place prevents the
producer/consumer drift that silently broke the audit-log pipeline, where the
middleware pushed to ``audit_log_queue`` while the worker drained
``audit:log:queue``.
"""

# Redis list key bridging the audit middleware (producer) and the
# ``process_audit_log_queue`` Celery task (consumer). Both MUST use this.
AUDIT_LOG_QUEUE_KEY = "audit:log:queue"
