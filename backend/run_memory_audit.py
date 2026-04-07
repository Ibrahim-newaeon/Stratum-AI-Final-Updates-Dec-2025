#!/usr/bin/env python3
"""
Standalone memory audit runner for Stratum AI.

Runs the full memory audit engine directly — no FastAPI server,
no PostgreSQL, no Redis required. Simulates real workload patterns,
takes snapshots, diffs them, and generates the full HTML report.

Usage:
    python run_memory_audit.py
"""

import gc
import hashlib
import os
import sys
import time

# Ensure backend is on the path
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BACKEND_DIR)

# ---- Direct imports (no app.core.config dependency) ----
from app.monitoring.memory_audit import MemoryAuditor
from app.monitoring.visualizations import generate_html_report


def simulate_workload() -> dict:
    """Simulate typical Stratum AI workload patterns to generate real memory data."""
    print("  [1/5] Importing heavy modules (simulating app boot)...")
    import collections
    import datetime
    import json
    import re
    import urllib.parse

    # Simulate pandas/numpy (if available)
    try:
        import numpy as np
        import pandas as pd

        _data = np.random.randn(10000, 50)
        _df = pd.DataFrame(_data, columns=[f"feature_{i}" for i in range(50)])
        _df["target"] = np.random.randint(0, 2, 10000)
        print(f"    Loaded DataFrame: {_df.shape} ({sys.getsizeof(_df) / 1024:.1f} KB)")
    except ImportError:
        _df = None
        print("    numpy/pandas not available, skipping ML simulation")

    print("  [2/5] Simulating API request data structures...")
    cache: dict = {}
    for i in range(500):
        cache[f"tenant_{i % 10}_campaign_{i}"] = {
            "id": i,
            "name": f"Campaign #{i}",
            "platform": ["meta", "google", "tiktok", "snapchat"][i % 4],
            "metrics": {
                "impressions": i * 1000,
                "clicks": i * 50,
                "conversions": i * 5,
                "spend": round(i * 12.50, 2),
                "roas": round(2.5 + (i % 10) * 0.3, 2),
            },
            "daily_data": [
                {"date": f"2025-{m:02d}-{d:02d}", "spend": round(i * 0.5, 2)}
                for m in range(1, 13)
                for d in range(1, 29)
            ],
        }
    print(f"    Built campaign cache: {len(cache)} entries")

    print("  [3/5] Simulating CDP profile data...")
    profiles: list = []
    for i in range(2000):
        profiles.append({
            "profile_id": f"prof_{i:06d}",
            "email_hash": hashlib.sha256(f"user{i}@example.com".encode()).hexdigest(),
            "traits": {
                "name": f"User {i}",
                "lifecycle_stage": ["anonymous", "known", "active", "churned"][i % 4],
                "ltv": round(i * 15.0, 2),
                "rfm_score": i % 100,
                "segments": [f"seg_{j}" for j in range(i % 5)],
            },
            "events": [
                {"type": "page_view", "timestamp": time.time() - j * 3600}
                for j in range(i % 20)
            ],
        })
    print(f"    Built {len(profiles)} CDP profiles")

    print("  [4/5] Simulating segment computation...")
    segments: dict = {}
    for s in range(50):
        matching = [p for p in profiles if p["traits"]["rfm_score"] > s * 2]
        segments[f"segment_{s}"] = {
            "name": f"High Value Segment {s}",
            "conditions": [
                {"field": "rfm_score", "operator": "gt", "value": s * 2},
                {"field": "lifecycle_stage", "operator": "in", "value": ["active", "known"]},
            ],
            "profile_count": len(matching),
            "profile_ids": [p["profile_id"] for p in matching[:100]],
        }
    print(f"    Computed {len(segments)} segments")

    print("  [5/5] Simulating signal health calculations...")
    signals: list = []
    for i in range(200):
        signals.append({
            "signal_id": f"sig_{i}",
            "source": ["meta_api", "google_api", "webhook", "capi"][i % 4],
            "health_score": 40 + (i % 60),
            "components": {
                "freshness": 50 + (i % 50),
                "completeness": 60 + (i % 40),
                "consistency": 45 + (i % 55),
            },
            "samples": list(range(i * 10)),
        })
    print(f"    Evaluated {len(signals)} signals")

    return {
        "cache": cache,
        "profiles": profiles,
        "segments": segments,
        "signals": signals,
    }


def run_audit() -> str:
    """Run the full memory audit with snapshots and report generation."""
    print("=" * 70)
    print("  STRATUM AI - FULL MEMORY AUDIT")
    print("=" * 70)

    auditor = MemoryAuditor()

    print("\n[PHASE 1] Starting tracemalloc tracking...")
    auditor.start_tracking()
    auditor.record_point("audit_start")
    time.sleep(0.2)

    print("[PHASE 2] Taking baseline snapshot...")
    auditor.take_snapshot(label="baseline")
    time.sleep(0.3)

    print("\n[PHASE 3] Simulating Stratum AI workload...")
    workload_data = simulate_workload()
    auditor.record_point("workload_complete")
    time.sleep(0.2)

    print("\n[PHASE 4] Taking post-workload snapshot...")
    auditor.take_snapshot(label="post_workload")
    time.sleep(0.3)

    print("[PHASE 5] Simulating request churn (GC pressure)...")
    for i in range(100):
        temp = {f"key_{j}": list(range(100)) for j in range(50)}
        del temp
    gc.collect()
    auditor.record_point("churn_complete")
    time.sleep(0.2)

    print("[PHASE 6] Forcing GC and taking final snapshot...")
    gc_result = auditor.force_gc()
    print(f"    GC collected: {gc_result['collected']['total']} objects, freed {gc_result['rss_freed_kb']:.1f} KB")
    auditor.take_snapshot(label="post_gc")
    time.sleep(0.2)

    print("\n[PHASE 7] Running full audit...")
    audit_data = auditor.full_audit()

    # ---- Console Summary ----
    process = audit_data["process"]
    print("\n" + "=" * 70)
    print("  AUDIT RESULTS SUMMARY")
    print("=" * 70)
    print(f"  Process RSS:        {process['rss_mb']:>10.1f} MB")
    print(f"  Process VMS:        {process['vms_mb']:>10.1f} MB")
    print(f"  Memory %:           {process['memory_percent']:>10.1f}%")
    print(f"  Threads:            {process['num_threads']:>10d}")
    print(f"  CPU %:              {process['cpu_percent']:>10.1f}%")

    tm = audit_data["tracemalloc"]
    print(f"  Tracemalloc Curr:   {tm.get('current_mb', 0):>10.2f} MB")
    print(f"  Tracemalloc Peak:   {tm.get('peak_mb', 0):>10.2f} MB")

    system = audit_data["system_memory"]
    print(f"  System RAM Used:    {system['used_mb']:>10.0f} MB ({system['percent']}%)")
    print(f"  System RAM Total:   {system['total_mb']:>10.0f} MB")

    if audit_data.get("snapshot_diff"):
        diff = audit_data["snapshot_diff"]
        print(f"\n  Snapshot Diff:")
        print(f"    RSS Delta:        {diff['rss_delta_mb']:>+10.2f} MB")
        print(f"    Duration:         {diff['duration_seconds']:>10.1f}s")
        print(f"    Growing types:    {diff['grown_types_count']:>10d}")

    print(f"\n  Top 5 Allocations:")
    for a in audit_data["top_allocations"][:5]:
        fname = a["file"].replace("\\", "/").split("/")[-1]
        print(f"    {fname}:{a['line']:>4d}  {a['size_kb']:>8.1f} KB  ({a['count']:>5d} allocs)")

    print(f"\n  Top 5 Object Types:")
    for o in audit_data["object_stats"][:5]:
        print(f"    {o['type']:<20s}  {o['count']:>10,d}  ({o.get('size_kb', 0):>8.1f} KB)")

    # ---- Generate HTML Report ----
    print("\n[PHASE 8] Generating HTML report with visualizations...")
    html = generate_html_report(audit_data=audit_data)

    report_path = os.path.join(BACKEND_DIR, "memory_audit_report.html")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)

    size_kb = os.path.getsize(report_path) / 1024
    print(f"\n  Report saved to: {report_path}")
    print(f"  Report size:     {size_kb:.1f} KB")
    print("=" * 70)
    print("  DONE - Open the HTML file in your browser to view the report")
    print("=" * 70)

    del workload_data
    auditor.stop_tracking()

    return report_path


if __name__ == "__main__":
    report = run_audit()
