         yield acquired
        finally:
            if acquired:
                try:
                    lock.release()
                except redis.exceptions.LockNotOwnedError:
                    # Lock expired or was released by another process
                    logger.warning(f"Lock {lock_name} was not owned when releasing")


# Global lock instance
_distributed_lock = DistributedLock()


def with_distributed_lock(
    lock_name: str = None,
    timeout: int = 3600,
    skip_if_locked: bool = True
) -> Callable:
    """
    Decorator to ensure only one instance of a task runs across all workers.

    Args:
        lock_name: Name of the lock (defaults to task name)
        timeout: Lock timeout in seconds (default 1 hour)
        skip_if_locked: If True, skip task silently when locked. If False, raise exception.

    Usage:
        @celery_app.task
        @with_distributed_lock(timeout=1800)
        def my_scheduled_task():
            # Only one worker will execute this
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            name = lock_name or f"{func.__module__}.{func.__name__}"
            with _distributed_lock.acquire(name, timeout=timeout) as acquired:
                if not acquired:
                    if skip_if_locked:
                        logger.info(
                            f"Task {name} skipped - already running on another worker"
                        )
                        return {"status": "skipped", "reason": "lock_held"}
                    else:
                        raise RuntimeError(f"Could not acquire lock for task {name}")
                return func(*args, **kwargs)
        return wrapper
    return decorator

# Create Celery app
celery_app = Celery(
    "stratum_ai",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.workers.tasks.sync",
        "app.workers.tasks.rules",
        "app.workers.tasks.competitors",
        "app.workers.tasks.forecast",