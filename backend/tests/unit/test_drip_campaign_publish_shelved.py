# =============================================================================
# Stratum AI - Drip + Campaign-Publish Flag-Off Tests
# =============================================================================
"""
Tests for shelving Drip Campaigns and Campaign Publish off for launch (Tier 2).

Drip has no execution engine (no drip Celery task; activate only flips a flag,
manual_trigger writes a "simulated" record), and campaign publish marks a draft
PUBLISHED with no platform call / no platform_campaign_id — a data-integrity
risk. Both are gated: the whole /drip-campaigns router 503s, and the single
publish endpoint 503s (draft CRUD stays available), while the flags are off
(the default).
"""

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.campaign_builder import require_campaign_publish_enabled
from app.api.v1.endpoints.drip_campaigns import require_drip_enabled
from app.core.config import settings


# --- Drip gate ---
async def test_drip_disabled_by_default_returns_503(monkeypatch):
    monkeypatch.setattr(settings, "feature_drip_campaigns", False)
    with pytest.raises(HTTPException) as exc:
        await require_drip_enabled()
    assert exc.value.status_code == 503


async def test_drip_enabled_passes(monkeypatch):
    monkeypatch.setattr(settings, "feature_drip_campaigns", True)
    assert await require_drip_enabled() is None


# --- Campaign publish gate ---
async def test_campaign_publish_disabled_by_default_returns_503(monkeypatch):
    monkeypatch.setattr(settings, "enable_campaign_publish", False)
    with pytest.raises(HTTPException) as exc:
        await require_campaign_publish_enabled()
    assert exc.value.status_code == 503


async def test_campaign_publish_enabled_passes(monkeypatch):
    monkeypatch.setattr(settings, "enable_campaign_publish", True)
    assert await require_campaign_publish_enabled() is None


# --- Shipped defaults must be off ---
def test_flags_default_off():
    assert settings.feature_drip_campaigns is False
    assert settings.enable_campaign_publish is False
