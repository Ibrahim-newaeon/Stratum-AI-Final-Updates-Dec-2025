# =============================================================================
# Stratum AI - Celery Memory Profiling Hooks
# =============================================================================
"""
Celery signal hooks that track memory usage per task type.

Connects to task_prerun/task_postrun signals to measure RSS delta
for every task execution. Aggregates stats by task name.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

import psutil
from celery import Celery
from celery.signals import task_postrun, task_prerun, worker_process_init

logger = logging.getLogger("stratum.monitoring.celery")


@dataclass
class TaskMemoryStats:
    """Aggregated memory stats for a single Celery task type."""
    task_name: str
    execution_count: int = 0
    total_rss_delta_kb: float = 0.0
    max_rss_delta_kb: float = 0.0
    min_rss_delta_kb: float = float("inf")
    avg_rss_delta_kb: float = 0.0
    total_duration_ms: float = 0.0
    max_duration_ms: float = 0.0
    failure_count: int = 0
    last_rss_delta_kb: float = 0.0
    peak_rss_mb: float = 0.0
    recent_deltas: list[float] = field(default_factory=list)

    def record(
        self,
        rss_delta_kb: float,
        duration_ms: float,
        peak_rss_mb: float,
        failed: bool = False,
    ) -> None:
        """Record a task execution measurement."""
        self.execution_count += 1
        self.total_rss_delta_kb += rss_delta_kb
        self.total_duration_ms += duration_ms
        self.last_rss_delta_kb = rss_delta_kb

        if failed:
            self.failure_count += 1
        if rss_delta_kb > self.max_rss_delta_kb:
            self.max_rss_delta_kb = rss_delta_kb
        if rss_delta_kb < self.min_rss_delta_kb:
            self.min_rss_delta_kb = rss_delta_kb
        if duration_ms > self.max_duration_ms:
            self.max_duration_ms = duration_ms
        if peak_rss_mb > self.peak_rss_mb:
            self.peak_rss_mb = peak_rss_mb

        self.avg_rss_delta_kb = round(
            self.total_rss_delta_kb / self.execution_count, 2
        )

        self.recent_deltas.append(rss_delta_kb)
        if len(self.recent_deltas) > 50:
            self.recent_deltas.pop(0)

    def to_dict(self) -> dict[str, Any]:
        short_name = self.task_name.split(".")[-1]
        return {
            "task_name": self.task_name,
            "short_name": short_name,
            "execution_count": self.execution_count,
            "avg_rss_delta_kb": self.avg_rss_delta_kb,
            "max_rss_delta_kb": round(self.max_rss_delta_kb, 2),
            "min_rss_delta_kb": round(self.min_rss_delta_kb, 2)
            if self.min_rss_delta_kb != float("inf")
            else 0.0,
            "total_rss_delta_kb": round(self.total_rss_delta_kb, 2),
            "avg_duration_ms": round(
                self.total_duration_ms / self.execution_count, 2
            )
            if self.execution_count > 0
            else 0.0,
            "max_duration_ms": round(self.max_duration_ms, 2),
            "peak_rss_mb": round(self.peak_rss_mb, 2),
            "failure_count": self.failure_count,
            "leak_risk": self._assess_leak_risk(),
        }

    def _assess_leak_risk(self) -> str:
        """Assess whether this task type shows signs of memory leaks."""
        if len(self.recent_deltas) < 5:
            return "unknown"
        avg = sum(self.recent_deltas[-10:]) / len(self.recent_deltas[-10:])
        if avg > 5000:  # >5MB average growth per run
            return "high"
        if avg > 1000:  # >1MB average growth per run
            return "medium"
        if avg > 100:  # >100KB average growth per run
            return "low"
        return "none"


class CeleryMemoryHooks:
    """
    Hooks into Celery signals to track per-task memory usage.

    Usage:
        hooks = CeleryMemoryHooks()
        hooks.connect(celery_app)
    """

    def __init__(self) -> None:
        self._task_stats: dict[str, TaskMemoryStats] = {}
        self._active_tasks: dict[str, dict[str, Any]] = {}
        self._process = psutil.Process()
        self._worker_start_rss: float = 0.0

    def connect(self, app: Celery) -> None:
        """Connect signal handlers to the Celery app."""
        task_prerun.connect(self._on_task_prerun)
        task_postrun.connect(self._on_task_postrun)
        worker_process_init.connect(self._on_worker_init)
        logger.info("Celery memory hooks connected")

    def _on_worker_init(self, sender: Any = None, **kwargs: Any) -> None:
        """Record worker baseline memory on init."""
        self._worker_start_rss = self._process.memory_info().rss
        logger.info(
            "Worker memory baseline: %.2f MB",
            self._worker_start_rss / (1024 * 1024),
        )

    def _on_task_prerun(
        self,
        sender: Any = None,
        task_id: str = "",
        task: Any = None,
        **kwargs: Any,
    ) -> None:
        """Record memory state before task execution."""
        self._active_tasks[task_id] = {
            "rss_before": self._process.memory_info().rss,
            "start_time": time.perf_counter(),
            "task_name": sender.name if sender else "unknown",
        }

    def _on_task_postrun(
        self,
        sender: Any = None,
        task_id: str = "",
        task: Any = None,
        state: str = "",
        **kwargs: Any,
    ) -> None:
        """Record memory delta after task execution."""
        if task_id not in self._active_tasks:
            return

        pre = self._active_tasks.pop(task_id)
        rss_after = self._process.memory_info().rss
        rss_delta_kb = round((rss_after - pre["rss_before"]) / 1024, 2)
        duration_ms = (time.perf_counter() - pre["start_time"]) * 1000
        peak_rss_mb = round(rss_after / (1024 * 1024), 2)
        task_name = pre["task_name"]
        failed = state == "FAILURE"

        if task_name not in self._task_stats:
            self._task_stats[task_name] = TaskMemoryStats(task_name=task_name)

        self._task_stats[task_name].record(
            rss_delta_kb=rss_delta_kb,
            duration_ms=duration_ms,
            peak_rss_mb=peak_rss_mb,
            failed=failed,
        )

        # Log warning for large memory growth
        if rss_delta_kb > 50_000:  # >50MB
            logger.warning(
                "High memory usage in task %s: +%.2f MB",
                task_name,
                rss_delta_kb / 1024,
            )

    def get_task_stats(
        self, sort_by: str = "avg_rss_delta_kb", limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get all task memory stats, sorted by specified field."""
        stats = [s.to_dict() for s in self._task_stats.values()]
        stats.sort(key=lambda x: abs(x.get(sort_by, 0)), reverse=True)
        return stats[:limit]

    def get_top_consumers(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get tasks with highest average memory consumption."""
        return self.get_task_stats(sort_by="avg_rss_delta_kb", limit=limit)

    def get_leak_risks(self) -> list[dict[str, Any]]:
        """Get tasks flagged as potential memory leak risks."""
        return [
            s.to_dict()
            for s in self._task_stats.values()
            if s._assess_leak_risk() in ("high", "medium")
        ]

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of task profiling data."""
        total_executions = sum(
            s.execution_count for s in self._task_stats.values()
        )
        total_tasks = len(self._task_stats)
        leak_risks = self.get_leak_risks()

        return {
            "total_executions_profiled": total_executions,
            "total_task_types_tracked": total_tasks,
            "leak_risk_tasks": len(leak_risks),
            "worker_start_rss_mb": round(
                self._worker_start_rss / (1024 * 1024), 2
            ),
            "current_rss_mb": round(
                self._process.memory_info().rss / (1024 * 1024), 2
            ),
            "worker_growth_mb": round(
                (self._process.memory_info().rss - self._worker_start_rss)
                / (1024 * 1024),
                2,
            ),
            "top_5_consumers": self.get_top_consumers(limit=5),
        }

    def reset_stats(self) -> None:
        """Reset all collected statistics."""
        self._task_stats.clear()
        self._active_tasks.clear()
