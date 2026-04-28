---
name: add-celery-task
description: Use when adding a new Celery background task to Stratum AI. Encodes idempotency, retry policy, async-session safety, audit logging, and tenant scoping so tasks land production-safe. Trigger when the user says "add task", "add worker", "background job", or creates a file under `backend/app/workers/`.
---

# Add Celery Task

Tasks are the async backbone — collectors, syncs, billing events, autopilot execution. The bugs here are nasty: double-charges, lost events, exhausted connection pools. This skill makes them safe by construction.

## Task anatomy

```python
# backend/app/workers/<domain>_tasks.py
from celery import shared_task
from celery.utils.log import get_task_logger
import structlog

from app.core.celery_app import celery_app
from app.db.session import async_session_factory

log = structlog.get_logger(__name__)

@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=60,        # seconds; uses exponential backoff via retry_backoff
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    acks_late=True,                 # only ack after success — survives worker crashes
    name="stratum.<domain>.<action>",
)
async def collect_meta_signals(self, tenant_id: int, account_id: int, idempotency_key: str | None = None):
    log.info("task.start", task=self.name, tenant_id=tenant_id, account_id=account_id, attempt=self.request.retries)

    # 1. Idempotency check (fast, separate session)
    async with async_session_factory() as db:
        if idempotency_key and await already_processed(db, idempotency_key):
            log.info("task.skip", reason="already_processed", key=idempotency_key)
            return

    # 2. External API call — NO database session held here
    try:
        result = await meta_client.fetch_signals(tenant_id, account_id)
    except RateLimitError as e:
        log.warning("task.retry", reason="rate_limit", retry_after=e.retry_after)
        raise self.retry(exc=e, countdown=e.retry_after)
    except TransientError as e:
        log.warning("task.retry", reason="transient", error=str(e))
        raise self.retry(exc=e)

    # 3. Write result + audit log in one transaction
    async with async_session_factory() as db:
        async with db.begin():
            for sig in result.signals:
                await signal_repo.upsert(db, tenant_id=tenant_id, signal=sig)
            await audit_log.create(db, action="signal.collect", tenant_id=tenant_id,
                                    target_id=account_id, count=len(result.signals))

    log.info("task.success", count=len(result.signals))
```

## The non-negotiables

1. **Decorator config** — always `bind=True`, `max_retries`, `default_retry_delay`, `acks_late=True`, named `stratum.<domain>.<action>`.
2. **Tenant first** — `tenant_id` is the first or second positional arg; never resolved inside the task.
3. **Idempotency** — one of:
   - `idempotency_key` parameter checked at task start
   - Check-and-skip (`if record.processed_at: return`)
   - Database unique constraint that makes retries safe
     Tasks that mutate external systems (email, Stripe, ad platform) MUST have idempotency.
4. **Retry policy** — wrap external calls in try/except; call `self.retry(exc=e, countdown=...)`. Never bare `except`.
5. **Async session lifetime** — a session must NOT be held across `await client.<network>()`. Open → read → close → call → open → write → close.
6. **Structured logging** — every task logs `task.start`, `task.success` or `task.error`, with `tenant_id`, `attempt`, and result counts. Use `structlog`, not `print` or stdlib logging.
7. **Audit log** — any task that mutates tenant data writes an audit entry inside the same transaction as the mutation.
8. **No `.delay()` inside an open transaction** — use `transaction.on_commit(...)` or schedule after the commit.

## Scheduling

In `backend/app/workers/celery_beat.py`:

```python
celery_app.conf.beat_schedule = {
    "collect-meta-every-15min": {
        "task": "stratum.meta.collect",
        "schedule": crontab(minute="*/15"),
        "args": [],
        "options": {"queue": "collectors"},
    },
}
```

Per-tenant scheduling: enqueue in a dispatcher task that fan-outs `for tenant in active_tenants: collect_meta.delay(tenant.id)`.

## Tests

**Unit** — `backend/tests/unit/workers/test_<domain>_tasks.py`:

- Happy path
- Idempotency: second call with same key returns early
- Retry: simulate `RateLimitError`, verify `self.retry` called
- Tenant scoping: task receiving wrong tenant_id raises or skips
- Audit log written

**Integration** — `backend/tests/integration/test_<domain>_task_flow.py`:

- Full flow with celery `task_always_eager=True`
- Connects to test DB, asserts signals written
- Asserts audit row exists

Coverage target: 90%+.

## Definition of Done

- [ ] Task in `workers/<domain>_tasks.py` with all decorator args
- [ ] `tenant_id` first/second arg
- [ ] Idempotency mechanism in place (or documented as not needed with reason)
- [ ] Retry on transient errors
- [ ] No DB session held across network calls
- [ ] Structured logging on enter/success/error
- [ ] Audit log on mutating side effects
- [ ] Beat schedule registered (if periodic)
- [ ] Unit + integration tests, 90%+ coverage
- [ ] `celery-task-reviewer` agent passes review
- [ ] `make lint` and `make test` clean

## Anti-patterns

- ❌ `@app.task` without `bind=True` and `max_retries`
- ❌ `try/except Exception: pass` swallowing failures
- ❌ Holding `async with db:` across an `await httpx.get(...)`
- ❌ `datetime.utcnow()` (use `datetime.now(timezone.utc)`)
- ❌ Using `print()` instead of `structlog`
- ❌ Resolving "current tenant" from anywhere except the explicit arg
- ❌ Calling `task.delay()` while a DB transaction is open
- ❌ Returning data through the task result that contains PII
