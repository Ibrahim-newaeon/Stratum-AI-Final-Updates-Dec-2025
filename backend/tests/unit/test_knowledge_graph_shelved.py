# =============================================================================
# Stratum AI - Knowledge Graph Shelving Tests
# =============================================================================
"""
Tests for gating the Knowledge Graph behind a feature flag (P1-6).

The KG depends on the Apache AGE Postgres extension. AGE is now provisioned
(backend/Dockerfile.postgres) and the graph created (migration 065), so the
flag ships on and survives as an operator kill switch. The router-level gate
must still return 503 when it is turned off.
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


def test_flag_defaults_on():
    # AGE is provisioned by the custom database image and the graph by
    # migration 065, so the shipped default is on.
    assert settings.feature_knowledge_graph is True
