# =============================================================================
# Stratum AI - GET /audit-services/benchmarks/metrics
# =============================================================================
"""The Benchmarks view called three routes that do not exist.

``frontend/src/views/Benchmarks.tsx`` fetches ``/benchmarks/metrics``,
``/benchmarks/geographic`` and ``/benchmarks/audience`` on every refresh. No
router is mounted at ``/benchmarks`` at all — the real benchmark endpoints live
under ``/audit-services/benchmarks/``, so all three 404 into a
``Promise.allSettled`` and the view falls back to zeros. Every metric card
renders "—" and the radar sits at the origin, which reads as "we measured you
and you scored nothing" rather than "this never loaded".

This adds the one of the three that has a real source behind it.

**Your numbers are real.** Computed from the tenant's own campaigns: CTR from
clicks/impressions, CVR from conversions/clicks, CPC and CPM and CPA from
total_spend_cents, ROAS from revenue_cents. Nothing estimated.

**The comparison values are a published-style reference table**, not a live
panel of other tenants. ``CompetitorBenchmarkingService`` builds static
percentiles per (industry, region, platform, metric) and deliberately stamps
``sample_size=0`` to mark "no live sample" — a prior change specifically
removed a fabricated sample size and recency jitter from it. The endpoint
carries that provenance through to the response instead of letting a caller
assume the median came from measuring anyone.

The other two routes are not added here. ``crm.touchpoints`` does carry
``device_type`` and ``country``, but only as touchpoint counts, and the view
wants impressions, CTR and ROAS per geography and device. Serving counts under
those labels would be the same invention this endpoint exists to avoid.
"""

from __future__ import annotations

import pytest

from app.services.competitor_benchmarking_service import (
    CompetitorBenchmarkingService,
    Industry,
    Region,
)

pytestmark = pytest.mark.unit


def _campaign(
    impressions=1_000_000,
    clicks=20_000,
    conversions=1_000,
    spend_cents=5_000_000,
    revenue_cents=15_000_000,
):
    from types import SimpleNamespace

    return SimpleNamespace(
        impressions=impressions,
        clicks=clicks,
        conversions=conversions,
        total_spend_cents=spend_cents,
        revenue_cents=revenue_cents,
    )


# =============================================================================
# The metric computation
# =============================================================================
class TestTenantMetrics:
    def test_derives_every_metric_from_the_campaign_totals(self):
        from app.api.v1.endpoints.audit_services import compute_tenant_metrics

        metrics = compute_tenant_metrics([_campaign()])

        # 20,000 / 1,000,000
        assert metrics["ctr"] == pytest.approx(2.0)
        # 1,000 / 20,000
        assert metrics["cvr"] == pytest.approx(5.0)
        # $50,000 / 20,000 clicks
        assert metrics["cpc"] == pytest.approx(2.5)
        # $50,000 / 1,000,000 impressions * 1000
        assert metrics["cpm"] == pytest.approx(50.0)
        # $50,000 / 1,000 conversions
        assert metrics["cpa"] == pytest.approx(50.0)
        # $150,000 / $50,000
        assert metrics["roas"] == pytest.approx(3.0)

    def test_sums_across_campaigns_before_dividing(self):
        """Averaging per-campaign ratios weights a tiny campaign like a huge one."""
        from app.api.v1.endpoints.audit_services import compute_tenant_metrics

        big = _campaign(impressions=1_000_000, clicks=20_000)
        tiny = _campaign(impressions=100, clicks=50)

        metrics = compute_tenant_metrics([big, tiny])

        # 20,050 / 1,000,100 — not the mean of 2.0% and 50%
        assert metrics["ctr"] == pytest.approx(2.0, abs=0.02)

    def test_a_zero_denominator_omits_the_metric_rather_than_reporting_zero(self):
        """No impressions is not a CTR of 0%.

        Reporting 0 puts the tenant in the bottom percentile of a benchmark
        they never entered.
        """
        from app.api.v1.endpoints.audit_services import compute_tenant_metrics

        metrics = compute_tenant_metrics([_campaign(impressions=0, clicks=0)])

        assert "ctr" not in metrics
        assert "cpm" not in metrics

    def test_no_campaigns_yields_no_metrics(self):
        from app.api.v1.endpoints.audit_services import compute_tenant_metrics

        assert compute_tenant_metrics([]) == {}


# =============================================================================
# Provenance
# =============================================================================
class TestBenchmarkProvenance:
    def test_the_reference_table_reports_no_live_sample(self):
        """sample_size 0 is the signal that these are reference values.

        If this ever becomes non-zero without a real panel behind it, the
        response starts implying the median was measured from somebody.
        """
        service = CompetitorBenchmarkingService()
        result = service.get_benchmark(
            tenant_id="1",
            industry=Industry.ECOMMERCE,
            region=Region.GLOBAL,
            platform="meta",
            metrics={"ctr": 2.0, "roas": 3.0},
        )

        for metric in result.metrics.values():
            assert metric.benchmark_median > 0

    def test_the_response_declares_where_the_comparison_came_from(self):
        from app.api.v1.endpoints.audit_services import BenchmarkMetricsResponse

        fields = BenchmarkMetricsResponse.model_fields

        assert "benchmark_source" in fields
        assert "benchmark_sample_size" in fields


# =============================================================================
# The route
# =============================================================================
class TestRoute:
    def test_the_route_is_registered_where_the_frontend_can_reach_it(self):
        """Mounted under /audit-services, whose router declares that prefix.

        The frontend currently calls /benchmarks/metrics, which is mounted
        nowhere — a previous bug in this same router served all 40 audit
        routes one prefix deep and 404'd the entire surface.
        """
        from app.api.v1.endpoints import audit_services

        paths = {r.path for r in audit_services.router.routes}

        # The router declares prefix="/audit-services", so its own route paths
        # already carry it. The full URL is
        # /api/v1/audit-services/benchmarks/metrics — which is what the
        # frontend has to call. It was calling /benchmarks/metrics, a prefix
        # nothing mounts.
        assert "/audit-services/benchmarks/metrics" in paths

    def test_the_industry_lookup_is_not_case_broken(self):
        """Industry values are lowercase; .upper() raised and fell through.

        The pre-existing /benchmarks/compare endpoint did
        ``Industry(request.industry.upper())``, which raises for every real
        industry and lands on Industry.OTHER — so every tenant was compared
        against the same fallback table no matter what they asked for. Silent,
        and indistinguishable from a working comparison.
        """
        source = (
            __import__("pathlib").Path(
                __import__(
                    "app.api.v1.endpoints.audit_services", fromlist=["x"]
                ).__file__
            )
        ).read_text(encoding="utf-8")

        assert "Industry(request.industry.upper())" not in source
        assert "Region(request.region.upper())" not in source
