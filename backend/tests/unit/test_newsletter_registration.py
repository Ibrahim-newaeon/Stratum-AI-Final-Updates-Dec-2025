# =============================================================================
# Stratum AI - Newsletter Task Registration Tests
# =============================================================================
"""
Tests for registering the newsletter task module (Tier 3).

``newsletter_tasks`` defined ``send_newsletter_campaign`` (dispatched by the
send endpoint via .delay) and ``process_scheduled_campaigns`` (a beat sweep),
but the module was never in the Celery ``include`` — so the worker never
registered the tasks and the endpoint's dispatch silently vanished. The module
is now included; the scheduled-send beat is gated behind ``enable_newsletter_beat``
(default off) since it sends live email.
"""

from app.core.config import settings
from app.workers.celery_app import celery_app


def test_newsletter_module_in_include():
    assert "app.workers.newsletter_tasks" in celery_app.conf.include


def test_newsletter_tasks_registered():
    # Importing binds the @shared_task defs to the app registry.
    from app.workers.newsletter_tasks import (
        process_scheduled_campaigns,
        send_newsletter_campaign,
    )

    assert send_newsletter_campaign.name in celery_app.tasks
    assert process_scheduled_campaigns.name in celery_app.tasks


def test_newsletter_beat_flag_defaults_off():
    # The sweep sends live email — must not auto-fire without explicit opt-in.
    assert settings.enable_newsletter_beat is False


def test_newsletter_beat_absent_when_flag_off():
    assert "process-scheduled-newsletters" not in celery_app.conf.beat_schedule
