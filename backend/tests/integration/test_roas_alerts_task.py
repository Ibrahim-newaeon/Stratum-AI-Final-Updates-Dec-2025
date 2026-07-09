# =============================================================================
# Stratum AI - ROAS Alert Task Integration Tests
# =============================================================================
"""
Integration tests for ``generate_roas_alerts`` and its dispatch from
``run_all_tenant_predictions``.

These guard the regression where the task called ``detect_anomalies`` with a
signature it never had (``campaign_id=``/``tenant_id=``/``metrics=``) and read
dict keys off ``AnomalyResult`` objects — every campaign raised ``TypeError``,
which was swallowed, so the task silently emitted zero alerts forever and was
never dispatched by the beat fan-out.

The task uses ``SyncSessionLocal`` against the test DB, so rows are committed
via the sync engine (mirroring ``test_apply_actions_task``) and cleaned up in
teardown. WebSocket publishing (Redis pub/sub) is mocked.
"""

import uuid
from datetime import date, timedelta
from typing import Any, List
from unittest.mock import patch

import pytest
from sqlalchemy.orm import Session

from app.base_models import (
    AdPlatform,
    Campaign,
    CampaignMetric,
    CampaignStatus,
    Tenant,
)
from app.workers.tasks import ml as ml_mod

pytestmark = pytest.mark.integration


@pytest.fixture
def campaign_env(sync_engine):
    """A committed tenant + an ``add_campaign`` factory that seeds a campaign
    with a daily ``campaign_metrics`` series. Everything is torn down after."""
    session = Session(bind=sync_engine)
    tenant = Tenant(
        name="ROAS Alert Tenant",
        slug=f"roas-alert-{uuid.uuid4().hex[:10]}",
    )
    session.add(tenant)
    session.commit()

    created_campaign_ids: List[int] = []

    def add_campaign(daily: List[dict], status: str = CampaignStatus.ACTIVE) -> int:
        """Seed one active campaign plus one CampaignMetric row per entry in
        ``daily`` (oldest first). Each entry: {spend, revenue, conversions}."""
        campaign = Campaign(
            tenant_id=tenant.id,
            platform=AdPlatform.META,
            external_id=f"ext-{uuid.uuid4().hex[:8]}",
            account_id=f"act-{uuid.uuid4().hex[:8]}",
            name="ROAS Alert Campaign",
            status=status,
        )
        session.add(campaign)
        session.commit()
        created_campaign_ids.append(campaign.id)

        n = len(daily)
        for i, row in enumerate(daily):
            day = date.today() - timedelta(days=(n - 1 - i))
            session.add(
                CampaignMetric(
                    tenant_id=tenant.id,
                    campaign_id=campaign.id,
                    date=day,
                    spend_cents=int(row["spend"] * 100),
                    revenue_cents=int(row["revenue"] * 100),
                    conversions=int(row.get("conversions", 0)),
                )
            )
        session.commit()
        return campaign.id

    yield {"tenant_id": tenant.id, "add_campaign": add_campaign, "session": session}

    # Teardown: metrics cascade on campaign delete (FK ondelete=CASCADE).
    for cid in created_campaign_ids:
        session.query(CampaignMetric).filter(
            CampaignMetric.campaign_id == cid
        ).delete()
        camp = session.get(Campaign, cid)
        if camp is not None:
            session.delete(camp)
    session.commit()
    session.delete(session.get(Tenant, tenant.id))
    session.commit()
    session.close()


def _run(tenant_id: int) -> dict:
    """Run the task eagerly with Redis publishing mocked; capture alerts."""
    published: List[Any] = []

    def _capture(tid, event, payload):
        published.append((tid, event, payload))

    with patch.object(ml_mod, "publish_event", side_effect=_capture):
        result = ml_mod.generate_roas_alerts.apply(
            kwargs={"tenant_id": tenant_id}
        ).get()
    return {"result": result, "published": published}


class TestGenerateRoasAlerts:
    def test_roas_collapse_emits_alert(self, campaign_env):
        """A stable ~2.0 ROAS baseline with a today-collapse to ~0.2 is a
        strong negative z-score → a HIGH/CRITICAL alert is emitted (the exact
        case the broken signature could never produce)."""
        # 14 baseline days around revenue 200 (small spread), then today = 20.
        baseline = [
            {"spend": 100.0, "revenue": 200.0 + ((i % 5) - 2) * 6, "conversions": 10}
            for i in range(14)
        ]
        today = [{"spend": 100.0, "revenue": 20.0, "conversions": 1}]
        tid = campaign_env["tenant_id"]
        campaign_env["add_campaign"](baseline + today)

        out = _run(tid)

        assert out["result"]["alerts"] >= 1
        assert len(out["published"]) == out["result"]["alerts"]
        metrics = {p[2]["metric"] for p in out["published"]}
        assert "roas" in metrics
        for _, event, payload in out["published"]:
            assert event == "roas_alert"
            assert payload["severity"] in ("high", "critical")
            # AnomalyResult attributes must be read correctly (not dict keys).
            assert isinstance(payload["z_score"], float)
            assert "baseline" in payload

    def test_stable_series_runs_and_emits_no_alert(self, campaign_env):
        """A stable in-range series produces zero alerts but must still RUN to
        completion (the old code returned 0 by crashing on every campaign)."""
        stable = [
            {"spend": 100.0, "revenue": 200.0 + ((i % 5) - 2) * 4, "conversions": 10}
            for i in range(15)
        ]
        tid = campaign_env["tenant_id"]
        campaign_env["add_campaign"](stable)

        out = _run(tid)

        assert out["result"]["alerts"] == 0
        assert out["published"] == []

    def test_insufficient_history_is_skipped(self, campaign_env):
        """Fewer than 4 daily points can't yield a meaningful z-score → skip
        the campaign without error."""
        tid = campaign_env["tenant_id"]
        campaign_env["add_campaign"](
            [{"spend": 100.0, "revenue": 200.0, "conversions": 10}] * 3
        )

        out = _run(tid)

        assert out["result"]["alerts"] == 0


class TestFanOutDispatch:
    def test_run_all_tenants_dispatches_roas_alerts(self, campaign_env):
        """The beat fan-out must dispatch generate_roas_alerts per tenant, not
        just run_live_predictions (previously it was never dispatched)."""
        with (
            patch.object(ml_mod.run_live_predictions, "delay") as pred_delay,
            patch.object(ml_mod.generate_roas_alerts, "delay") as alert_delay,
        ):
            ml_mod.run_all_tenant_predictions()

        dispatched = {c.args[0] for c in alert_delay.call_args_list}
        assert campaign_env["tenant_id"] in dispatched
        # Both tasks fan out for the same tenants.
        assert alert_delay.call_count == pred_delay.call_count
