# =============================================================================
# Stratum AI - Memory Audit Visualization & Report Generator
# =============================================================================
"""
Generates interactive HTML reports with embedded matplotlib charts.

Charts included:
1. Memory Timeline (RSS over time) - area chart
2. Top Allocations by File - horizontal bar chart
3. Top Allocations by Line - horizontal bar chart
4. Object Type Distribution - pie + bar chart
5. Per-Endpoint Memory Usage - horizontal bar chart
6. Per-Celery-Task Memory Usage - horizontal bar chart
7. Leak Detection / Snapshot Diff - comparison chart
8. GC Generation Stats - grouped bar chart
9. System vs Process Memory - gauge/donut chart

All charts rendered as base64 PNG images embedded in HTML.
"""

from __future__ import annotations

import base64
import io
from datetime import UTC, datetime
from typing import Any, Optional

import matplotlib

matplotlib.use("Agg")  # Non-interactive backend for server
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import numpy as np

# =============================================================================
# Color Palette (matches Stratum AI brand)
# =============================================================================

COLORS = {
    "primary": "#6366F1",      # Indigo
    "secondary": "#8B5CF6",    # Violet
    "success": "#10B981",      # Emerald
    "warning": "#F59E0B",      # Amber
    "danger": "#EF4444",       # Red
    "info": "#3B82F6",         # Blue
    "muted": "#6B7280",        # Gray
    "bg_dark": "#111827",      # Dark background
    "bg_card": "#1F2937",      # Card background
    "text": "#F9FAFB",         # Light text
    "text_muted": "#9CA3AF",   # Muted text
    "grid": "#374151",         # Grid lines
    "border": "#4B5563",       # Borders
}

CHART_PALETTE = [
    "#6366F1", "#8B5CF6", "#EC4899", "#F43F5E", "#F59E0B",
    "#10B981", "#3B82F6", "#14B8A6", "#F97316", "#A855F7",
    "#06B6D4", "#84CC16", "#E11D48", "#7C3AED", "#0EA5E9",
]


def _fig_to_base64(fig: plt.Figure) -> str:
    """Convert a matplotlib figure to a base64-encoded PNG string."""
    buf = io.BytesIO()
    fig.savefig(
        buf,
        format="png",
        dpi=150,
        bbox_inches="tight",
        facecolor=COLORS["bg_card"],
        edgecolor="none",
        transparent=False,
    )
    plt.close(fig)
    buf.seek(0)
    return base64.b64encode(buf.read()).decode("utf-8")


def _setup_chart_style(ax: plt.Axes, title: str) -> None:
    """Apply consistent dark theme styling to chart axes."""
    ax.set_facecolor(COLORS["bg_card"])
    ax.set_title(title, color=COLORS["text"], fontsize=14, fontweight="bold", pad=12)
    ax.tick_params(colors=COLORS["text_muted"], labelsize=9)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["bottom"].set_color(COLORS["grid"])
    ax.spines["left"].set_color(COLORS["grid"])
    ax.grid(axis="y", color=COLORS["grid"], alpha=0.3, linestyle="--")


# =============================================================================
# Chart Generators
# =============================================================================

def chart_memory_timeline(timeline: list[dict[str, Any]]) -> str:
    """Generate RSS memory timeline area chart."""
    if not timeline:
        return ""

    fig, ax = plt.subplots(figsize=(12, 4))
    _setup_chart_style(ax, "Memory Timeline (RSS)")

    elapsed = [p["elapsed_seconds"] for p in timeline]
    rss = [p["rss_mb"] for p in timeline]
    vms = [p.get("vms_mb", 0) for p in timeline]

    ax.fill_between(elapsed, rss, alpha=0.3, color=COLORS["primary"])
    ax.plot(elapsed, rss, color=COLORS["primary"], linewidth=2, label="RSS (MB)")
    ax.plot(elapsed, vms, color=COLORS["secondary"], linewidth=1.5, alpha=0.6, label="VMS (MB)", linestyle="--")

    # Mark labeled points
    for p in timeline:
        if p["label"] not in ("manual", "request"):
            ax.axvline(x=p["elapsed_seconds"], color=COLORS["warning"], alpha=0.3, linestyle=":")

    ax.set_xlabel("Elapsed Time (seconds)", color=COLORS["text_muted"], fontsize=10)
    ax.set_ylabel("Memory (MB)", color=COLORS["text_muted"], fontsize=10)
    ax.legend(facecolor=COLORS["bg_dark"], edgecolor=COLORS["border"], labelcolor=COLORS["text"], fontsize=9)

    return _fig_to_base64(fig)


def chart_top_allocations(allocations: list[dict[str, Any]], title: str = "Top Memory Allocations (by line)") -> str:
    """Generate horizontal bar chart of top memory-consuming allocations."""
    if not allocations:
        return ""

    data = allocations[:15]
    fig, ax = plt.subplots(figsize=(12, max(4, len(data) * 0.4)))
    _setup_chart_style(ax, title)

    labels = []
    for a in data:
        filename = a["file"].split("/")[-1] if "/" in a["file"] else a["file"].split("\\")[-1]
        labels.append(f"{filename}:{a['line']}")

    sizes = [a["size_kb"] for a in data]
    y_pos = np.arange(len(labels))

    bars = ax.barh(y_pos, sizes, color=CHART_PALETTE[:len(data)], height=0.6, edgecolor="none")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("Size (KB)", color=COLORS["text_muted"], fontsize=10)
    ax.invert_yaxis()

    # Value labels on bars
    for bar, size in zip(bars, sizes, strict=False):
        ax.text(
            bar.get_width() + max(sizes) * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{size:,.1f} KB",
            va="center", color=COLORS["text_muted"], fontsize=8,
        )

    return _fig_to_base64(fig)


def chart_top_files(files: list[dict[str, Any]]) -> str:
    """Generate horizontal bar chart of top memory-consuming files."""
    if not files:
        return ""

    data = files[:15]
    fig, ax = plt.subplots(figsize=(12, max(4, len(data) * 0.4)))
    _setup_chart_style(ax, "Top Memory-Consuming Files")

    labels = []
    for f in data:
        path = f["file"]
        short = path.split("/")[-1] if "/" in path else path.split("\\")[-1]
        labels.append(short)

    sizes = [f["size_kb"] for f in data]
    y_pos = np.arange(len(labels))

    colors = []
    for size in sizes:
        if size > 1000:
            colors.append(COLORS["danger"])
        elif size > 500:
            colors.append(COLORS["warning"])
        else:
            colors.append(COLORS["primary"])

    bars = ax.barh(y_pos, sizes, color=colors, height=0.6, edgecolor="none")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("Size (KB)", color=COLORS["text_muted"], fontsize=10)
    ax.invert_yaxis()

    for bar, size in zip(bars, sizes, strict=False):
        ax.text(
            bar.get_width() + max(sizes) * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{size:,.1f} KB",
            va="center", color=COLORS["text_muted"], fontsize=8,
        )

    return _fig_to_base64(fig)


def chart_object_distribution(object_stats: list[dict[str, Any]]) -> str:
    """Generate pie chart + bar chart of Python object type distribution."""
    if not object_stats:
        return ""

    # Take top 10 for pie, rest as "Other"
    top = object_stats[:10]
    other_count = sum(o["count"] for o in object_stats[10:])

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    fig.patch.set_facecolor(COLORS["bg_card"])

    # Pie chart (left)
    _setup_chart_style(ax1, "Object Type Distribution (count)")
    labels = [o["type"] for o in top]
    values = [o["count"] for o in top]
    if other_count > 0:
        labels.append("Other")
        values.append(other_count)

    colors = CHART_PALETTE[:len(labels)]
    wedges, texts, autotexts = ax1.pie(
        values,
        labels=None,
        autopct="%1.1f%%",
        colors=colors,
        startangle=140,
        pctdistance=0.8,
        textprops={"color": COLORS["text"], "fontsize": 8},
    )
    ax1.legend(
        wedges, labels,
        loc="center left", bbox_to_anchor=(1.0, 0.5),
        facecolor=COLORS["bg_dark"], edgecolor=COLORS["border"],
        labelcolor=COLORS["text"], fontsize=8,
    )

    # Bar chart (right) - top types by size
    _setup_chart_style(ax2, "Top Object Types by Size (KB)")
    size_sorted = sorted(object_stats[:15], key=lambda x: x.get("size_kb", 0), reverse=True)
    bar_labels = [o["type"] for o in size_sorted[:10]]
    bar_sizes = [o.get("size_kb", 0) for o in size_sorted[:10]]
    y_pos = np.arange(len(bar_labels))

    ax2.barh(y_pos, bar_sizes, color=COLORS["info"], height=0.6, edgecolor="none")
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(bar_labels, fontsize=8)
    ax2.set_xlabel("Size (KB)", color=COLORS["text_muted"], fontsize=10)
    ax2.invert_yaxis()

    plt.tight_layout()
    return _fig_to_base64(fig)


def chart_endpoint_memory(endpoint_stats: list[dict[str, Any]]) -> str:
    """Generate horizontal bar chart of per-endpoint memory consumption."""
    if not endpoint_stats:
        return ""

    data = endpoint_stats[:20]
    fig, ax = plt.subplots(figsize=(12, max(4, len(data) * 0.35)))
    _setup_chart_style(ax, "Per-Endpoint Memory Consumption (avg RSS delta)")

    labels = [f"{d['method']} {d['path']}" for d in data]
    # Truncate long labels
    labels = [lbl[:60] + "..." if len(lbl) > 60 else lbl for lbl in labels]
    values = [d["avg_rss_delta_kb"] for d in data]
    counts = [d["call_count"] for d in data]
    y_pos = np.arange(len(labels))

    colors = []
    for v in values:
        if v > 500:
            colors.append(COLORS["danger"])
        elif v > 100:
            colors.append(COLORS["warning"])
        elif v > 0:
            colors.append(COLORS["primary"])
        else:
            colors.append(COLORS["success"])

    bars = ax.barh(y_pos, values, color=colors, height=0.6, edgecolor="none")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=7, fontfamily="monospace")
    ax.set_xlabel("Avg RSS Delta (KB)", color=COLORS["text_muted"], fontsize=10)
    ax.invert_yaxis()
    ax.axvline(x=0, color=COLORS["grid"], linewidth=0.8)

    for bar, val, count in zip(bars, values, counts, strict=False):
        ax.text(
            bar.get_width() + abs(max(values)) * 0.02 if val >= 0 else bar.get_width() - abs(max(values)) * 0.02,
            bar.get_y() + bar.get_height() / 2,
            f"{val:+,.1f} KB ({count} calls)",
            va="center", ha="left" if val >= 0 else "right",
            color=COLORS["text_muted"], fontsize=7,
        )

    return _fig_to_base64(fig)


def chart_task_memory(task_stats: list[dict[str, Any]]) -> str:
    """Generate horizontal bar chart of per-Celery-task memory consumption."""
    if not task_stats:
        return ""

    data = task_stats[:15]
    fig, ax = plt.subplots(figsize=(12, max(4, len(data) * 0.4)))
    _setup_chart_style(ax, "Per-Celery-Task Memory Consumption")

    labels = [d.get("short_name", d["task_name"].split(".")[-1]) for d in data]
    avg_values = [d["avg_rss_delta_kb"] for d in data]
    max_values = [d["max_rss_delta_kb"] for d in data]
    y_pos = np.arange(len(labels))
    bar_height = 0.35

    bars_max = ax.barh(
        y_pos - bar_height / 2, max_values, bar_height,
        color=COLORS["danger"], alpha=0.5, label="Peak", edgecolor="none",
    )
    bars_avg = ax.barh(
        y_pos + bar_height / 2, avg_values, bar_height,
        color=COLORS["primary"], label="Average", edgecolor="none",
    )

    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("RSS Delta (KB)", color=COLORS["text_muted"], fontsize=10)
    ax.invert_yaxis()
    ax.legend(facecolor=COLORS["bg_dark"], edgecolor=COLORS["border"], labelcolor=COLORS["text"], fontsize=9)

    # Leak risk badges
    for i, d in enumerate(data):
        risk = d.get("leak_risk", "unknown")
        risk_color = {
            "high": COLORS["danger"],
            "medium": COLORS["warning"],
            "low": COLORS["info"],
        }.get(risk, COLORS["muted"])

        if risk in ("high", "medium"):
            ax.text(
                max(max_values) * 1.05,
                i,
                f" {risk.upper()} RISK",
                va="center", color=risk_color, fontsize=7, fontweight="bold",
            )

    return _fig_to_base64(fig)


def chart_gc_stats(gc_stats: list[dict[str, Any]]) -> str:
    """Generate grouped bar chart of GC generation statistics."""
    if not gc_stats:
        return ""

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    fig.patch.set_facecolor(COLORS["bg_card"])

    gens = [f"Gen {s['generation']}" for s in gc_stats]
    x = np.arange(len(gens))
    width = 0.25

    # Left: Collections and Collected
    _setup_chart_style(ax1, "GC Collections & Objects Collected")
    collections = [s.get("collections", 0) for s in gc_stats]
    collected = [s.get("collected", 0) for s in gc_stats]
    uncollectable = [s.get("uncollectable", 0) for s in gc_stats]

    ax1.bar(x - width, collections, width, color=COLORS["primary"], label="Collections")
    ax1.bar(x, collected, width, color=COLORS["success"], label="Collected")
    ax1.bar(x + width, uncollectable, width, color=COLORS["danger"], label="Uncollectable")
    ax1.set_xticks(x)
    ax1.set_xticklabels(gens, color=COLORS["text_muted"])
    ax1.legend(facecolor=COLORS["bg_dark"], edgecolor=COLORS["border"], labelcolor=COLORS["text"], fontsize=8)
    ax1.yaxis.set_major_formatter(ticker.EngFormatter())

    # Right: Thresholds vs Current Counts
    _setup_chart_style(ax2, "GC Thresholds vs Current Counts")
    thresholds = [s.get("threshold", 0) for s in gc_stats]
    current = [s.get("current_count", 0) for s in gc_stats]

    ax2.bar(x - width / 2, thresholds, width, color=COLORS["warning"], label="Threshold")
    ax2.bar(x + width / 2, current, width, color=COLORS["info"], label="Current Count")
    ax2.set_xticks(x)
    ax2.set_xticklabels(gens, color=COLORS["text_muted"])
    ax2.legend(facecolor=COLORS["bg_dark"], edgecolor=COLORS["border"], labelcolor=COLORS["text"], fontsize=8)

    plt.tight_layout()
    return _fig_to_base64(fig)


def chart_snapshot_diff(diff_data: Optional[dict[str, Any]]) -> str:
    """Generate visualization of snapshot diff (leak detection)."""
    if not diff_data:
        return ""

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))
    fig.patch.set_facecolor(COLORS["bg_card"])

    # Left: RSS and tracemalloc delta gauge
    _setup_chart_style(ax1, "Memory Delta Between Snapshots")
    metrics = ["RSS", "Tracemalloc"]
    values = [diff_data["rss_delta_mb"], diff_data["tracemalloc_delta_kb"] / 1024]
    colors = [
        COLORS["danger"] if v > 0 else COLORS["success"] for v in values
    ]

    bars = ax1.barh(metrics, values, color=colors, height=0.5, edgecolor="none")
    ax1.set_xlabel("Delta (MB)", color=COLORS["text_muted"], fontsize=10)
    ax1.axvline(x=0, color=COLORS["text_muted"], linewidth=0.8)

    for bar, val in zip(bars, values, strict=False):
        ax1.text(
            bar.get_width() + 0.1 if val >= 0 else bar.get_width() - 0.1,
            bar.get_y() + bar.get_height() / 2,
            f"{val:+.2f} MB",
            va="center", ha="left" if val >= 0 else "right",
            color=COLORS["text"], fontsize=10, fontweight="bold",
        )

    # Right: Top grown types
    _setup_chart_style(ax2, "Top Growing Object Types")
    grown = diff_data.get("top_grown_types", [])[:8]
    if grown:
        type_names = [g["type"] for g in grown]
        deltas = [g["delta"] for g in grown]
        y_pos = np.arange(len(type_names))

        ax2.barh(y_pos, deltas, color=COLORS["warning"], height=0.5, edgecolor="none")
        ax2.set_yticks(y_pos)
        ax2.set_yticklabels(type_names, fontsize=8)
        ax2.set_xlabel("Count Increase", color=COLORS["text_muted"], fontsize=10)
        ax2.invert_yaxis()

        for i, (bar_val, g) in enumerate(zip(deltas, grown, strict=False)):
            pct = g.get("growth_pct", 0)
            ax2.text(
                bar_val + max(deltas) * 0.02,
                i,
                f"+{bar_val:,} ({pct:+.1f}%)",
                va="center", color=COLORS["text_muted"], fontsize=8,
            )
    else:
        ax2.text(0.5, 0.5, "No growth detected", transform=ax2.transAxes,
                 ha="center", va="center", color=COLORS["success"], fontsize=12)

    plt.tight_layout()
    return _fig_to_base64(fig)


def chart_system_memory(system_mem: dict[str, Any], process_mem: dict[str, Any]) -> str:
    """Generate system vs process memory donut chart."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
    fig.patch.set_facecolor(COLORS["bg_card"])

    # System memory donut
    _setup_chart_style(ax1, "System Memory")
    used = system_mem.get("used_mb", 0)
    available = system_mem.get("available_mb", 0)
    ax1.pie(
        [used, available],
        labels=None,
        colors=[COLORS["primary"], COLORS["grid"]],
        startangle=90,
        wedgeprops={"width": 0.4, "edgecolor": COLORS["bg_card"]},
    )
    ax1.text(0, 0, f"{system_mem.get('percent', 0)}%",
             ha="center", va="center", color=COLORS["text"],
             fontsize=18, fontweight="bold")
    ax1.legend(
        [f"Used: {used:,.0f} MB", f"Free: {available:,.0f} MB"],
        loc="lower center",
        facecolor=COLORS["bg_dark"], edgecolor=COLORS["border"],
        labelcolor=COLORS["text"], fontsize=8,
    )

    # Process memory donut
    _setup_chart_style(ax2, "Process Memory (RSS)")
    rss = process_mem.get("rss_mb", 0)
    total = system_mem.get("total_mb", 1)
    rest = total - rss

    ax2.pie(
        [rss, rest],
        labels=None,
        colors=[COLORS["secondary"], COLORS["grid"]],
        startangle=90,
        wedgeprops={"width": 0.4, "edgecolor": COLORS["bg_card"]},
    )
    ax2.text(0, 0, f"{rss:,.0f}\nMB",
             ha="center", va="center", color=COLORS["text"],
             fontsize=16, fontweight="bold")
    pct = process_mem.get("memory_percent", 0)
    ax2.legend(
        [f"Process: {rss:,.0f} MB ({pct}%)", f"System rest: {rest:,.0f} MB"],
        loc="lower center",
        facecolor=COLORS["bg_dark"], edgecolor=COLORS["border"],
        labelcolor=COLORS["text"], fontsize=8,
    )

    plt.tight_layout()
    return _fig_to_base64(fig)


def chart_child_processes(children: list[dict[str, Any]]) -> str:
    """Generate bar chart of child process memory usage."""
    if not children:
        return ""

    fig, ax = plt.subplots(figsize=(12, max(3, len(children) * 0.4)))
    _setup_chart_style(ax, "Child Process Memory (Celery Workers, etc.)")

    labels = [f"PID {c['pid']} - {c['name']}" for c in children]
    rss = [c["rss_mb"] for c in children]
    y_pos = np.arange(len(labels))

    colors = [COLORS["danger"] if r > 400 else COLORS["warning"] if r > 200 else COLORS["primary"] for r in rss]

    bars = ax.barh(y_pos, rss, color=colors, height=0.6, edgecolor="none")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=8)
    ax.set_xlabel("RSS (MB)", color=COLORS["text_muted"], fontsize=10)
    ax.invert_yaxis()

    # 400MB limit line
    ax.axvline(x=400, color=COLORS["danger"], linestyle="--", alpha=0.7, label="Worker limit (400 MB)")
    ax.legend(facecolor=COLORS["bg_dark"], edgecolor=COLORS["border"], labelcolor=COLORS["text"], fontsize=8)

    for bar, r in zip(bars, rss, strict=False):
        ax.text(
            bar.get_width() + max(rss) * 0.01,
            bar.get_y() + bar.get_height() / 2,
            f"{r:,.1f} MB",
            va="center", color=COLORS["text_muted"], fontsize=8,
        )

    return _fig_to_base64(fig)


# =============================================================================
# Executive Summary & Recommendations Engine
# =============================================================================

def _analyze_audit(
    audit_data: dict[str, Any],
    endpoint_stats: Optional[list[dict[str, Any]]] = None,
    task_stats: Optional[list[dict[str, Any]]] = None,
) -> dict[str, Any]:
    """
    Analyze audit data and produce an executive summary with findings
    and actionable recommendations.

    Returns:
        {
            "overall_grade": "A" | "B" | "C" | "D" | "F",
            "overall_verdict": str,
            "overall_color": str,
            "categories": [
                {
                    "name": str,
                    "status": "pass" | "warn" | "fail",
                    "color": str,
                    "icon": str,
                    "findings": [str, ...],
                    "recommendations": [str, ...],
                }
            ],
            "quick_wins": [str, ...],
        }
    """
    process = audit_data.get("process", {})
    system_mem = audit_data.get("system_memory", {})
    tm = audit_data.get("tracemalloc", {})
    gc_stats = audit_data.get("gc_stats", [])
    diff_info = audit_data.get("snapshot_diff")
    top_allocs = audit_data.get("top_allocations", [])
    obj_stats = audit_data.get("object_stats", [])
    ref_cycles = audit_data.get("reference_cycles", [])
    children = audit_data.get("child_processes", [])

    rss_mb = process.get("rss_mb", 0)
    vms_mb = process.get("vms_mb", 0)
    mem_pct = process.get("memory_percent", 0)
    sys_pct = system_mem.get("percent", 0)
    num_threads = process.get("num_threads", 0)
    num_connections = process.get("connections", 0)
    tm_current_mb = tm.get("current_mb", 0)
    tm_peak_mb = tm.get("peak_mb", 0)

    categories = []
    total_score = 0
    max_score = 0

    # ---- 1. Process RSS ----
    cat = {"name": "Process Memory (RSS)", "findings": [], "recommendations": []}
    max_score += 25
    if rss_mb < 200:
        cat["status"] = "pass"
        cat["score"] = 25
        cat["findings"].append(f"RSS at {rss_mb:.1f} MB — well within safe operating range (<200 MB).")
    elif rss_mb < 400:
        cat["status"] = "pass"
        cat["score"] = 20
        cat["findings"].append(f"RSS at {rss_mb:.1f} MB — acceptable for a loaded application.")
        cat["recommendations"].append("Monitor RSS trend over 24h to confirm it stays stable under sustained traffic.")
    elif rss_mb < 600:
        cat["status"] = "warn"
        cat["score"] = 12
        cat["findings"].append(f"RSS at {rss_mb:.1f} MB — approaching the Celery worker limit (400 MB per child).")
        cat["recommendations"].append("Profile the top memory-consuming endpoints and optimize data structures (generators instead of lists, lazy loading).")
        cat["recommendations"].append("Consider increasing `worker_max_memory_per_child` or splitting heavy tasks into smaller batches.")
    else:
        cat["status"] = "fail"
        cat["score"] = 5
        cat["findings"].append(f"RSS at {rss_mb:.1f} MB — exceeds recommended thresholds. Workers will be recycled frequently.")
        cat["recommendations"].append("URGENT: Investigate top allocations for large in-memory caches or data structures that should be streamed/paginated.")
        cat["recommendations"].append("Consider offloading large datasets to Redis or database-backed pagination instead of holding them in process memory.")

    # VMS ratio check
    if vms_mb > 0 and rss_mb > 0:
        ratio = vms_mb / rss_mb
        if ratio > 4:
            cat["findings"].append(f"VMS/RSS ratio is {ratio:.1f}x — high virtual memory reservation. This is typical for Python with numpy/pandas but worth noting.")
    total_score += cat["score"]
    categories.append(cat)

    # ---- 2. System Memory Pressure ----
    cat = {"name": "System Memory Pressure", "findings": [], "recommendations": []}
    max_score += 15
    if sys_pct < 60:
        cat["status"] = "pass"
        cat["score"] = 15
        cat["findings"].append(f"System RAM at {sys_pct}% — plenty of headroom available.")
    elif sys_pct < 80:
        cat["status"] = "warn"
        cat["score"] = 10
        cat["findings"].append(f"System RAM at {sys_pct}% — moderate usage. Other processes may compete for memory under load.")
        cat["recommendations"].append("Set up Prometheus alerts for system memory >85% to catch pressure before OOM events.")
    else:
        cat["status"] = "fail"
        cat["score"] = 4
        cat["findings"].append(f"System RAM at {sys_pct}% — high pressure. Risk of OOM killer intervention.")
        cat["recommendations"].append("CRITICAL: Scale vertically (add RAM) or horizontally (distribute workers across nodes).")
        cat["recommendations"].append("Review swap usage — if swapping is active, performance will degrade severely.")

    swap_pct = system_mem.get("swap_percent", 0)
    if swap_pct > 10:
        cat["findings"].append(f"Swap usage at {swap_pct}% — active swapping detected, causing I/O slowdowns.")
        cat["recommendations"].append("Reduce process memory footprint or add physical RAM to eliminate swap usage.")
        cat["score"] = max(cat["score"] - 3, 0)
    total_score += cat["score"]
    categories.append(cat)

    # ---- 3. Memory Leak Detection ----
    cat = {"name": "Leak Detection (Snapshot Diff)", "findings": [], "recommendations": []}
    max_score += 25
    if diff_info:
        rss_delta = diff_info.get("rss_delta_mb", 0)
        duration = diff_info.get("duration_seconds", 1)
        grown_count = diff_info.get("grown_types_count", 0)
        rate = (rss_delta / duration * 60) if duration > 0 else 0

        if rss_delta <= 0:
            cat["status"] = "pass"
            cat["score"] = 25
            cat["findings"].append(f"Memory is stable or shrinking ({rss_delta:+.2f} MB). No leak pattern detected.")
        elif rate < 0.5:
            cat["status"] = "pass"
            cat["score"] = 20
            cat["findings"].append(f"Minor growth of {rss_delta:+.2f} MB ({rate:.2f} MB/min) — likely normal allocation churn, not a leak.")
            if grown_count > 5:
                cat["findings"].append(f"{grown_count} object types growing — review if these stabilize after warm-up.")
        elif rate < 5:
            cat["status"] = "warn"
            cat["score"] = 12
            cat["findings"].append(f"Moderate growth of {rss_delta:+.2f} MB ({rate:.2f} MB/min) between snapshots.")
            cat["recommendations"].append("Take snapshots 15 minutes apart under steady load. If growth is linear, there is a leak.")
            cat["recommendations"].append("Check the 'Top Growing Object Types' chart to identify which types are accumulating.")
            if grown_count > 3:
                top_grown = diff_info.get("top_grown_types", [])
                for g in top_grown[:3]:
                    cat["recommendations"].append(f"Investigate growing type `{g['type']}` (+{g['delta']:,} objects, {g.get('growth_pct', 0):+.1f}%).")
        else:
            cat["status"] = "fail"
            cat["score"] = 5
            cat["findings"].append(f"Rapid growth of {rss_delta:+.2f} MB ({rate:.2f} MB/min) — strong leak signal.")
            cat["recommendations"].append("URGENT: Use `objgraph.show_growth()` and `objgraph.show_backrefs()` to trace which objects are not being freed.")
            cat["recommendations"].append("Common culprits: unclosed database sessions, growing caches without eviction, accumulating event listeners.")
    else:
        cat["status"] = "pass"
        cat["score"] = 18
        cat["findings"].append("Only one snapshot available — diff analysis requires 2+ snapshots.")
        cat["recommendations"].append("Take snapshots periodically (e.g. every 10 min) and revisit the diff report to detect gradual leaks.")
    total_score += cat["score"]
    categories.append(cat)

    # ---- 4. Garbage Collector Health ----
    cat = {"name": "Garbage Collector Health", "findings": [], "recommendations": []}
    max_score += 15
    uncollectable_total = sum(g.get("uncollectable", 0) for g in gc_stats)
    gc_score = 15

    if uncollectable_total == 0:
        cat["findings"].append("Zero uncollectable objects — GC is operating cleanly.")
    elif uncollectable_total < 50:
        gc_score = 12
        cat["findings"].append(f"{uncollectable_total} uncollectable objects detected — minor, but indicates reference cycles with `__del__` methods.")
        cat["recommendations"].append("Audit classes with `__del__` finalizers and refactor to use `weakref` or context managers.")
    else:
        gc_score = 5
        cat["findings"].append(f"{uncollectable_total} uncollectable objects — GC cannot free these. This is a memory leak source.")
        cat["recommendations"].append("URGENT: Remove or refactor `__del__` methods in classes involved in reference cycles.")

    if ref_cycles:
        gc_score = max(gc_score - 3, 0)
        cat["findings"].append(f"{len(ref_cycles)} reference cycles found in `gc.garbage`. These objects will never be freed.")
        cycle_types = {c["type"] for c in ref_cycles}
        cat["recommendations"].append(f"Reference cycle types: {', '.join(cycle_types)}. Break cycles with `weakref` or redesign ownership.")

    # Check Gen2 pressure (indicates long-lived objects accumulating)
    for g in gc_stats:
        if g.get("generation") == 2:
            gen2_count = g.get("current_count", 0)
            gen2_threshold = g.get("threshold", 10)
            if gen2_count > gen2_threshold * 0.8:
                cat["findings"].append(f"Gen 2 count ({gen2_count}) is near its threshold ({gen2_threshold}) — frequent full GC sweeps may occur.")
                gc_score = max(gc_score - 2, 0)

    cat["score"] = gc_score
    cat["status"] = "pass" if gc_score >= 12 else "warn" if gc_score >= 8 else "fail"
    total_score += gc_score
    categories.append(cat)

    # ---- 5. Allocation Hotspots ----
    cat = {"name": "Allocation Hotspots", "findings": [], "recommendations": []}
    max_score += 10
    alloc_score = 10

    large_allocs = [a for a in top_allocs if a.get("size_kb", 0) > 1000]
    heavy_alloc_files = [a for a in top_allocs if a.get("count", 0) > 100_000]

    if not large_allocs and not heavy_alloc_files:
        cat["findings"].append("No allocation hotspots exceeding 1 MB or 100K allocations. Distribution looks healthy.")
    else:
        if large_allocs:
            alloc_score -= min(len(large_allocs) * 2, 5)
            for a in large_allocs[:3]:
                fname = a["file"].replace("\\", "/").split("/")[-1]
                cat["findings"].append(f"`{fname}:{a['line']}` holds {a['size_kb']:,.0f} KB ({a['count']:,} allocations).")
            cat["recommendations"].append("Use generators/iterators instead of building large lists in memory.")
            cat["recommendations"].append("For API responses with large datasets, implement cursor-based pagination.")
        if heavy_alloc_files:
            for a in heavy_alloc_files[:2]:
                fname = a["file"].replace("\\", "/").split("/")[-1]
                cat["findings"].append(f"`{fname}:{a['line']}` has {a['count']:,} allocations — high churn overhead.")
            cat["recommendations"].append("Reduce allocation count by pre-allocating arrays (numpy) or using `__slots__` on frequently created objects.")

    cat["score"] = max(alloc_score, 2)
    cat["status"] = "pass" if alloc_score >= 8 else "warn" if alloc_score >= 5 else "fail"
    total_score += cat["score"]
    categories.append(cat)

    # ---- 6. Thread & Connection Health ----
    cat = {"name": "Threads & Connections", "findings": [], "recommendations": []}
    max_score += 10
    tc_score = 10

    if num_threads > 100:
        tc_score -= 4
        cat["findings"].append(f"{num_threads} active threads — high count may indicate thread leaks or unbounded pools.")
        cat["recommendations"].append("Audit thread pools (DB connection pool, async workers) and set explicit max sizes.")
    elif num_threads > 50:
        tc_score -= 2
        cat["findings"].append(f"{num_threads} active threads — moderate count. Ensure pools have bounded sizes.")
    else:
        cat["findings"].append(f"{num_threads} active threads — within normal range.")

    if num_connections > 100:
        tc_score -= 3
        cat["findings"].append(f"{num_connections} network connections — may indicate connection leaks.")
        cat["recommendations"].append("Ensure all HTTP/DB connections use context managers and are properly closed.")
    elif num_connections > 0:
        cat["findings"].append(f"{num_connections} active network connections.")

    open_files = process.get("open_files", 0)
    if open_files > 100:
        tc_score -= 2
        cat["findings"].append(f"{open_files} open file descriptors — check for unclosed file handles.")
        cat["recommendations"].append("Audit file operations for missing `close()` calls or use `with` statements.")
    elif open_files > 0:
        cat["findings"].append(f"{open_files} open file descriptors — normal range.")

    cat["score"] = max(tc_score, 2)
    cat["status"] = "pass" if tc_score >= 8 else "warn" if tc_score >= 5 else "fail"
    total_score += tc_score
    categories.append(cat)

    # ---- 7. Endpoint Profiling (if available) ----
    if endpoint_stats:
        cat = {"name": "Endpoint Memory Profile", "findings": [], "recommendations": []}
        max_score += 10
        ep_score = 10
        growing_eps = [e for e in endpoint_stats if e.get("trend") == "growing"]
        heavy_eps = [e for e in endpoint_stats if abs(e.get("avg_rss_delta_kb", 0)) > 500]

        if not growing_eps and not heavy_eps:
            cat["findings"].append("All profiled endpoints show stable or minimal memory usage. No concerns.")
        else:
            if growing_eps:
                ep_score -= min(len(growing_eps) * 2, 5)
                cat["findings"].append(f"{len(growing_eps)} endpoint(s) showing growing memory trend.")
                for e in growing_eps[:3]:
                    cat["recommendations"].append(f"Investigate `{e['method']} {e['path']}` — avg delta {e['avg_rss_delta_kb']:+,.0f} KB/request with growing trend.")
            if heavy_eps:
                ep_score -= min(len(heavy_eps), 3)
                for e in heavy_eps[:3]:
                    cat["findings"].append(f"`{e['method']} {e['path']}` averages {e['avg_rss_delta_kb']:+,.0f} KB per request ({e['call_count']} calls).")
                cat["recommendations"].append("Endpoints with high memory delta likely load large querysets or build big response objects. Add pagination or streaming.")

        cat["score"] = max(ep_score, 2)
        cat["status"] = "pass" if ep_score >= 8 else "warn" if ep_score >= 5 else "fail"
        total_score += cat["score"]
        categories.append(cat)

    # ---- 8. Celery Task Profiling (if available) ----
    if task_stats:
        cat = {"name": "Celery Task Memory Profile", "findings": [], "recommendations": []}
        max_score += 10
        tk_score = 10
        risky_tasks = [t for t in task_stats if t.get("leak_risk") in ("high", "medium")]
        heavy_tasks = [t for t in task_stats if t.get("avg_rss_delta_kb", 0) > 5000]

        if not risky_tasks and not heavy_tasks:
            cat["findings"].append("All profiled tasks show healthy memory patterns. No leak risk detected.")
        else:
            if risky_tasks:
                tk_score -= min(len(risky_tasks) * 3, 6)
                for t in risky_tasks[:3]:
                    cat["findings"].append(f"Task `{t.get('short_name', t['task_name'])}` flagged as {t['leak_risk'].upper()} leak risk.")
                cat["recommendations"].append("Tasks with leak risk should be profiled individually with `tracemalloc` inside the task body.")
                cat["recommendations"].append("Ensure tasks release large objects explicitly (`del`, scope exit) and call `gc.collect()` for heavy workloads.")
            if heavy_tasks:
                for t in heavy_tasks[:2]:
                    cat["findings"].append(f"Task `{t.get('short_name', t['task_name'])}` uses {t['avg_rss_delta_kb']:,.0f} KB per run on average.")
                cat["recommendations"].append("Break heavy tasks into smaller batches. The current `worker_max_memory_per_child=400MB` limit will trigger frequent worker restarts if tasks are too heavy.")

        cat["score"] = max(tk_score, 2)
        cat["status"] = "pass" if tk_score >= 8 else "warn" if tk_score >= 5 else "fail"
        total_score += cat["score"]
        categories.append(cat)

    # ---- Compute Overall Grade ----
    pct = (total_score / max_score * 100) if max_score > 0 else 0
    if pct >= 90:
        grade, verdict, color = "A", "Excellent", COLORS["success"]
    elif pct >= 75:
        grade, verdict, color = "B", "Good", COLORS["info"]
    elif pct >= 60:
        grade, verdict, color = "C", "Needs Attention", COLORS["warning"]
    elif pct >= 40:
        grade, verdict, color = "D", "Needs Improvement", COLORS["warning"]
    else:
        grade, verdict, color = "F", "Critical", COLORS["danger"]

    # Assign icons and colors to categories
    for cat in categories:
        if cat["status"] == "pass":
            cat["icon"] = "&#10004;"  # checkmark
            cat["color"] = COLORS["success"]
        elif cat["status"] == "warn":
            cat["icon"] = "&#9888;"  # warning triangle
            cat["color"] = COLORS["warning"]
        else:
            cat["icon"] = "&#10008;"  # X mark
            cat["color"] = COLORS["danger"]

    # Quick wins — top 3 most impactful recommendations
    quick_wins = []
    fail_cats = [c for c in categories if c["status"] == "fail"]
    warn_cats = [c for c in categories if c["status"] == "warn"]
    for c in fail_cats + warn_cats:
        for r in c.get("recommendations", []):
            if len(quick_wins) < 4:
                quick_wins.append(r)

    return {
        "overall_grade": grade,
        "overall_verdict": verdict,
        "overall_color": color,
        "overall_score": round(pct, 1),
        "total_score": total_score,
        "max_score": max_score,
        "categories": categories,
        "quick_wins": quick_wins,
        "pass_count": sum(1 for c in categories if c["status"] == "pass"),
        "warn_count": sum(1 for c in categories if c["status"] == "warn"),
        "fail_count": sum(1 for c in categories if c["status"] == "fail"),
    }


# =============================================================================
# HTML Report Generator
# =============================================================================

def generate_html_report(
    audit_data: dict[str, Any],
    endpoint_stats: Optional[list[dict[str, Any]]] = None,
    task_stats: Optional[list[dict[str, Any]]] = None,
) -> str:
    """
    Generate a complete HTML memory audit report with embedded visualizations.

    Args:
        audit_data: Output from MemoryAuditor.full_audit()
        endpoint_stats: Output from MemoryProfilingMiddleware.get_endpoint_stats()
        task_stats: Output from CeleryMemoryHooks.get_task_stats()

    Returns:
        Complete HTML string ready to serve or save as file.
    """
    now = datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")
    process = audit_data.get("process", {})
    system_mem = audit_data.get("system_memory", {})

    # Generate all charts
    charts = {}
    charts["timeline"] = chart_memory_timeline(audit_data.get("timeline", []))
    charts["system"] = chart_system_memory(system_mem, process)
    charts["top_allocs"] = chart_top_allocations(audit_data.get("top_allocations", []))
    charts["top_files"] = chart_top_files(audit_data.get("top_files", []))
    charts["objects"] = chart_object_distribution(audit_data.get("object_stats", []))
    charts["gc"] = chart_gc_stats(audit_data.get("gc_stats", []))
    charts["diff"] = chart_snapshot_diff(audit_data.get("snapshot_diff"))
    charts["children"] = chart_child_processes(audit_data.get("child_processes", []))

    if endpoint_stats:
        charts["endpoints"] = chart_endpoint_memory(endpoint_stats)
    if task_stats:
        charts["tasks"] = chart_task_memory(task_stats)

    # Run the analysis engine
    analysis = _analyze_audit(audit_data, endpoint_stats, task_stats)

    health_status = analysis["overall_grade"]
    health_color = analysis["overall_color"]
    rss_mb = process.get("rss_mb", 0)
    mem_pct = process.get("memory_percent", 0)

    # Build HTML
    def _chart_section(chart_id: str, title: str) -> str:
        b64 = charts.get(chart_id, "")
        if not b64:
            return ""
        return f"""
        <div class="chart-card">
            <h3>{title}</h3>
            <img src="data:image/png;base64,{b64}" alt="{title}" />
        </div>
        """

    # Allocation table rows
    alloc_rows = ""
    for a in audit_data.get("top_allocations", [])[:20]:
        filename = a["file"].split("/")[-1] if "/" in a["file"] else a["file"].split("\\")[-1]
        size_class = "danger" if a["size_kb"] > 500 else "warning" if a["size_kb"] > 100 else ""
        alloc_rows += f"""
        <tr class="{size_class}">
            <td class="mono">{filename}:{a['line']}</td>
            <td class="num">{a['size_kb']:,.1f}</td>
            <td class="num">{a['count']:,}</td>
            <td class="mono code">{a.get('code', '')[:80]}</td>
        </tr>
        """

    # Object stats table
    obj_rows = ""
    for o in audit_data.get("object_stats", [])[:20]:
        obj_rows += f"""
        <tr>
            <td class="mono">{o['type']}</td>
            <td class="num">{o['count']:,}</td>
            <td class="num">{o.get('size_kb', 0):,.1f}</td>
        </tr>
        """

    # Endpoint stats table
    endpoint_rows = ""
    if endpoint_stats:
        for e in endpoint_stats[:25]:
            trend_icon = {"growing": "&#9650;", "shrinking": "&#9660;", "stable": "&#9644;"}.get(e.get("trend", ""), "?")
            trend_class = {"growing": "danger", "shrinking": "success", "stable": ""}.get(e.get("trend", ""), "")
            endpoint_rows += f"""
            <tr>
                <td class="mono">{e['method']}</td>
                <td class="mono">{e['path'][:50]}</td>
                <td class="num">{e['call_count']:,}</td>
                <td class="num">{e['avg_rss_delta_kb']:+,.1f}</td>
                <td class="num">{e['max_rss_delta_kb']:+,.1f}</td>
                <td class="num">{e.get('avg_duration_ms', 0):,.1f}</td>
                <td class="{trend_class}">{trend_icon} {e.get('trend', 'n/a')}</td>
            </tr>
            """

    # Task stats table
    task_rows = ""
    if task_stats:
        for t in task_stats[:20]:
            risk = t.get("leak_risk", "unknown")
            risk_class = {"high": "danger", "medium": "warning"}.get(risk, "")
            task_rows += f"""
            <tr>
                <td class="mono">{t.get('short_name', t['task_name'])}</td>
                <td class="num">{t['execution_count']:,}</td>
                <td class="num">{t['avg_rss_delta_kb']:+,.1f}</td>
                <td class="num">{t['max_rss_delta_kb']:+,.1f}</td>
                <td class="num">{t.get('peak_rss_mb', 0):,.1f}</td>
                <td class="num">{t.get('avg_duration_ms', 0):,.1f}</td>
                <td class="{risk_class}">{risk.upper()}</td>
            </tr>
            """

    # GC stats
    gc_rows = ""
    for g in audit_data.get("gc_stats", []):
        gc_rows += f"""
        <tr>
            <td>Gen {g['generation']}</td>
            <td class="num">{g.get('collections', 0):,}</td>
            <td class="num">{g.get('collected', 0):,}</td>
            <td class="num">{g.get('uncollectable', 0):,}</td>
            <td class="num">{g.get('threshold', 'n/a')}</td>
            <td class="num">{g.get('current_count', 'n/a')}</td>
        </tr>
        """

    # Reference cycles
    cycle_rows = ""
    for c in audit_data.get("reference_cycles", []):
        cycle_rows += f"""
        <tr>
            <td class="mono">{c['type']}</td>
            <td class="num">{c['size_bytes']:,}</td>
            <td class="num">{c['referrers_count']}</td>
            <td class="mono code">{c['repr'][:100]}</td>
        </tr>
        """

    tracemalloc_info = audit_data.get("tracemalloc", {})
    diff_info = audit_data.get("snapshot_diff")

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Stratum AI - Memory Audit Report</title>
<style>
    * {{ margin: 0; padding: 0; box-sizing: border-box; }}
    body {{
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background: {COLORS['bg_dark']};
        color: {COLORS['text']};
        line-height: 1.6;
    }}
    .container {{ max-width: 1400px; margin: 0 auto; padding: 24px; }}

    /* Header */
    .header {{
        background: linear-gradient(135deg, {COLORS['primary']}22, {COLORS['secondary']}22);
        border: 1px solid {COLORS['border']};
        border-radius: 12px;
        padding: 32px;
        margin-bottom: 24px;
    }}
    .header h1 {{
        font-size: 28px;
        background: linear-gradient(135deg, {COLORS['primary']}, {COLORS['secondary']});
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 8px;
    }}
    .header .subtitle {{ color: {COLORS['text_muted']}; font-size: 14px; }}

    /* Status badge */
    .status-badge {{
        display: inline-block;
        padding: 4px 16px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 13px;
        letter-spacing: 1px;
    }}

    /* Stat cards row */
    .stats-row {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 16px;
        margin-bottom: 24px;
    }}
    .stat-card {{
        background: {COLORS['bg_card']};
        border: 1px solid {COLORS['border']};
        border-radius: 10px;
        padding: 20px;
        text-align: center;
    }}
    .stat-card .value {{
        font-size: 28px;
        font-weight: 700;
        margin: 8px 0 4px;
    }}
    .stat-card .label {{
        color: {COLORS['text_muted']};
        font-size: 12px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}

    /* Chart cards */
    .chart-card {{
        background: {COLORS['bg_card']};
        border: 1px solid {COLORS['border']};
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
    }}
    .chart-card h3 {{
        color: {COLORS['text']};
        font-size: 16px;
        margin-bottom: 16px;
        padding-bottom: 8px;
        border-bottom: 1px solid {COLORS['grid']};
    }}
    .chart-card img {{
        width: 100%;
        border-radius: 6px;
    }}

    /* Charts grid */
    .charts-grid {{
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(580px, 1fr));
        gap: 20px;
        margin-bottom: 24px;
    }}

    /* Tables */
    .table-card {{
        background: {COLORS['bg_card']};
        border: 1px solid {COLORS['border']};
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        overflow-x: auto;
    }}
    .table-card h3 {{
        color: {COLORS['text']};
        font-size: 16px;
        margin-bottom: 16px;
        padding-bottom: 8px;
        border-bottom: 1px solid {COLORS['grid']};
    }}
    table {{
        width: 100%;
        border-collapse: collapse;
        font-size: 13px;
    }}
    th {{
        background: {COLORS['bg_dark']};
        color: {COLORS['text_muted']};
        font-weight: 600;
        text-transform: uppercase;
        font-size: 11px;
        letter-spacing: 0.5px;
        padding: 10px 12px;
        text-align: left;
        border-bottom: 2px solid {COLORS['grid']};
    }}
    td {{
        padding: 8px 12px;
        border-bottom: 1px solid {COLORS['grid']}33;
        color: {COLORS['text']};
    }}
    tr:hover {{ background: {COLORS['bg_dark']}88; }}
    .mono {{ font-family: 'SF Mono', 'Fira Code', monospace; font-size: 12px; }}
    .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .code {{ color: {COLORS['text_muted']}; font-size: 11px; max-width: 400px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .danger {{ color: {COLORS['danger']}; }}
    .warning {{ color: {COLORS['warning']}; }}
    .success {{ color: {COLORS['success']}; }}

    /* Section headers */
    .section-header {{
        font-size: 20px;
        font-weight: 700;
        color: {COLORS['text']};
        margin: 32px 0 16px;
        padding-bottom: 8px;
        border-bottom: 2px solid {COLORS['primary']}44;
    }}

    /* Executive Summary */
    .exec-summary {{
        background: {COLORS['bg_card']};
        border: 1px solid {COLORS['border']};
        border-radius: 12px;
        padding: 28px 32px;
        margin-bottom: 28px;
    }}
    .exec-summary h2 {{
        font-size: 22px;
        margin-bottom: 20px;
        color: {COLORS['text']};
    }}
    .grade-row {{
        display: flex;
        align-items: center;
        gap: 24px;
        margin-bottom: 24px;
        flex-wrap: wrap;
    }}
    .grade-circle {{
        width: 80px;
        height: 80px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 36px;
        font-weight: 800;
        flex-shrink: 0;
    }}
    .grade-detail {{ flex: 1; min-width: 200px; }}
    .grade-detail .verdict {{
        font-size: 20px;
        font-weight: 700;
        margin-bottom: 4px;
    }}
    .grade-detail .score-text {{
        color: {COLORS['text_muted']};
        font-size: 14px;
    }}
    .grade-detail .score-bar {{
        height: 8px;
        background: {COLORS['grid']};
        border-radius: 4px;
        margin-top: 8px;
        overflow: hidden;
    }}
    .grade-detail .score-bar-fill {{
        height: 100%;
        border-radius: 4px;
        transition: width 0.5s ease;
    }}
    .pass-fail-row {{
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
    }}
    .pf-badge {{
        padding: 4px 14px;
        border-radius: 16px;
        font-size: 12px;
        font-weight: 600;
        letter-spacing: 0.5px;
    }}

    /* Category cards */
    .cat-card {{
        border: 1px solid {COLORS['border']};
        border-radius: 10px;
        padding: 18px 22px;
        margin-bottom: 14px;
        border-left: 4px solid;
    }}
    .cat-header {{
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 10px;
    }}
    .cat-icon {{
        font-size: 18px;
        width: 28px;
        text-align: center;
    }}
    .cat-name {{
        font-size: 15px;
        font-weight: 600;
        color: {COLORS['text']};
    }}
    .cat-status {{
        margin-left: auto;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
        padding: 2px 10px;
        border-radius: 10px;
    }}
    .finding {{
        color: {COLORS['text_muted']};
        font-size: 13px;
        padding: 3px 0 3px 38px;
        line-height: 1.5;
    }}
    .rec-list {{
        margin: 8px 0 0 38px;
        padding: 0;
        list-style: none;
    }}
    .rec-list li {{
        font-size: 13px;
        padding: 4px 0 4px 18px;
        position: relative;
        color: {COLORS['text']};
        line-height: 1.5;
    }}
    .rec-list li::before {{
        content: "\\2192";
        position: absolute;
        left: 0;
        font-weight: 700;
    }}

    /* Quick Wins box */
    .quick-wins {{
        background: {COLORS['bg_dark']};
        border: 1px solid {COLORS['primary']}44;
        border-radius: 10px;
        padding: 18px 22px;
        margin-top: 20px;
    }}
    .quick-wins h3 {{
        font-size: 15px;
        color: {COLORS['primary']};
        margin-bottom: 12px;
    }}
    .quick-wins ol {{
        margin: 0;
        padding-left: 20px;
    }}
    .quick-wins li {{
        font-size: 13px;
        color: {COLORS['text']};
        padding: 4px 0;
        line-height: 1.5;
    }}

    /* Footer */
    .footer {{
        text-align: center;
        color: {COLORS['text_muted']};
        font-size: 12px;
        padding: 24px 0;
        border-top: 1px solid {COLORS['grid']};
        margin-top: 40px;
    }}

    /* Responsive */
    @media (max-width: 640px) {{
        .charts-grid {{ grid-template-columns: 1fr; }}
        .stats-row {{ grid-template-columns: repeat(2, 1fr); }}
        .grade-row {{ flex-direction: column; align-items: flex-start; }}
    }}
</style>
</head>
<body>
<div class="container">

    <!-- Header -->
    <div class="header">
        <h1>Stratum AI Memory Audit Report</h1>
        <p class="subtitle">
            Generated: {now} &nbsp;|&nbsp;
            PID: {process.get('pid', 'N/A')} &nbsp;|&nbsp;
            Python: {audit_data.get('python_version', 'N/A')[:12]} &nbsp;|&nbsp;
            Platform: {audit_data.get('platform', 'N/A')} &nbsp;|&nbsp;
            <span class="status-badge" style="background: {health_color}22; color: {health_color}; border: 1px solid {health_color};">
                {health_status}
            </span>
        </p>
    </div>

    <!-- Summary Stat Cards -->
    <div class="stats-row">
        <div class="stat-card">
            <div class="label">Process RSS</div>
            <div class="value" style="color: {health_color}">{rss_mb:,.1f} MB</div>
            <div class="label">{mem_pct}% of system</div>
        </div>
        <div class="stat-card">
            <div class="label">Virtual Memory</div>
            <div class="value">{process.get('vms_mb', 0):,.1f} MB</div>
            <div class="label">VMS</div>
        </div>
        <div class="stat-card">
            <div class="label">Tracemalloc</div>
            <div class="value">{tracemalloc_info.get('current_mb', 0):,.2f} MB</div>
            <div class="label">Peak: {tracemalloc_info.get('peak_mb', 0):,.2f} MB</div>
        </div>
        <div class="stat-card">
            <div class="label">Threads</div>
            <div class="value">{process.get('num_threads', 0)}</div>
            <div class="label">Active threads</div>
        </div>
        <div class="stat-card">
            <div class="label">Open Files</div>
            <div class="value">{process.get('open_files', 0)}</div>
            <div class="label">File descriptors</div>
        </div>
        <div class="stat-card">
            <div class="label">Connections</div>
            <div class="value">{process.get('connections', 0)}</div>
            <div class="label">Network sockets</div>
        </div>
        <div class="stat-card">
            <div class="label">CPU Usage</div>
            <div class="value">{process.get('cpu_percent', 0):.1f}%</div>
            <div class="label">Process CPU</div>
        </div>
        <div class="stat-card">
            <div class="label">System RAM</div>
            <div class="value">{system_mem.get('percent', 0)}%</div>
            <div class="label">{system_mem.get('used_mb', 0):,.0f} / {system_mem.get('total_mb', 0):,.0f} MB</div>
        </div>
    </div>

    <!-- Executive Summary & Recommendations -->
    <div class="exec-summary">
        <h2>Executive Summary &amp; Recommendations</h2>

        <div class="grade-row">
            <div class="grade-circle" style="background: {analysis['overall_color']}22; color: {analysis['overall_color']}; border: 3px solid {analysis['overall_color']};">
                {analysis['overall_grade']}
            </div>
            <div class="grade-detail">
                <div class="verdict" style="color: {analysis['overall_color']};">{analysis['overall_verdict']}</div>
                <div class="score-text">Score: {analysis['overall_score']}% ({analysis['total_score']} / {analysis['max_score']} points)</div>
                <div class="score-bar">
                    <div class="score-bar-fill" style="width: {analysis['overall_score']}%; background: {analysis['overall_color']};"></div>
                </div>
            </div>
            <div class="pass-fail-row">
                <span class="pf-badge" style="background: {COLORS['success']}22; color: {COLORS['success']};">&#10004; {analysis['pass_count']} Passed</span>
                <span class="pf-badge" style="background: {COLORS['warning']}22; color: {COLORS['warning']};">&#9888; {analysis['warn_count']} Warnings</span>
                <span class="pf-badge" style="background: {COLORS['danger']}22; color: {COLORS['danger']};">&#10008; {analysis['fail_count']} Failed</span>
            </div>
        </div>

        {''.join(f"""
        <div class="cat-card" style="border-left-color: {cat['color']};">
            <div class="cat-header">
                <span class="cat-icon" style="color: {cat['color']};">{cat['icon']}</span>
                <span class="cat-name">{cat['name']}</span>
                <span class="cat-status" style="background: {cat['color']}22; color: {cat['color']};">{cat['status'].upper()}</span>
            </div>
            {''.join(f'<div class="finding">{f}</div>' for f in cat.get('findings', []))}
            {f'<ul class="rec-list">{"".join(f"<li>{r}</li>" for r in cat.get("recommendations", []))}</ul>' if cat.get('recommendations') else ''}
        </div>
        """ for cat in analysis['categories'])}

        {f"""
        <div class="quick-wins">
            <h3>Priority Action Items</h3>
            <ol>
                {''.join(f'<li>{qw}</li>' for qw in analysis['quick_wins'])}
            </ol>
        </div>
        """ if analysis['quick_wins'] else f"""
        <div class="quick-wins" style="border-color: {COLORS['success']}44;">
            <h3 style="color: {COLORS['success']};">No Critical Actions Required</h3>
            <p style="color: {COLORS['text_muted']}; font-size: 13px; margin: 0;">
                All memory categories are within healthy thresholds. Continue monitoring with periodic snapshots to detect gradual changes.
            </p>
        </div>
        """}
    </div>

    <!-- System & Timeline Charts -->
    <h2 class="section-header">System Overview</h2>
    <div class="charts-grid">
        {_chart_section("system", "System vs Process Memory")}
        {_chart_section("timeline", "Memory Timeline")}
    </div>

    <!-- Child Processes -->
    {_chart_section("children", "Child Processes (Workers)")}

    <!-- Allocation Analysis -->
    <h2 class="section-header">Allocation Analysis (tracemalloc)</h2>
    <div class="charts-grid">
        {_chart_section("top_files", "Top Files by Memory")}
        {_chart_section("top_allocs", "Top Allocations by Line")}
    </div>

    <div class="table-card">
        <h3>Detailed Allocation Table</h3>
        <table>
            <thead>
                <tr>
                    <th>Location</th>
                    <th>Size (KB)</th>
                    <th>Count</th>
                    <th>Code</th>
                </tr>
            </thead>
            <tbody>{alloc_rows}</tbody>
        </table>
    </div>

    <!-- Object Analysis -->
    <h2 class="section-header">Object Analysis</h2>
    {_chart_section("objects", "Object Distribution")}

    <div class="table-card">
        <h3>Object Types by Count</h3>
        <table>
            <thead>
                <tr><th>Type</th><th>Count</th><th>Size (KB)</th></tr>
            </thead>
            <tbody>{obj_rows}</tbody>
        </table>
    </div>

    <!-- Endpoint Profiling -->
    {"<h2 class='section-header'>Endpoint Memory Profiling</h2>" if endpoint_stats else ""}
    {_chart_section("endpoints", "Per-Endpoint Memory Usage")}
    {f'''<div class="table-card">
        <h3>Endpoint Memory Stats</h3>
        <table>
            <thead>
                <tr><th>Method</th><th>Path</th><th>Calls</th><th>Avg Delta (KB)</th><th>Max Delta (KB)</th><th>Avg Duration (ms)</th><th>Trend</th></tr>
            </thead>
            <tbody>{endpoint_rows}</tbody>
        </table>
    </div>''' if endpoint_stats else ""}

    <!-- Celery Task Profiling -->
    {"<h2 class='section-header'>Celery Task Memory Profiling</h2>" if task_stats else ""}
    {_chart_section("tasks", "Per-Task Memory Usage")}
    {f'''<div class="table-card">
        <h3>Task Memory Stats</h3>
        <table>
            <thead>
                <tr><th>Task</th><th>Runs</th><th>Avg Delta (KB)</th><th>Max Delta (KB)</th><th>Peak RSS (MB)</th><th>Avg Duration (ms)</th><th>Leak Risk</th></tr>
            </thead>
            <tbody>{task_rows}</tbody>
        </table>
    </div>''' if task_stats else ""}

    <!-- Leak Detection -->
    <h2 class="section-header">Leak Detection (Snapshot Diff)</h2>
    {_chart_section("diff", "Snapshot Comparison")}
    {f'''<div class="stats-row">
        <div class="stat-card">
            <div class="label">RSS Delta</div>
            <div class="value" style="color: {COLORS['danger'] if diff_info and diff_info['rss_delta_mb'] > 0 else COLORS['success']}">{diff_info['rss_delta_mb']:+.2f} MB</div>
            <div class="label">Between snapshots</div>
        </div>
        <div class="stat-card">
            <div class="label">Duration</div>
            <div class="value">{diff_info['duration_seconds']:.1f}s</div>
            <div class="label">Time between snapshots</div>
        </div>
        <div class="stat-card">
            <div class="label">New Allocations</div>
            <div class="value">{diff_info['new_allocations']}</div>
            <div class="label">tracemalloc entries</div>
        </div>
        <div class="stat-card">
            <div class="label">Growing Types</div>
            <div class="value">{diff_info['grown_types_count']}</div>
            <div class="label">Object types increased</div>
        </div>
    </div>''' if diff_info else '<p style="color: ' + COLORS["text_muted"] + '; padding: 20px;">Take at least 2 snapshots to see diff analysis. Use <code>POST /debug/memory/snapshot</code> to capture snapshots.</p>'}

    <!-- GC Stats -->
    <h2 class="section-header">Garbage Collector</h2>
    {_chart_section("gc", "GC Generation Statistics")}

    <div class="table-card">
        <h3>GC Details</h3>
        <table>
            <thead>
                <tr><th>Generation</th><th>Collections</th><th>Collected</th><th>Uncollectable</th><th>Threshold</th><th>Current Count</th></tr>
            </thead>
            <tbody>{gc_rows}</tbody>
        </table>
    </div>

    <!-- Reference Cycles -->
    {f'''<div class="table-card">
        <h3>Reference Cycles (Potential Leaks)</h3>
        <table>
            <thead>
                <tr><th>Type</th><th>Size (bytes)</th><th>Referrers</th><th>Preview</th></tr>
            </thead>
            <tbody>{cycle_rows}</tbody>
        </table>
    </div>''' if cycle_rows else ""}

    <!-- Footer -->
    <div class="footer">
        Stratum AI Memory Audit Report &mdash; Generated by Memory Profiling Engine<br>
        tracemalloc + psutil + gc &mdash; {now}
    </div>

</div>
</body>
</html>"""

    return html
