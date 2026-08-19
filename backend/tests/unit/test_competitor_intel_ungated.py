# =============================================================================
# Stratum AI - Competitor Intelligence, un-gated
# =============================================================================
"""Competitor Intelligence ships on, serving only what it can actually source.

The flag was off because the refresh worker fabricated spend/impressions/CTR
with ``random.randint``. That stopped being true when ``_apply_scan_result``
was rewritten to write "honest null rather than the fabricated random numbers
this used to write" -- but the rationale was never updated, so four separate
places went on asserting a reason that no longer held.

Turning the flag on without changing anything else would have been worse than
leaving it off, because the surface still manufactured zeros from columns
nothing writes:

* ``GET /competitors/share-of-voice`` computed
  ``total_market = sum(c.estimated_traffic or 0)`` over a column no code path
  populates, so it reported a market size of 0 as a measurement.
* ``GET /competitors/{id}/keywords`` returned ``[]`` from ``top_keywords``,
  indistinguishable from "this competitor buys no keywords".
* ``CompetitorResponse`` exposed eight fields nothing can fill, and the list
  route ordered by one of them.

So the split is drawn where the data is. Sourceable today, free: website
metadata, social links, and the Meta Ad Library active-ad count and platforms.
Not sourceable without a paid ad-intelligence provider: traffic, share of
voice, keywords, ad-spend estimates, category rank. The second group is gone
from the API rather than served as nulls that a caller will coerce to zero --
which is exactly what the frontend did.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.api.v1.endpoints import competitors as competitors_endpoint
from app.base_schemas import CompetitorResponse
from app.core.config import settings
from app.workers.celery_app import celery_app

pytestmark = pytest.mark.unit

BACKEND_DIR = Path(__file__).resolve().parents[2]

# Columns on CompetitorBenchmark that no code path writes. They need a paid
# ad-intelligence provider (Similarweb / SEMrush / DataForSEO); until one is
# wired they are permanently NULL, and a NULL that reaches a dashboard becomes
# a zero.
UNSOURCEABLE = {
    "estimated_traffic",
    "traffic_trend",
    "top_keywords",
    "paid_keywords_count",
    "organic_keywords_count",
    "share_of_voice",
    "category_rank",
    "estimated_ad_spend_cents",
    "meta_keywords",
}

# What scan_competitor actually produces, via website scrape + Ad Library.
SOURCEABLE = {
    "meta_title",
    "meta_description",
    "social_links",
    "detected_ad_platforms",
    "ad_creatives_count",
    "data_source",
    "last_fetched_at",
    "fetch_error",
}


def _routes() -> set[str]:
    return {route.path for route in competitors_endpoint.router.routes}


def _source(relative: str) -> str:
    return (BACKEND_DIR / relative).read_text(encoding="utf-8")


# =============================================================================
# The response carries only what a source fills
# =============================================================================
class TestResponseShape:
    def test_omits_every_metric_nothing_can_fill(self):
        """A null that reaches a dashboard becomes a zero.

        The frontend proved it: ``Number(c.shareOfVoice ?? 0)``. Serving these
        as nulls and asking every caller to distinguish "unknown" from "zero"
        is a contract nobody keeps, so they are not served.
        """
        leaked = UNSOURCEABLE & set(CompetitorResponse.model_fields)

        assert leaked == set(), (
            f"CompetitorResponse still exposes {sorted(leaked)}, which no code "
            "path populates. Remove them or wire a provider that fills them."
        )

    def test_keeps_everything_the_scanner_does_fill(self):
        """The point is a smaller honest surface, not a smaller surface."""
        missing = SOURCEABLE - set(CompetitorResponse.model_fields)

        assert missing == set(), f"dropped fields the scanner writes: {sorted(missing)}"


# =============================================================================
# Routes that could only ever manufacture a number
# =============================================================================
class TestRoutes:
    def test_share_of_voice_route_is_gone(self):
        """It summed a column nothing writes and called the result a market."""
        assert "/share-of-voice" not in _routes()

    def test_keywords_route_is_gone(self):
        """``top_keywords`` is never written; the route only ever returned []."""
        assert not any(path.endswith("/keywords") for path in _routes())

    def test_the_routes_that_work_are_still_there(self):
        paths = _routes()

        assert "" in paths or "/" in paths
        assert "/{competitor_id}" in paths
        assert "/{competitor_id}/refresh" in paths

    def test_scan_route_exists(self):
        """AddCompetitorModal has always POSTed to /competitors/scan.

        The route was never implemented, so the modal's "scan" preview 404'd —
        invisible while the whole router was 503, and the first thing a user
        would hit once it was not. ``scan_competitor`` already returns exactly
        the shape the frontend types, so this is wiring, not new capability.
        """
        assert "/scan" in _routes()

    def test_list_is_not_ordered_by_a_column_nothing_writes(self):
        """Ordering by share_of_voice sorted every row by NULL.

        Harmless-looking, and it made the list order arbitrary while implying
        it was ranked by competitive prominence.
        """
        source = _source("app/api/v1/endpoints/competitors.py")

        assert "CompetitorBenchmark.share_of_voice" not in source
        assert "CompetitorBenchmark.ad_creatives_count.desc()" in source


# =============================================================================
# The gate
# =============================================================================
class TestGate:
    def test_flag_defaults_on(self):
        assert settings.feature_competitor_intel is True

    async def test_disabled_still_returns_503(self, monkeypatch):
        """The gate stays wired so a deployment can turn it back off."""
        from fastapi import HTTPException

        monkeypatch.setattr(settings, "feature_competitor_intel", False)
        with pytest.raises(HTTPException) as exc:
            await competitors_endpoint.require_competitor_intel_enabled()

        assert exc.value.status_code == 503

    def test_refresh_is_scheduled(self):
        """A surface that never refreshes goes stale silently."""
        assert "refresh-competitor-data" in celery_app.conf.beat_schedule


# =============================================================================
# Nothing fabricates
# =============================================================================
class TestNothingFabricates:
    """The invariant the flag was really protecting.

    An earlier draft of these tests grepped the config and router prose for
    "random.randint" to catch the stale rationale. That is the wrong thing to
    pin: it fails on a comment *explaining* that the fabrication is gone, and
    it passes for any amount of fabrication that avoids the phrase. What
    matters is whether a code path can put an unsourced number in front of a
    user, so that is what these assert.
    """

    def test_the_scanner_writes_no_column_it_cannot_source(self):
        """``_apply_scan_result`` is the only writer; it must stay honest.

        Its docstring already promises "honest null rather than the fabricated
        random numbers this used to write". This makes the promise executable —
        the flag is on now, so a regression here reaches production rather than
        a 503.
        """
        source = _source("app/workers/tasks/competitors.py")
        assignments = set(re.findall(r"competitor\.([a-z_]+)\s*=", source))

        fabricated = assignments & UNSOURCEABLE

        assert fabricated == set(), (
            f"the competitor worker now writes {sorted(fabricated)}, which no "
            "source fills. If a provider was wired, add the columns back to "
            "CompetitorResponse in the same change."
        )

    def test_the_worker_does_not_reach_for_a_random_number(self):
        source = _source("app/workers/tasks/competitors.py")

        assert not re.search(r"^\s*import random", source, re.MULTILINE)
        assert "random." not in source

    def test_the_mock_market_proxy_is_not_wired_to_anything(self):
        """``market_proxy.MockService`` still generates seeded fake metrics.

        It is dead code — imported in services/__init__.py and called by no
        endpoint or task. Harmless while that stays true, and a fabricated
        benchmark source the moment it does not.
        """
        callers = [
            path
            for path in (BACKEND_DIR / "app").rglob("*.py")
            if path.name not in ("market_proxy.py", "__init__.py")
            and "MarketIntelligenceService" in path.read_text(encoding="utf-8")
        ]

        assert callers == [], (
            "market_proxy's mock strategy is now reachable from "
            f"{[p.name for p in callers]}; it fabricates metrics with a seeded RNG."
        )
