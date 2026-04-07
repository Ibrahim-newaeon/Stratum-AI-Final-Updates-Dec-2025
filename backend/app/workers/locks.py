"""
Redis distributed lock utilities used by Celery tasks.

Moved out of celery_app.py to avoid circular imports when tasks import
with_distributed_lock while celery_app is importing tasks.
"""

import functools
import logging
from collections.abc import Callable
from contextlib import contextmanager
from typing import Any

import redis

from app.core.config import settings

logger = logging.getLogger("stratum.workers.celery")


class DistributedLock:
    """
    Redis-based distributed lock to prevent duplicate task execution.

    When multiple Celery workers are running with beat scheduler,
    this lock ensures only one worker executes a scheduled task.
    """

    def __init__(self, redis_url: str | None = None):
        self.redis_url = redis_url or settings.redis_url
        self._redis_client: redis.Redis | None = None

    @property
    def redis_client(self) -> redis.Redis:
        """Lazy initialization of Redis client."""
        if self._redis_client is None:
            self._redis_client = redis.from_url(self.redis_url)
        return self._redis_client

    @contextmanager
    def acquire(self, lock_name: str, timeout: int = 3600, blocking: bool = False):
        """
        Acquire a distributed lock.

        Args:
            lock_name: Unique name for the lock (usually task name)
            timeout: Lock expiration in seconds (default 1 hour)
            blocking: Whether to wait for lock (default False)

        Yields:
            bool: True if lock was acquired, False otherwise
        """
        lock_key = f"celery:lock:{lock_name}"
        lock = self.redis_client.lock(lock_key, timeout=timeout, blocking=blocking)

        acquired = False
        try:
            acquired = lock.acquire(blocking=blocking)
            yield acquired
        finally:
            if acquired:
                try:
                    lock.release()
                except redis.exceptions.LockNotOwnedError:
                    logger.warning(f"Lock {lock_name} was not owned when releasing")


_distributed_lock = DistributedLock()


def with_distributed_lock(
    lock_name: str | None = None,
    timeout: int = 3600,
    skip_if_locked: bool = True,
) -> Callable:
    """
    Decorator to ensure only one instance of a task runs across all workers.
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
                    raise RuntimeError(f"Could not acquire lock for task {name}")
                return func(*args, **kwargs)

        return wrapper

    return decorator
