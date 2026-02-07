# =============================================================================
# Stratum AI - Memory Debug API Endpoints
# =============================================================================
"""
Debug endpoints for on-demand memory analysis, snapshots, and HTML reports.

All endpoints are gated behind development/staging mode.
In production, requires superadmin authentication.

Endpoints:
    GET  /debug/memory              - Current memory overview
    GET  /debug/memory/process      - Detailed process info
    GET  /debug/memory/allocations  - Top tracemalloc allocations
    GET  /debug/memory/objects      - Object type statistics
    GET  /debug/memory/endpoints    - Per-endpoint memory stats
    GET  /debug/memory/tasks        - Per-Celery-task memory stats
    GET  /debug/memory/gc           - GC statistics
    GET  /debug/memory/timeline     - Memory timeline data
    POST /debug/memory/snapshot     - Take a new memory snapshot
    GET  /debug/memory/diff         - Diff last two snapshots
    POST /debug/memory/gc/collect   - Force garbage collection
    GET  /debug/memory/report       - Full HTML report with charts
    POST /debug/memory/reset        - Reset profiling data
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse

router = APIRouter(prefix="/debug/memory", tags=["Memory Debug"])

# These will be set during app startup
_auditor = None
_middleware = None
_celery_hooks = None


def init_debug_endpoints(
    auditor: Any,
    middleware: Any = None,
    celery_hooks: Any = None,
) -> None:
    """Initialize debug endpoints with monitoring instances."""
    global _auditor, _middleware, _celery_hooks
    _auditor = auditor
    _middleware = middleware
    _celery_hooks = celery_hooks


def _require_auditor() -> Any:
    if _auditor is None:
        raise HTTPException(
            status_code=503,
            detail="Memory auditor not initialized. Set APP_ENV=development.",
        )
    return _auditor


# -------------------------------------------------------------------------
# Overview
# -------------------------------------------------------------------------

@router.get("")
async def memory_overview() -> dict[str, Any]:
    """Get current memory overview with key metrics."""
    auditor = _require_auditor()
    process = auditor.get_process_info()
    tm = auditor.get_tracemalloc_stats()

    summary: dict[str, Any] = {
        "status": "profiling_active" if auditor.is_tracking else "tracking_off",
        "process": {
            "pid": process.pid,
            "rss_mb": process.rss_mb,
            "vms_mb": process.vms_mb,
            "memory_percent": process.percent,
            "num_threads": process.num_threads,
            "cpu_percent": process.cpu_percent,
        },
        "tracemalloc": tm,
        "snapshots_taken": len(auditor.snapshots),
        "timeline_points": len(auditor.timeline),
    }

    if _middleware:
        summary["endpoint_profiling"] = _middleware.get_summary()
    if _celery_hooks:
        summary["task_profiling"] = _celery_hooks.get_summary()

    return summary


# -------------------------------------------------------------------------
# Process Info
# -------------------------------------------------------------------------

@router.get("/process")
async def process_info() -> dict[str, Any]:
    """Get detailed process and system memory info."""
    auditor = _require_auditor()
    process = auditor.get_process_info()
    system = auditor.get_system_memory()
    children = auditor.get_child_processes()

    return {
        "process": {
            "pid": process.pid,
            "rss_mb": process.rss_mb,
            "vms_mb": process.vms_mb,
            "memory_percent": process.percent,
            "num_threads": process.num_threads,
            "num_fds": process.num_fds,
            "cpu_percent": process.cpu_percent,
            "open_files": process.open_files_count,
            "connections": process.connections_count,
        },
        "system": system,
        "child_processes": children,
    }


# -------------------------------------------------------------------------
# Allocations
# -------------------------------------------------------------------------

@router.get("/allocations")
async def top_allocations(
    limit: int = Query(default=30, le=100),
    group_by: str = Query(default="lineno", regex="^(lineno|filename|traceback)$"),
) -> dict[str, Any]:
    """Get top memory allocations from tracemalloc."""
    auditor = _require_auditor()
    allocs = auditor.get_top_allocations(limit=limit, key_type=group_by)
    files = auditor.get_top_files(limit=20)

    return {
        "group_by": group_by,
        "allocations": [
            {
                "file": a.file,
                "line": a.line,
                "size_kb": a.size_kb,
                "count": a.count,
                "code": a.code_line,
            }
            for a in allocs
        ],
        "top_files": files,
    }


# -------------------------------------------------------------------------
# Object Stats
# -------------------------------------------------------------------------

@router.get("/objects")
async def object_stats(
    limit: int = Query(default=30, le=100),
) -> dict[str, Any]:
    """Get Python object type statistics."""
    auditor = _require_auditor()
    stats = auditor.get_object_stats(limit=limit)
    cycles = auditor.detect_reference_cycles(limit=10)

    return {
        "object_types": [
            {"type": s.type_name, "count": s.count, "size_kb": s.size_kb}
            for s in stats
        ],
        "reference_cycles": cycles,
        "total_tracked_objects": sum(s.count for s in stats),
    }


# -------------------------------------------------------------------------
# Endpoint Profiling
# -------------------------------------------------------------------------

@router.get("/endpoints")
async def endpoint_memory_stats(
    sort_by: str = Query(default="avg_rss_delta_kb"),
    limit: int = Query(default=50, le=200),
) -> dict[str, Any]:
    """Get per-endpoint memory consumption stats."""
    if not _middleware:
        raise HTTPException(status_code=503, detail="Endpoint profiling middleware not active.")

    return {
        "summary": _middleware.get_summary(),
        "endpoints": _middleware.get_endpoint_stats(sort_by=sort_by, limit=limit),
        "growing_endpoints": _middleware.get_growing_endpoints(),
        "recent_requests": _middleware.get_recent_requests(limit=20),
    }


# -------------------------------------------------------------------------
# Celery Task Profiling
# -------------------------------------------------------------------------

@router.get("/tasks")
async def task_memory_stats(
    sort_by: str = Query(default="avg_rss_delta_kb"),
    limit: int = Query(default=50, le=200),
) -> dict[str, Any]:
    """Get per-Celery-task memory consumption stats."""
    if not _celery_hooks:
        raise HTTPException(status_code=503, detail="Celery memory hooks not active.")

    return {
        "summary": _celery_hooks.get_summary(),
        "tasks": _celery_hooks.get_task_stats(sort_by=sort_by, limit=limit),
        "leak_risks": _celery_hooks.get_leak_risks(),
    }


# -------------------------------------------------------------------------
# GC Stats
# -------------------------------------------------------------------------

@router.get("/gc")
async def gc_stats() -> dict[str, Any]:
    """Get garbage collector statistics."""
    auditor = _require_auditor()
    return {
        "gc_stats": auditor.get_gc_stats(),
        "reference_cycles": auditor.detect_reference_cycles(limit=10),
    }


@router.post("/gc/collect")
async def force_gc() -> dict[str, Any]:
    """Force garbage collection and return results."""
    auditor = _require_auditor()
    result = auditor.force_gc()
    auditor.record_point("gc_forced")
    return result


# -------------------------------------------------------------------------
# Timeline
# -------------------------------------------------------------------------

@router.get("/timeline")
async def memory_timeline() -> dict[str, Any]:
    """Get memory timeline data for charting."""
    auditor = _require_auditor()
    return {
        "timeline": auditor.timeline,
        "total_points": len(auditor.timeline),
    }


# -------------------------------------------------------------------------
# Snapshots & Diff
# -------------------------------------------------------------------------

@router.post("/snapshot")
async def take_snapshot(
    label: str = Query(default="", description="Optional label for the snapshot"),
) -> dict[str, Any]:
    """Take a new memory snapshot for later comparison."""
    auditor = _require_auditor()
    snapshot = auditor.take_snapshot(label=label or "api_triggered")

    return {
        "message": "Snapshot taken",
        "snapshot_index": len(auditor.snapshots) - 1,
        "timestamp": snapshot.timestamp,
        "rss_mb": snapshot.rss_mb,
        "tracemalloc_current_kb": snapshot.tracemalloc_current_kb,
        "total_snapshots": len(auditor.snapshots),
    }


@router.get("/diff")
async def snapshot_diff() -> dict[str, Any]:
    """Diff the last two memory snapshots for leak detection."""
    auditor = _require_auditor()
    diff = auditor.diff_snapshots()

    if diff is None:
        raise HTTPException(
            status_code=400,
            detail=f"Need at least 2 snapshots. Currently have {len(auditor.snapshots)}. "
                   "Use POST /debug/memory/snapshot to capture.",
        )

    return {
        "diff": {
            "timestamp_start": diff.timestamp_start,
            "timestamp_end": diff.timestamp_end,
            "duration_seconds": diff.duration_seconds,
            "rss_delta_mb": diff.rss_delta_mb,
            "tracemalloc_delta_kb": diff.tracemalloc_delta_kb,
            "new_allocations": [
                {
                    "file": a.file,
                    "line": a.line,
                    "size_kb": a.size_kb,
                    "count": a.count,
                    "code": a.code_line,
                }
                for a in diff.new_allocations
            ],
            "freed_allocations_count": len(diff.freed_allocations),
            "grown_types": diff.grown_types,
        },
        "verdict": _assess_diff(diff.rss_delta_mb, diff.duration_seconds),
    }


def _assess_diff(rss_delta_mb: float, duration_s: float) -> dict[str, Any]:
    """Provide a human-readable verdict on the snapshot diff."""
    rate_mb_per_min = (rss_delta_mb / duration_s * 60) if duration_s > 0 else 0

    if rss_delta_mb <= 0:
        severity = "ok"
        message = "Memory is stable or shrinking. No leak detected."
    elif rate_mb_per_min < 1:
        severity = "low"
        message = f"Minor growth: {rate_mb_per_min:.2f} MB/min. Likely normal allocation patterns."
    elif rate_mb_per_min < 5:
        severity = "medium"
        message = f"Moderate growth: {rate_mb_per_min:.2f} MB/min. Monitor for sustained increase."
    else:
        severity = "high"
        message = f"Rapid growth: {rate_mb_per_min:.2f} MB/min. Possible memory leak."

    return {
        "severity": severity,
        "growth_rate_mb_per_min": round(rate_mb_per_min, 3),
        "message": message,
    }


# -------------------------------------------------------------------------
# Full HTML Report
# -------------------------------------------------------------------------

@router.get("/report", response_class=HTMLResponse)
async def memory_report() -> HTMLResponse:
    """Generate and serve the full HTML memory audit report with charts."""
    auditor = _require_auditor()

    # Take a fresh snapshot for the report
    auditor.take_snapshot(label="report_generation")

    audit_data = auditor.full_audit()

    endpoint_stats = None
    if _middleware:
        endpoint_stats = _middleware.get_endpoint_stats(limit=30)

    task_stats = None
    if _celery_hooks:
        task_stats = _celery_hooks.get_task_stats(limit=20)

    from app.monitoring.visualizations import generate_html_report
    html = generate_html_report(
        audit_data=audit_data,
        endpoint_stats=endpoint_stats,
        task_stats=task_stats,
    )

    return HTMLResponse(content=html)


# -------------------------------------------------------------------------
# Full JSON Audit
# -------------------------------------------------------------------------

@router.get("/audit")
async def full_audit() -> dict[str, Any]:
    """Run a complete memory audit and return JSON data."""
    auditor = _require_auditor()
    auditor.take_snapshot(label="full_audit")
    data = auditor.full_audit()

    if _middleware:
        data["endpoint_profiling"] = {
            "summary": _middleware.get_summary(),
            "top_consumers": _middleware.get_top_consumers(limit=15),
            "growing": _middleware.get_growing_endpoints(),
        }

    if _celery_hooks:
        data["task_profiling"] = {
            "summary": _celery_hooks.get_summary(),
            "top_consumers": _celery_hooks.get_top_consumers(limit=10),
            "leak_risks": _celery_hooks.get_leak_risks(),
        }

    return data


# -------------------------------------------------------------------------
# Reset
# -------------------------------------------------------------------------

@router.post("/reset")
async def reset_profiling() -> dict[str, str]:
    """Reset all profiling data (keeps tracemalloc running)."""
    if _middleware:
        _middleware.reset_stats()
    if _celery_hooks:
        _celery_hooks.reset_stats()

    return {"message": "Profiling data reset. Tracemalloc still active."}
