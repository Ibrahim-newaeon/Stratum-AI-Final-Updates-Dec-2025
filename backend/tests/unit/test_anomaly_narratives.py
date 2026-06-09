# =============================================================================
# Stratum AI - Anomaly Narratives unit tests
# =============================================================================
"""Unit tests for app.analytics.logic.anomaly_narratives.

Pure narrative generation over anomaly-detection results, no I/O. Covers value
formatting, percent change, per-anomaly narrative generation, cross-metric
correlation detection, executive summary, portfolio-risk assessment, and the
build_anomaly_narratives entry point.
"""

import pytest

from app.analytics.logic import anomaly_narratives as an
from app.analytics.logic.anomaly_narratives import (
    AnomalyNarrativesResponse,
    build_anomaly_narratives,
    generate_narrative,
)
from app.analytics.logic.types import AlertSeverity, AnomalyResult

pytestmark = pytest.mark.unit


def _anom(
    metric,
    direction="high",
    severity=AlertSeverity.HIGH,
    current=100.0,
    baseline=50.0,
    is_anomaly=True,
    zscore=3.0,
):
    return AnomalyResult(
        metric=metric,
        zscore=zscore,
        severity=severity,
        current_value=current,
        baseline_mean=baseline,
        baseline_std=10.0,
        is_anomaly=is_anomaly,
        direction=direction,
    )


# =============================================================================
# Formatting + pct change
# =============================================================================
class TestHelpers:
    @pytest.mark.parametrize(
        "value,fmt,expected",
        [
            (2_500_000, "currency", "$2.5M"),
            (1_500, "currency", "$1.5K"),
            (42.5, "currency", "$42.50"),
            (3.5, "ratio", "3.50x"),
            (12.3, "percent", "12.3%"),
            (87, "score", "87/100"),
            (2500, "number", "2.5K"),
        ],
    )
    def test_format_value(self, value, fmt, expected):
        assert an._format_value(value, fmt) == expected

    def test_pct_change(self):
        assert an._pct_change(150, 100) == 50.0
        assert an._pct_change(100, 0) == 0.0  # guard


# =============================================================================
# Narrative generation
# =============================================================================
class TestNarrative:
    def test_up_narrative(self):
        n = generate_narrative(
            _anom("spend", direction="high", current=150, baseline=100)
        )
        assert n.direction == "up"
        assert n.change_percent == 50.0
        assert "increased" in n.summary
        assert len(n.likely_causes) <= 3
        assert len(n.recommended_actions) <= 3

    def test_down_narrative(self):
        n = generate_narrative(
            _anom("roas", direction="low", current=2.0, baseline=4.0)
        )
        assert n.direction == "down"
        assert "decreased" in n.summary

    def test_critical_severity_context(self):
        n = generate_narrative(_anom("revenue", severity=AlertSeverity.CRITICAL))
        assert "critical deviation" in n.summary
        assert n.severity == "critical"

    def test_moderate_severity_context(self):
        n = generate_narrative(_anom("ctr", severity=AlertSeverity.MEDIUM))
        assert "moderate deviation" in n.summary


# =============================================================================
# Correlations
# =============================================================================
class TestCorrelations:
    def test_scaling_inefficiency_pattern(self):
        anomalies = [
            _anom("spend", direction="high"),
            _anom("roas", direction="low"),
        ]
        insights = an.detect_correlations(anomalies)
        assert any("Scaling Inefficiency" in c.title for c in insights)

    def test_no_correlation_when_unrelated(self):
        anomalies = [_anom("ctr", direction="high")]
        # a single unrelated anomaly shouldn't trip the paired patterns
        insights = an.detect_correlations(anomalies)
        assert all("Scaling Inefficiency" not in c.title for c in insights)


# =============================================================================
# Executive summary + risk
# =============================================================================
class TestSummaryAndRisk:
    def test_empty_summary(self):
        assert "No significant anomalies" in an.generate_executive_summary([], [])

    def test_summary_mentions_critical(self):
        narratives = [
            generate_narrative(_anom("revenue", severity=AlertSeverity.CRITICAL))
        ]
        summary = an.generate_executive_summary(narratives, [])
        assert "critical anomaly" in summary

    def test_risk_high_with_two_criticals(self):
        narratives = [
            generate_narrative(_anom("revenue", severity=AlertSeverity.CRITICAL)),
            generate_narrative(_anom("spend", severity=AlertSeverity.CRITICAL)),
        ]
        assert an.assess_portfolio_risk(narratives, []) == "high"

    def test_risk_elevated_with_one_critical(self):
        narratives = [
            generate_narrative(_anom("revenue", severity=AlertSeverity.CRITICAL))
        ]
        assert an.assess_portfolio_risk(narratives, []) == "elevated"

    def test_risk_low_when_quiet(self):
        narratives = [generate_narrative(_anom("ctr", severity=AlertSeverity.MEDIUM))]
        assert an.assess_portfolio_risk(narratives, []) == "low"


# =============================================================================
# build_anomaly_narratives (entry point)
# =============================================================================
class TestBuild:
    def test_filters_non_anomalies(self):
        anomalies = [
            _anom("spend", is_anomaly=True),
            _anom("ctr", is_anomaly=False),  # filtered out
        ]
        resp = build_anomaly_narratives(anomalies)
        assert isinstance(resp, AnomalyNarrativesResponse)
        metrics = {n.metric for n in resp.narratives}
        assert "spend" in metrics
        assert "ctr" not in metrics

    def test_empty_quiet_summary(self):
        resp = build_anomaly_narratives([])
        assert resp.narratives == []
        assert "No significant anomalies" in resp.executive_summary

    def test_full_with_correlation(self):
        anomalies = [
            _anom("spend", direction="high", severity=AlertSeverity.HIGH),
            _anom("roas", direction="low", severity=AlertSeverity.CRITICAL),
        ]
        resp = build_anomaly_narratives(anomalies)
        assert len(resp.narratives) == 2
        assert resp.correlations  # scaling inefficiency
        assert resp.portfolio_risk in {"low", "moderate", "elevated", "high"}
