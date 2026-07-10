# =============================================================================
# Stratum AI - Competitor Real-Source Mapping Tests
# =============================================================================
"""
Tests for wiring the competitor refresh worker to the real scraper (Tier 3).

``fetch_competitor_data`` used to write random.randint spend/impressions/CTR.
It now runs ``scan_competitor`` (website scrape + Meta Ad Library) and maps only
genuinely sourced fields via ``_apply_scan_result``; un-sourceable estimates
are left as honest nulls, never fabricated.
"""

from types import SimpleNamespace

from app.workers.tasks.competitors import _apply_scan_result


def _competitor(**kw):
    base = dict(
        domain="rival.com",
        name="Rival Co",
        social_links=None,
        meta_title=None,
        meta_description=None,
        ad_creatives_count=None,
        detected_ad_platforms=None,
        data_source="pending",
        fetch_error=None,
        metrics_history=None,
        # estimates we must NOT fabricate:
        estimated_ad_spend_cents=None,
        estimated_traffic=None,
        share_of_voice=None,
        top_keywords=None,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def _scan(has_ads=True, ad_error=None, scrape_error=None, ad_count=7):
    return {
        "domain": "rival.com",
        "social_links": {"facebook": "https://facebook.com/rival"},
        "meta_title": "Rival Co",
        "meta_description": "We sell things",
        "fb_page_name": "Rival Co",
        "ig_account_name": None,
        "ad_library": {
            "has_ads": has_ads,
            "ad_count": ad_count,
            "ads": (
                [
                    {"platforms": ["facebook", "instagram"]},
                    {"platforms": ["facebook"]},
                ]
                if has_ads
                else []
            ),
            "error": ad_error,
        },
        "scanned_at": "2026-07-11T00:00:00+00:00",
        "scrape_error": scrape_error,
    }


def test_real_ad_library_data_mapped():
    c = _competitor()
    _apply_scan_result(c, _scan())
    assert c.data_source == "meta_ad_library"
    assert c.ad_creatives_count == 7
    assert c.detected_ad_platforms == ["facebook", "instagram"]  # sorted, deduped
    assert c.meta_title == "Rival Co"
    assert c.social_links["facebook"].endswith("/rival")
    assert len(c.metrics_history) == 1
    assert c.metrics_history[0]["active_ads"] == 7


def test_no_token_means_unknown_not_zero():
    c = _competitor()
    _apply_scan_result(c, _scan(has_ads=False, ad_error="no_access_token", ad_count=0))
    # Ad Library couldn't run -> unknown, not a fabricated / misleading zero.
    assert c.ad_creatives_count is None
    assert c.data_source == "website_scrape"
    assert c.fetch_error is None


def test_scrape_failure_marks_unavailable():
    c = _competitor()
    _apply_scan_result(c, _scan(has_ads=False, scrape_error="timeout"))
    assert c.data_source == "unavailable"
    assert c.fetch_error == "timeout"


def test_estimates_never_fabricated():
    c = _competitor()
    _apply_scan_result(c, _scan())
    # These require a paid provider we don't have — must stay honest null.
    assert c.estimated_ad_spend_cents is None
    assert c.estimated_traffic is None
    assert c.share_of_voice is None
    assert c.top_keywords is None


def test_metrics_history_capped_at_30():
    c = _competitor(metrics_history=[{"n": i} for i in range(30)])
    _apply_scan_result(c, _scan())
    assert len(c.metrics_history) == 30
    assert c.metrics_history[-1]["active_ads"] == 7  # newest appended
    assert c.metrics_history[0] == {"n": 1}  # oldest dropped
