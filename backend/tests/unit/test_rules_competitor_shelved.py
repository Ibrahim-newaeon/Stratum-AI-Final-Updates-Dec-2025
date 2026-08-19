# =============================================================================
# Stratum AI - Rules + Competitor Intelligence Shelving Tests
# =============================================================================
"""
Tests for the Automation Rules and Competitor Intelligence feature gates.

Both shipped behind flags (Tier 2 flag-off). Both are now ON:

* **Automation Rules.** The gate existed because the beat evaluator read
  ``rule.conditions`` while the model stores flat
  ``condition_field/operator/value`` columns, raising AttributeError every
  15 minutes. ``ff6823ca`` (Tier 3) reconciled the evaluator with the flat
  schema — see ``test_rules_worker_eval.py``.
* **Competitor Intelligence.** The gate existed because the refresh worker
  fabricated spend/impressions/CTR with ``random.randint``.
  ``_apply_scan_result`` was rewritten to write honest nulls, and the API
  stopped serving the columns no source fills — see
  ``test_competitor_intel_ungated.py``, which pins the un-gating and the
  no-fabrication invariant.

The router dependency still returns 503 whenever a flag is off, which is what
the disabled-path tests below pin — both surfaces can still be switched off per
deployment without a code change.
"""

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.competitors import require_competitor_intel_enabled
from app.api.v1.endpoints.rules import require_automation_rules_enabled
from app.core.config import settings
from app.workers.celery_app import celery_app


# --- Automation Rules gate ---
async def test_rules_disabled_returns_503(monkeypatch):
    monkeypatch.setattr(settings, "feature_automation_rules", False)
    with pytest.raises(HTTPException) as exc:
        await require_automation_rules_enabled()
    assert exc.value.status_code == 503
    assert "Automation Rules" in exc.value.detail


async def test_rules_enabled_passes(monkeypatch):
    monkeypatch.setattr(settings, "feature_automation_rules", True)
    assert await require_automation_rules_enabled() is None


# --- Competitor Intelligence gate ---
async def test_competitor_disabled_by_default_returns_503(monkeypatch):
    monkeypatch.setattr(settings, "feature_competitor_intel", False)
    with pytest.raises(HTTPException) as exc:
        await require_competitor_intel_enabled()
    assert exc.value.status_code == 503
    assert "Competitor Intelligence" in exc.value.detail


async def test_competitor_enabled_passes(monkeypatch):
    monkeypatch.setattr(settings, "feature_competitor_intel", True)
    assert await require_competitor_intel_enabled() is None


# --- Shipped defaults ---
def test_rules_flag_defaults_on():
    """Rules ships: ff6823ca reconciled the evaluator with the flat schema."""
    assert settings.feature_automation_rules is True


def test_competitor_flag_defaults_on():
    """Competitor intel ships: the worker stopped inventing its numbers."""
    assert settings.feature_competitor_intel is True


# --- Beat schedule reflects the flags ---
def test_beat_includes_both_flagged_entries():
    scheduled = set(celery_app.conf.beat_schedule.keys())
    assert "evaluate-active-rules" in scheduled
    assert "refresh-competitor-data" in scheduled
    # A healthy always-on entry stays scheduled (sanity: we didn't nuke beat).
    assert "sync-all-campaigns" in scheduled
