# =============================================================================
# Stratum AI - Memory Profiling Middleware
# =============================================================================
"""
FastAPI middleware that tracks memory consumption per API endpoint.

Records memory delta (RSS before vs after) for every request,
aggregates statistics per route, and exposes data for the audit report.
"""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

import psutil
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


@dataclass
class EndpointMemoryStats:
    """Aggregated memory stats for a single endpoint."""
    path: str
    method: str
    call_count: int = 0
    total_rss_delta_kb: float = 0.0
    max_rss_delta_kb: float = 0.0
    min_rss_delta_kb: float = float("inf")
    avg_rss_delta_kb: float = 0.0
    total_duration_ms: float = 0.0
    max_duration_ms: float = 0.0
    last_rss_delta_kb: float = 0.0
    # Track recent deltas for trend analysis
    recent_deltas: list[float] = field(default_factory=list)

    def record(self, rss_delta_kb: float, duration_ms: float) -> None:
        """Record a new request measurement."""
        self.call_count += 1
        self.total_rss_delta_kb += rss_delta_kb
        self.total_duration_ms += duration_ms
        self.last_rss_delta_kb = rss_delta_kb

        if rss_delta_kb > self.max_rss_delta_kb:
            self.max_rss_delta_kb = rss_delta_kb
        if rss_delta_kb < self.min_rss_delta_kb:
            self.min_rss_delta_kb = rss_delta_kb
        if duration_ms > self.max_duration_ms:
            self.max_duration_ms = duration_ms

        self.avg_rss_delta_kb = round(
            self.total_rss_delta_kb / self.call_count, 2
        )

        # Keep last 50 deltas for trend
        self.recent_deltas.append(rss_delta_kb)
        if len(self.recent_deltas) > 50:
            self.recent_deltas.pop(0)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "method": self.method,
            "call_count": self.call_count,
            "avg_rss_delta_kb": self.avg_rss_delta_kb,
            "max_rss_delta_kb": self.max_rss_delta_kb,
            "min_rss_delta_kb": round(self.min_rss_delta_kb, 2)
            if self.min_rss_delta_kb != float("inf")
            else 0.0,
            "total_rss_delta_kb": round(self.total_rss_delta_kb, 2),
            "avg_duration_ms": round(
                self.total_duration_ms / self.call_count, 2
            )
            if self.call_count > 0
            else 0.0,
            "max_duration_ms": round(self.max_duration_ms, 2),
            "last_rss_delta_kb": self.last_rss_delta_kb,
            "trend": self._calculate_trend(),
        }

    def _calculate_trend(self) -> str:
        """Determine if memory usage is trending up, down, or stable."""
        if len(self.recent_deltas) < 5:
            return "insufficient_data"
        recent = self.recent_deltas[-5:]
        avg_recent = sum(recent) / len(recent)
        if avg_recent > 100:
            return "growing"
        if avg_recent < -100:
            return "shrinking"
        return "stable"


class MemoryProfilingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that measures RSS memory delta for each HTTP request.

    Skips profiling for health checks and the debug/memory endpoints
    themselves to avoid noise and recursion.
    """

    # Paths to skip profiling (health checks, metrics, debug endpoints)
    SKIP_PATHS = {"/health", "/health/ready", "/health/live", "/metrics"}
    SKIP_PREFIXES = ("/debug/memory", "/docs", "/redoc", "/openapi.json")

    def __init__(self, app: Any, enabled: bool = True) -> None:
        super().__init__(app)
        self.enabled = enabled
        self._endpoint_stats: dict[str, EndpointMemoryStats] = {}
        self._process = psutil.Process()
        self._request_log: list[dict[str, Any]] = []
        self._max_log_size = 500

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        if not self.enabled:
            return await call_next(request)

        path = request.url.path
        method = request.method

        # Skip noise paths
        if path in self.SKIP_PATHS or path.startswith(self.SKIP_PREFIXES):
            return await call_next(request)

        # Normalize path (remove IDs for grouping: /api/v1/campaigns/123 -> /api/v1/campaigns/{id})
        normalized = self._normalize_path(path)
        key = f"{method}:{normalized}"

        # Measure
        rss_before = self._process.memory_info().rss
        start = time.perf_counter()

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start) * 1000
        rss_after = self._process.memory_info().rss
        rss_delta_kb = round((rss_after - rss_before) / 1024, 2)

        # Record stats
        if key not in self._endpoint_stats:
            self._endpoint_stats[key] = EndpointMemoryStats(
                path=normalized, method=method
            )
        self._endpoint_stats[key].record(rss_delta_kb, duration_ms)

        # Add to recent request log
        self._request_log.append({
            "path": normalized,
            "method": method,
            "status": response.status_code,
            "rss_delta_kb": rss_delta_kb,
            "duration_ms": round(duration_ms, 2),
        })
        if len(self._request_log) > self._max_log_size:
            self._request_log.pop(0)

        # Add memory header in dev
        response.headers["X-Memory-Delta-KB"] = str(rss_delta_kb)

        return response

    def _normalize_path(self, path: str) -> str:
        """Replace numeric path segments with {id} for grouping."""
        parts = path.split("/")
        normalized = []
        for part in parts:
            if part.isdigit():
                normalized.append("{id}")
            else:
                normalized.append(part)
        return "/".join(normalized)

    def get_endpoint_stats(
        self, sort_by: str = "avg_rss_delta_kb", limit: int = 50
    ) -> list[dict[str, Any]]:
        """Get all endpoint memory stats, sorted by specified field."""
        stats = [s.to_dict() for s in self._endpoint_stats.values()]
        stats.sort(key=lambda x: abs(x.get(sort_by, 0)), reverse=True)
        return stats[:limit]

    def get_top_consumers(self, limit: int = 15) -> list[dict[str, Any]]:
        """Get endpoints with highest average memory consumption."""
        return self.get_endpoint_stats(sort_by="avg_rss_delta_kb", limit=limit)

    def get_recent_requests(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent request memory measurements."""
        return self._request_log[-limit:]

    def get_growing_endpoints(self) -> list[dict[str, Any]]:
        """Get endpoints with growing memory trend."""
        return [
            s.to_dict()
            for s in self._endpoint_stats.values()
            if s._calculate_trend() == "growing"
        ]

    def reset_stats(self) -> None:
        """Reset all collected statistics."""
        self._endpoint_stats.clear()
        self._request_log.clear()

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of endpoint profiling data."""
        total_requests = sum(
            s.call_count for s in self._endpoint_stats.values()
        )
        total_endpoints = len(self._endpoint_stats)
        growing = self.get_growing_endpoints()

        return {
            "total_requests_profiled": total_requests,
            "total_endpoints_tracked": total_endpoints,
            "growing_endpoints": len(growing),
            "top_5_consumers": self.get_top_consumers(limit=5),
        }
