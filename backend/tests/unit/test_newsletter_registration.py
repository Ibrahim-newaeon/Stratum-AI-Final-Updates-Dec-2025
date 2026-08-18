# =============================================================================
# Stratum AI - Newsletter Task Registration Tests
# =============================================================================
"""
Tests for registering the newsletter task module (Tier 3).

``newsletter_tasks`` defined ``send_newsletter_campaign`` (dispatched by the
send endpoint via .delay) and ``process_scheduled_campaigns`` (a beat sweep),
but the module was never in the Celery ``include`` — so the worker never
registered the tasks and the endpoint's dispatch silently vanished. The module
is now included, and the scheduled-send sweep is enabled: it runs every five
minutes, dispatching campaigns whose ``scheduled_at`` has arrived.

``enable_newsletter_beat`` is kept as an operator kill switch — set it false to
stop scheduled sends without touching the manual send endpoint, which dispatches
independently of the beat.
"""

from celery.schedules import crontab

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


def test_newsletter_beat_flag_defaults_on():
    # Scheduled sends ship; the flag remains as an operator kill switch.
    assert settings.enable_newsletter_beat is True


def test_newsletter_beat_scheduled():
    assert "process-scheduled-newsletters" in celery_app.conf.beat_schedule


def test_newsletter_beat_runs_every_five_minutes():
    """Five minutes, not every minute.

    The sweep queries for due campaigns on every tick and sends live email;
    per-minute granularity buys nothing for a scheduled newsletter and
    multiplies both the query load and the blast radius of a bad campaign.
    """
    entry = celery_app.conf.beat_schedule["process-scheduled-newsletters"]
    assert entry["task"] == "app.workers.newsletter_tasks.process_scheduled_campaigns"
    assert entry["schedule"] == crontab(minute="*/5")
