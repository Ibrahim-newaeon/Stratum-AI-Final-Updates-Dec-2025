# =============================================================================
# Stratum AI - Memory Audit Core Engine
# =============================================================================
"""
Core memory auditing engine using tracemalloc, psutil, gc.

Provides:
- Process-level memory tracking (RSS, VMS, shared)
- Python allocation tracking (top files, top lines)
- Object-level analysis (type counts, growth detection)
- Snapshot diffing for leak detection
- GC statistics and reference cycle detection
"""

from __future__ import annotations

import gc
import linecache
import os
import sys
import time
import tracemalloc
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import psutil


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ProcessMemory:
    """Process-level memory information."""
    pid: int
    rss_mb: float
    vms_mb: float
    percent: float
    num_threads: int
    num_fds: int
    cpu_percent: float
    create_time: float
    open_files_count: int
    connections_count: int


@dataclass
class AllocationRecord:
    """A single memory allocation record from tracemalloc."""
    file: str
    line: int
    size_kb: float
    count: int
    code_line: str


@dataclass
class ObjectTypeStats:
    """Statistics for a Python object type."""
    type_name: str
    count: int
    size_kb: float


@dataclass
class SnapshotDiff:
    """Difference between two memory snapshots."""
    timestamp_start: str
    timestamp_end: str
    duration_seconds: float
    rss_delta_mb: float
    tracemalloc_delta_kb: float
    new_allocations: list[AllocationRecord]
    freed_allocations: list[AllocationRecord]
    grown_types: list[dict[str, Any]]


@dataclass
class MemorySnapshot:
    """A point-in-time memory snapshot."""
    timestamp: str
    rss_mb: float
    vms_mb: float
    tracemalloc_current_kb: float
    tracemalloc_peak_kb: float
    top_allocations: list[AllocationRecord]
    object_counts: dict[str, int]
    gc_stats: list[dict[str, Any]]
    _raw_snapshot: Optional[Any] = field(default=None, repr=False)


# =============================================================================
# Memory Auditor
# =============================================================================

class MemoryAuditor:
    """
    Core memory auditing engine for Stratum AI.

    Usage:
        auditor = MemoryAuditor()
        auditor.start_tracking()

        # ... application runs ...

        snapshot = auditor.take_snapshot()
        report_data = auditor.full_audit()
    """

    def __init__(self, nframe: int = 10) -> None:
        self._nframe = nframe
        self._tracking = False
        self._snapshots: list[MemorySnapshot] = []
        self._timeline: list[dict[str, Any]] = []
        self._start_time: Optional[float] = None
        self._process = psutil.Process(os.getpid())

    # -------------------------------------------------------------------------
    # Lifecycle
    # -------------------------------------------------------------------------

    def start_tracking(self) -> None:
        """Start tracemalloc and begin collecting memory data."""
        if not self._tracking:
            tracemalloc.start(self._nframe)
            self._tracking = True
            self._start_time = time.monotonic()
            self._record_timeline_point("tracking_started")

    def stop_tracking(self) -> None:
        """Stop tracemalloc tracking."""
        if self._tracking:
            tracemalloc.stop()
            self._tracking = False

    @property
    def is_tracking(self) -> bool:
        return self._tracking

    # -------------------------------------------------------------------------
    # Process-Level Metrics (psutil)
    # -------------------------------------------------------------------------

    def get_process_info(self) -> ProcessMemory:
        """Get current process memory info via psutil."""
        mem = self._process.memory_info()
        try:
            num_fds = self._process.num_fds()
        except AttributeError:
            # Windows doesn't have num_fds
            num_fds = len(self._process.open_files())

        return ProcessMemory(
            pid=self._process.pid,
            rss_mb=round(mem.rss / (1024 * 1024), 2),
            vms_mb=round(mem.vms / (1024 * 1024), 2),
            percent=round(self._process.memory_percent(), 2),
            num_threads=self._process.num_threads(),
            num_fds=num_fds,
            cpu_percent=self._process.cpu_percent(interval=0.1),
            create_time=self._process.create_time(),
            open_files_count=len(self._process.open_files()),
            connections_count=len(self._process.net_connections()),
        )

    def get_system_memory(self) -> dict[str, Any]:
        """Get system-wide memory information."""
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return {
            "total_mb": round(vm.total / (1024 * 1024), 2),
            "available_mb": round(vm.available / (1024 * 1024), 2),
            "used_mb": round(vm.used / (1024 * 1024), 2),
            "percent": vm.percent,
            "swap_total_mb": round(swap.total / (1024 * 1024), 2),
            "swap_used_mb": round(swap.used / (1024 * 1024), 2),
            "swap_percent": swap.percent,
        }

    def get_child_processes(self) -> list[dict[str, Any]]:
        """Get memory info for child processes (Celery workers, etc.)."""
        children = []
        for child in self._process.children(recursive=True):
            try:
                mem = child.memory_info()
                children.append({
                    "pid": child.pid,
                    "name": child.name(),
                    "status": child.status(),
                    "rss_mb": round(mem.rss / (1024 * 1024), 2),
                    "vms_mb": round(mem.vms / (1024 * 1024), 2),
                    "cpu_percent": child.cpu_percent(interval=0.1),
                    "num_threads": child.num_threads(),
                    "cmdline": " ".join(child.cmdline()[:3]),
                })
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return children

    # -------------------------------------------------------------------------
    # Allocation Tracking (tracemalloc)
    # -------------------------------------------------------------------------

    def get_top_allocations(
        self, limit: int = 30, key_type: str = "lineno"
    ) -> list[AllocationRecord]:
        """Get top memory allocations by file/line."""
        if not self._tracking:
            return []

        snapshot = tracemalloc.take_snapshot()
        # Filter out importlib and tracemalloc internals
        snapshot = snapshot.filter_traces([
            tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
            tracemalloc.Filter(False, "<frozen importlib._bootstrap_external>"),
            tracemalloc.Filter(False, tracemalloc.__file__),
            tracemalloc.Filter(False, "<unknown>"),
        ])

        stats = snapshot.statistics(key_type)
        records = []

        for stat in stats[:limit]:
            frame = stat.traceback[0]
            code_line = linecache.getline(frame.filename, frame.lineno).strip()
            records.append(AllocationRecord(
                file=frame.filename,
                line=frame.lineno,
                size_kb=round(stat.size / 1024, 2),
                count=stat.count,
                code_line=code_line,
            ))

        return records

    def get_top_files(self, limit: int = 20) -> list[dict[str, Any]]:
        """Get top memory-consuming files (grouped by filename)."""
        if not self._tracking:
            return []

        snapshot = tracemalloc.take_snapshot()
        snapshot = snapshot.filter_traces([
            tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
            tracemalloc.Filter(False, "<frozen importlib._bootstrap_external>"),
            tracemalloc.Filter(False, "<unknown>"),
        ])

        stats = snapshot.statistics("filename")
        return [
            {
                "file": stat.traceback[0].filename,
                "size_kb": round(stat.size / 1024, 2),
                "count": stat.count,
            }
            for stat in stats[:limit]
        ]

    def get_tracemalloc_stats(self) -> dict[str, Any]:
        """Get current tracemalloc usage statistics."""
        if not self._tracking:
            return {"tracking": False}

        current, peak = tracemalloc.get_traced_memory()
        return {
            "tracking": True,
            "current_kb": round(current / 1024, 2),
            "peak_kb": round(peak / 1024, 2),
            "current_mb": round(current / (1024 * 1024), 2),
            "peak_mb": round(peak / (1024 * 1024), 2),
        }

    # -------------------------------------------------------------------------
    # Object-Level Analysis (gc + inspection)
    # -------------------------------------------------------------------------

    def get_object_stats(self, limit: int = 30, max_objects: int = 200_000) -> list[ObjectTypeStats]:
        """Get object counts by type, sorted by count.

        Uses a capped iteration to avoid stalling on huge heaps.
        Counts are always complete; sizes are estimated from sampled objects.
        """
        type_counts: dict[str, int] = defaultdict(int)
        type_sizes: dict[str, int] = defaultdict(int)
        size_samples: dict[str, int] = defaultdict(int)

        for i, obj in enumerate(gc.get_objects()):
            type_name = type(obj).__name__
            type_counts[type_name] += 1
            # Sample sizes for the first N objects per type (avoid full scan)
            if size_samples[type_name] < 50:
                try:
                    type_sizes[type_name] += sys.getsizeof(obj)
                    size_samples[type_name] += 1
                except (TypeError, ReferenceError):
                    pass
            if i >= max_objects:
                break

        sorted_types = sorted(
            type_counts.items(), key=lambda x: x[1], reverse=True
        )

        results = []
        for name, count in sorted_types[:limit]:
            # Extrapolate size from samples
            sampled = size_samples.get(name, 0)
            raw_size = type_sizes.get(name, 0)
            estimated_size = (raw_size / sampled * count) if sampled > 0 else 0
            results.append(ObjectTypeStats(
                type_name=name,
                count=count,
                size_kb=round(estimated_size / 1024, 2),
            ))

        return results

    def get_gc_stats(self) -> list[dict[str, Any]]:
        """Get garbage collector generation statistics."""
        stats = []
        for i, gen_stat in enumerate(gc.get_stats()):
            stats.append({
                "generation": i,
                "collections": gen_stat.get("collections", 0),
                "collected": gen_stat.get("collected", 0),
                "uncollectable": gen_stat.get("uncollectable", 0),
            })

        thresholds = gc.get_threshold()
        for i, threshold in enumerate(thresholds):
            if i < len(stats):
                stats[i]["threshold"] = threshold

        counts = gc.get_count()
        for i, count in enumerate(counts):
            if i < len(stats):
                stats[i]["current_count"] = count

        return stats

    def detect_reference_cycles(self, limit: int = 10) -> list[dict[str, Any]]:
        """Detect reference cycles that might prevent garbage collection."""
        gc.collect()
        garbage = gc.garbage[:limit]
        cycles = []
        for obj in garbage:
            cycles.append({
                "type": type(obj).__name__,
                "size_bytes": sys.getsizeof(obj),
                "referrers_count": len(gc.get_referrers(obj)),
                "repr": repr(obj)[:200],
            })
        return cycles

    def force_gc(self) -> dict[str, Any]:
        """Force garbage collection and return stats."""
        before_counts = gc.get_count()
        process_mem_before = self._process.memory_info().rss

        collected_gen0 = gc.collect(0)
        collected_gen1 = gc.collect(1)
        collected_gen2 = gc.collect(2)

        after_counts = gc.get_count()
        process_mem_after = self._process.memory_info().rss

        return {
            "collected": {
                "gen0": collected_gen0,
                "gen1": collected_gen1,
                "gen2": collected_gen2,
                "total": collected_gen0 + collected_gen1 + collected_gen2,
            },
            "counts_before": list(before_counts),
            "counts_after": list(after_counts),
            "rss_freed_kb": round(
                (process_mem_before - process_mem_after) / 1024, 2
            ),
            "garbage_remaining": len(gc.garbage),
        }

    # -------------------------------------------------------------------------
    # Snapshot & Diff (Leak Detection)
    # -------------------------------------------------------------------------

    def take_snapshot(self, label: str = "") -> MemorySnapshot:
        """Take a full memory snapshot for later comparison.

        Uses a single tracemalloc.take_snapshot() call to avoid
        repeated expensive snapshot operations.
        """
        process_info = self.get_process_info()
        tm_stats = self.get_tracemalloc_stats()

        # Take ONE raw tracemalloc snapshot (expensive — do it once)
        raw_snapshot = None
        top_allocs: list[AllocationRecord] = []
        if self._tracking:
            raw_snapshot = tracemalloc.take_snapshot()
            filtered = raw_snapshot.filter_traces([
                tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
                tracemalloc.Filter(False, "<frozen importlib._bootstrap_external>"),
                tracemalloc.Filter(False, "<unknown>"),
            ])
            for stat in filtered.statistics("lineno")[:20]:
                frame = stat.traceback[0]
                code_line = linecache.getline(frame.filename, frame.lineno).strip()
                top_allocs.append(AllocationRecord(
                    file=frame.filename, line=frame.lineno,
                    size_kb=round(stat.size / 1024, 2), count=stat.count,
                    code_line=code_line,
                ))

        # Object counts (lightweight — capped scan)
        type_counts: dict[str, int] = defaultdict(int)
        for i, obj in enumerate(gc.get_objects()):
            type_counts[type(obj).__name__] += 1
            if i >= 200_000:
                break

        snapshot = MemorySnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            rss_mb=process_info.rss_mb,
            vms_mb=process_info.vms_mb,
            tracemalloc_current_kb=tm_stats.get("current_kb", 0),
            tracemalloc_peak_kb=tm_stats.get("peak_kb", 0),
            top_allocations=top_allocs,
            object_counts=dict(
                sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:30]
            ),
            gc_stats=self.get_gc_stats(),
            _raw_snapshot=raw_snapshot,
        )

        self._snapshots.append(snapshot)
        self._record_timeline_point(label or f"snapshot_{len(self._snapshots)}")

        return snapshot

    def diff_snapshots(
        self,
        idx_start: int = -2,
        idx_end: int = -1,
    ) -> Optional[SnapshotDiff]:
        """Compare two snapshots to detect memory growth (leaks)."""
        if len(self._snapshots) < 2:
            return None

        start = self._snapshots[idx_start]
        end = self._snapshots[idx_end]

        # Tracemalloc diff
        new_allocs: list[AllocationRecord] = []
        freed_allocs: list[AllocationRecord] = []

        if start._raw_snapshot and end._raw_snapshot:
            filtered_end = end._raw_snapshot.filter_traces([
                tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
                tracemalloc.Filter(False, "<frozen importlib._bootstrap_external>"),
                tracemalloc.Filter(False, "<unknown>"),
            ])
            stats = filtered_end.compare_to(start._raw_snapshot, "lineno")

            for stat in stats[:20]:
                if stat.size_diff > 0:
                    frame = stat.traceback[0]
                    code_line = linecache.getline(
                        frame.filename, frame.lineno
                    ).strip()
                    new_allocs.append(AllocationRecord(
                        file=frame.filename,
                        line=frame.lineno,
                        size_kb=round(stat.size_diff / 1024, 2),
                        count=stat.count_diff,
                        code_line=code_line,
                    ))
                elif stat.size_diff < 0:
                    frame = stat.traceback[0]
                    freed_allocs.append(AllocationRecord(
                        file=frame.filename,
                        line=frame.lineno,
                        size_kb=round(abs(stat.size_diff) / 1024, 2),
                        count=abs(stat.count_diff),
                        code_line="",
                    ))

        # Object type growth
        grown_types = []
        for type_name, end_count in end.object_counts.items():
            start_count = start.object_counts.get(type_name, 0)
            delta = end_count - start_count
            if delta > 0:
                grown_types.append({
                    "type": type_name,
                    "start_count": start_count,
                    "end_count": end_count,
                    "delta": delta,
                    "growth_pct": round(
                        (delta / start_count * 100) if start_count > 0 else 100, 1
                    ),
                })

        grown_types.sort(key=lambda x: x["delta"], reverse=True)

        return SnapshotDiff(
            timestamp_start=start.timestamp,
            timestamp_end=end.timestamp,
            duration_seconds=round(
                (
                    datetime.fromisoformat(end.timestamp)
                    - datetime.fromisoformat(start.timestamp)
                ).total_seconds(),
                2,
            ),
            rss_delta_mb=round(end.rss_mb - start.rss_mb, 2),
            tracemalloc_delta_kb=round(
                end.tracemalloc_current_kb - start.tracemalloc_current_kb, 2
            ),
            new_allocations=new_allocs[:15],
            freed_allocations=freed_allocs[:10],
            grown_types=grown_types[:15],
        )

    # -------------------------------------------------------------------------
    # Timeline Recording
    # -------------------------------------------------------------------------

    def _record_timeline_point(self, label: str) -> None:
        """Record a point on the memory timeline."""
        mem = self._process.memory_info()
        tm_current = 0
        if self._tracking:
            tm_current, _ = tracemalloc.get_traced_memory()

        elapsed = 0.0
        if self._start_time:
            elapsed = round(time.monotonic() - self._start_time, 2)

        self._timeline.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": elapsed,
            "label": label,
            "rss_mb": round(mem.rss / (1024 * 1024), 2),
            "vms_mb": round(mem.vms / (1024 * 1024), 2),
            "tracemalloc_kb": round(tm_current / 1024, 2),
            "gc_count": sum(gc.get_count()),
        })

    def record_point(self, label: str = "manual") -> None:
        """Manually record a timeline data point."""
        self._record_timeline_point(label)

    @property
    def timeline(self) -> list[dict[str, Any]]:
        return self._timeline

    @property
    def snapshots(self) -> list[MemorySnapshot]:
        return self._snapshots

    # -------------------------------------------------------------------------
    # Full Audit
    # -------------------------------------------------------------------------

    def full_audit(self) -> dict[str, Any]:
        """Run a complete memory audit and return all data."""
        self._record_timeline_point("full_audit")

        process_info = self.get_process_info()
        system_memory = self.get_system_memory()
        children = self.get_child_processes()

        # Take ONE tracemalloc snapshot and reuse it for all analysis
        tm_snapshot = None
        top_allocations: list[AllocationRecord] = []
        top_files: list[dict[str, Any]] = []
        if self._tracking:
            tm_snapshot = tracemalloc.take_snapshot()
            tm_snapshot = tm_snapshot.filter_traces([
                tracemalloc.Filter(False, "<frozen importlib._bootstrap>"),
                tracemalloc.Filter(False, "<frozen importlib._bootstrap_external>"),
                tracemalloc.Filter(False, "<unknown>"),
            ])
            # Top allocations by line
            for stat in tm_snapshot.statistics("lineno")[:30]:
                frame = stat.traceback[0]
                code_line = linecache.getline(frame.filename, frame.lineno).strip()
                top_allocations.append(AllocationRecord(
                    file=frame.filename, line=frame.lineno,
                    size_kb=round(stat.size / 1024, 2), count=stat.count,
                    code_line=code_line,
                ))
            # Top files
            for stat in tm_snapshot.statistics("filename")[:20]:
                top_files.append({
                    "file": stat.traceback[0].filename,
                    "size_kb": round(stat.size / 1024, 2),
                    "count": stat.count,
                })

        object_stats = self.get_object_stats(limit=30)
        gc_stats = self.get_gc_stats()
        tracemalloc_stats = self.get_tracemalloc_stats()
        ref_cycles = self.detect_reference_cycles(limit=10)

        # Snapshot diff if available
        diff = None
        if len(self._snapshots) >= 2:
            diff = self.diff_snapshots()

        return {
            "audit_timestamp": datetime.now(timezone.utc).isoformat(),
            "python_version": sys.version,
            "platform": sys.platform,
            "process": {
                "pid": process_info.pid,
                "rss_mb": process_info.rss_mb,
                "vms_mb": process_info.vms_mb,
                "memory_percent": process_info.percent,
                "num_threads": process_info.num_threads,
                "num_fds": process_info.num_fds,
                "cpu_percent": process_info.cpu_percent,
                "open_files": process_info.open_files_count,
                "connections": process_info.connections_count,
            },
            "system_memory": system_memory,
            "child_processes": children,
            "tracemalloc": tracemalloc_stats,
            "top_allocations": [
                {
                    "file": a.file,
                    "line": a.line,
                    "size_kb": a.size_kb,
                    "count": a.count,
                    "code": a.code_line,
                }
                for a in top_allocations
            ],
            "top_files": top_files,
            "object_stats": [
                {
                    "type": o.type_name,
                    "count": o.count,
                    "size_kb": o.size_kb,
                }
                for o in object_stats
            ],
            "gc_stats": gc_stats,
            "reference_cycles": ref_cycles,
            "snapshot_diff": {
                "rss_delta_mb": diff.rss_delta_mb,
                "tracemalloc_delta_kb": diff.tracemalloc_delta_kb,
                "duration_seconds": diff.duration_seconds,
                "new_allocations": len(diff.new_allocations),
                "grown_types_count": len(diff.grown_types),
                "top_grown_types": diff.grown_types[:5],
            } if diff else None,
            "timeline": self._timeline,
            "snapshots_count": len(self._snapshots),
        }
