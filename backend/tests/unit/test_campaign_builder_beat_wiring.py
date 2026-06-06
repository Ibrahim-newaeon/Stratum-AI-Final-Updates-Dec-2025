# =============================================================================
# Stratum AI - Campaign-Builder Beat Wiring Tests
# =============================================================================
"""
Tests for wiring the orphaned campaign-builder connector tasks (P1-2).

The tasks (ad-account sync, token refresh, connector health check) existed
but were never on the beat schedule, and the module wasn't in the Celery
`include` list. They hit live platform APIs, so they're gated behind
``enable_campaign_builder_beat`` (default off).
"""

from app.core.config import settings
from app.workers.celery_app import celery_app

_CAMPAIGN_BUILDER_ENTRIES = {
    "sync-all-ad-accounts",
    "refresh-expiring-tokens",
    "connector-health-check",
}


def test_flag_defaults_off():
    # Live platform calls must not auto-fire without explicit opt-in.
    assert settings.enable_campaign_builder_beat is False


def test_task_module_is_included():
    assert "app.workers.campaign_builder_tasks" in celery_app.conf.include


def test_beat_excludes_campaign_builder_when_flag_off():
    scheduled = set(celery_app.conf.beat_schedule.keys())
    assert _CAMPAIGN_BUILDER_ENTRIES.isdisjoint(scheduled)
