# =============================================================================
# Stratum AI - Knowledge Graph Shelving Tests
# =============================================================================
"""
Tests for gating the Knowledge Graph behind a feature flag (P1-6).

AGE is now provisioned (backend/Dockerfile.postgres) and the graph created
(migration 065), so the extension is no longer what holds this back — the
routes would resolve rather than 500.

The flag stays off for a second reason: the graph starts empty. A writer now
exists -- scripts/backfill_knowledge_graph.py -- but it is a manual run, so in
any environment where it has not been run the routes would turn a 503 into a
confidently empty answer, which is the worse of the two. The router-level gate
must keep returning 503 until the backfill has actually populated that
environment.
"""

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints.knowledge_graph import require_knowledge_graph_enabled
from app.core.config import settings


async def test_disabled_returns_503(monkeypatch):
    monkeypatch.setattr(settings, "feature_knowledge_graph", False)
    with pytest.raises(HTTPException) as exc:
        await require_knowledge_graph_enabled()
    assert exc.value.status_code == 503
    assert "AGE" in exc.value.detail


async def test_enabled_passes(monkeypatch):
    monkeypatch.setattr(settings, "feature_knowledge_graph", True)
    assert await require_knowledge_graph_enabled() is None


def test_flag_defaults_off():
    # Not because AGE is missing any more, and not because no writer exists --
    # scripts/backfill_knowledge_graph.py is that writer. Off because running
    # it is a deploy step, and until it has run against a given environment the
    # routes there answer "no problems found" when the truth is "no data has
    # ever been loaded". See app/core/config.py for the note.
    assert settings.feature_knowledge_graph is False
