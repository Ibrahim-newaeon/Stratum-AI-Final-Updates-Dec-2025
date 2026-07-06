# =============================================================================
# Stratum AI - Dashboard Endpoint Integration Tests
# =============================================================================
"""Integration tests for the main dashboard API under ``/api/v1/dashboard/...``:
overview KPIs, campaign performance, recommendations, activity feed,
quick-actions, and the signal-health summary. All routes authenticate via
``get_current_user``.

NOTE: run with the session-scoped event loop the CI uses, e.g.
``-o asyncio_default_test_loop_scope=session`` — multiple authenticated
requests per module rely on a single consistent loop.
"""

from datetime import date, timedelta

import pytest
import pytest_asyncio
from httpx import AsyncClient

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]

_BASE = "/api/v1/dashboard"

_GETS = [
    "/overview",
    "/campaigns",
    "/recommendations",
    "/activity",
    "/quick-actions",
    "/signal-health",
    # Intelligence / briefing surfaces (all DB-backed, no LLM/external calls).
    "/morning-briefing",
    "/signal-recovery",
    "/predictive-budget",
    "/ai-report",
    "/churn-prevention",
    "/settings/metric-visibility",
    "/anomaly-narratives",
    "/notifications-prioritized",
    "/cross-platform-optimizer",
    "/audience-lifecycle",
]


# =============================================================================
# Fixtures — seeded data for data-dependent branches
# =============================================================================


@pytest_asyncio.fixture
async def seeded_campaigns(db_session, test_tenant) -> list[dict]:
    """Seed unified ``Campaign`` rows across the ROAS recommendation buckets.

    Buckets: scale (ROAS 4.0), fix (0.4), watch (1.2), stable/skip (2.0),
    and a paused zero-spend campaign (no recommendation).
    """
    from app.models import AdPlatform, Campaign, CampaignStatus

    specs = [
        # (name, platform, status, spend_cents, revenue_cents, conv, imp, clicks)
        (
            "Scale Meta",
            AdPlatform.META,
            CampaignStatus.ACTIVE,
            1_000_000,
            4_000_000,
            200,
            100_000,
            2_000,
        ),
        (
            "Fix Google",
            AdPlatform.GOOGLE,
            CampaignStatus.ACTIVE,
            500_000,
            200_000,
            10,
            50_000,
            400,
        ),
        (
            "Watch TikTok",
            AdPlatform.TIKTOK,
            CampaignStatus.ACTIVE,
            100_000,
            120_000,
            12,
            20_000,
            300,
        ),
        (
            "Stable Meta",
            AdPlatform.META,
            CampaignStatus.ACTIVE,
            100_000,
            200_000,
            20,
            10_000,
            150,
        ),
        ("Paused Zero", AdPlatform.META, CampaignStatus.PAUSED, 0, 0, 0, 0, 0),
    ]

    rows = []
    for i, (name, platform, c_status, spend, revenue, conv, imp, clicks) in enumerate(
        specs
    ):
        campaign = Campaign(
            tenant_id=test_tenant["id"],
            platform=platform,
            external_id=f"ext-dash-{i}",
            account_id="acct-dash-1",
            name=name,
            status=c_status,
            total_spend_cents=spend,
            revenue_cents=revenue,
            conversions=conv,
            impressions=imp,
            clicks=clicks,
        )
        db_session.add(campaign)
        rows.append(campaign)

    await db_session.flush()

    return [
        {
            "id": c.id,
            "name": c.name,
            "platform": c.platform.value,
            "status": c.status.value,
        }
        for c in rows
    ]


@pytest_asyncio.fixture
async def seeded_metrics(db_session, test_tenant, seeded_campaigns) -> dict:
    """Seed CampaignMetric time-series rows (today + 2 days ago) for the first
    campaign, so period-scoped aggregations return non-zero values."""
    from app.models import CampaignMetric

    campaign_id = seeded_campaigns[0]["id"]
    today = date.today()

    m1 = CampaignMetric(
        tenant_id=test_tenant["id"],
        campaign_id=campaign_id,
        date=today,
        spend_cents=15_000,
        revenue_cents=60_000,
        conversions=5,
        impressions=1_000,
        clicks=50,
    )
    m2 = CampaignMetric(
        tenant_id=test_tenant["id"],
        campaign_id=campaign_id,
        date=today - timedelta(days=2),
        spend_cents=10_000,
        revenue_cents=20_000,
        conversions=3,
        impressions=500,
        clicks=30,
    )
    db_session.add_all([m1, m2])
    await db_session.flush()

    return {
        "campaign_id": campaign_id,
        "total_spend": 250.0,
        "total_revenue": 800.0,
        "total_conversions": 8,
        "total_impressions": 1_500,
        "total_clicks": 80,
    }


@pytest_asyncio.fixture
async def seeded_audit_logs(db_session, test_tenant, test_user) -> int:
    """Seed one AuditLog per action type to walk every activity-feed branch."""
    from app.base_models import AuditAction, AuditLog

    actions = [
        (AuditAction.LOGIN, "session", None),
        (AuditAction.LOGOUT, "session", None),
        (AuditAction.CREATE, "campaign", "1"),
        (AuditAction.UPDATE, "campaign", "1"),
        (AuditAction.DELETE, "campaign", "2"),
        (AuditAction.EXPORT, "report", "3"),
    ]
    for action, resource_type, resource_id in actions:
        db_session.add(
            AuditLog(
                tenant_id=test_tenant["id"],
                user_id=test_user["id"],
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
            )
        )
    await db_session.flush()
    return len(actions)


@pytest_asyncio.fixture
async def seeded_cdp_profiles(db_session, test_tenant) -> int:
    """Seed CDP profiles across lifecycle stages for audience-lifecycle."""
    from datetime import datetime
    from datetime import timedelta as td
    from datetime import timezone

    from app.models.cdp import CDPProfile

    now = datetime.now(timezone.utc)
    specs = [
        # (stage, revenue, purchases, last_seen, previous_stage)
        ("anonymous", 0, 0, now, None),
        ("known", 0, 0, now, "anonymous"),
        ("customer", 450.0, 3, now, "known"),
        ("customer", 120.0, 1, now - td(days=30), "known"),
        ("churned", 0, 0, now - td(days=90), "customer"),
    ]
    for stage, revenue, purchases, last_seen, prev in specs:
        db_session.add(
            CDPProfile(
                tenant_id=test_tenant["id"],
                lifecycle_stage=stage,
                total_revenue=revenue,
                total_events=10,
                total_sessions=4,
                total_purchases=purchases,
                first_seen_at=now - td(days=120),
                last_seen_at=last_seen,
                computed_traits=({"previous_lifecycle_stage": prev} if prev else {}),
            )
        )
    await db_session.flush()
    return len(specs)


class TestAuth:
    @pytest.mark.parametrize("path", ["/overview", "/recommendations"])
    async def test_requires_auth(self, client: AsyncClient, path):
        resp = await client.get(f"{_BASE}{path}")
        assert resp.status_code in {401, 403}


class TestSmoke:
    @pytest.mark.parametrize("path", _GETS)
    async def test_get_returns_200(self, authenticated_client: AsyncClient, path):
        resp = await authenticated_client.get(f"{_BASE}{path}")
        assert resp.status_code == 200, f"{path}: {resp.text}"
        assert resp.json()["success"] is True


class TestOverview:
    async def test_overview_period_filter(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(
            f"{_BASE}/overview", params={"period": "30d"}
        )
        assert resp.status_code == 200, resp.text
        assert "data" in resp.json()

    @pytest.mark.parametrize(
        "period", ["today", "yesterday", "90d", "this_month", "last_month"]
    )
    async def test_overview_all_periods(
        self, authenticated_client: AsyncClient, period
    ):
        resp = await authenticated_client.get(
            f"{_BASE}/overview", params={"period": period}
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["period"] == period
        assert "start" in data["date_range"] and "end" in data["date_range"]

    async def test_overview_custom_period(self, authenticated_client: AsyncClient):
        start = (date.today() - timedelta(days=10)).isoformat()
        end = date.today().isoformat()
        resp = await authenticated_client.get(
            f"{_BASE}/overview",
            params={"period": "custom", "start_date": start, "end_date": end},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["date_range"] == {"start": start, "end": end}
        # Custom period label is rendered from the dates
        assert data["period"] == "custom"

    async def test_overview_custom_without_dates_falls_back(
        self, authenticated_client: AsyncClient
    ):
        resp = await authenticated_client.get(
            f"{_BASE}/overview", params={"period": "custom"}
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        # Falls back to the default 7-day window
        start = date.fromisoformat(data["date_range"]["start"])
        end = date.fromisoformat(data["date_range"]["end"])
        assert (end - start).days == 6

    async def test_overview_invalid_period_422(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(
            f"{_BASE}/overview", params={"period": "bogus"}
        )
        assert resp.status_code == 422

    async def test_overview_empty_db_shape(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"{_BASE}/overview")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["has_campaigns"] is False
        assert data["total_campaigns"] == 0
        assert data["signal_health"]["status"] == "unknown"
        assert data["metrics"]["spend"]["value"] == 0
        # All five ad platforms are listed in the breakdown
        assert len(data["platforms"]) == 5

    async def test_overview_with_campaign_data(
        self, authenticated_client: AsyncClient, seeded_campaigns, seeded_metrics
    ):
        resp = await authenticated_client.get(f"{_BASE}/overview")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]

        assert data["has_campaigns"] is True
        assert data["total_campaigns"] == 5
        assert data["active_campaigns"] == 4

        metrics = data["metrics"]
        assert metrics["spend"]["value"] == pytest.approx(seeded_metrics["total_spend"])
        assert metrics["revenue"]["value"] == pytest.approx(
            seeded_metrics["total_revenue"]
        )
        assert metrics["conversions"]["value"] == seeded_metrics["total_conversions"]
        assert metrics["roas"]["value"] == pytest.approx(800.0 / 250.0)
        assert metrics["spend"]["formatted"].startswith("$")

        # Signal health is computed (not "unknown") when campaigns exist
        assert data["signal_health"]["status"] in {"healthy", "at_risk", "critical"}
        assert 0 <= data["signal_health"]["overall_score"] <= 100

        meta = next(p for p in data["platforms"] if p["platform"] == "meta")
        assert meta["campaigns_count"] == 3
        assert meta["spend"] == pytest.approx(11_000.0)


class TestCampaigns:
    async def test_list_with_recommendations(
        self, authenticated_client: AsyncClient, seeded_campaigns
    ):
        resp = await authenticated_client.get(f"{_BASE}/campaigns")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["total"] == 5
        assert len(data["campaigns"]) == 5

        by_name = {c["name"]: c for c in data["campaigns"]}
        assert by_name["Scale Meta"]["recommendation"] == "scale"
        assert by_name["Fix Google"]["recommendation"] == "fix"
        assert by_name["Stable Meta"]["recommendation"] == "watch"
        assert by_name["Paused Zero"]["recommendation"] is None
        assert by_name["Paused Zero"]["roas"] is None
        assert by_name["Scale Meta"]["roas"] == pytest.approx(4.0)
        assert by_name["Scale Meta"]["trend"] == "up"

    async def test_platform_filter(
        self, authenticated_client: AsyncClient, seeded_campaigns
    ):
        resp = await authenticated_client.get(
            f"{_BASE}/campaigns", params={"platform": "meta"}
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["total"] == 3
        assert all(c["platform"] == "meta" for c in data["campaigns"])

    async def test_unknown_platform_filter_ignored(
        self, authenticated_client: AsyncClient, seeded_campaigns
    ):
        resp = await authenticated_client.get(
            f"{_BASE}/campaigns", params={"platform": "myspace"}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["total"] == 5

    async def test_status_filter(
        self, authenticated_client: AsyncClient, seeded_campaigns
    ):
        resp = await authenticated_client.get(
            f"{_BASE}/campaigns", params={"status": "paused"}
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["total"] == 1
        assert data["campaigns"][0]["name"] == "Paused Zero"

    async def test_unknown_status_filter_ignored(
        self, authenticated_client: AsyncClient, seeded_campaigns
    ):
        resp = await authenticated_client.get(
            f"{_BASE}/campaigns", params={"status": "exploded"}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["total"] == 5

    async def test_sort_by_name_asc(
        self, authenticated_client: AsyncClient, seeded_campaigns
    ):
        resp = await authenticated_client.get(
            f"{_BASE}/campaigns", params={"sort_by": "name", "sort_order": "asc"}
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        names = [c["name"] for c in data["campaigns"]]
        assert names == sorted(names)
        assert data["sort_by"] == "name"
        assert data["sort_order"] == "asc"

    async def test_unknown_sort_column_falls_back(
        self, authenticated_client: AsyncClient, seeded_campaigns
    ):
        resp = await authenticated_client.get(
            f"{_BASE}/campaigns", params={"sort_by": "not_a_column"}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["total"] == 5

    async def test_pagination(
        self, authenticated_client: AsyncClient, seeded_campaigns
    ):
        resp = await authenticated_client.get(
            f"{_BASE}/campaigns", params={"page": 2, "page_size": 2}
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["total"] == 5
        assert len(data["campaigns"]) == 2
        assert data["page"] == 2
        assert data["page_size"] == 2

    @pytest.mark.parametrize(
        "params", [{"page": 0}, {"page_size": 0}, {"page_size": 101}]
    )
    async def test_invalid_pagination_422(
        self, authenticated_client: AsyncClient, params
    ):
        resp = await authenticated_client.get(f"{_BASE}/campaigns", params=params)
        assert resp.status_code == 422


class TestRecommendations:
    async def test_generated_from_campaign_performance(
        self, authenticated_client: AsyncClient, seeded_campaigns
    ):
        resp = await authenticated_client.get(f"{_BASE}/recommendations")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]

        # scale + fix + watch; the 2.0x ROAS campaign and paused one are skipped
        assert data["total"] == 3
        assert data["by_type"]["scale"] == 1
        assert data["by_type"]["fix"] == 1
        assert data["by_type"]["watch"] == 1
        assert data["by_type"]["pause"] == 0

        # Sorted by confidence descending
        confidences = [r["confidence"] for r in data["recommendations"]]
        assert confidences == sorted(confidences, reverse=True)

        rec = data["recommendations"][0]
        for key in ("id", "type", "entity_id", "entity_name", "platform", "title"):
            assert key in rec
        assert rec["status"] == "pending"

    async def test_type_filter(
        self, authenticated_client: AsyncClient, seeded_campaigns
    ):
        resp = await authenticated_client.get(
            f"{_BASE}/recommendations", params={"type": "scale"}
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["total"] == 1
        assert all(r["type"] == "scale" for r in data["recommendations"])

    async def test_limit(self, authenticated_client: AsyncClient, seeded_campaigns):
        resp = await authenticated_client.get(
            f"{_BASE}/recommendations", params={"limit": 1}
        )
        assert resp.status_code == 200, resp.text
        assert len(resp.json()["data"]["recommendations"]) == 1

    @pytest.mark.parametrize("limit", [0, 51])
    async def test_invalid_limit_422(self, authenticated_client: AsyncClient, limit):
        resp = await authenticated_client.get(
            f"{_BASE}/recommendations", params={"limit": limit}
        )
        assert resp.status_code == 422


class TestRecommendationActions:
    async def test_approve(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            f"{_BASE}/recommendations/rec_123_scale/approve"
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["recommendation_id"] == "rec_123_scale"
        assert data["status"] in {"approved", "queued_for_execution"}

    @pytest.mark.parametrize("bad_id", ["bad", "two_parts"])
    async def test_approve_invalid_id_400(
        self, authenticated_client: AsyncClient, bad_id
    ):
        resp = await authenticated_client.post(
            f"{_BASE}/recommendations/{bad_id}/approve"
        )
        assert resp.status_code == 400

    async def test_reject(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            f"{_BASE}/recommendations/rec_123_fix/reject"
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["status"] == "rejected"
        assert data["recommendation_id"] == "rec_123_fix"

    async def test_approve_requires_auth(self, client: AsyncClient):
        resp = await client.post(f"{_BASE}/recommendations/rec_1_scale/approve")
        assert resp.status_code in {401, 403}


class TestActivity:
    async def test_empty_feed(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"{_BASE}/activity")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["activities"] == []
        assert data["total"] == 0
        assert data["has_more"] is False

    async def test_feed_maps_audit_actions(
        self, authenticated_client: AsyncClient, seeded_audit_logs
    ):
        resp = await authenticated_client.get(f"{_BASE}/activity")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["total"] == seeded_audit_logs
        assert len(data["activities"]) == seeded_audit_logs

        by_title = {a["title"]: a for a in data["activities"]}
        assert by_title["User logged in"]["type"] == "auth"
        assert by_title["Created campaign"]["severity"] == "success"
        assert by_title["Updated campaign"]["severity"] == "info"
        assert by_title["Deleted campaign"]["severity"] == "warning"
        # Fallback branch for non-CRUD actions (export)
        assert by_title["Export report"]["type"] == "system"

    async def test_feed_pagination_has_more(
        self, authenticated_client: AsyncClient, seeded_audit_logs
    ):
        resp = await authenticated_client.get(f"{_BASE}/activity", params={"limit": 2})
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert len(data["activities"]) == 2
        assert data["has_more"] is True

    async def test_feed_offset_beyond_end(
        self, authenticated_client: AsyncClient, seeded_audit_logs
    ):
        resp = await authenticated_client.get(
            f"{_BASE}/activity", params={"offset": 100}
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["activities"] == []
        assert data["has_more"] is False

    async def test_invalid_limit_422(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"{_BASE}/activity", params={"limit": 0})
        assert resp.status_code == 422


class TestQuickActions:
    async def test_new_tenant_gets_setup_actions(
        self, authenticated_client: AsyncClient
    ):
        resp = await authenticated_client.get(f"{_BASE}/quick-actions")
        assert resp.status_code == 200, resp.text
        actions = resp.json()["data"]["actions"]
        ids = [a["id"] for a in actions]
        # No onboarding row seeded → setup prompt is present
        assert "complete_onboarding" in ids
        # The standard actions are always appended
        for expected in ("create_campaign", "view_reports", "manage_rules"):
            assert expected in ids
        for action in actions:
            assert action["label"] and action["icon"] and action["action"]


class TestSignalHealth:
    async def test_empty_tenant_shape(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"{_BASE}/signal-health")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert 0 <= data["overall_score"] <= 100
        assert data["status"] in {"unknown", "healthy", "degraded", "critical"}
        assert isinstance(data["issues"], list)
        assert isinstance(data["autopilot_enabled"], bool)

    async def test_with_campaigns_computes_score(
        self, authenticated_client: AsyncClient, seeded_campaigns
    ):
        resp = await authenticated_client.get(f"{_BASE}/signal-health")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        # Campaigns exist → the computed branch runs (not the "unknown" early return)
        assert data["status"] in {"healthy", "degraded", "critical"}
        assert 0 <= data["overall_score"] <= 100


class TestExport:
    async def test_csv_empty_db(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(f"{_BASE}/export", json={})
        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"].startswith("text/csv")
        assert "attachment" in resp.headers["content-disposition"]
        assert "=== METRICS SUMMARY ===" in resp.text

    async def test_csv_with_campaigns(
        self, authenticated_client: AsyncClient, seeded_campaigns, seeded_metrics
    ):
        resp = await authenticated_client.post(
            f"{_BASE}/export", json={"format": "csv", "period": "7d"}
        )
        assert resp.status_code == 200, resp.text
        body = resp.text
        assert "=== CAMPAIGNS ===" in body
        assert "Scale Meta" in body
        # scale (ROAS 4.0) and fix (ROAS 0.4) recommendations from all-time totals
        assert "=== RECOMMENDATIONS ===" in body
        assert "scale" in body
        assert "fix" in body

    async def test_json_format(
        self, authenticated_client: AsyncClient, seeded_campaigns, seeded_metrics
    ):
        resp = await authenticated_client.post(
            f"{_BASE}/export", json={"format": "json", "period": "30d"}
        )
        assert resp.status_code == 200, resp.text
        assert resp.headers["content-type"].startswith("application/json")
        payload = resp.json()
        assert payload["period"] == "30d"
        assert "export_date" in payload and "date_range" in payload
        assert payload["metrics"]["total_spend"] == pytest.approx(
            seeded_metrics["total_spend"]
        )
        assert len(payload["campaigns"]) == 5
        rec_types = {r["type"] for r in payload["recommendations"]}
        assert {"scale", "fix"} <= rec_types

    async def test_json_sections_excluded(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            f"{_BASE}/export",
            json={
                "format": "json",
                "include_campaigns": False,
                "include_metrics": False,
                "include_recommendations": False,
            },
        )
        assert resp.status_code == 200, resp.text
        payload = resp.json()
        assert "metrics" not in payload
        assert "campaigns" not in payload
        assert "recommendations" not in payload

    async def test_invalid_format_422(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.post(
            f"{_BASE}/export", json={"format": "xlsx"}
        )
        assert resp.status_code == 422

    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.post(f"{_BASE}/export", json={})
        assert resp.status_code in {401, 403}


class TestMetricVisibility:
    async def test_get_defaults(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"{_BASE}/settings/metric-visibility")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["hidden_metrics"] == []
        assert len(data["available_metrics"]) == 11

    async def test_patch_roundtrip(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.patch(
            f"{_BASE}/settings/metric-visibility",
            json={"hidden_metrics": ["cpc", "cpm"]},
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["hidden_metrics"] == ["cpc", "cpm"]

        # Persisted: GET reflects the update
        resp = await authenticated_client.get(f"{_BASE}/settings/metric-visibility")
        assert resp.json()["data"]["hidden_metrics"] == ["cpc", "cpm"]

        # And the overview surfaces the same setting
        resp = await authenticated_client.get(f"{_BASE}/overview")
        assert resp.json()["data"]["hidden_metrics"] == ["cpc", "cpm"]

    async def test_patch_clears_with_empty_list(
        self, authenticated_client: AsyncClient
    ):
        resp = await authenticated_client.patch(
            f"{_BASE}/settings/metric-visibility", json={"hidden_metrics": []}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["hidden_metrics"] == []

    async def test_patch_invalid_key_400(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.patch(
            f"{_BASE}/settings/metric-visibility",
            json={"hidden_metrics": ["not_a_metric"]},
        )
        assert resp.status_code == 400
        assert "not_a_metric" in resp.json()["detail"]

    async def test_patch_missing_body_422(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.patch(
            f"{_BASE}/settings/metric-visibility", json={}
        )
        assert resp.status_code == 422

    async def test_patch_requires_auth(self, client: AsyncClient):
        resp = await client.patch(
            f"{_BASE}/settings/metric-visibility", json={"hidden_metrics": []}
        )
        assert resp.status_code in {401, 403}


class TestMorningBriefing:
    async def test_with_campaigns(
        self, authenticated_client: AsyncClient, seeded_campaigns
    ):
        resp = await authenticated_client.get(f"{_BASE}/morning-briefing")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]

        assert data["date"] == date.today().isoformat()
        assert data["greeting"]
        assert data["summary_narrative"]
        assert data["portfolio_health"] in {
            "strong",
            "steady",
            "needs_attention",
            "critical",
        }
        assert data["active_campaigns"] == 4
        assert data["total_spend"] > 0
        # Active campaigns → at least one scale candidate action
        assert data["scale_candidates"] >= 1
        assert len(data["actions_today"]) >= 1
        assert isinstance(data["top_changes"], list)
        assert 0 <= data["signal_score"] <= 100


class TestAnomalyNarratives:
    async def test_with_campaigns(
        self, authenticated_client: AsyncClient, seeded_campaigns
    ):
        resp = await authenticated_client.get(f"{_BASE}/anomaly-narratives")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert "executive_summary" in data
        assert data["portfolio_risk"] in {"low", "medium", "high", "critical"}


class TestSignalRecovery:
    async def test_with_campaigns(
        self, authenticated_client: AsyncClient, seeded_campaigns
    ):
        resp = await authenticated_client.get(f"{_BASE}/signal-recovery")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert "status" in data
        assert 0 <= data["overall_health_score"] <= 100
        assert isinstance(data["has_active_recovery"], bool)


class TestPredictiveBudget:
    async def test_with_campaigns(
        self, authenticated_client: AsyncClient, seeded_campaigns
    ):
        resp = await authenticated_client.get(f"{_BASE}/predictive-budget")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert "summary" in data
        assert "trust_gate_status" in data
        assert isinstance(data["autopilot_eligible"], bool)
        # 4 campaigns with spend > 0 are analyzed (zero-spend one is skipped)
        assert data["total_campaigns_analyzed"] == 4


class TestAIReport:
    async def test_with_campaigns(
        self, authenticated_client: AsyncClient, seeded_campaigns
    ):
        resp = await authenticated_client.get(f"{_BASE}/ai-report")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["report_title"]
        assert data["executive_summary"]
        assert data["health_grade"]


class TestChurnPrevention:
    async def test_with_campaigns(
        self, authenticated_client: AsyncClient, seeded_campaigns
    ):
        resp = await authenticated_client.get(f"{_BASE}/churn-prevention")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["total_campaigns_analyzed"] == 5
        assert "portfolio_risk_level" in data
        assert (
            data["at_risk_count"] + data["critical_count"] + data["healthy_count"]
            <= data["total_campaigns_analyzed"]
        )


class TestNotificationsPrioritized:
    async def test_with_campaigns(
        self, authenticated_client: AsyncClient, seeded_campaigns
    ):
        resp = await authenticated_client.get(f"{_BASE}/notifications-prioritized")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        for key in ("summary", "total_count", "unread_count", "critical_count"):
            assert key in data


class TestCrossPlatformOptimizer:
    @pytest.mark.parametrize("strategy", ["roas_max", "balanced", "volume_max"])
    async def test_strategies(
        self, authenticated_client: AsyncClient, seeded_campaigns, strategy
    ):
        resp = await authenticated_client.get(
            f"{_BASE}/cross-platform-optimizer", params={"strategy": strategy}
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["strategy"] == strategy
        assert "total_budget" in data

    async def test_unknown_strategy_falls_back_to_balanced(
        self, authenticated_client: AsyncClient
    ):
        resp = await authenticated_client.get(
            f"{_BASE}/cross-platform-optimizer", params={"strategy": "yolo"}
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["data"]["strategy"] == "balanced"


class TestAudienceLifecycle:
    async def test_shape(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"{_BASE}/audience-lifecycle")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert "summary" in data
        assert isinstance(data["total_profiles"], int)

    async def test_with_cdp_profiles(
        self, authenticated_client: AsyncClient, seeded_cdp_profiles
    ):
        resp = await authenticated_client.get(f"{_BASE}/audience-lifecycle")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["total_profiles"] == seeded_cdp_profiles
        assert isinstance(data["total_rules"], int)


class TestErrorFallbacks:
    """The overview and signal-health endpoints degrade to a safe empty
    payload (still HTTP 200) when their builder raises a database error."""

    async def test_overview_degrades_gracefully(
        self, authenticated_client: AsyncClient
    ):
        from unittest.mock import patch

        from sqlalchemy.exc import SQLAlchemyError

        with patch(
            "app.api.v1.endpoints.dashboard._build_dashboard_overview",
            side_effect=SQLAlchemyError("boom"),
        ):
            resp = await authenticated_client.get(f"{_BASE}/overview")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["has_campaigns"] is False
        assert data["metrics"]["spend"]["value"] == 0
        assert (
            "Dashboard data temporarily unavailable" in data["signal_health"]["issues"]
        )

    async def test_signal_health_degrades_gracefully(
        self, authenticated_client: AsyncClient
    ):
        from unittest.mock import patch

        from sqlalchemy.exc import SQLAlchemyError

        with patch(
            "app.api.v1.endpoints.dashboard._build_signal_health",
            side_effect=SQLAlchemyError("boom"),
        ):
            resp = await authenticated_client.get(f"{_BASE}/signal-health")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["overall_score"] == 0
        assert data["status"] == "unknown"
        assert "Signal health data temporarily unavailable" in data["issues"]


class TestGoalTracking:
    async def test_with_campaigns(
        self, authenticated_client: AsyncClient, seeded_campaigns
    ):
        resp = await authenticated_client.get(f"{_BASE}/goal-tracking")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["days_total"] > 0
        assert data["days_elapsed"] + data["days_remaining"] <= data["days_total"] + 1
        assert isinstance(data["goals"], list)

    async def test_with_tenant_goal_targets(
        self,
        authenticated_client: AsyncClient,
        db_session,
        test_tenant,
        seeded_campaigns,
    ):
        from sqlalchemy import select

        from app.base_models import Tenant

        tenant = (
            await db_session.execute(
                select(Tenant).where(Tenant.id == test_tenant["id"])
            )
        ).scalar_one()
        tenant.settings = {"goals": {"revenue": 100_000.0, "spend": 50_000.0}}
        await db_session.flush()

        resp = await authenticated_client.get(f"{_BASE}/goal-tracking")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert isinstance(data["goals"], list)
        assert "summary" in data


class TestABTestAnalysis:
    async def test_with_campaigns(
        self, authenticated_client: AsyncClient, seeded_campaigns
    ):
        resp = await authenticated_client.get(f"{_BASE}/ab-test-analysis")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert "summary" in data
        assert isinstance(data["total_tests"], int)


class TestKnowledgeGraph:
    async def test_with_campaigns(
        self, authenticated_client: AsyncClient, seeded_campaigns
    ):
        resp = await authenticated_client.get(f"{_BASE}/knowledge-graph")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert "summary" in data
        assert isinstance(data["nodes"], list)
        assert isinstance(data["edges"], list)
        assert isinstance(data["patterns_discovered"], int)


class TestJourneyMap:
    async def test_with_campaigns(
        self, authenticated_client: AsyncClient, seeded_campaigns
    ):
        resp = await authenticated_client.get(f"{_BASE}/journey-map")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert "summary" in data
        assert isinstance(data["top_paths"], list)


class TestNLFilter:
    async def test_empty_query(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"{_BASE}/nl-filter")
        assert resp.status_code == 200, resp.text
        interp = resp.json()["data"]["interpretation"]
        assert interp["original_query"] == ""
        assert isinstance(interp["parsed_filters"], list)

    async def test_query_with_campaigns(
        self, authenticated_client: AsyncClient, seeded_campaigns
    ):
        query = "show meta campaigns with roas above 2"
        resp = await authenticated_client.get(
            f"{_BASE}/nl-filter", params={"query": query}
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["interpretation"]["original_query"] == query
        assert data["interpretation"]["intent"]
        assert isinstance(data["interpretation"]["parsed_filters"], list)


# =============================================================================
# Intel endpoints previously broken by non-existent attributes (#525)
# =============================================================================


class TestAttributionConfidence:
    """Regression for #525: 500ed on user.current_tenant_id +
    CampaignStatus.DELETED."""

    async def test_empty(self, authenticated_client: AsyncClient):
        resp = await authenticated_client.get(f"{_BASE}/attribution-confidence")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["confidence_label"]
        assert isinstance(data["channels"], list)

    async def test_with_campaigns(
        self, authenticated_client: AsyncClient, seeded_campaigns
    ):
        resp = await authenticated_client.get(f"{_BASE}/attribution-confidence")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert 0 <= data["overall_confidence"] <= 100
        assert isinstance(data["model_comparisons"], list)
        assert isinstance(data["data_quality_metrics"], list)


class TestLTVForecast:
    """Regression for #525 (same broken attributes)."""

    async def test_with_campaigns(
        self, authenticated_client: AsyncClient, seeded_campaigns
    ):
        resp = await authenticated_client.get(f"{_BASE}/ltv-forecast")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["ltv_health"]
        assert isinstance(data["total_customers"], int)
        assert isinstance(data["cohorts"], list)
        assert isinstance(data["segments"], list)


class TestCreativeScoring:
    """Regression for #525 (same broken attributes)."""

    async def test_with_campaigns(
        self, authenticated_client: AsyncClient, seeded_campaigns
    ):
        resp = await authenticated_client.get(f"{_BASE}/creative-scoring")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["overall_grade"]
        assert isinstance(data["creatives"], list)
        assert isinstance(data["total_creatives"], int)


class TestCompetitorIntel:
    """Regression for #525 (same broken attributes)."""

    async def test_with_campaigns(
        self, authenticated_client: AsyncClient, seeded_campaigns
    ):
        resp = await authenticated_client.get(f"{_BASE}/competitor-intel")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["market_position"]
        assert 0 <= data["competitive_pressure"] <= 100
        assert isinstance(data["competitors"], list)


class TestCollaborativeAnnotations:
    """Regression for #525: 500ed on current_user.first_name/last_name
    (CurrentUser only exposes full_name)."""

    async def test_with_campaigns(
        self, authenticated_client: AsyncClient, seeded_campaigns
    ):
        resp = await authenticated_client.get(f"{_BASE}/collaborative-annotations")
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert isinstance(data["annotations"], list)
        assert isinstance(data["active_discussions"], int)
        # Author names derive from CurrentUser.full_name with an
        # email-prefix fallback (the harness hits the fallback: the fixture
        # stores full_name unencrypted so decrypt_pii yields None). Either
        # way every author must have a non-empty name — the #525 bug made
        # this endpoint unreachable entirely.
        assert data["annotations"], "expected seeded campaigns to yield annotations"
        for annotation in data["annotations"]:
            assert annotation["author"]["name"]
