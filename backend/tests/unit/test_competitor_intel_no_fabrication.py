# =============================================================================
# Stratum AI - /dashboard/competitor-intel reports only measured signals
# =============================================================================
"""What this endpoint may and may not claim to know.

``build_competitor_intel`` receives one thing: the tenant's own campaigns. It
has no competitor data, no market panel and no ad-intelligence provider. Three
of the things it returned were manufactured from that nothing, and the endpoint
is not behind a feature flag — it renders on the dashboard today.

* ``_generate_competitors`` returned five invented companies — "Apex Digital
  Group", "VeloMedia", "Horizon Ads Co.", "RisePoint Media", "PinPoint Ads" —
  each with an ``estimated_spend`` that is the tenant's own spend times a
  hard-coded multiplier, plus a threat level and a trend. Every tenant saw the
  same five names. CompetitorIntelCard renders them under a "Competitors" tab,
  and that tab is the default.

* ``your_estimated_sov`` was ``total_spend / (total_spend * MARKET_MULTIPLIER)``
  — algebraically ``100 / MARKET_MULTIPLIER``, a constant fixed by platform mix
  alone. A meta-only tenant reads 12.5% at $1k/month and 12.5% at $5M/month.
  ``market_position`` is a threshold over that constant, so it never moved
  either.

* ``estimated_market_spend`` was the tenant's own spend times the same
  multiplier — a restatement, not a measurement.

What survives is real, because it comes from the campaigns actually passed in:
spend, ROAS, CTR and CPM per platform, compared against published industry CPM
averages. That comparison is worth making and is honestly labelled. The rest is
gone rather than relabelled — a "share of voice" that cannot move is not a
weaker measurement, it is not one.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from app.analytics.logic import competitor_intel as ci

pytestmark = pytest.mark.unit

BACKEND_DIR = Path(__file__).resolve().parents[2]
MODULE = BACKEND_DIR / "app" / "analytics" / "logic" / "competitor_intel.py"

INVENTED_NAMES = [
    "Apex Digital Group",
    "VeloMedia",
    "Horizon Ads Co.",
    "RisePoint Media",
    "PinPoint Ads",
]


def campaigns(
    spend: float, platform: str = "meta", cpm: float = 10.0, roas: float = 3.0
):
    """One campaign with the CPM stated directly.

    Impressions are derived so a test can hold CPM fixed while spend varies, or
    the reverse. Passing impressions raw conflates the two — which is how the
    first draft of the score tests below managed to assert both "the score
    responds to CPM" and "the score ignores spend" using inputs where the two
    moved together.
    """
    impressions = int(spend / cpm * 1000)
    return [
        {
            "platform": platform,
            "spend": spend,
            "revenue": spend * roas,
            "conversions": 50,
            "impressions": impressions,
            "clicks": 2_000,
        }
    ]


# =============================================================================
# Invented competitors
# =============================================================================
class TestNoInventedCompetitors:
    def test_no_company_name_survives_in_executable_code(self):
        """Checked against string *values*, not the file text.

        A plain substring search over the source fails on the module docstring,
        which names all five while explaining that they are gone — and would
        equally pass for any new roster that picked different names. Walking
        the AST for non-docstring string constants asks the question that
        matters: can this module still put a company name in a response?
        """
        tree = ast.parse(MODULE.read_text(encoding="utf-8"))
        docstrings = {
            node.body[0].value
            for node in ast.walk(tree)
            if isinstance(
                node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
            )
            and node.body
            and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, ast.Constant)
            and isinstance(node.body[0].value.value, str)
        }
        literals = [
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node not in docstrings
        ]

        present = [n for n in INVENTED_NAMES if any(n in lit for lit in literals)]

        assert present == [], (
            f"{MODULE.name} can still emit invented competitor names: {present}. "
            "There is no source of competitor identities in this endpoint — it "
            "only receives the tenant's own campaigns."
        )

    def test_the_response_does_not_carry_a_competitor_roster(self):
        """Removed rather than emptied.

        An empty ``competitors: []`` would read as "no competitors found",
        which is a different claim from "this endpoint cannot see competitors".
        """
        resp = ci.build_competitor_intel(campaigns(50_000))

        assert not hasattr(resp, "competitors")

    def test_no_generator_remains(self):
        assert not hasattr(ci, "_generate_competitors")


# =============================================================================
# The constants that never moved
# =============================================================================
class TestNoConstantMetrics:
    def test_share_of_voice_is_not_reported(self):
        resp = ci.build_competitor_intel(campaigns(50_000))

        assert not hasattr(resp, "your_estimated_sov")
        assert not hasattr(resp, "market_position")
        assert not hasattr(resp, "estimated_market_spend")

    def test_the_market_multipliers_are_gone(self):
        """Their only job was to turn your own spend into a "market"."""
        assert not hasattr(ci, "MARKET_MULTIPLIERS")

    def test_competition_score_moves_with_a_real_signal(self):
        """CPM pressure is measured, so the score has to respond to it.

        Same spend, same ROAS, five times the CPM. A score that cannot tell
        those apart is not scoring anything. Both sit either side of the
        published meta average ($11), so neither is clamped at the cap.
        """
        cheap = ci.build_competitor_intel(campaigns(50_000, cpm=5.0))
        pricey = ci.build_competitor_intel(campaigns(50_000, cpm=25.0))

        assert (
            pricey.platform_competition[0].competition_score
            > cheap.platform_competition[0].competition_score
        )

    def test_competition_score_ignores_absolute_spend(self):
        """Spending more does not make a platform more competitive.

        The old score folded in ``your_spend / (your_spend * multiplier)``,
        a constant that only shifted every score by the same amount.

        CPM and ROAS are held fixed, so spend is the only thing that differs.
        """
        small = ci.build_competitor_intel(campaigns(1_000, cpm=10.0))
        large = ci.build_competitor_intel(campaigns(1_000_000, cpm=10.0))

        assert small.platform_competition[0].competition_score == pytest.approx(
            large.platform_competition[0].competition_score
        )


# =============================================================================
# What is actually measured
# =============================================================================
class TestMeasuredSignals:
    def test_platform_rows_report_the_campaign_figures_given(self):
        resp = ci.build_competitor_intel(campaigns(50_000, cpm=50.0))
        row = resp.platform_competition[0]

        assert row.your_spend == pytest.approx(50_000)
        assert row.your_roas == pytest.approx(3.0)
        # 2,000 clicks / 1,000,000 impressions
        assert row.your_ctr == pytest.approx(0.2)
        assert row.your_cpm == pytest.approx(50.0)

    def test_cpm_is_labelled_as_ours_not_the_market(self):
        """It is computed from the tenant's own spend and impressions.

        The field was called ``estimated_market_cpm``, which claims a
        measurement of what everyone else pays.
        """
        row = ci.build_competitor_intel(campaigns(50_000)).platform_competition[0]

        assert hasattr(row, "your_cpm")
        assert not hasattr(row, "estimated_market_cpm")

    def test_published_benchmarks_are_labelled_as_published(self):
        """CPM_BENCHMARKS are industry averages, not something we measured.

        Keeping them is fine — comparing your CPM to a published average is a
        real and useful thing to do. Presenting them as observed market data
        is not.
        """
        source = MODULE.read_text(encoding="utf-8")
        head = source[: source.index("CPM_BENCHMARKS")]

        assert re.search(r"published|industry average", head, re.IGNORECASE)

    def test_empty_campaigns_say_so(self):
        resp = ci.build_competitor_intel([])

        assert resp.platform_competition == []
        assert "No campaign data" in resp.summary
