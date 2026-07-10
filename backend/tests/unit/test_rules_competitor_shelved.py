# =============================================================================
# Stratum AI - Rules + Competitor Intelligence Shelving Tests
# =============================================================================
"""
Tests for shelving Automation Rules and Competitor Intelligence behind flags
(Tier 2 flag-off).

The rules beat evaluator reads ``rule.conditions`` while the model stores flat
``condition_field/operator/value`` columns (AttributeError every 15 min), and
the competitor refresh worker fabricates spend/impressions/CTR with
``random.randint`` (no real source wired). Both surfaces are gated off for
launch: the router deps return 503 while the flag is off (the default), and the
beat entries are absent from the schedule.
"""

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.competitors import require_competitor_intel_enabled
from app.api.v1.endpoints.rules import require_automation_rules_enabled
from app.core.config import settings
from app.workers.celery_app import celery_app


# --- Automation Rules gate ---
async def test_rules_disabled_by_default_returns_503(monkeypatch):
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


# --- Shipped defaults must be off (crashing / fabricated surfaces) ---
def test_flags_default_off():
    assert settings.feature_automation_rules is False
    assert settings.feature_competitor_intel is False


# --- Beat schedule gating (flags default off => entries absent) ---
def test_beat_excludes_shelved_entries_when_flags_off():
    scheduled = set(celery_app.conf.beat_schedule.keys())
    assert "evaluate-active-rules" not in scheduled
    assert "refresh-competitor-data" not in scheduled
    # A healthy always-on entry stays scheduled (sanity: we didn't nuke beat).
    assert "sync-all-campaigns" in scheduled
